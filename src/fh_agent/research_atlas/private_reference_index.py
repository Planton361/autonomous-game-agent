"""Pure declared-reference resolution and finite navigation; no scientific inference or IO."""

import json
import re
import string
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from .private_projection import (
    COMMIT,
    REPOSITORY,
    SHA256,
    ProjectionError,
    digest,
    private_path,
    yaml_text,
)
from .validator import Atlas
from .wiki_schema import EpistemicRecord, validate_wiki_records

OWNER = "research-wiki-derived"
REFERENCE_INDEX = PurePosixPath("indexes/declared-reference-index.yaml")
NAVIGATION = PurePosixPath("indexes/Declared Literature Navigation.md")
Resolution = Literal["resolved-public", "resolved-private", "unresolved-external-or-missing"]
Profile = Literal["ra2", "legacy"]
DocType = Literal[
    "dossier",
    "process",
    "topic",
    "reading_note",
    "synthesis",
    "search_record",
    "journal_entry",
    "paper",
    "finding",
    "research_question",
    "experiment_lead",
    "research_thread",
    "decision_draft",
]
Role = Literal[
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
]
Property = Literal[
    "paper_refs",
    "reading_note_refs",
    "finding_refs",
    "rq_refs",
    "process_refs",
    "source_refs",
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
]
ROLES: tuple[Role, ...] = (
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
)
PROPERTIES: tuple[Property, ...] = (
    "paper_refs",
    "reading_note_refs",
    "finding_refs",
    "rq_refs",
    "process_refs",
    "source_refs",
    *ROLES,
)
EXPECTED: dict[Property, tuple[str, ...]] = {
    "paper_refs": ("private:paper", "public:Paper"),
    "reading_note_refs": ("private:reading_note",),
    "finding_refs": ("private:finding", "public:Finding"),
    "rq_refs": ("private:research_question", "public:ResearchQuestion"),
    "process_refs": ("private:process",),
}
TypeCheck = Literal["match", "mismatch", "unresolved", "not-constrained"]
Diagnostic = Literal[
    "unresolved-reference",
    "wrong-target-type",
    "legacy-target-not-expandable",
    "outside-path-allowlist",
    "reading-source-not-matched",
]
View = Literal["component", "rq", "process"]
Direction = Literal["forward", "inverse"]
EdgeID = Literal[
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "E8",
    "E9",
    "A:paper_refs",
    "A:reading_note_refs",
    "A:finding_refs",
    "A:rq_refs",
    "A:process_refs",
    "A:source_refs",
    "A:research_direct_subject_refs",
    "A:research_method_or_baseline_refs",
    "A:research_measurement_relevance_refs",
    "A:research_project_transfer_refs",
    "A:research_adjacent_context_refs",
]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class SnapshotRecord(Closed):
    wiki_id: str
    doc_type: DocType
    profile: Profile
    record_version: int | None = Field(gt=0)
    references: dict[Property, tuple[str, ...]]


class Snapshot(Closed):
    records: tuple[SnapshotRecord, ...]


class Identity(Closed):
    identifier: str
    resolution_status: Resolution
    resolved_type: str | None
    record_version: int | None = Field(gt=0)
    profile: Profile | None


class Via(Closed):
    edge_id: EdgeID
    declaring_wiki_id: str
    declaring_record_version: int = Field(gt=0)
    declaring_doc_type: DocType
    property: Property
    role: Role | None
    declared_target_identifier: str
    declared_target_resolution_status: Resolution
    declared_target_type: str | None
    declared_target_record_version: int | None = Field(gt=0)
    declared_target_profile: Profile | None
    traversal_direction: Direction
    traverse_from: Identity
    traverse_to: Identity


class RowContent(Closed):
    row_kind: Literal["declared-reference", "navigation-path"]
    source_wiki_id: str
    source_record_version: int = Field(gt=0)
    source_doc_type: DocType
    originating_property: Property
    originating_role: Role | None
    navigation_start: Identity | None
    navigation_view: View | None
    recipe: str | None
    target_identifier: str
    target_resolution_status: Resolution
    resolved_target_type: str | None
    target_record_version: int | None = Field(gt=0)
    target_profile: Profile | None
    expected_target_types: tuple[str, ...]
    type_check: TypeCheck
    path_eligible: bool
    diagnostic_codes: tuple[Diagnostic, ...]
    path_kind: Literal["direct", "derived"]
    via: tuple[Via, ...]
    prerequisite_refs: tuple[Via, ...]


class Row(RowContent):
    row_id: SHA256


