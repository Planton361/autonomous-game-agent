"""Human-first G4 source inspection; resolver internals stay in collapsed audit."""

import json
import posixpath
from collections import Counter
from pathlib import PurePosixPath
from urllib.parse import quote

from .private_projection import yaml_text
from .research_presentation import literal, record_link
from .source_resolution import (
    DERIVED,
    SOURCE_DETAIL,
    RecordBinding,
    Resolution,
    SourceFamily,
    SourceIndex,
    SourceResolver,
    SourceVersion,
)
from .wiki_schema import EpistemicRecord

DIAGNOSTIC_LABELS = {
    "catalog-unavailable": "Project source catalog unavailable.",
    "unresolved-reference": "Exact source reference unresolved; no replacement selected.",
    "duplicate-exact-alias": "Conflicting exact alias bindings; no candidate selected.",
    "wrong-source-type": "Exact reference has the wrong source type; binding rejected.",
    "paper-family-count": "Paper requires one explicit source family; binding rejected.",
    "reading-paper-unavailable": "Exact authored Paper unavailable; no replacement selected.",
    "cross-family-version": (
        "Version does not have a resolved matching source family; binding rejected."
    ),
    "preferred-version-missing": "No preferred navigation version authored; no default selected.",
    "preferred-version-unresolved": "Preferred navigation version unresolved; no default selected.",
    "preferred-version-conflict": "Preferred navigation version conflicts; no default selected.",
    "preferred-version-cross-family": (
        "Preferred navigation version belongs to another family; preference rejected."
    ),
    "preferred-version-retracted": (
        "Preferred navigation version is retracted; preference is not a scientific endorsement."
    ),
    "preferred-version-withdrawn": (
        "Preferred navigation version is withdrawn; preference is not a scientific endorsement."
    ),
    "version-read-missing": "No exact version read declared.",
    "source-status-unknown": "Source status unknown.",
    "retracted": "Retracted version remains available for historical inspection.",
    "withdrawn": "Withdrawn version remains available for historical inspection.",
    "correction": "This version is a correction.",
    "erratum": "This version is an erratum.",
    "superseded": "An explicit superseding version exists.",
    "corrected": "An explicit correction exists for this version.",
    "erratum-exists": "An explicit erratum exists for this version.",
    "attachment-unavailable": "Attachment unavailable; no replacement selected.",
    "not-locally-available": "Source known but not locally available.",
    "availability-unknown": "Local availability unknown.",
}
RELATION_LABELS = {
    "revision_of": "revision of",
    "published_from": "published from",
    "corrects": "corrects",
    "erratum_for": "erratum for",
    "supersedes": "supersedes",
}


