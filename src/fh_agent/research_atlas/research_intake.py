"""Read-only maintenance preflight over existing private authoring contracts.

No record creation, scientific assessment, new fingerprint domain or writer.
Diagnostics are local private output and must not be exported to GitHub.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .private_projection import (
    INDEX,
    OWNED_ROOT,
    OWNER,
    ProjectionError,
    authored_properties,
    digest,
    read_yaml,
    relative_target_path,
    utf8,
    validate_prior,
)
from .private_reference_index import (
    EXPECTED,
    TECHNICAL_TARGET_TYPES,
    Resolver,
    build_index,
    fingerprint,
    make_snapshot,
    type_check,
)
from .research_presentation import presentation_fingerprint
from .rq_presentation import RQReader
from .source_presentation import DIAGNOSTIC_LABELS, SourceReader
from .source_resolution import SourceCatalog, SourceResolver, load_catalog, source_fingerprint
from .validator import Atlas, load_registry
from .wiki_schema import EpistemicRecord, ResearchQuestion, validate_wiki_records
from .workspace_harness import WorkspaceError, check, resolve_context


@dataclass(frozen=True, order=True)
class Diagnostic:
    severity: str
    record: str
    field: str
    code: str
    action: str


@dataclass(frozen=True)
class IntakeReport:
    private_input_fingerprint: str
    presentation_input_fingerprint: str
    source_resolution_input_fingerprint: str
    diagnostics: tuple[Diagnostic, ...]

    @property
    def valid(self) -> bool:
        return not any(d.severity == "error" for d in self.diagnostics)


def inspect_records(
    atlas: Atlas,
    properties: list[dict],
    catalog: SourceCatalog | None,
    commit: str,
    *,
    previous_subjects: dict[str, dict] | None = None,
) -> IntakeReport:
    """Validate first, then diagnose exact declarations. Never modify inputs.

    previous_subjects is the existing digest-checked technical projection index,
    not an authoring database or inferred technical authority.
    """
    validated = validate_wiki_records(properties, atlas.entities.keys())
    records = tuple(r for r in validated if isinstance(r, EpistemicRecord))
    snapshot = make_snapshot(properties, atlas)
    resolver = Resolver(atlas, snapshot)
    source = SourceResolver(catalog)
    reader = RQReader(atlas, records, SourceReader(source))
    diagnostics: set[Diagnostic] = set()

    def add(severity: str, record: str, field: str, code: str, action: str) -> None:
        diagnostics.add(Diagnostic(severity, record, field, code, action))

    def reference(
        record: str, field: str, ref: str, kinds: set[str] | frozenset[str] | None = None
    ) -> None:
        target = resolver.resolve(ref)
        if target.resolution_status == "unresolved-external-or-missing":
            add(
                "error",
                record,
                field,
                "missing-reference",
                "Supply the exact referenced record; do not substitute by title.",
            )
        elif kinds is not None and target.resolved_type not in kinds:
            add(
                "error",
                record,
                field,
                "wrong-type-reference",
                "Use an exact record of the declared type: " + ", ".join(sorted(kinds)) + ".",
            )
        elif field in EXPECTED and type_check(field, target) == "mismatch":
            add(
                "error",
                record,
                field,
                "wrong-type-reference",
                "Repair the typed reference against the current validated snapshot.",
            )

    # Reuse the reference allowlist/type resolver; external source refs are
    # resolved separately by G4 and are not assumed missing private records.
    index = build_index(atlas, snapshot, commit)
    for row in index.rows:
        if row.row_kind != "declared-reference" or row.originating_property == "source_refs":
            continue
        reference(row.source_wiki_id, row.originating_property, row.target_identifier)

    for record in records:
        for context in getattr(record, "presentation_contexts", ()):
            for field, ref, kinds in (
                ("finding_ref", context.finding_ref, {"finding"}),
                ("reading_note_ref", context.reading_note_ref, {"reading_note"}),
            ):
                if ref is not None:
                    reference(record.wiki_id, "presentation_contexts." + field, ref, kinds)
        for location in getattr(record, "presentation_source_locations", ()):
            reference(
                record.wiki_id,
                "presentation_source_locations.reading_note_ref",
                location.reading_note_ref,
                {"reading_note"},
            )
        if record.document_maturity in {"superseded", "archived"}:
            add(
                "notice",
                record.wiki_id,
                "document_maturity",
                "historical-analysis",
                (
                    "Preserve history; explicitly select and review any replacement. No "
                    "successor is chosen."
                ),
            )
        for field, kinds in (
            ("search_refs", {"search_record"}),
            ("synthesis_refs", {"synthesis"}),
            ("decision_refs", {"decision_draft"}),
        ):
            for ref in getattr(record, field, ()):
                reference(record.wiki_id, field, ref, kinds)
        if not isinstance(record, ResearchQuestion) or record.epistemic_schema_version != "0.3":
            continue
        for ref in record.research_direct_subject_refs:
            reference(record.wiki_id, "research_direct_subject_refs", ref, TECHNICAL_TARGET_TYPES)
        if len(record.research_direct_subject_refs) > 1:
            add(
                "notice",
                record.wiki_id,
                "research_direct_subject_refs",
                "multi-subject-question",
                (
                    "Review each exact binding and its authored why-matters context "
                    "independently; no inheritance."
                ),
            )
        analysis = record.presentation_analysis
        if analysis is None:
            continue
        for row in analysis.literature_rows:
            reference(
                record.wiki_id,
                "presentation_analysis.literature_rows.paper_ref",
                row.paper_ref,
                {"paper"},
            )
            reference(
                record.wiki_id,
                "presentation_analysis.literature_rows.context_owner_ref",
                row.context_owner_ref,
                {"paper", "reading_note", "finding"},
            )
            reader.context(record, row)
        for row in analysis.nearest_work_rows:
            reference(
                record.wiki_id,
                "presentation_analysis.nearest_work_rows.paper_ref",
                row.paper_ref,
                {"paper"},
            )
            for ref in row.evidence_refs:
                reference(
                    record.wiki_id,
                    "presentation_analysis.nearest_work_rows.evidence_refs",
                    ref,
                    {"finding"},
                )
            reader.comparison_ok(record, row)
        for item in analysis.establishes:
            reference(
                record.wiki_id,
                "presentation_analysis.establishes.record_ref",
                item.record_ref,
                {"finding", "synthesis"},
            )
            reader.statement_ok(record, item.record_ref)
        reader.conclusion_ok(record)
        for message in sorted(reader.diagnostics):
            # The existing reader reports structural eligibility, never adequacy.
            add(
                "warning",
                record.wiki_id,
                "presentation_analysis",
                "reader-binding-unavailable",
                message + "; inspect exact selections, versions and human review provenance.",
            )
        reader.diagnostics.clear()

    source_index = source.index(commit, records)
    for binding in source_index.record_bindings:
        for field, resolution in [
            ("source_refs", binding.family),
            ("version_read", binding.version_read),
            *(("related_version_refs", r) for r in binding.related_versions),
        ]:
            if resolution is None:
                continue
            for code in resolution.diagnostics:
                add("warning", binding.wiki_id, field, code, DIAGNOSTIC_LABELS[code])
        read = binding.version_read
        if read and read.target_ref:
            version = source.version(read.target_ref)
            for code in source.version_diagnostics(version):
                add(
                    "warning",
                    binding.wiki_id,
                    "version_read",
                    code,
                    DIAGNOSTIC_LABELS[code]
                    + " Preserve the version actually read; human review determines consequences.",
                )
            family = source.family(version.source_family_ref)
            preference = source.preferred(family)
            if preference.target_ref and preference.target_ref != read.target_ref:
                add(
                    "notice",
                    binding.wiki_id,
                    "version_read",
                    "different-navigation-version",
                    (
                        "A different navigation version is declared. Preserve the exact version "
                        "read; authorize any new reading separately."
                    ),
                )

    if previous_subjects is not None:
        for identity, node in sorted(atlas.entities.items()):
            if node.type not in TECHNICAL_TARGET_TYPES:
                continue
            prior = previous_subjects.get(identity)
            if prior is None:
                add(
                    "notice",
                    identity,
                    "technical identity",
                    "new-technical-subject",
                    (
                        "Verify separate Registry approval; author only explicit question/context "
                        "bindings, then refresh/check."
                    ),
                )
            elif prior["display_name"] != node.name:
                add(
                    "notice",
                    identity,
                    "display name",
                    "renamed-technical-subject",
                    (
                        "Retain durable IDs and authored records; refresh generated labels/routes "
                        "and inspect links."
                    ),
                )

    return IntakeReport(
        fingerprint(snapshot),
        presentation_fingerprint(records),
        source_fingerprint(catalog, records),
        tuple(sorted(diagnostics)),
    )


def previous_subjects(vault: Path) -> dict[str, dict] | None:
    """Read only an intact prior generated index, with existing manifest checks."""
    root = vault / OWNED_ROOT
    prior = validate_prior(root)
    if not prior:
        return None
    item = prior.get(INDEX)
    path = relative_target_path(root, INDEX)
    if item is None or not path.is_file():
        raise ProjectionError(
            "Prior technical index missing; restore it before maintenance comparison"
        )
    data = path.read_bytes()
    props = read_yaml(utf8(data))
    if digest(data) != item.sha256 or props.get("generated_by") != OWNER:
        raise ProjectionError(
            "Prior technical index edited or owner marker lost; preserve or restore it"
        )
    return props["entries"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only private Research intake preflight; no scientific acceptance."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument(
        "--check-generated",
        action="store_true",
        help=(
            "Also run the existing zero-write workspace check; empty/unrefreshed "
            "output reports drift."
        ),
    )
    args = parser.parse_args(argv)
    checking_generated = False
    try:
        context = resolve_context(args.repo_root, args.vault_root)
        atlas = load_registry(context.repo_root / "docs/research-atlas")
        # Reuse discovery and closed-profile validation from the current writer.
        properties = authored_properties(context.vault_root, context.vault_root / "_generated")
        report = inspect_records(
            atlas,
            properties,
            load_catalog(context.vault_root),
            context.source_commit,
            previous_subjects=previous_subjects(context.vault_root),
        )
        if args.check_generated:
            checking_generated = True
            check(context.repo_root, context.vault_root)
        print(
            json.dumps(
                {
                    "source_commit": context.source_commit,
                    "structurally_valid": report.valid,
                    "scientific_acceptance": False,
                    **asdict(report),
                },
                sort_keys=True,
                indent=2,
            )
        )
        return 0 if report.valid else 2
    except (ValueError, OSError) as exc:
        # No values/bodies/private absolute paths in exception output. Chained
        # Pydantic locations aid local repair without exporting authored content.
        cause = exc
        while cause.__cause__ is not None:
            cause = cause.__cause__
        locations = (
            [".".join(map(str, e["loc"])) for e in cause.errors()]
            if hasattr(cause, "errors")
            else []
        )
        message = str(exc).lower()
        code = (
            "ownership-or-generated-drift"
            if any(
                word in message
                for word in ("owner", "edited", "drift", "unowned", "generated rq metadata")
            )
            else "preflight-failed"
        )
        action = (
            "Generated ownership/check failed. Preserve edited or unowned content; "
            "restore reviewed owner markers/output, then rerun workspace check. "
            "Do not overwrite authored work or adopt unknown files."
            if checking_generated and isinstance(exc, WorkspaceError)
            else "Inspect declared YAML/identity/type/privacy, source catalog and checkout. "
            "Preserve or restore edited/unowned outputs; never erase authored work."
        )
        print(
            json.dumps(
                {
                    "structurally_valid": False,
                    "scientific_acceptance": False,
                    "code": code,
                    "fields": sorted(locations),
                    "action": action,
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