class ReferenceIndex(Closed):
    index_schema_version: Literal["1.0"] = "1.0"
    generated_by: Literal["research-wiki-derived"] = OWNER
    source_repository: Literal["Planton361/autonomous-game-agent"] = REPOSITORY
    source_commit: COMMIT
    source_atlas_schema: Literal["0.2"] = "0.2"
    private_input_fingerprint: SHA256
    rows: tuple[Row, ...]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def safe_literal(value: str) -> None:
    if (
        any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value)
        or value.startswith(("/", "\\"))
        or PureWindowsPath(value).drive
        or value.lower().startswith("file:")
        or ".." in re.split(r"[/\\]", value)
    ):
        raise ProjectionError("Unsafe reference literal; use an opaque non-file identifier")


def make_snapshot(properties: Iterable[Mapping[str, object]], atlas: Atlas) -> Snapshot:
    """Validate before selecting fields; never hide a malformed profile by filtering it."""
    try:
        validated = validate_wiki_records(properties, atlas.entities.keys())
    except ValueError as exc:
        raise ProjectionError(
            "Invalid private identity or profile; repair declared records"
        ) from exc
    records = []
    for record in validated:
        references = {}
        ra2 = isinstance(record, EpistemicRecord)
        if ra2:
            for prop in PROPERTIES:
                if prop == "source_refs" and record.doc_type not in {
                    "paper",
                    "reading_note",
                    "finding",
                }:
                    continue
                if prop not in type(record).model_fields:
                    continue
                values = tuple(sorted(set(getattr(record, prop))))
                for value in values:
                    safe_literal(value)
                references[prop] = values
        records.append(
            SnapshotRecord(
                wiki_id=record.wiki_id,
                doc_type=record.doc_type,
                profile="ra2" if ra2 else "legacy",
                record_version=record.record_version if ra2 else None,
                references=references,
            )
        )
    return Snapshot(records=tuple(sorted(records, key=lambda r: r.wiki_id)))


def fingerprint(snapshot: Snapshot) -> str:
    records = []
    for record in snapshot.records:
        data = record.model_dump(mode="json")
        if record.profile == "legacy":
            del data["references"]
        records.append(data)
    return digest(canonical({"fingerprint_schema_version": "1.0", "records": records}))


class Resolver:
    def __init__(self, atlas: Atlas, snapshot: Snapshot):
        self.atlas = atlas
        self.private = {r.wiki_id: r for r in snapshot.records}
        if (
            len(self.private) != len(snapshot.records)
            or self.private.keys() & atlas.entities.keys()
        ):
            raise ProjectionError("Duplicate or colliding reference identity")

    def resolve(self, identifier: str) -> Identity:
        if identifier in self.atlas.entities:
            return Identity(
                identifier=identifier,
                resolution_status="resolved-public",
                resolved_type=self.atlas.entities[identifier].type,
                record_version=None,
                profile=None,
            )
        if identifier in self.private:
            record = self.private[identifier]
            return Identity(
                identifier=identifier,
                resolution_status="resolved-private",
                resolved_type=record.doc_type,
                record_version=record.record_version,
                profile=record.profile,
            )
        return Identity(
            identifier=identifier,
            resolution_status="unresolved-external-or-missing",
            resolved_type=None,
            record_version=None,
            profile=None,
        )


def private_type(identity: Identity, kind: str) -> bool:
    return identity.profile == "ra2" and identity.resolved_type == kind


def paper(identity: Identity) -> bool:
    return private_type(identity, "paper") or (
        identity.resolution_status == "resolved-public" and identity.resolved_type == "Paper"
    )


def question(identity: Identity) -> bool:
    return private_type(identity, "research_question") or (
        identity.resolution_status == "resolved-public"
        and identity.resolved_type == "ResearchQuestion"
    )


def terminal_view(identity: Identity) -> View | None:
    if identity.resolution_status == "resolved-public" and identity.resolved_type == "Component":
        return "component"
    if question(identity):
        return "rq"
    if private_type(identity, "process"):
        return "process"
    return None


def type_check(prop: Property, target: Identity) -> TypeCheck:
    if target.resolution_status == "unresolved-external-or-missing":
        return "unresolved"
    if prop not in EXPECTED:
        return "not-constrained"
    namespace = "public" if target.resolution_status == "resolved-public" else "private"
    return "match" if f"{namespace}:{target.resolved_type}" in EXPECTED[prop] else "mismatch"


def e1(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type == "reading_note"
        and prop in {"paper_refs", "source_refs"}
        and paper(target)
    )


def e2(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type == "paper"
        and prop == "reading_note_refs"
        and private_type(target, "reading_note")
    )