class SourceReader:
    """Labels navigate generated inspection, never a second editable source master."""

    def __init__(self, resolver: SourceResolver):
        self.resolver = resolver
        self.headings: dict[str, str] = {}
        catalog = resolver.catalog
        if catalog is not None:
            labels = {f.source_family_id: "Source family — " + f.title for f in catalog.families}
            labels.update(
                {
                    v.source_version_id: "Version — "
                    + resolver.family(v.source_family_ref).title
                    + " — "
                    + v.label
                    for v in catalog.versions
                }
            )
            counts = Counter(label.casefold() for label in labels.values())
            for identity, label in labels.items():
                self.headings[identity] = label + (
                    " — " + identity if counts[label.casefold()] > 1 else ""
                )

    def link(self, identity: str, label: str, page: PurePosixPath) -> str:
        relative = posixpath.relpath(str(DERIVED / SOURCE_DETAIL), start=str(page.parent))
        return (
            "["
            + literal(label)
            + "]("
            + quote(relative, safe="/.-_")
            + "#"
            + quote(self.headings[identity], safe="")
            + ")"
        )

    def family_link(self, family: SourceFamily, page: PurePosixPath) -> str:
        return self.link(family.source_family_id, family.bibliographic_label or family.title, page)

    def version_link(self, version: SourceVersion, page: PurePosixPath) -> str:
        return self.link(version.source_version_id, version.label, page)

    @staticmethod
    def diagnostics(result: Resolution) -> list[str]:
        return ["**Diagnostic:** " + DIAGNOSTIC_LABELS[c] for c in result.diagnostics]

    def read_label(self, binding: RecordBinding, page: PurePosixPath) -> str:
        read = binding.version_read
        if read is not None and read.status == "resolved":
            return self.version_link(self.resolver.version(read.target_ref), page)
        return "Unresolved exact version; authored provenance retained in Source detail / Audit"

    def summary(self, binding: RecordBinding, page: PurePosixPath) -> list[str]:
        resolver = self.resolver
        if binding.family.status != "resolved":
            lines = [
                "**Source:** " + binding.family.status + ".",
                *self.diagnostics(binding.family),
            ]
            if binding.version_read is not None:
                lines += [
                    "**Version read:** " + self.read_label(binding, page) + ".",
                    *self.diagnostics(binding.version_read),
                ]
            relative = posixpath.relpath(str(DERIVED / SOURCE_DETAIL), start=str(page.parent))
            lines += ["[Source detail / Audit](" + quote(relative, safe="/.-_") + ")."]
            return [item for line in lines for item in (line, "")]
        family = resolver.family(binding.family.target_ref)
        versions = sorted(
            (
                v
                for v in resolver.catalog.versions
                if v.source_family_ref == family.source_family_id
            ),
            key=lambda v: (v.label.casefold(), v.source_version_id),
        )
        preferred = resolver.preferred(family)
        lines = ["**Source:** " + self.family_link(family, page) + "."]
        if binding.version_read is not None:
            lines += [
                "**Version read:** " + self.read_label(binding, page) + ".",
                *self.diagnostics(binding.version_read),
            ]
        others = [
            v
            for v in versions
            if binding.version_read is None
            or v.source_version_id != binding.version_read.target_ref
        ]
        lines += [
            "**Other known versions:** "
            + (", ".join(self.version_link(v, page) for v in others) if others else "None declared")
            + "."
        ]
        if family.preferred_version_ref is not None:
            label = (
                self.version_link(resolver.version(preferred.target_ref), page)
                if preferred.status == "resolved"
                else preferred.status + " — no default selected"
            )
            lines += ["**Preferred for navigation:** " + label + "."]
        lines += self.diagnostics(preferred)
        focus_ref = (
            binding.version_read.target_ref
            if binding.version_read is not None and binding.version_read.status == "resolved"
            else preferred.target_ref
            if preferred.status == "resolved"
            else None
        )
        if focus_ref is not None:
            focus = resolver.version(focus_ref)
            lines += [
                "**Status — "
                + literal(focus.label)
                + ":** "
                + focus.status
                + "; local availability: "
                + focus.availability.replace("_", " ")
                + "."
            ]
        else:
            lines += ["**Status:** No resolved read or preferred version; inspect known versions."]
        for version in versions:
            codes = resolver.version_diagnostics(version)
            if codes:
                lines += [
                    "**Warning — "
                    + literal(version.label)
                    + ":** "
                    + " ".join(DIAGNOSTIC_LABELS[c] for c in codes)
                ]
        for result in binding.related_versions:
            if result.status != "resolved":
                lines += self.diagnostics(result)
        if binding.version_read is not None and binding.version_read.status == "resolved":
            lines += self.locator(resolver.version(binding.version_read.target_ref))
        lines += [
            (
                "Source metadata does not infer scientific invalidation or change "
                "Research review state."
            )
        ]
        return [item for line in lines for item in (line, "")]

    @staticmethod
    def locator(version: SourceVersion) -> list[str]:
        location = version.locator
        if location is None:
            return ["**Open source:** No authorized locator declared for this exact version."]
        lines = []
        if location.url:
            lines += [
                "**Open source — "
                + literal(version.label)
                + ":** [Open exact version]("
                + quote(location.url, safe=":/?=&%#@+;,-._~")
                + ")."
            ]
        if location.page or location.section:
            lines += [
                "**Exact source locator:** "
                + "; ".join(literal(v) for v in (location.page, location.section) if v)
                + "."
            ]
        return lines

    def detail(
        self,
        index: SourceIndex,
        records: tuple[EpistemicRecord, ...],
        locators: dict[str, PurePosixPath],
    ) -> bytes:
        page = DERIVED / SOURCE_DETAIL
        lines = [
            "# Source details",
            "",
            (
                "[Literature inspection](Literature%20Inspection.md) · [Research "
                "landscape](Research%20Landscape.md)"
            ),
            "",
            (
                "Private generated inspection of the authored project catalog. "
                "Source status is metadata; no scientific invalidation is inferred."
            ),
            "",
        ]
        catalog = self.resolver.catalog
        if catalog is None:
            lines += [
                (
                    "Project source catalog unavailable. No synthetic or adapter "
                    "catalog is substituted."
                ),
                "",
            ]
        elif not catalog.families:
            lines += ["No project source families are declared in this catalog snapshot.", ""]
        for family in (
            sorted(catalog.families, key=lambda f: (f.title.casefold(), f.source_family_id))
            if catalog
            else ()
        ):
            lines += [
                "## " + literal(self.headings[family.source_family_id]),
                "",
                "**Source family:** " + literal(family.bibliographic_label or family.title),
                "",
            ]
            preference = self.resolver.preferred(family)
            if family.preferred_version_ref is not None:
                label = (
                    self.version_link(self.resolver.version(preference.target_ref), page)
                    if preference.status == "resolved"
                    else preference.status + " — no default selected"
                )
                lines += ["**Preferred for navigation:** " + label + ".", ""]
            lines += [item for line in self.diagnostics(preference) for item in (line, "")]
            versions = sorted(
                (v for v in catalog.versions if v.source_family_ref == family.source_family_id),
                key=lambda v: (v.label.casefold(), v.source_version_id),
            )
            lines += ["### Version lineage", ""]
            relations = [
                (v, r)
                for v in versions
                for r in sorted(v.relations, key=lambda r: (r.relation, r.target_version_ref))
            ]
            if not relations:
                lines += ["No version relations declared; dates establish no lineage.", ""]
            for version, relation in relations:
                lines += [
                    "- "
                    + self.version_link(version, page)
                    + " — "
                    + RELATION_LABELS[relation.relation]
                    + " → "
                    + self.version_link(self.resolver.version(relation.target_version_ref), page)
                ]
            lines += ["", "### Papers and exact reading history", ""]
            by_id = {r.wiki_id: r for r in records}
            for binding in index.record_bindings:
                if binding.family.target_ref == family.source_family_id:
                    record = by_id[binding.wiki_id]
                    lines += [
                        "- "
                        + record_link(record, locators, page)
                        + (
                            " — **Version read:** " + self.read_label(binding, page)
                            if binding.doc_type == "reading_note"
                            else " — Paper bound to this source family"
                        )
                    ]
            lines += [""]
            for version in versions:
                lines += [
                    "## " + literal(self.headings[version.source_version_id]),
                    "",
                    "**Source family:** " + self.family_link(family, page) + ".",
                    "",
                    "**Exact version:** "
                    + literal(version.label)
                    + " ("
                    + version.kind.replace("_", " ")
                    + ").",
                    "",
                    "**Status:** "
                    + version.status
                    + "; "
                    + version.availability.replace("_", " ")
                    + ".",
                    "",
                ]
                for code in self.resolver.version_diagnostics(version):
                    lines += ["**Warning:** " + DIAGNOSTIC_LABELS[code], ""]
                lines += [item for line in self.locator(version) for item in (line, "")]
                for binding in index.record_bindings:
                    if (
                        binding.version_read is not None
                        and binding.version_read.target_ref == version.source_version_id
                    ):
                        lines += [
                            "**Read as this exact version:** "
                            + record_link(by_id[binding.wiki_id], locators, page)
                            + ".",
                            "",
                        ]
        lines += ["## Unresolved and conflicting references", ""]
        by_id = {r.wiki_id: r for r in records}
        for binding in index.record_bindings:
            problems = [
                binding.family,
                *binding.related_versions,
                *([binding.version_read] if binding.version_read is not None else []),
            ]
            for result in problems:
                if result.status != "resolved":
                    lines += [
                        "- "
                        + record_link(by_id[binding.wiki_id], locators, page)
                        + ": "
                        + " ".join(DIAGNOSTIC_LABELS[c] for c in result.diagnostics)
                    ]
        for result in index.alias_resolutions:
            if result.status == "conflict":
                lines += [
                    (
                        "- Conflicting exact alias bindings; no candidate selected. Exact "
                        "values are in Audit."
                    )
                ]
        lines += [
            "",
            "## Source detail / Audit",
            "",
            "> [!aga-audit]- Full source audit",
            (
                "> Exact identities, authored bindings, references, diagnostics "
                "and source-resolution fingerprint."
            ),
            ">",
            "> ```json",
        ]
        audit = json.dumps(
            index.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2
        )
        lines += ["> " + line for line in audit.splitlines()]
        lines += ["> ```", "", "[Return to Literature inspection](Literature%20Inspection.md)", ""]
        return (
            "---\n"
            + yaml_text(
                dict(generated_by="research-wiki-derived", source_resolution_schema_version="1.0")
            )
            + "---\n\n"
            + "\n".join(lines)
        ).encode()