def e3(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return source.doc_type == "finding" and prop == "source_refs" and paper(target)


def e4(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type == "reading_note"
        and prop == "finding_refs"
        and private_type(target, "finding")
    )


def e5(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type == "finding"
        and prop == "reading_note_refs"
        and private_type(target, "reading_note")
    )


def e6(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return source.doc_type in {"reading_note", "finding"} and prop == "rq_refs" and question(target)


def e7(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type == "research_question"
        and prop == "finding_refs"
        and private_type(target, "finding")
    )


def e8(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return source.doc_type == "process" and prop == "rq_refs" and question(target)


def e9(source: SnapshotRecord, prop: Property, target: Identity) -> bool:
    return (
        source.doc_type in {"paper", "reading_note", "finding"}
        and prop in ROLES
        and terminal_view(target) is not None
    )


def edge(
    resolver: Resolver,
    source: SnapshotRecord,
    prop: Property,
    target: Identity,
    edge_id: EdgeID,
    direction: Direction = "forward",
) -> Via:
    origin = resolver.resolve(source.wiki_id)
    return Via(
        edge_id=edge_id,
        declaring_wiki_id=source.wiki_id,
        declaring_record_version=source.record_version,
        declaring_doc_type=source.doc_type,
        property=prop,
        role=prop if prop in ROLES else None,
        declared_target_identifier=target.identifier,
        declared_target_resolution_status=target.resolution_status,
        declared_target_type=target.resolved_type,
        declared_target_record_version=target.record_version,
        declared_target_profile=target.profile,
        traversal_direction=direction,
        traverse_from=origin if direction == "forward" else target,
        traverse_to=target if direction == "forward" else origin,
    )


@dataclass(frozen=True)
class Hop:
    via: Via
    prerequisites: tuple[Via, ...] = ()


def classify(
    resolver: Resolver, source: SnapshotRecord, prop: Property, target: Identity
) -> tuple[EdgeID, Hop | None, tuple[Diagnostic, ...]]:
    check = type_check(prop, target)
    if check == "unresolved":
        return f"A:{prop}", None, ("unresolved-reference",)
    if check == "mismatch":
        return f"A:{prop}", None, ("wrong-target-type",)
    if target.profile == "legacy":
        return f"A:{prop}", None, ("legacy-target-not-expandable",)
    # Fixed edge predicates, not a graph traversal or a general reference-field interpreter.
    for edge_id, predicate, direction in (
        ("E1", e1, "inverse"),
        ("E2", e2, "forward"),
        ("E3", e3, "inverse"),
        ("E4", e4, "forward"),
        ("E5", e5, "inverse"),
        ("E6", e6, "forward"),
        ("E7", e7, "inverse"),
        ("E8", e8, "inverse"),
        ("E9", e9, "forward"),
    ):
        if not predicate(source, prop, target):
            continue
        prerequisites = ()
        if edge_id == "E2":
            reading = resolver.private[target.identifier]
            confirmation = [
                (field, ref)
                for field in ("paper_refs", "source_refs")
                for ref in reading.references.get(field, ())
            ]
            if len(confirmation) != 1 or confirmation[0][1] != source.wiki_id:
                return "E2", None, ("reading-source-not-matched",)
            field, ref = confirmation[0]
            prerequisites = (edge(resolver, reading, field, resolver.resolve(ref), "E1"),)
        return (
            edge_id,
            Hop(edge(resolver, source, prop, target, edge_id, direction), prerequisites),
            (),
        )
    return f"A:{prop}", None, ("outside-path-allowlist",)


@dataclass(frozen=True)
class NavigationPath:
    start: Identity
    prefix: str
    hops: tuple[Hop, ...] = ()

    @property
    def end(self) -> Identity:
        return self.hops[-1].via.traverse_to if self.hops else self.start

    def extend(self, hop: Hop, prefix: str | None = None) -> "NavigationPath | None":
        seen = {self.start.identifier, *(h.via.traverse_to.identifier for h in self.hops)}
        if (
            len(self.hops) >= 4
            or hop.via.traverse_from != self.end
            or hop.via.traverse_to.identifier in seen
        ):
            return None
        return NavigationPath(self.start, prefix or self.prefix, (*self.hops, hop))


def row_content(
    via: tuple[Via, ...],
    prerequisites: tuple[Via, ...],
    *,
    eligible: bool,
    diagnostics: tuple[Diagnostic, ...] = (),
    path: NavigationPath | None = None,
    view: View | None = None,
) -> RowContent:
    last = via[-1]
    target = last.traverse_to
    declared = Identity(
        identifier=last.declared_target_identifier,
        resolution_status=last.declared_target_resolution_status,
        resolved_type=last.declared_target_type,
        record_version=last.declared_target_record_version,
        profile=last.declared_target_profile,
    )
    recipe = None
    if path:
        family = {"component": "N-C", "rq": "N-Q", "process": "N-P"}[view]
        recipe = "/".join(
            [family, path.prefix, *[f"{v.edge_id}:{v.traversal_direction}" for v in via]]
        )
    return RowContent(
        row_kind="navigation-path" if path else "declared-reference",
        source_wiki_id=last.declaring_wiki_id,
        source_record_version=last.declaring_record_version,
        source_doc_type=last.declaring_doc_type,
        originating_property=last.property,
        originating_role=last.role,
        navigation_start=path.start if path else None,
        navigation_view=view,
        recipe=recipe,
        target_identifier=target.identifier,
        target_resolution_status=target.resolution_status,
        resolved_target_type=target.resolved_type,
        target_record_version=target.record_version,
        target_profile=target.profile,
        expected_target_types=EXPECTED.get(last.property, ()),
        type_check=type_check(last.property, declared),
        path_eligible=eligible,
        diagnostic_codes=diagnostics,
        path_kind="direct"
        if len(via) == 1 and last.traversal_direction == "forward"
        else "derived",
        via=via,
        prerequisite_refs=prerequisites,
    )


def build_index(atlas: Atlas, snapshot: Snapshot, commit: str) -> ReferenceIndex:
    resolver = Resolver(atlas, snapshot)
    rows: dict[str, Row] = {}
    outgoing: dict[tuple[str, str], list[Hop]] = {}

    def add(content: RowContent) -> None:
        row_id = digest(canonical(content.model_dump(mode="json")))
        row = Row(row_id=row_id, **content.model_dump())
        if row_id in rows and rows[row_id] != row:
            raise ProjectionError("Reference row identity collision")
        rows[row_id] = row

    for source in snapshot.records:
        if source.profile != "ra2":
            continue
        for prop, refs in sorted(source.references.items()):
            for ref in refs:
                target = resolver.resolve(ref)
                edge_id, hop, diagnostics = classify(resolver, source, prop, target)
                add(
                    row_content(
                        (edge(resolver, source, prop, target, edge_id),),
                        hop.prerequisites if hop else (),
                        eligible=hop is not None,
                        diagnostics=diagnostics,
                    )
                )
                if hop:
                    outgoing.setdefault((edge_id, hop.via.traverse_from.identifier), []).append(hop)

    def steps(path: NavigationPath, *edge_ids: str) -> Iterable[Hop]:
        for edge_id in edge_ids:
            yield from outgoing.get((edge_id, path.end.identifier), ())

    prefixes = [
        NavigationPath(resolver.resolve(identity), "K0")
        for identity in sorted(atlas.entities.keys() | resolver.private.keys())
        if paper(resolver.resolve(identity))
    ]
    anchors = tuple(prefixes)
    for anchor in anchors:
        for edge_ids, kind in ((("E1", "E2"), "K1"), (("E3",), "K2")):
            for hop in steps(anchor, *edge_ids):
                path = anchor.extend(hop, kind)
                if path:
                    prefixes.append(path)
    for reading in tuple(p for p in prefixes if p.prefix == "K1"):
        for hop in steps(reading, "E4", "E5"):
            path = reading.extend(hop, "K3")
            if path:
                prefixes.append(path)

    def navigation(path: NavigationPath, view: View) -> None:
        add(
            row_content(
                tuple(h.via for h in path.hops),
                tuple(p for h in path.hops for p in h.prerequisites),
                eligible=True,
                path=path,
                view=view,
            )
        )

    for prefix in prefixes:
        # E9 is terminal. A role target is never expanded, even when it is an RQ.
        for hop in steps(prefix, "E9"):
            path = prefix.extend(hop)
            if path:
                navigation(path, terminal_view(path.end))
        if prefix.prefix == "K0":
            continue
        for hop in steps(prefix, *(("E6",) if prefix.prefix == "K1" else ("E6", "E7"))):
            rq = prefix.extend(hop)
            if not rq:
                continue
            navigation(rq, "rq")
            for process_hop in steps(rq, "E8"):
                process = rq.extend(process_hop)
                if process:
                    navigation(process, "process")
    return ReferenceIndex(
        source_commit=commit,
        private_input_fingerprint=fingerprint(snapshot),
        rows=tuple(rows[k] for k in sorted(rows)),
    )


WARNING = (
    "Declared reference paths only. Roles belong to the named declaring record and are not "
    "inherited by the paper. These paths do not establish support, implementation evaluation "
    "or literature coverage. An empty view means no matching declared paths in this snapshot."
)
VIEW_NAMES: dict[View, str] = {
    "component": "Literature by Component — declared role paths (derived navigation)",
    "rq": "Literature by RQ — declared reference paths (derived navigation)",
    "process": "Literature by Process — declared reference paths (derived navigation)",
}


def plain(value: object) -> str:
    # Entity-encode punctuation before Markdown parsing: no table/link/HTML/autolink injection.
    return "".join(f"&#{ord(c)};" if c in string.punctuation else c for c in str(value))


def render_navigation(
    index: ReferenceIndex, atlas: Atlas, locators: Mapping[str, PurePosixPath]
) -> bytes:
    def link(identifier: str) -> str:
        relative = locators.get(identifier)
        if identifier in atlas.entities:
            relative = PurePosixPath("_generated/technical-atlas") / private_path(
                atlas.entities[identifier]
            )
        if relative is None:
            return plain(identifier)
        raw = str(relative)
        if (
            relative.is_absolute()
            or PureWindowsPath(raw).drive
            or "\\" in raw
            or ".." in relative.parts
            or not relative.parts
            or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in raw)
        ):
            raise ProjectionError("Unsafe navigation locator")
        target = "../../../" + "/".join(quote(part, safe="") for part in relative.parts)
        return f"[{plain(identifier)}]({target})"

    def chain(via: tuple[Via, ...]) -> str:
        return " ; ".join(
            f"{link(v.traverse_from.identifier)} → {link(v.traverse_to.identifier)} "
            f"({plain(v.edge_id)}, {plain(v.traversal_direction)}; declared by "
            f"{link(v.declaring_wiki_id)} v{v.declaring_record_version} "
            f"{plain(v.property)} → {plain(v.declared_target_identifier)})"
            for v in via
        )

    lines = [
        "---",
        yaml_text(
            {
                "generated_by": OWNER,
                "source_commit": index.source_commit,
                "private_input_fingerprint": index.private_input_fingerprint,
            }
        ).rstrip(),
        "---",
        "# Declared Literature Navigation",
        "",
    ]
    for view, title in VIEW_NAMES.items():
        lines += [
            "## " + title,
            "",
            WARNING,
            "",
            "| Paper / resolution | Target / type | Declaring record / revision | "
            "Originating property / role | Kind | Via / prerequisites | Row ID |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        selected = sorted(
            (r for r in index.rows if r.navigation_view == view),
            key=lambda r: (
                r.target_identifier,
                r.navigation_start.identifier,
                r.originating_property,
                r.source_wiki_id,
                r.row_id,
            ),
        )
        for row in selected:
            lines.append(
                "| "
                + " | ".join(
                    [
                        link(row.navigation_start.identifier)
                        + " / "
                        + plain(row.navigation_start.resolution_status),
                        link(row.target_identifier) + " / " + plain(row.resolved_target_type),
                        link(row.source_wiki_id) + f" / v{row.source_record_version}",
                        plain(row.originating_property)
                        + " / "
                        + plain(row.originating_role or "none"),
                        row.path_kind,
                        chain(row.via)
                        + (
                            " ; prerequisite: " + chain(row.prerequisite_refs)
                            if row.prerequisite_refs
                            else ""
                        ),
                        row.row_id,
                    ]
                )
                + " |"
            )
        if not selected:
            lines += ["", "No matching declared paths in this snapshot."]
        lines.append("")
    lines += [
        "## Direct Reference Audit",
        "",
        "Unresolved source references and wrong-type declarations remain here; "
        "no guessed identities.",
        "",
        "| Declaring record / revision | Property / role | Declared target | "
        "Resolution / actual type | Type check / eligible / diagnostics | "
        "Via / prerequisites | Row ID |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in index.rows:
        if row.row_kind != "declared-reference":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    link(row.source_wiki_id) + f" / v{row.source_record_version}",
                    plain(row.originating_property) + " / " + plain(row.originating_role or "none"),
                    link(row.target_identifier),
                    plain(row.target_resolution_status) + " / " + plain(row.resolved_target_type),
                    plain(row.type_check)
                    + " / "
                    + str(row.path_eligible)
                    + " / "
                    + plain(", ".join(row.diagnostic_codes)),
                    chain(row.via)
                    + (
                        " ; prerequisite: " + chain(row.prerequisite_refs)
                        if row.prerequisite_refs
                        else ""
                    ),
                    row.row_id,
                ]
            )
            + " |"
        )
    return ("\n".join(lines) + "\n").encode()


def render_index(index: ReferenceIndex) -> bytes:
    return yaml_text(index.model_dump(mode="json")).encode()
