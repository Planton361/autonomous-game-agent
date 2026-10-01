"""Private declared-reference navigation and direct Bases; no scientific adjudication."""

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .assembly_scopes import (
    OBSERVE_COMPONENT_IDS,
    OBSERVE_SCOPE_RELATIVE_PATH,
    registry_content_revision,
    render_observe_scope,
)
from .private_projection import ANATOMY as TECHNICAL_ANATOMY
from .private_projection import (
    COMMIT,
    REPOSITORY,
    SHA256,
    ProjectionError,
    atomic_write,
    digest,
    git,
    inspect_owned,
    markdown_parts,
    no_symlink_boundary,
    private_link,
    private_path,
    read_yaml,
    target_path,
    unreadable_tree,
    utf8,
    yaml_text,
)
from .private_projection import DOMAIN_SLICE as TECHNICAL_DOMAIN_SLICE
from .private_projection import (
    HOME as TECHNICAL_HOME,
)
from .private_projection import (
    MAP as TECHNICAL_MAP,
)
from .private_projection import (
    OWNED_ROOT as TECHNICAL_ROOT,
)
from .private_projection import (
    project as technical_projection,
)
from .private_reference_index import (
    NAVIGATION,
    REFERENCE_INDEX,
    Identity,
    ReferenceIndex,
    Row,
    Snapshot,
    Via,
    build_index,
    component_navigation_rows,
    make_snapshot,
    render_index,
    render_navigation,
)
from .private_reference_index import (
    plain as reference_plain,
)
from .schema import PREFIXES, Evidence, Function, Relationship, TechnicalIdentity
from .validator import Atlas, AtlasSourceSchema, UniqueKeyLoader, load_registry
from .wiki_schema import EpistemicRecord, Paper, ReadingNote, validate_wiki_records

OWNER = "research-wiki-derived"
OWNED_ROOT = PurePosixPath("_generated/derived")
MANIFEST = PurePosixPath("manifest/direct-views.yaml")
TECHNICAL_BASE = PurePosixPath("bases/Technical Atlas Views.base")
DIRECT_BASE = PurePosixPath("bases/Research Wiki Direct Views.base")
INDEX = PurePosixPath("indexes/Direct Views Index.md")
PUBLIC_SOURCE = PurePosixPath("docs/research-atlas/Generated/Atlas Views.base")
DIRECT_SOURCE = PurePosixPath("docs/research-atlas/Wiki Views/Research Wiki Direct Views.base")
SOURCE_PATHS = (
    str(PUBLIC_SOURCE),
    "docs/research-atlas/Wiki Views",
    "docs/research-atlas/Process Seeds",
)
BASE_OWNER = f"# generated_by: {OWNER}\n"
STRICT_OWNERSHIP = "strict-bytes"
OBSIDIAN_BASE_OWNERSHIP = "obsidian-base-semantics"
OBSIDIAN_MANAGED_BASES = frozenset((TECHNICAL_BASE, DIRECT_BASE))

K3_HOME = PurePosixPath("indexes/Research Knowledge Home.md")
RESEARCH_LANDSCAPE = PurePosixPath("indexes/Research Landscape.md")
LITERATURE_INSPECTION = PurePosixPath("indexes/Literature Inspection.md")
HIERARCHY = PurePosixPath("indexes/Technical Hierarchy.md")
HIERARCHY_DIR = PurePosixPath("hierarchy")
MEMORY_WORKBENCH = PurePosixPath("workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL.md")
VERIFIER_WORKBENCH = PurePosixPath("workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER.md")
MEMORY_HUB_TECHNICAL = PurePosixPath(
    "workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Technical.md"
)
MEMORY_HUB_RESEARCH = PurePosixPath("workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL/Research.md")
VERIFIER_HUB_TECHNICAL = PurePosixPath(
    "workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Technical.md"
)
VERIFIER_HUB_RESEARCH = PurePosixPath(
    "workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER/Research.md"
)
LEGACY_MEMORY_WORKBENCH = PurePosixPath("workbenches/CMP-MEM-RETRIEVAL — Memory Retrieval.md")
LEGACY_VERIFIER_WORKBENCH = PurePosixPath(
    "workbenches/CMP-INDEPENDENT-VERIFIER — Independent Verifier.md"
)
K3_PRE_W07_PAYLOADS = frozenset(
    (
        K3_HOME,
        MEMORY_WORKBENCH,
        VERIFIER_WORKBENCH,
        MEMORY_HUB_TECHNICAL,
        MEMORY_HUB_RESEARCH,
        VERIFIER_HUB_TECHNICAL,
        VERIFIER_HUB_RESEARCH,
    )
)
W07_PAYLOADS = frozenset((RESEARCH_LANDSCAPE,))
W10_PAYLOADS = frozenset((LITERATURE_INSPECTION,))
OBSERVE_SCOPE_PAYLOADS = frozenset((OBSERVE_SCOPE_RELATIVE_PATH,))
OBSERVE_SCOPE_METADATA_MARKER = "<!-- observe-scope-generated-metadata\n"
K3_PAYLOADS = K3_PRE_W07_PAYLOADS | W07_PAYLOADS
K3_HUB_CHILD_PAYLOADS = frozenset(
    (
        MEMORY_HUB_TECHNICAL,
        MEMORY_HUB_RESEARCH,
        VERIFIER_HUB_TECHNICAL,
        VERIFIER_HUB_RESEARCH,
    )
)
LEGACY_K3_PAYLOADS = frozenset((LEGACY_MEMORY_WORKBENCH, LEGACY_VERIFIER_WORKBENCH))
K3_PRIOR_PAYLOADS = frozenset((K3_HOME, MEMORY_WORKBENCH, VERIFIER_WORKBENCH)) | LEGACY_K3_PAYLOADS
TECHNICAL_DETAIL_ROOT = PurePosixPath("workbenches/Technical Details")
OBSERVE_SCOPE = OBSERVE_SCOPE_RELATIVE_PATH
IDENTITY_PAGE_TYPES = {
    "CMP-PERCEPTION": "Component",
    "CMP-OBSERVATION-BUILDER": "Component",
    "CMP-PERCEPTION-UI-STATE": "Component",
    "DAT-OBSERVATION": "DataArtifact",
}
IDENTITY_PAGE_PATHS = {
    "CMP-PERCEPTION": PurePosixPath("identity-pages/Perception.md"),
    "CMP-OBSERVATION-BUILDER": PurePosixPath("identity-pages/Observation Builder.md"),
    "CMP-PERCEPTION-UI-STATE": PurePosixPath("identity-pages/UI State Classification.md"),
    "DAT-OBSERVATION": PurePosixPath("identity-pages/Observation.md"),
}
IDENTITY_PAGE_PAYLOADS = frozenset(IDENTITY_PAGE_PATHS.values())
IDENTITY_PAGE_SUBJECT_BY_PATH = {path: identity for identity, path in IDENTITY_PAGE_PATHS.items()}
SUPPORTED_IDENTITY_PAGE_TYPES = frozenset(
    {
        "System",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
        "MeasurementPoint",
        "Environment",
        "Function",
    }
)
IDENTITY_PAGE_SCHEMA_VERSION = "1.1"
IDENTITY_PAGE_METADATA_MARKER = "<!-- identity-page-generated-metadata\n"
TECHNICAL_DETAIL_ENDPOINT_TYPES = {
    "IF-MEM-CORTEX": "Interface",
    "CON-CORTEX-CONTEXT": "Contract",
    "DAT-RETRIEVAL-SNAPSHOT": "DataArtifact",
    "MEAS-RETRIEVAL-DELIVERY-001": "MeasurementPoint",
    "CON-VERIFIER-RESULT": "Contract",
    "DAT-OBSERVATION": "DataArtifact",
    "DAT-VISIBLE-OUTCOME": "DataArtifact",
}
TECHNICAL_DETAIL_IDS = tuple(TECHNICAL_DETAIL_ENDPOINT_TYPES)
TECHNICAL_DETAIL_RELATIONS = frozenset(
    {
        "part_of",
        "supplies",
        "consumes",
        "controls",
        "constrains",
        "proposes_to",
        "grounds",
        "executes",
        "observes",
        "verifies",
        "updates",
        "retrieves_from",
        "measured_at",
        "derived_from",
    }
)
TECHNICAL_DETAIL_PAYLOADS = frozenset(
    path
    for identity in TECHNICAL_DETAIL_IDS
    for path in (
        TECHNICAL_DETAIL_ROOT / f"{identity}.md",
        TECHNICAL_DETAIL_ROOT / f"{identity}.canvas",
    )
)
K3_VIEW_SCHEMA_VERSION = "1.6"

LANDSCAPE_PUBLIC_TYPES = (
    "ResearchQuestion",
    "ResearchThread",
    "Paper",
    "Finding",
    "ExperimentLead",
    "Decision",
)
LANDSCAPE_PRIVATE_TYPES = (
    "research_question",
    "research_thread",
    "search_record",
    "reading_note",
    "finding",
    "synthesis",
    "experiment_lead",
    "decision_draft",
    "paper",
    "dossier",
    "process",
    "topic",
    "journal_entry",
)
LANDSCAPE_PRIVATE_LABELS = {
    "research_question": "Research Question",
    "research_thread": "Research Thread",
    "search_record": "Search Record",
    "reading_note": "Reading Note",
    "finding": "Finding",
    "synthesis": "Synthesis",
    "experiment_lead": "Experiment Lead",
    "decision_draft": "Decision draft",
    "paper": "Paper",
    "dossier": "Dossier",
    "process": "Process",
    "topic": "Topic",
    "journal_entry": "Journal Entry",
}
LANDSCAPE_PRIVATE_STATUS_FIELDS = {
    "research_question": ("question_stage", "decision_state"),
    "experiment_lead": ("question_stage", "decision_state"),
    "finding": ("review_state",),
    "decision_draft": ("decision_record_state",),
}
V25_INDEX_PAYLOADS = frozenset((INDEX, NAVIGATION, K3_HOME, RESEARCH_LANDSCAPE, HIERARCHY))
V26_INDEX_PAYLOADS = V25_INDEX_PAYLOADS | W10_PAYLOADS
V27_INDEX_PAYLOADS = V26_INDEX_PAYLOADS

LITERATURE_RESEARCH_ROLE_FIELDS = (
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
)
LITERATURE_PAPER_FIELDS = (
    "source_refs",
    "doi",
    "url",
    "authors",
    "publication_year",
    "venue",
    "reading_note_refs",
    "related_version_refs",
    *LITERATURE_RESEARCH_ROLE_FIELDS,
)
LITERATURE_READING_NOTE_FIELDS = (
    "paper_refs",
    "source_refs",
    "version_read",
    "read_date",
    "reading_depth",
    "checked_sections",
    "finding_refs",
    "search_refs",
    "rq_refs",
    *LITERATURE_RESEARCH_ROLE_FIELDS,
)


def technical_detail_paths(identity: str) -> tuple[PurePosixPath, PurePosixPath]:
    """Return finite stable workbench and Canvas paths for a W05 endpoint."""
    if identity not in TECHNICAL_DETAIL_ENDPOINT_TYPES:
        raise ProjectionError(f"Unsupported W05 detail endpoint: {identity}")
    return (
        TECHNICAL_DETAIL_ROOT / f"{identity}.md",
        TECHNICAL_DETAIL_ROOT / f"{identity}.canvas",
    )


@dataclass(frozen=True, slots=True)
class ComponentHubPaths:
    overview: PurePosixPath
    technical: PurePosixPath
    research: PurePosixPath


COMPONENT_HUB_PATHS = {
    "CMP-MEM-RETRIEVAL": ComponentHubPaths(
        overview=MEMORY_WORKBENCH,
        technical=MEMORY_HUB_TECHNICAL,
        research=MEMORY_HUB_RESEARCH,
    ),
    "CMP-INDEPENDENT-VERIFIER": ComponentHubPaths(
        overview=VERIFIER_WORKBENCH,
        technical=VERIFIER_HUB_TECHNICAL,
        research=VERIFIER_HUB_RESEARCH,
    ),
}

_COMPONENT_LANE_RELATIONS = {
    "Interface": frozenset({"supplies", "consumes"}),
    "Contract": frozenset({"supplies", "consumes", "constrains", "executes", "verifies"}),
    "DataArtifact": frozenset(
        {"supplies", "consumes", "observes", "updates", "retrieves_from", "derived_from"}
    ),
    "MeasurementPoint": frozenset({"measured_at"}),
}


@dataclass(frozen=True, slots=True)
class ComponentHubModel:
    """Shared Hub inputs resolved from one Component's exact Registry relations."""

    subject_id: str
    paths: ComponentHubPaths
    technical_parent_ids: tuple[str, ...]
    child_component_ids: tuple[str, ...]
    presentation_domain_ids: tuple[str, ...]
    interface_ids: tuple[str, ...]
    contract_ids: tuple[str, ...]
    data_artifact_ids: tuple[str, ...]
    measurement_point_ids: tuple[str, ...]
    selected_ids: tuple[str, ...]
    direct_relationships: tuple[Relationship, ...]


@dataclass(frozen=True, slots=True)
class ComponentResearchModel:
    """One exact Component's Registry RQ edges and existing N-C index rows."""

    subject_id: str
    research_question_relationships: tuple[Relationship, ...]
    literature_paths: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class TechnicalDetailModel:
    """One exact endpoint scope shared by Markdown and native Canvas renderers."""

    endpoint_id: str
    originating_hub_ids: tuple[str, ...]
    direct_relationships: tuple[Relationship, ...]


@dataclass(frozen=True, slots=True)
class IdentityPageModel:
    """One human-first view over an exact, allowlisted Registry identity."""

    subject: TechnicalIdentity | Function
    path: PurePosixPath
    technical_parent_ids: tuple[str, ...]
    child_component_ids: tuple[str, ...]
    presentation_domain_ids: tuple[str, ...]
    direct_relationships: tuple[Relationship, ...]
    research_question_relationships: tuple[Relationship, ...]
    literature_paths: tuple[Row, ...]
    private_input_fingerprint: str


def _derived_link(path: PurePosixPath, label: str) -> str:
    return f"[[{OWNED_ROOT / path.with_suffix('')}|{label}]]"


def _canvas_link(path: PurePosixPath, label: str) -> str:
    return f"[[{OWNED_ROOT / path}|{label}]]"


def _technical_surface_link(path: PurePosixPath, label: str) -> str:
    return f"[[{TECHNICAL_ROOT / path.with_suffix('')}|{label}]]"


def _relative_markdown_link(source: PurePosixPath, destination: PurePosixPath, label: str) -> str:
    relative = posixpath.relpath(destination.as_posix(), start=source.parent.as_posix())
    return f"[{label}]({quote(relative, safe='/.-_')})"


def _observe_scope_generated_metadata(text: str) -> dict:
    """Read scope ownership metadata from legacy frontmatter or its hidden metadata comment."""
    properties, body = markdown_parts(text)
    if properties.get("generated_by") == OWNER:
        return properties
    _, marker, remainder = body.partition(OBSERVE_SCOPE_METADATA_MARKER)
    if not marker:
        return {}
    metadata_text, end_marker, _ = remainder.partition("\n-->")
    if not end_marker:
        return {}
    try:
        return read_yaml(metadata_text)
    except ProjectionError:
        return {}


def _identity_page_type_for_id(identity: str) -> str | None:
    return next(
        (
            kind
            for kind in SUPPORTED_IDENTITY_PAGE_TYPES
            if identity.startswith(PREFIXES[kind] + "-")
            and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", identity)
        ),
        None,
    )


def _identity_page_subject_for_path(relative: PurePosixPath) -> str | None:
    """Resolve only the legacy v2.9 ID-shaped path contract."""
    pilot = IDENTITY_PAGE_SUBJECT_BY_PATH.get(relative)
    if pilot is not None:
        return pilot
    if relative.parent != PurePosixPath("identity-pages") or relative.suffix != ".md":
        return None
    identity = relative.stem
    if identity in IDENTITY_PAGE_PATHS or identity in COMPONENT_HUB_PATHS:
        return None
    return identity if _identity_page_type_for_id(identity) is not None else None


_UNSAFE_IDENTITY_FILENAME = frozenset('/\\<>:"|?*#^[]')
_RESERVED_IDENTITY_FILENAME = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def _identity_filename_stem(name: str) -> tuple[str, bool]:
    """Return one portable, human-first basename and whether it needs an ID suffix."""
    normalized = unicodedata.normalize("NFKC", name)
    safe = "".join(
        " "
        if char in _UNSAFE_IDENTITY_FILENAME or unicodedata.category(char).startswith("C")
        else char
        for char in normalized
    )
    stem = " ".join(safe.split()).strip(" .")
    degenerate = not any(char.isalnum() for char in stem)
    if degenerate:
        stem = "Untitled"
    return stem, degenerate or stem.split(".", 1)[0].upper() in _RESERVED_IDENTITY_FILENAME


def _is_identity_page_path(relative: PurePosixPath) -> bool:
    if relative in {hub.overview for hub in COMPONENT_HUB_PATHS.values()}:
        return True
    return (
        relative.parent == PurePosixPath("identity-pages")
        and relative.suffix == ".md"
        and _identity_filename_stem(relative.stem)[0] == relative.stem
    )


def _identity_page_path(atlas: Atlas, identity: str) -> PurePosixPath | None:
    return identity_page_paths(atlas).get(identity)


def identity_page_paths(atlas: Atlas) -> dict[str, PurePosixPath]:
    """Resolve portable human filenames, with stable-ID suffixes only when needed."""
    supported = {}
    for identity, node in sorted(atlas.entities.items()):
        if (
            not isinstance(node, (TechnicalIdentity, Function))
            or node.type not in SUPPORTED_IDENTITY_PAGE_TYPES
        ):
            continue
        if _identity_page_type_for_id(identity) != node.type:
            raise ProjectionError(f"Identity Page subject has the wrong Registry type: {identity}")
        supported[identity] = node

    paths = {
        identity: path for identity, path in IDENTITY_PAGE_PATHS.items() if identity in supported
    }
    paths.update(
        (identity, hub.overview)
        for identity, hub in COMPONENT_HUB_PATHS.items()
        if identity in supported
    )
    reserved = {
        path.stem.casefold() for identity, path in paths.items() if identity in IDENTITY_PAGE_PATHS
    }
    reserved.update(
        _identity_filename_stem(supported[identity].name)[0].casefold()
        for identity in COMPONENT_HUB_PATHS
        if identity in supported
    )
    stems = {
        identity: _identity_filename_stem(node.name)
        for identity, node in supported.items()
        if identity not in paths
    }
    counts: dict[str, int] = {}
    for stem, _ in stems.values():
        key = stem.casefold()
        counts[key] = counts.get(key, 0) + 1
    for identity, (stem, forced_suffix) in stems.items():
        suffix = forced_suffix or stem.casefold() in reserved or counts[stem.casefold()] > 1
        filename = f"{stem} — {identity}.md" if suffix else f"{stem}.md"
        if len(filename.encode("utf-8")) > 240:
            raise ProjectionError(f"Identity Page human filename exceeds 240 bytes: {identity}")
        paths[identity] = PurePosixPath("identity-pages") / filename
    if len({str(path).casefold() for path in paths.values()}) != len(paths):
        raise ProjectionError("Identity Page path collision")
    return {identity: paths[identity] for identity in sorted(paths)}


def _identity_page_generated_metadata(text: str, relative: PurePosixPath) -> dict:
    """Read a valid, path-bound hidden owner marker from an Identity Page."""
    if (
        not _is_identity_page_path(relative)
        or text.startswith("---\n")
        or text.count(IDENTITY_PAGE_METADATA_MARKER) != 1
    ):
        return {}

    visible, _, remainder = text.partition(IDENTITY_PAGE_METADATA_MARKER)
    if not visible.startswith("# "):
        return {}
    metadata_text, end_marker, trailing = remainder.partition("\n-->")
    if not end_marker or trailing not in {"", "\n"}:
        return {}
    try:
        metadata = read_yaml(metadata_text)
    except ProjectionError:
        return {}

    required_fields = {
        "generated_by",
        "source_repository",
        "source_commit",
        "identity_page_schema_version",
        "identity_page_subject_id",
        "identity_page_registry_type",
        "source_registry_revision",
        "reference_index_schema_version",
        "private_input_fingerprint",
    }
    version = metadata.get("identity_page_schema_version")
    if version == "1.0":
        subject_id = _identity_page_subject_for_path(relative)
        if subject_id is None:
            return {}
    elif version == IDENTITY_PAGE_SCHEMA_VERSION:
        subject_id = metadata.get("identity_page_subject_id")
        required_fields.add("identity_page_path")
    else:
        return {}
    if not isinstance(subject_id, str) or _identity_page_type_for_id(subject_id) is None:
        return {}
    pilot_subject = {
        **IDENTITY_PAGE_SUBJECT_BY_PATH,
        **{hub.overview: identity for identity, hub in COMPONENT_HUB_PATHS.items()},
    }.get(relative)
    if pilot_subject is not None and subject_id != pilot_subject:
        return {}
    expected = {
        "generated_by": OWNER,
        "source_repository": REPOSITORY,
        "identity_page_schema_version": version,
        "identity_page_subject_id": subject_id,
        "identity_page_registry_type": _identity_page_type_for_id(subject_id),
        "reference_index_schema_version": "1.0",
    }
    if version == IDENTITY_PAGE_SCHEMA_VERSION:
        expected["identity_page_path"] = str(relative)
    if set(metadata) != required_fields or any(
        metadata.get(key) != value for key, value in expected.items()
    ):
        return {}
    if not isinstance(metadata.get("source_commit"), str) or not re.fullmatch(
        r"[a-f0-9]{40}", metadata["source_commit"]
    ):
        return {}
    if not isinstance(metadata.get("source_registry_revision"), str) or not re.fullmatch(
        r"sha256:[a-f0-9]{64}", metadata["source_registry_revision"]
    ):
        return {}
    if not isinstance(metadata.get("private_input_fingerprint"), str) or not re.fullmatch(
        r"[a-f0-9]{64}", metadata["private_input_fingerprint"]
    ):
        return {}
    return metadata


def _technical_link(atlas: Atlas, identity: str) -> str:
    try:
        node = atlas.entities[identity]
    except KeyError as exc:
        raise ProjectionError(f"K3 anchor is missing from the Registry: {identity}") from exc
    return private_link(private_path(node), f"{node.name} · {node.id}")


def _hierarchy_path(identity: str) -> PurePosixPath:
    if not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", identity):
        raise ProjectionError(f"Invalid hierarchy identity: {identity}")
    return HIERARCHY_DIR / f"{identity}.md"


def _hierarchy_link(atlas: Atlas, identity: str) -> str:
    node = atlas.entities[identity]
    return _derived_link(_hierarchy_path(identity), f"{node.name} · {node.id}")


def hierarchy_tree(commit: str, atlas: Atlas) -> dict[PurePosixPath, bytes]:
    """Render every technical identity using only child-to-parent part_of edges."""
    technical = {
        identity: node
        for identity, node in atlas.entities.items()
        if isinstance(node, TechnicalIdentity)
    }
    parents: dict[str, set[str]] = {identity: set() for identity in technical}
    children: dict[str, set[str]] = {identity: set() for identity in technical}
    groups: dict[str, set[str]] = {identity: set() for identity in technical}
    for edge in atlas.relationships:
        if edge.relation not in {"part_of", "presented_in_domain"}:
            continue
        if edge.source not in atlas.entities or edge.target not in atlas.entities:
            raise ProjectionError(
                f"Missing hierarchy relationship endpoint: {edge.source} -> {edge.target}"
            )
        if edge.relation == "presented_in_domain":
            if edge.source in groups:
                if atlas.entities[edge.target].type != "Domain":
                    raise ProjectionError("Presentation group is not a Domain")
                groups[edge.source].add(edge.target)
            continue
        if edge.source not in technical or edge.target not in technical:
            raise ProjectionError("part_of endpoint is not a technical identity")
        if edge.source == edge.target:
            raise ProjectionError(f"Self-parent part_of relationship: {edge.source}")
        if edge.target in parents[edge.source]:
            raise ProjectionError(f"Duplicate part_of relationship: {edge.source} -> {edge.target}")
        parents[edge.source].add(edge.target)
        children[edge.target].add(edge.source)

    def order(identity: str) -> tuple[str, str]:
        return (technical[identity].name.casefold(), identity)

    # Resolve all paths, retaining every valid parent. An active-stack hit is a cycle.
    paths: dict[str, tuple[tuple[str, ...], ...]] = {}
    active: set[str] = set()

    def paths_to(identity: str) -> tuple[tuple[str, ...], ...]:
        if identity in active:
            raise ProjectionError(f"Technical part_of cycle: {identity}")
        if identity in paths:
            return paths[identity]
        active.add(identity)
        result = (
            tuple(
                path + (identity,)
                for parent in sorted(parents[identity], key=order)
                for path in paths_to(parent)
            )
            if parents[identity]
            else ((identity,),)
        )
        active.remove(identity)
        paths[identity] = result
        return result

    page_paths = identity_page_paths(atlas)
    for identity in sorted(technical):
        paths_to(identity)

    systems = sorted((i for i, n in technical.items() if n.type == "System"), key=order)
    reachable = {
        path[-1] for identity in technical for path in paths[identity] if path[0] in systems
    }
    detached = sorted(technical.keys() - reachable, key=lambda i: (technical[i].type, *order(i)))

    def frontmatter(surface: str, identity: str | None = None) -> str:
        props = dict(
            generated_by=OWNER,
            source_repository=REPOSITORY,
            source_commit=commit,
            hierarchy_view_schema_version="1.0",
            hierarchy_surface=surface,
        )
        if identity is not None:
            props.update(
                hierarchy_subject=identity,
                technical_parents=sorted(parents[identity], key=order),
                technical_children=sorted(children[identity], key=order),
                presentation_domains=sorted(groups[identity]),
            )
            if parents[identity]:
                props["up"] = [
                    f"[[{OWNED_ROOT / _hierarchy_path(parent).with_suffix('')}]]"
                    for parent in sorted(parents[identity], key=order)
                ]
        return "---\n" + yaml_text(props) + "---\n"

    tree: dict[PurePosixPath, bytes] = {}
    entry = [
        "# Technical Hierarchy",
        "",
        "Registry `part_of` defines technical ancestry: child → parent. "
        "Domain grouping is a separate presentation view. Labels lead; stable IDs remain in links.",
        "",
        "## System roots",
        "",
    ]

    def branch(identity: str, depth: int) -> None:
        entry.append("  " * depth + "- " + _identity_page_human_link(atlas, identity, page_paths))
        for child in sorted(children[identity], key=order):
            branch(child, depth + 1)

    for system in systems:
        branch(system, 0)
    if not systems:
        entry.append("- No System root is declared.")
    entry += [
        "",
        "## Without a `part_of` path to a System",
        "",
        "These technical records are not assigned a System parent by this view. "
        "Other Registry relations and Domain grouping do not create ancestry.",
        "",
    ]
    for identity in detached:
        entry.append(
            f"- {_identity_page_human_link(atlas, identity, page_paths)} — "
            f"`{technical[identity].type}`"
        )
    if not detached:
        entry.append("- None.")
    entry += [
        "",
        "## Presentation Domains",
        "",
        "Domain links below are grouping aids only; they are never technical parents.",
        "",
    ]
    for identity, node in sorted(
        atlas.entities.items(), key=lambda item: (item[1].name.casefold(), item[0])
    ):
        if node.type != "Domain":
            continue
        members = sorted((i for i in technical if identity in groups[i]), key=order)
        entry.append(
            f"- {_technical_link(atlas, identity)}: "
            + (
                "; ".join(_identity_page_human_link(atlas, i, page_paths) for i in members)
                if members
                else "No members."
            )
        )
    entry += ["", f"{_derived_link(K3_HOME, 'Research Knowledge Home')}", ""]
    tree[HIERARCHY] = (frontmatter("entry") + "\n".join(entry)).encode()

    for identity in sorted(technical):
        node = technical[identity]
        parent_ids = sorted(parents[identity], key=order)
        child_ids = sorted(children[identity], key=order)
        lines = [
            f"# {node.name}",
            "",
            f"Stable ID: `{identity}` · Type: `{node.type}`",
            "",
            f"- **Hierarchy:** {_derived_link(HIERARCHY, 'Technical Hierarchy')}",
            f"- **Technical record:** {_technical_link(atlas, identity)}",
        ]
        hub_paths = COMPONENT_HUB_PATHS.get(identity)
        if hub_paths is not None:
            lines.append(
                f"- **Component Hub:** {_derived_link(hub_paths.overview, 'Open Overview')}"
            )
        elif identity in page_paths:
            lines.append(
                f"- **Identity Page:** {_derived_link(page_paths[identity], 'Open Identity Page')}"
            )
        lines.extend(["", "## Paths from System roots", ""])
        rooted = [path for path in paths[identity] if path[0] in systems]
        if rooted:
            for path in sorted(rooted, key=lambda p: tuple(order(i) for i in p)):
                lines.append("- " + " → ".join(_hierarchy_link(atlas, i) for i in path))
        else:
            lines.append("- No `part_of` path to a System is declared; no root is inferred.")
        lines += ["", "## Technical parents (`part_of`: this node → parent)", ""]
        lines += [f"- {_hierarchy_link(atlas, i)}" for i in parent_ids] or ["- None declared."]
        lines += ["", "## Technical children (`part_of`: child → this node)", ""]
        lines += [f"- {_hierarchy_link(atlas, i)}" for i in child_ids] or ["- None declared."]
        lines += [
            "",
            "## Presentation Domains (not technical ancestry)",
            "",
            "`presented_in_domain` is a view/navigation aid only.",
            "",
        ]
        lines += [f"- {_technical_link(atlas, i)}" for i in sorted(groups[identity])] or [
            "- None declared."
        ]
        lines += ["", f"{_derived_link(HIERARCHY, 'Back to Technical Hierarchy')}", ""]
        path = _hierarchy_path(identity)
        if path in tree:
            raise ProjectionError(f"Duplicate hierarchy output path: {path}")
        tree[path] = (frontmatter("technical-node", identity) + "\n".join(lines)).encode()
    return tree


def _markdown_table_cell(value: str) -> str:
    """Escape cell delimiters without changing ordinary Markdown links."""
    return re.sub(r"(?<!\\)\|", lambda _: r"\|", value)


def _k3_node(atlas: Atlas, identity: str):
    try:
        node = atlas.entities[identity]
    except KeyError as exc:
        raise ProjectionError(f"K3 anchor is missing from the Registry: {identity}") from exc
    if node.type not in {
        "System",
        "Domain",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
        "MeasurementPoint",
        "Evidence",
    }:
        raise ProjectionError(f"K3 anchor has an unsupported Registry type: {identity}")
    return node


def _k3_relationships(atlas: Atlas, identities: tuple[str, ...]) -> list[Relationship]:
    selected = set(identities)
    return sorted(
        (
            edge
            for edge in atlas.relationships
            if edge.source in selected and edge.target in selected
        ),
        key=lambda edge: (edge.relation, edge.source, edge.target),
    )


def _relationship_targets(atlas: Atlas, source: str, relation: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            edge.target
            for edge in atlas.relationships
            if edge.source == source and edge.relation == relation
        )
    )


def _component_hub_model(atlas: Atlas, subject_id: str) -> ComponentHubModel:
    """Build the common Hub input from exact, directly registered Component relations."""
    try:
        paths = COMPONENT_HUB_PATHS[subject_id]
    except KeyError as exc:
        raise ProjectionError(f"Unsupported Component Hub subject: {subject_id}") from exc
    subject = _k3_node(atlas, subject_id)
    if not isinstance(subject, TechnicalIdentity) or subject.type != "Component":
        raise ProjectionError(f"Component Hub subject is not a Component: {subject_id}")

    def ordered(identities: set[str] | tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                identities,
                key=lambda identity: (atlas.entities[identity].name.casefold(), identity),
            )
        )

    parents = set(_relationship_targets(atlas, subject_id, "part_of"))
    children = {
        edge.source
        for edge in atlas.relationships
        if edge.relation == "part_of"
        and edge.target == subject_id
        and atlas.entities[edge.source].type == "Component"
    }
    domains = set(_relationship_targets(atlas, subject_id, "presented_in_domain"))
    for identity in parents | children:
        if not isinstance(_k3_node(atlas, identity), TechnicalIdentity):
            raise ProjectionError("Component Hub part_of endpoint is not a technical identity")
    for identity in domains:
        if _k3_node(atlas, identity).type != "Domain":
            raise ProjectionError("Component Hub presentation endpoint is not a Domain")

    related: dict[str, set[str]] = {
        "Interface": set(),
        "Contract": set(),
        "DataArtifact": set(),
        "MeasurementPoint": set(),
    }
    direct_relationships = tuple(
        sorted(
            (
                edge
                for edge in atlas.relationships
                if edge.source == subject_id or edge.target == subject_id
            ),
            key=lambda edge: (edge.relation, edge.source, edge.target),
        )
    )
    for edge in direct_relationships:
        if edge.relation in {"part_of", "presented_in_domain"}:
            continue
        neighbor = edge.target if edge.source == subject_id else edge.source
        kind = atlas.entities[neighbor].type
        if kind in related and edge.relation in _COMPONENT_LANE_RELATIONS[kind]:
            related[kind].add(neighbor)

    interface_ids = ordered(related["Interface"])
    contract_ids = ordered(related["Contract"])
    data_artifact_ids = ordered(related["DataArtifact"])
    measurement_point_ids = ordered(related["MeasurementPoint"])
    selected = {
        subject_id,
        *parents,
        *children,
        *domains,
        *interface_ids,
        *contract_ids,
        *data_artifact_ids,
        *measurement_point_ids,
    }
    historical = _historical_technical_evidence(atlas, tuple(sorted(selected - domains)))
    selected.update(source.id for source, _ in historical)
    return ComponentHubModel(
        subject_id=subject_id,
        paths=paths,
        technical_parent_ids=ordered(parents),
        child_component_ids=ordered(children),
        presentation_domain_ids=ordered(domains),
        interface_ids=interface_ids,
        contract_ids=contract_ids,
        data_artifact_ids=data_artifact_ids,
        measurement_point_ids=measurement_point_ids,
        selected_ids=ordered(selected),
        direct_relationships=direct_relationships,
    )


def _component_research_model(
    atlas: Atlas, reference: ReferenceIndex, subject_id: str
) -> ComponentResearchModel:
    """Select only exact Registry RQ relations and existing N-C rows for one Hub subject."""
    if subject_id not in COMPONENT_HUB_PATHS:
        raise ProjectionError(f"Unsupported Component Hub subject: {subject_id}")
    subject = atlas.entities.get(subject_id)
    if not isinstance(subject, TechnicalIdentity) or subject.type != "Component":
        raise ProjectionError(f"Component Hub subject is not a Component: {subject_id}")
    questions = tuple(
        sorted(
            (
                edge
                for edge in atlas.relationships
                if edge.source == subject_id and edge.relation == "related_to_research_question"
            ),
            key=lambda edge: (
                atlas.entities[edge.target].name.casefold(),
                edge.target,
                edge.source,
            ),
        )
    )
    if any(atlas.entities[edge.target].type != "ResearchQuestion" for edge in questions):
        raise ProjectionError(
            "Component Research Question relation has a wrong Registry target type"
        )
    return ComponentResearchModel(
        subject_id=subject_id,
        research_question_relationships=questions,
        literature_paths=component_navigation_rows(reference, subject_id),
    )


def _render_orientation_header(
    *,
    title: str,
    surface: str,
    home: str,
    broader_context: str,
    research_fallback: str,
    stable_id: str | None = None,
    presentation_context: str | None = None,
    authority: str | None = None,
) -> list[str]:
    opened = surface if stable_id is None else f"{surface}; stable ID `{stable_id}`"
    authority_text = authority or (
        "Technical structure and status come from the Research Atlas. Current implementation "
        "truth requires current code plus executable or CI evidence; authored private Research "
        "remains separate."
    )
    lines = [
        f"# {title}",
        "",
        "## Orientation",
        "",
        f"- **Open:** {opened}.",
        f"- **Home:** {home}",
        f"- **Broader context:** {broader_context}",
    ]
    if presentation_context is not None:
        lines.append(f"- **Presentation group:** {presentation_context}")
    lines.extend(
        [
            f"- **Research / fallback:** {research_fallback}",
            "- **View type:** Generated, derived navigation projection; not an independent source "
            "of truth.",
            f"- **Authority:** {authority_text}",
            "",
        ]
    )
    return lines


def _render_hub_header(
    atlas: Atlas, hub: ComponentHubModel, view: Literal["overview", "technical", "research"]
) -> list[str]:
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"Component Hub subject is not technical: {hub.subject_id}")
    labels = (("overview", "Overview"), ("technical", "Technical"), ("research", "Research"))
    links = [
        f"**{label}**" if view == key else _derived_link(getattr(hub.paths, key), label)
        for key, label in labels
    ]
    return [
        f"# {subject.name}",
        "",
        f"*Component Hub · {view.title()}*  ",
        f"`{subject.id}`",
        "",
        "**Views:** " + " · ".join(links),
        "",
        "---",
        "",
    ]


def _render_hub_return_navigation(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    lines = ["## Return navigation", ""]
    lines.extend(
        [
            f"- {_derived_link(hub.paths.overview, 'Back to Overview')}",
            f"- {_technical_surface_link(TECHNICAL_ANATOMY, 'Agent Anatomy')}",
            f"- {_derived_link(HIERARCHY, 'Technical Hierarchy')}",
            f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}",
        ]
    )
    for identity in hub.presentation_domain_ids:
        lines.append(f"- {_technical_link(atlas, identity)} — Registry presentation Domain")
        if identity == "DOM-EVIDENCE-MEMORY":
            lines.append(
                "- "
                + _technical_surface_link(
                    TECHNICAL_DOMAIN_SLICE, "Evidence, Memory & Retrieval · Domain slice"
                )
            )
    lines.append("")
    return lines


def _render_presentation_context(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    subject_link = _technical_link(atlas, hub.subject_id)
    lines = ["## Navigation location and technical parentage", ""]
    lines.append(
        "**Navigation location** follows the Agent → presentation Domain → Component path; "
        "this is not technical ancestry."
    )
    if hub.presentation_domain_ids:
        for identity in hub.presentation_domain_ids:
            lines.append(
                f"- {_technical_surface_link(TECHNICAL_ANATOMY, 'Agent')} → "
                f"{_technical_link(atlas, identity)} → {subject_link}"
            )
    else:
        lines.append("- No Registry presentation Domain is declared; none is inferred.")
    lines.extend(["", "**Technical parent(s)** come only from outgoing Registry `part_of` edges."])
    if hub.technical_parent_ids:
        for identity in hub.technical_parent_ids:
            lines.append(f"- {subject_link} — `part_of` → {_technical_link(atlas, identity)}")
    else:
        lines.append("- No technical parent is declared in the Registry; none is inferred.")
    lines.append("")
    return lines


def _render_overview_status(subject: TechnicalIdentity) -> list[str]:
    status = subject.technical
    return [
        "## Current technical state",
        "",
        "These Registry axes stay separate; this view creates no combined status "
        "or maturity label.",
        "",
        "| Axis | Current Registry state | What it describes |",
        "| --- | --- | --- |",
        f"| Architecture authority | `{status.architecture_authority}` | "
        "Target or accepted basis. |",
        f"| Implementation status | `{status.implementation_status}` | "
        "Implementation declaration only. |",
        f"| Technical verification | `{status.verification_status}` | "
        "Technical verification only. |",
        "",
    ]


def _render_mechanism_summary(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    subject = _k3_node(atlas, hub.subject_id)
    lines = [
        "## Mechanism in the Registry",
        "",
        "A short orientation from exact direct Registry relations; this is not a technical map.",
        "",
    ]
    selected = [
        edge
        for edge in hub.direct_relationships
        if edge.relation not in {"part_of", "presented_in_domain"}
        and edge.source in hub.selected_ids
        and edge.target in hub.selected_ids
        and atlas.entities[edge.source].type != "Evidence"
        and atlas.entities[edge.target].type != "Evidence"
    ]
    for edge in selected:
        lines.append(
            f"- {_technical_link(atlas, edge.source)} — `{edge.relation}` → "
            f"{_technical_link(atlas, edge.target)}"
        )
    if not selected:
        lines.append(f"- No direct mechanism relation is registered for {subject.name}.")
    lines.append("")
    return lines


def _historical_technical_evidence(
    atlas: Atlas, identities: tuple[str, ...]
) -> list[tuple[Evidence, Relationship]]:
    selected = set(identities)
    result: list[tuple[Evidence, Relationship]] = []
    for edge in atlas.relationships:
        if edge.relation != "supports" or edge.target not in selected:
            continue
        source = atlas.entities[edge.source]
        if (
            isinstance(source, Evidence)
            and source.id.startswith("EVID-48-")
            and source.provenance_kind == "github_implementation"
        ):
            result.append((source, edge))
    return sorted(result, key=lambda item: (item[0].id, item[1].target))


def identity_page_model(
    atlas: Atlas,
    reference: ReferenceIndex,
    identity_id: str,
    *,
    page_paths: dict[str, PurePosixPath] | None = None,
) -> IdentityPageModel:
    """Resolve one supported identity from exact Registry facts."""
    subject = atlas.entities.get(identity_id)
    if subject is None or subject.type not in SUPPORTED_IDENTITY_PAGE_TYPES:
        raise ProjectionError(f"Unsupported Identity Page subject: {identity_id}")
    if (
        not isinstance(subject, (TechnicalIdentity, Function))
        or _identity_page_type_for_id(identity_id) != subject.type
    ):
        raise ProjectionError(f"Identity Page subject has the wrong Registry type: {identity_id}")
    path = (page_paths if page_paths is not None else identity_page_paths(atlas)).get(identity_id)
    if path is None:
        raise ProjectionError(f"Unsupported Identity Page subject: {identity_id}")

    direct_relationships = tuple(
        sorted(
            (edge for edge in atlas.relationships if identity_id in {edge.source, edge.target}),
            key=lambda edge: (edge.relation, edge.source, edge.target),
        )
    )
    parent_edges = tuple(
        edge
        for edge in direct_relationships
        if edge.relation == "part_of" and edge.source == identity_id
    )
    child_edges = tuple(
        edge
        for edge in direct_relationships
        if edge.relation == "part_of" and edge.target == identity_id
    )
    if subject.type in {"Component", "System"}:
        if any(
            atlas.entities[edge.target].type not in {"System", "Component"} for edge in parent_edges
        ):
            raise ProjectionError("Identity Page part_of parent is not a System or Component")
        if any(atlas.entities[edge.source].type != "Component" for edge in child_edges):
            raise ProjectionError("Identity Page part_of child is not a Component")
    elif parent_edges or child_edges:
        raise ProjectionError(
            "Identity Page does not infer Component containment for non-Component"
        )

    presentation_edges = tuple(
        edge
        for edge in direct_relationships
        if edge.relation == "presented_in_domain" and edge.source == identity_id
    )
    if any(atlas.entities[edge.target].type != "Domain" for edge in presentation_edges):
        raise ProjectionError("Identity Page presentation context is not a Registry Domain")
    question_edges = tuple(
        edge
        for edge in direct_relationships
        if edge.relation == "related_to_research_question" and edge.source == identity_id
    )
    if any(atlas.entities[edge.target].type != "ResearchQuestion" for edge in question_edges):
        raise ProjectionError("Identity Page Research Question relation has a wrong target type")

    def sort_ids(edges: tuple[Relationship, ...], attribute: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                {getattr(edge, attribute) for edge in edges},
                key=lambda item: (atlas.entities[item].name.casefold(), item),
            )
        )

    return IdentityPageModel(
        subject=subject,
        path=path,
        technical_parent_ids=sort_ids(parent_edges, "target"),
        child_component_ids=sort_ids(child_edges, "source"),
        presentation_domain_ids=sort_ids(presentation_edges, "target"),
        direct_relationships=direct_relationships,
        research_question_relationships=question_edges,
        literature_paths=(
            component_navigation_rows(reference, identity_id) if subject.type == "Component" else ()
        ),
        private_input_fingerprint=reference.private_input_fingerprint,
    )


def identity_page_models(
    atlas: Atlas,
    reference: ReferenceIndex,
    *,
    page_paths: dict[str, PurePosixPath] | None = None,
) -> tuple[IdentityPageModel, ...]:
    """Build current supported identities; expanded Hubs keep their preferred pages."""
    paths = page_paths if page_paths is not None else identity_page_paths(atlas)
    return tuple(
        identity_page_model(atlas, reference, identity, page_paths=paths)
        for identity in sorted(
            paths,
            key=lambda item: (atlas.entities[item].name.casefold(), item),
        )
    )


def _identity_page_entity_link(
    atlas: Atlas,
    identity: str,
    label: str,
    page_paths: dict[str, PurePosixPath] | None = None,
) -> str:
    try:
        node = atlas.entities[identity]
    except KeyError as exc:
        raise ProjectionError(
            f"Identity Page relationship endpoint is missing: {identity}"
        ) from exc
    path = (page_paths if page_paths is not None else identity_page_paths(atlas)).get(identity)
    if path is not None:
        return _derived_link(path, label)
    return private_link(private_path(node), label)


def _identity_page_human_link(
    atlas: Atlas, identity: str, page_paths: dict[str, PurePosixPath] | None = None
) -> str:
    node = atlas.entities[identity]
    return _identity_page_entity_link(atlas, identity, node.name, page_paths)


def _identity_page_audit_link(atlas: Atlas, identity: str) -> str:
    node = atlas.entities[identity]
    return private_link(private_path(node), f"{node.name} (`{node.id}`)")


def _identity_page_relation_label(atlas: Atlas, subject_id: str, edge: Relationship) -> str | None:
    """Return an accepted human label in the subject's exact edge direction."""
    if edge.source == subject_id:
        forward = True
    elif edge.target == subject_id:
        forward = False
    else:
        return None

    if edge.relation == "part_of":
        return "Part of" if forward else "Contains"
    if edge.relation == "consumes":
        return "Uses" if forward else "Used by"
    if edge.relation == "supplies":
        data_artifact_target = atlas.entities[edge.target].type == "DataArtifact"
        if forward:
            return "Produces" if data_artifact_target else "Provides to"
        return "Produced by" if data_artifact_target else "Provided by"
    if edge.relation == "presented_in_domain":
        return "Browse area" if forward else None
    if edge.relation == "supports":
        return "Supports" if forward else "Supported by"

    directional_labels = {
        "controls": ("Controls", "Controlled by"),
        "executes": ("Executes", "Executed by"),
        "grounds": ("Grounds", "Grounded by"),
        "measured_at": ("Measures", "Measured by"),
        "observes": ("Observes", "Observed by"),
        "proposes_to": ("Proposes to", "Receives proposals from"),
        "constrains": ("Constrains", "Constrained by"),
        "verifies": ("Verifies", "Verified by"),
    }
    labels = directional_labels.get(edge.relation)
    if labels is None:
        return None
    return labels[0] if forward else labels[1]


def _identity_page_human_relation_groups(
    atlas: Atlas, model: IdentityPageModel
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    groups: dict[str, set[str]] = {}
    for edge in model.direct_relationships:
        if edge.relation == "related_to_research_question":
            continue
        label = _identity_page_relation_label(atlas, model.subject.id, edge)
        if label in {None, "Supports", "Supported by"}:
            continue
        endpoint = edge.target if edge.source == model.subject.id else edge.source
        groups.setdefault(label, set()).add(endpoint)

    label_order = (
        "Part of",
        "Contains",
        "Uses",
        "Produces",
        "Produced by",
        "Used by",
        "Provides to",
        "Provided by",
        "Controls",
        "Controlled by",
        "Executes",
        "Executed by",
        "Grounds",
        "Grounded by",
        "Measures",
        "Measured by",
        "Observes",
        "Observed by",
        "Proposes to",
        "Receives proposals from",
        "Constrains",
        "Constrained by",
        "Verifies",
        "Verified by",
        "Browse area",
    )
    return tuple(
        (
            label,
            tuple(
                sorted(
                    groups[label],
                    key=lambda identity: _identity_page_relation_endpoint_order(
                        atlas, model.subject.id, label, identity
                    ),
                )
            ),
        )
        for label in label_order
        if groups.get(label)
    )


def _identity_page_relation_endpoint_order(
    atlas: Atlas, subject_id: str, label: str, identity: str
) -> tuple[int, str, str]:
    if subject_id == "DAT-OBSERVATION" and label == "Used by":
        observation_consumer_order = (
            "CMP-CORTEX",
            "CMP-MEMORY",
            "CMP-INDEPENDENT-VERIFIER",
            "CMP-TEMPORAL-STATE",
        )
        if identity in observation_consumer_order:
            return observation_consumer_order.index(identity), "", identity
    return (len(SUPPORTED_IDENTITY_PAGE_TYPES), atlas.entities[identity].name.casefold(), identity)


def _identity_page_supporting_evidence(
    atlas: Atlas, model: IdentityPageModel
) -> tuple[tuple[Evidence, Relationship], ...]:
    result: list[tuple[Evidence, Relationship]] = []
    for edge in model.direct_relationships:
        if edge.relation != "supports":
            continue
        evidence_id = edge.source if edge.target == model.subject.id else edge.target
        evidence = atlas.entities.get(evidence_id)
        if isinstance(evidence, Evidence):
            result.append((evidence, edge))
    return tuple(sorted(result, key=lambda item: (item[0].name.casefold(), item[0].id)))


def _identity_page_evidence_locator(evidence: Evidence) -> tuple[str, str, str]:
    if evidence.provenance_kind == "github_implementation":
        revision = evidence.ref or ""
        locator = evidence.path or ""
        if evidence.symbol:
            locator += f" · {evidence.symbol}"
        if evidence.line is not None:
            locator += f" · line {evidence.line}"
        source = evidence.repository or ""
    else:
        revision = evidence.version or ""
        source = evidence.document or ""
        locator = next(
            (
                value
                for value in (
                    evidence.section,
                    evidence.page,
                    evidence.figure,
                    evidence.table,
                    evidence.quote_or_paraphrase_location,
                )
                if value
            ),
            "",
        )
    return source, revision, locator


def _identity_page_evidence_kind(evidence: Evidence) -> str:
    return {
        "canonical_project_source": "Architecture source",
        "github_implementation": "Implementation source inspection",
        "primary_literature": "Primary literature",
        "scientific_project_artifact": "Scientific project artifact",
        "chat_historical_context": "Historical project context",
        "synthesis_inference": "Synthesis or inference",
        "project_decision": "Project decision record",
    }[evidence.provenance_kind]


def _identity_page_callout(
    kind: str, title: str, body: list[str], *, collapsed: bool = False
) -> list[str]:
    """Native Markdown only: titles and content carry meaning without a stylesheet."""
    return [f"> [!{kind}]{'-' if collapsed else ''} {title}", ">", *(f"> {line}" for line in body)]


def _identity_page_mermaid(atlas: Atlas, model: IdentityPageModel) -> list[str]:
    """A redundant view of direct parent/child and Uses/Produces facts only."""
    subject_id = model.subject.id
    edges: list[Relationship] = []
    for edge in model.direct_relationships:
        if subject_id not in {edge.source, edge.target}:
            continue
        parent_or_child = edge.relation == "part_of" and (
            (edge.source == subject_id and edge.target in model.technical_parent_ids)
            or (edge.target == subject_id and edge.source in model.child_component_ids)
        )
        data_flow = (
            edge.relation == "consumes"
            or (edge.relation == "supplies" and atlas.entities[edge.target].type == "DataArtifact")
        ) and all(
            isinstance(atlas.entities[identity], TechnicalIdentity)
            for identity in (edge.source, edge.target)
        )
        if parent_or_child or data_flow:
            edges.append(edge)
    identities = {subject_id} | {
        identity for edge in edges for identity in (edge.source, edge.target)
    }
    if len(identities) < 3 or len(identities) > 10:
        return []
    ordered_ids = [subject_id, *sorted(identities - {subject_id})]
    node_ids = {identity: f"n{number}" for number, identity in enumerate(ordered_ids)}

    def label(text: str) -> str:
        # Mermaid decimal entities keep Registry names from becoming diagram syntax/HTML.
        return "".join(
            char if char.isalnum() or char in " -_." else f"#{ord(char)};" for char in text
        )

    lines = [
        "### Local relation diagram",
        "",
        "The text summaries on this page retain every relation shown here.",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    lines.extend(
        f'    {node_ids[identity]}["{label(atlas.entities[identity].name)}"]'
        for identity in ordered_ids
    )
    for edge in sorted(edges, key=lambda edge: (edge.relation, edge.source, edge.target)):
        human_label = _identity_page_relation_label(atlas, edge.source, edge)
        lines.append(f'    {node_ids[edge.source]} -->|"{human_label}"| {node_ids[edge.target]}')
    return [*lines, "```", ""]


def _identity_page_location(
    atlas: Atlas, model: IdentityPageModel, page_paths: dict[str, PurePosixPath]
) -> list[str]:
    """Show every Registry ancestry path; never select a synthetic primary parent."""

    def human_link(identity: str) -> str:
        return _identity_page_human_link(atlas, identity, page_paths)

    parents: dict[str, set[str]] = {}
    for edge in atlas.relationships:
        if edge.relation == "part_of":
            parents.setdefault(edge.source, set()).add(edge.target)

    def order(identity: str) -> tuple[str, str]:
        return atlas.entities[identity].name.casefold(), identity

    def paths(identity: str, active: frozenset[str]) -> tuple[tuple[str, ...], ...]:
        if identity in active:
            raise ProjectionError(f"Identity Page part_of cycle: {identity}")
        direct = parents.get(identity, set())
        if not direct:
            return ((identity,),)
        return tuple(
            path + (identity,)
            for parent in sorted(direct, key=order)
            for path in paths(parent, active | {identity})
        )

    if model.subject.type == "Function":
        return [
            "**Location:** Functional context (non-containment).",
            "- " + _derived_link(K3_HOME, "Research Knowledge Home"),
            "Participants link back to their preferred Identity Pages below; "
            "no technical parent is asserted.",
        ]
    trails = paths(model.subject.id, frozenset())
    lines = ["**Location:**"]
    for trail in trails:
        segments = [human_link(identity) for identity in trail[:-1]]
        segments.append(model.subject.name)
        lines.append("- " + " → ".join(segments))
    if model.technical_parent_ids:
        lines.append(
            "**Back up to direct parent(s):** "
            + ", ".join(human_link(identity) for identity in model.technical_parent_ids)
        )
    elif model.subject.type == "Component":
        lines.append("No technical parent is registered in this snapshot; no ancestry is inferred.")
    return lines


def _identity_page_function_edges(
    model: IdentityPageModel, *, participants: bool = False
) -> tuple[Relationship, ...]:
    return tuple(
        edge
        for edge in model.direct_relationships
        if edge.relation == "contributes_to_function"
        and (edge.target if participants else edge.source) == model.subject.id
    )


def _identity_page_function_context(
    atlas: Atlas,
    model: IdentityPageModel,
    page_paths: dict[str, PurePosixPath],
    *,
    participants: bool = False,
) -> list[str]:
    title = "Explicit participants" if participants else "Functional Context"
    lines = [
        "",
        f"## {title}",
        "",
        "Authored Registry `contributes_to_function` only. Membership is non-containment: "
        "it creates no technical ancestry, authority subordination or Research relevance.",
    ]
    edges = _identity_page_function_edges(model, participants=participants)
    if not edges:
        lines.extend(
            [
                "",
                "No explicit functional participants are registered in this snapshot."
                if participants
                else "No explicit Function mapping is registered in this snapshot.",
            ]
        )
        return lines
    endpoint = "source" if participants else "target"
    edges = sorted(
        edges,
        key=lambda edge: (
            edge.functional_order is None,
            edge.functional_order if edge.functional_order is not None else 0,
            atlas.entities[getattr(edge, endpoint)].name.casefold(),
            getattr(edge, endpoint),
        ),
    )
    show_role = any(edge.functional_role is not None for edge in edges)
    show_order = any(edge.functional_order is not None for edge in edges)
    columns = ["Participant" if participants else "Function", "Stable ID / type"]
    if show_role:
        columns.append("Authored role")
    if show_order:
        columns.append("Authored order")
    lines.extend(
        ["", "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    )
    for edge in edges:
        identity = getattr(edge, endpoint)
        node = atlas.entities[identity]
        cells = [
            _identity_page_human_link(atlas, identity, page_paths),
            f"`{identity}` · {node.type}",
        ]
        if show_role:
            cells.append(
                reference_plain(edge.functional_role) if edge.functional_role is not None else "—"
            )
        if show_order:
            cells.append(str(edge.functional_order) if edge.functional_order is not None else "—")
        lines.append("| " + " | ".join(_markdown_table_cell(cell) for cell in cells) + " |")
    return lines


def render_identity_page(
    commit: str,
    atlas: Atlas,
    model: IdentityPageModel,
    *,
    registry_revision: str | None = None,
    page_paths: dict[str, PurePosixPath] | None = None,
) -> bytes:
    """Render the shared human-first page grammar over the exact Registry snapshot."""
    subject = model.subject
    paths = page_paths if page_paths is not None else identity_page_paths(atlas)
    if paths.get(subject.id) != model.path:
        raise ProjectionError("Identity Page model path is not the resolved ID-to-page mapping")

    def human_link(identity: str) -> str:
        return _identity_page_human_link(atlas, identity, paths)

    if subject.type not in SUPPORTED_IDENTITY_PAGE_TYPES:
        raise ProjectionError("Identity Page model type is unsupported")
    registry_revision_value = registry_revision or registry_content_revision(atlas)

    status = subject.technical if isinstance(subject, TechnicalIdentity) else None
    supporting_evidence = _identity_page_supporting_evidence(atlas, model)
    implementation_evidence = tuple(
        evidence
        for evidence, _edge in supporting_evidence
        if evidence.provenance_kind == "github_implementation"
    )
    relation_groups = _identity_page_human_relation_groups(atlas, model)
    technical_entry_text = {
        "System": "Architecture, behavior and registered technical connections.",
        "Component": "Responsibility, mechanism and registered technical connections.",
        "Interface": "Endpoint meaning and registered participants.",
        "Contract": "Execution meaning, participants and registered constraints.",
        "DataArtifact": "Meaning, registered producers and consumers.",
        "MeasurementPoint": "Measurement definition and registered instrumentation.",
        "Environment": "Environment boundary and registered technical context.",
        "Function": "Purpose, responsibility and explicit functional participants.",
    }[subject.type]
    research_entry_text = (
        "Direct Research attachment is deferred for Environment."
        if subject.type == "Environment"
        else "Resolved research records and limits of this snapshot."
    )
    lines = [
        f"# {subject.name}",
        "",
        *_identity_page_callout(
            "aga-hero",
            "Responsibility",
            [subject.description, "", f"*{subject.type} · Stable ID `{subject.id}`*"],
        ),
        "",
        *_identity_page_location(atlas, model, paths),
        "",
        *_identity_page_callout(
            "aga-nav",
            "On this page",
            [
                " · ".join(
                    f"[[#{anchor}|{label}]]"
                    for anchor, label in (
                        ("Overview / General", "Overview"),
                        ("Technical", "Technical"),
                        ("Research", "Research"),
                        ("Evidence / Provenance", "Evidence"),
                        ("Registry / Audit", "Audit"),
                    )
                )
            ],
        ),
        "",
        "## Overview / General",
        "",
    ]
    if model.presentation_domain_ids:
        lines.extend(
            [
                "**Browse area (presentation only):** "
                + ", ".join(human_link(identity) for identity in model.presentation_domain_ids),
                "",
            ]
        )
    state_lines = (
        [
            f"**Architecture:** {status.architecture_authority.replace('-', ' ').capitalize()}",
            "",
            f"**Implementation:** {status.implementation_status.replace('-', ' ').title()}",
            "",
            f"**Verification:** {status.verification_status.replace('-', ' ').title()}",
        ]
        if status is not None
        else [
            "**Type:** Function · explicit responsibility / process context.",
            "Membership is a Registry declaration; it does not establish runtime implementation.",
        ]
    )
    profile = _identity_page_callout("aga-status", "Current state", state_lines)
    lines.extend(_identity_page_callout("aga-grid", "At a glance", profile))
    lines.extend(
        [
            "",
            *_identity_page_callout(
                "aga-pillars",
                "Explore this identity",
                [
                    *_identity_page_callout(
                        "aga-technical-entry",
                        "TECHNICAL — How does it work?",
                        [
                            technical_entry_text,
                            "[[#Technical|Read Technical on this page]]",
                        ],
                    ),
                    "",
                    *_identity_page_callout(
                        "aga-research-entry",
                        "RESEARCH — What do we know or need to know?",
                        [
                            research_entry_text,
                            "[[#Research|Read Research on this page]]",
                        ],
                    ),
                ],
            ),
        ]
    )
    if subject.type == "Function":
        lines.extend(_identity_page_function_context(atlas, model, paths, participants=True))
    else:
        lines.extend(_identity_page_function_context(atlas, model, paths))
    if subject.type != "Function":
        lines.extend(["", "## Local Anatomy", ""])
    if subject.type in {"System", "Component"}:
        children = model.child_component_ids
        lines.append(f"Registered direct subcomponents: **{len(children)}**.")
        if not children:
            lines.append("No registered direct subcomponents in this snapshot.")
        else:
            lines.extend(["", "### Go deeper", ""])
            if len(children) >= 5:
                lines.extend(["| Direct Component | Responsibility |", "| --- | --- |"])
                for identity in children:
                    child = atlas.entities[identity]
                    lines.append(
                        f"| {_markdown_table_cell(human_link(identity))} | "
                        f"{reference_plain(child.description)} |"
                    )
            else:
                for identity in children:
                    child = atlas.entities[identity]
                    lines.extend(
                        [
                            *_identity_page_callout(
                                "aga-child",
                                child.name,
                                [human_link(identity), "", child.description],
                            ),
                            "",
                        ]
                    )
    elif subject.type != "Function":
        lines.append("Not Component containment; typed connections appear under Related Objects.")
    visual = _identity_page_mermaid(atlas, model)
    if visual:
        lines.extend(["", "## Visual Context", "", *visual])
    lines.extend(
        [
            "",
            "---",
            "",
            '<span class="aga-primary-section"></span>',
            "",
            "## Technical",
            "",
            f"### {technical_entry_text.rstrip('.')}",
            "",
        ]
    )
    lines.extend(
        [
            "Current implementation provenance beyond the registered source inspection "
            "is unavailable.",
            "Accepted design rationale / best-practice inputs are not attached in this slice.",
        ]
    )
    # Explicit accepted baseline limitations, never inferred from status or missing data.
    limitation_ids = {
        "CMP-PERCEPTION": {"EVID-48-OCR-LIMIT", "EVID-48-SPATIAL-LIMIT"},
        "CMP-PERCEPTION-UI-STATE": {"EVID-48-UI"},
    }.get(subject.id, set())
    limitations = [
        f"- {evidence.description} ({human_link(evidence.id)})"
        for evidence in implementation_evidence
        if evidence.id in limitation_ids
    ]
    if limitations:
        lines.extend(
            [
                "",
                *_identity_page_callout(
                    "warning",
                    "Current limitations — baseline source inspection",
                    limitations,
                    collapsed=True,
                ),
            ]
        )
    if implementation_evidence:
        lines.extend(["", "### Implementation notes", ""])
        for evidence in implementation_evidence:
            lines.append(f"- {evidence.description}")
    typed_classes = {"Interface", "Contract", "DataArtifact", "MeasurementPoint"}
    technical_groups = tuple(
        (
            label,
            tuple(
                identity
                for identity in identities
                if subject.type not in typed_classes
                and atlas.entities[identity].type not in typed_classes
            ),
        )
        for label, identities in relation_groups
        if label not in {"Part of", "Contains", "Browse area"}
    )
    for label, identities in technical_groups:
        if identities:
            lines.append(f"- **{label}:** " + ", ".join(human_link(i) for i in identities))
    hub = COMPONENT_HUB_PATHS.get(subject.id)
    if hub is not None:
        lines.extend(
            [
                "",
                "Auxiliary technical inspection (same identity):",
                "- " + _derived_link(hub.technical, "Technical auxiliary view"),
            ]
        )
    if subject.id == "DAT-OBSERVATION":
        detail_markdown, detail_canvas = technical_detail_paths(subject.id)
        lines.extend(
            [
                "",
                "### Further technical detail",
                "",
                "- " + _derived_link(detail_markdown, "Exact technical relations"),
                "- " + _canvas_link(detail_canvas, "Visual relation map"),
            ]
        )

    lines.extend(["", "## Related Objects", ""])
    related = tuple(
        (
            label,
            tuple(
                identity
                for identity in identities
                if subject.type in typed_classes or atlas.entities[identity].type in typed_classes
            ),
        )
        for label, identities in relation_groups
        if label not in {"Part of", "Contains", "Browse area"}
    )
    if any(identities for _, identities in related):
        for label, identities in related:
            if identities:
                lines.append(f"- **{label}:** " + ", ".join(human_link(i) for i in identities))
    else:
        lines.append("No direct typed Related Object relation is registered in this snapshot.")
    lines.extend(
        [
            "",
            "---",
            "",
            '<span class="aga-primary-section"></span>',
            "",
            "## Research",
            "",
            "**Scope / availability:** direct Registry Research Questions and declared "
            "Component literature paths only; richer attachment is outside this slice.",
        ]
    )
    if hub is not None:
        lines.extend(
            [
                "",
                "Auxiliary declared-path inspection (same identity):",
                "- " + _derived_link(hub.research, "Research auxiliary view"),
            ]
        )
    if subject.type == "Environment":
        lines.extend(
            _identity_page_callout(
                "aga-research",
                "Direct Research deferred",
                [
                    "Direct Environment Research attachment is deferred. This does not assess "
                    "literature coverage or research completeness."
                ],
            )
        )
    elif model.research_question_relationships:
        lines.extend(["### Related research questions", ""])
        for edge in model.research_question_relationships:
            lines.append(f"- {human_link(edge.target)}")
    else:
        lines.extend(
            _identity_page_callout(
                "aga-research",
                "Research state",
                [
                    "No direct research question is linked to this identity in the current "
                    "Registry snapshot. This does not assess research coverage or completion."
                ],
            )
        )
    if subject.type == "Component":
        lines.extend(["", "### Declared literature navigation", ""])
        if model.literature_paths:
            lines.append(
                f"{len(model.literature_paths)} declared Component path(s) resolve in the "
                "current Reference Index snapshot."
            )
            lines.append(f"- {_derived_link(NAVIGATION, 'Open declared literature navigation')}")
        else:
            lines.append(
                "No declared Component literature path resolves to this identity in the current "
                "Reference Index snapshot; literature coverage and research completeness have "
                "not been assessed."
            )
    elif subject.type != "Environment":
        lines.extend(
            [
                "",
                "### Research targeting",
                "",
                "The current Reference Index resolves Component-terminal paths. Direct "
                f"{subject.type} targeting is outside this slice; no inherited path is inferred. "
                "Literature coverage and research completeness have not been assessed.",
            ]
        )
    lines.extend(
        [
            "",
            "Existing research navigation:",
            f"- {_derived_link(NAVIGATION, 'Declared Literature Navigation')}",
            f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}",
            f"- {_derived_link(RESEARCH_LANDSCAPE, 'Research Landscape')}",
            "",
            "## Gap Analysis",
            "",
            "Not assessed / no authorized gap assessment attached.",
            "",
            "## Evidence / Provenance",
            "",
        ]
    )
    if supporting_evidence:
        for title, kinds in (
            (
                "Technical and decision support",
                {"github_implementation", "canonical_project_source", "project_decision"},
            ),
            (
                "Research and scientific support",
                {"primary_literature", "scientific_project_artifact"},
            ),
            ("Other provenance", {"chat_historical_context", "synthesis_inference"}),
        ):
            selected = [
                (evidence, edge)
                for evidence, edge in supporting_evidence
                if evidence.provenance_kind in kinds
            ]
            if not selected:
                continue
            lines.extend([f"### {title}", ""])
            for evidence, edge in selected:
                direction = _identity_page_relation_label(atlas, subject.id, edge)
                lines.append(
                    f"- **{direction} — {human_link(evidence.id)}** "
                    f"({_identity_page_evidence_kind(evidence).lower()}): "
                    f"{evidence.description}"
                )
            lines.append("")
    else:
        lines.append(
            "No direct Evidence relation is registered for this identity in the current "
            "snapshot; this does not assess evidence availability elsewhere."
        )
    lines.extend(
        [
            "",
            *_identity_page_callout(
                "aga-evidence",
                "Evidence meaning",
                [
                    "Implementation inspection, test-source inspection, normative sources, "
                    "and scientific evidence are distinct. Source inspection alone is not "
                    "live or measurement validation."
                ],
            ),
            "",
            "## Registry / Audit",
            "",
        ]
    )
    audit_payload_start = len(lines)
    lines.extend(
        [
            "### Exact Registry relations",
            "",
            "Raw direction and predicates are retained here from the current Registry snapshot.",
            "",
            "| Source | Predicate | Target |",
            "| --- | --- | --- |",
        ]
    )
    for edge in model.direct_relationships:
        lines.append(
            f"| {_identity_page_audit_link(atlas, edge.source)} | `{edge.relation}` | "
            f"{_identity_page_audit_link(atlas, edge.target)} |"
        )
    if not model.direct_relationships:
        lines.append("| — | — | No direct Registry relations are registered. |")
    lines.extend(
        [
            "",
            "### Evidence source locators",
            "",
            "| Evidence identity | Provenance kind | "
            "Source revision | Source and locator | Checked |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if supporting_evidence:
        for evidence, _edge in supporting_evidence:
            source, revision, locator = _identity_page_evidence_locator(evidence)
            lines.append(
                f"| {_identity_page_audit_link(atlas, evidence.id)} | "
                f"`{evidence.provenance_kind}` | `{revision}` | `{source}` · `{locator}` | "
                f"{evidence.checked_date.isoformat()} |"
            )
    else:
        lines.append("| — | — | — | No direct Evidence locator is registered. | — |")
    if model.literature_paths:
        lines.extend(
            [
                "",
                "### Declared literature-path audit",
                "",
                "Exact path recipes and index row identities remain here; the Reference Index is "
                "the path authority.",
                "",
                "| Path | Recipe | Index row | Path kind |",
                "| --- | --- | --- | --- |",
            ]
        )
        for number, row in enumerate(model.literature_paths, start=1):
            lines.append(
                f"| {number} | `{row.recipe or ''}` | `{row.row_id}` | `{row.path_kind}` |"
            )
    raw_record = private_link(private_path(subject), "Open raw Registry record")
    lines.extend(
        [
            "",
            f"- Raw Registry record: {raw_record}",
            f"- Public Registry source commit: `{commit}`",
            f"- Registry content revision: `{registry_revision_value}`",
            f"- Reference Index input fingerprint: `{model.private_input_fingerprint}`",
            "- Generated owner: `research-wiki-derived`; this is a derived navigation page, "
            "not an editable Registry record or a second identity.",
        ]
    )
    audit_payload = lines[audit_payload_start:]
    lines[audit_payload_start:] = _identity_page_callout(
        "aga-audit", "Registry / Audit", audit_payload, collapsed=True
    )
    lines.extend(["", "## Return Navigation", ""])
    for identity in model.technical_parent_ids:
        lines.append("- Back up to " + human_link(identity))
    if subject.type == "Function":
        for edge in _identity_page_function_edges(model, participants=True):
            lines.append("- Participant: " + human_link(edge.source))
    else:
        for edge in _identity_page_function_edges(model):
            lines.append("- Functional context: " + human_link(edge.target))
    lines.extend(
        [
            "- " + _technical_surface_link(TECHNICAL_ANATOMY, "Agent Anatomy"),
            "- " + _derived_link(HIERARCHY, "Technical Hierarchy"),
            "- " + _derived_link(K3_HOME, "Research Knowledge Home"),
        ]
    )
    metadata = {
        "generated_by": OWNER,
        "source_repository": REPOSITORY,
        "source_commit": commit,
        "identity_page_schema_version": IDENTITY_PAGE_SCHEMA_VERSION,
        "identity_page_subject_id": subject.id,
        "identity_page_registry_type": subject.type,
        "identity_page_path": str(model.path),
        "source_registry_revision": registry_revision_value,
        "reference_index_schema_version": "1.0",
        "private_input_fingerprint": model.private_input_fingerprint,
    }
    hidden_metadata = IDENTITY_PAGE_METADATA_MARKER + yaml_text(metadata) + "-->\n"
    return ("\n".join(lines) + "\n\n" + hidden_metadata).encode()


def technical_detail_models(atlas: Atlas) -> tuple[TechnicalDetailModel, ...]:
    """Resolve only the finite W04 technical-lane endpoints and their exact direct edges."""
    origins: dict[str, set[str]] = {}
    for hub_id in COMPONENT_HUB_PATHS:
        hub = _component_hub_model(atlas, hub_id)
        for identity in (
            *hub.interface_ids,
            *hub.contract_ids,
            *hub.data_artifact_ids,
            *hub.measurement_point_ids,
        ):
            origins.setdefault(identity, set()).add(hub_id)

    if origins.keys() != TECHNICAL_DETAIL_ENDPOINT_TYPES.keys():
        actual = ", ".join(sorted(origins)) or "none"
        expected = ", ".join(TECHNICAL_DETAIL_IDS)
        raise ProjectionError(
            "W05 endpoint set differs from the accepted finite Hub scope; "
            f"Registry endpoints: {actual}; bounded endpoints: {expected}"
        )

    models: list[TechnicalDetailModel] = []
    for identity in TECHNICAL_DETAIL_IDS:
        node = _k3_node(atlas, identity)
        expected_type = TECHNICAL_DETAIL_ENDPOINT_TYPES[identity]
        if not isinstance(node, TechnicalIdentity) or node.type != expected_type:
            raise ProjectionError(
                f"W05 endpoint {identity} is not the bounded Registry type {expected_type}"
            )
        historical_edges = {edge for _, edge in _historical_technical_evidence(atlas, (identity,))}
        relationships = tuple(
            sorted(
                (
                    edge
                    for edge in atlas.relationships
                    if identity in {edge.source, edge.target}
                    and (
                        (
                            edge.relation in TECHNICAL_DETAIL_RELATIONS
                            and isinstance(atlas.entities[edge.source], TechnicalIdentity)
                            and isinstance(atlas.entities[edge.target], TechnicalIdentity)
                        )
                        or edge in historical_edges
                    )
                ),
                key=lambda edge: (edge.relation, edge.source, edge.target),
            )
        )
        models.append(
            TechnicalDetailModel(
                endpoint_id=identity,
                originating_hub_ids=tuple(sorted(origins[identity])),
                direct_relationships=relationships,
            )
        )
    return tuple(models)


_DETAIL_TYPE_LABELS = {
    "System": "System",
    "Component": "Component",
    "Interface": "Interface",
    "Contract": "Contract",
    "DataArtifact": "Data Artifact",
    "MeasurementPoint": "Measurement Point",
    "Evidence": "Technical Evidence",
}
_DETAIL_TYPE_MARKERS = {
    "System": "⬟",
    "Component": "■",
    "Interface": "○",
    "Contract": "□",
    "DataArtifact": "▧",
    "MeasurementPoint": "◎",
    "Evidence": "◇",
}
_DETAIL_TYPE_COLORS = {
    "System": "3",
    "Component": "1",
    "Interface": "5",
    "Contract": "2",
    "DataArtifact": "4",
    "MeasurementPoint": "6",
    "Evidence": "4",
}


def _detail_node_key(atlas: Atlas, identity: str) -> tuple[int, str, str]:
    node = atlas.entities[identity]
    type_order = {
        "System": 0,
        "Component": 1,
        "Interface": 2,
        "Contract": 3,
        "DataArtifact": 4,
        "MeasurementPoint": 5,
        "Evidence": 6,
    }
    return (type_order[node.type], node.name.casefold(), identity)


def _canvas_node_id(identity: str) -> str:
    return "node-" + hashlib.sha256(f"w05-node\0{identity}".encode()).hexdigest()[:16]


def _canvas_edge_id(edge: Relationship) -> str:
    key = f"w05-edge\0{edge.source}\0{edge.relation}\0{edge.target}"
    return "edge-" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _canvas_card_text(atlas: Atlas, identity: str, focal_id: str) -> tuple[str, str]:
    node = atlas.entities[identity]
    role = (
        f"✦ FOCAL ENDPOINT · {_DETAIL_TYPE_LABELS[node.type]}"
        if identity == focal_id
        else f"{_DETAIL_TYPE_MARKERS[node.type]} {_DETAIL_TYPE_LABELS[node.type]}"
    )
    name = re.sub(r"[\r\n`*_[\]#<>|]", " ", node.name)
    name = " ".join(name.split())
    stable_type = "Evidence" if isinstance(node, Evidence) else node.type
    return (
        f"**{role}**\n\n{name}\n\n`{identity}` · Registry type `{stable_type}`\n\n"
        f"{_technical_link(atlas, identity)}",
        _DETAIL_TYPE_COLORS[node.type],
    )


def render_technical_detail_canvas(atlas: Atlas, model: TechnicalDetailModel) -> bytes:
    """Render an endpoint-centered native JSON Canvas with exact directed relations."""
    focal_id = model.endpoint_id
    neighbors = {
        edge.target if edge.source == focal_id else edge.source
        for edge in model.direct_relationships
    }
    incoming = {edge.source for edge in model.direct_relationships if edge.target == focal_id}
    outgoing = {edge.target for edge in model.direct_relationships if edge.source == focal_id}
    source_only = sorted(incoming - outgoing, key=lambda item: _detail_node_key(atlas, item))
    target_only = sorted(outgoing - incoming, key=lambda item: _detail_node_key(atlas, item))
    both = sorted(incoming & outgoing, key=lambda item: _detail_node_key(atlas, item))
    focal_x, focal_y = 700, 390
    positions: dict[str, tuple[int, int]] = {focal_id: (focal_x, focal_y)}

    def column(identities: list[str], x: int) -> None:
        start_y = focal_y - (len(identities) - 1) * 110
        for index, identity in enumerate(identities):
            positions[identity] = (x, start_y + index * 220)

    column(source_only, 40)
    column(target_only, 1360)
    for index, identity in enumerate(both):
        positions[identity] = (focal_x + index * 420, focal_y + 250)

    node_ids = {identity: _canvas_node_id(identity) for identity in neighbors | {focal_id}}
    ordered_nodes = sorted(neighbors, key=lambda item: _detail_node_key(atlas, item)) + [focal_id]
    nodes = []
    for identity in ordered_nodes:
        x, y = positions[identity]
        text, color = _canvas_card_text(atlas, identity, focal_id)
        nodes.append(
            {
                "id": node_ids[identity],
                "type": "text",
                "x": x,
                "y": y,
                "width": 390 if identity == focal_id else 350,
                "height": 190 if identity == focal_id else 170,
                "color": "5" if identity == focal_id else color,
                "text": text,
            }
        )
    edges = [
        {
            "id": _canvas_edge_id(edge),
            "fromNode": node_ids[edge.source],
            "toNode": node_ids[edge.target],
            "fromEnd": "none",
            "toEnd": "arrow",
            "label": edge.relation,
        }
        for edge in model.direct_relationships
    ]
    canvas = {
        "generated_by": OWNER,
        "canvas_view_schema_version": "1.0",
        "nodes": nodes,
        "edges": edges,
    }
    return (json.dumps(canvas, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def render_technical_detail_workbench(
    commit: str, atlas: Atlas, model: TechnicalDetailModel
) -> bytes:
    """Render shared Markdown identity, status, relation, provenance, and return context."""
    subject = _k3_node(atlas, model.endpoint_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"W05 endpoint is not technical: {model.endpoint_id}")
    _, canvas_path = technical_detail_paths(subject.id)
    status = subject.technical
    lines = [
        f"# {subject.name}",
        "",
        f"`{subject.id}` · Registry type `{subject.type}`",
        "",
        "## Orientation",
        "",
        f"- **Open object:** {_technical_link(atlas, subject.id)}",
        "- **Current technical context:** one endpoint-centered scope of direct technical "
        "Registry relations; no deeper decomposition is inferred.",
        "- **Originating Component Hub(s):**",
    ]
    for hub_id in model.originating_hub_ids:
        paths = COMPONENT_HUB_PATHS[hub_id]
        lines.append(
            f"  - {_technical_link(atlas, hub_id)} · "
            f"{_derived_link(paths.overview, 'Hub Overview')} · "
            f"{_derived_link(paths.technical, 'Hub Technical view')}"
        )
    component_ids = sorted(
        {
            identity
            for edge in model.direct_relationships
            for identity in (edge.source, edge.target)
            if identity != subject.id and atlas.entities[identity].type == "Component"
        },
        key=lambda identity: _detail_node_key(atlas, identity),
    )
    lines.extend(["", "### Direct Component context", ""])
    if component_ids:
        lines.extend(f"- {_technical_link(atlas, identity)}" for identity in component_ids)
    else:
        lines.append("- No direct Component relation is registered in this scope.")
    lines.extend(
        [
            "",
            "## Technical status axes — kept separate",
            "",
            "These are independent Registry fields; this workbench creates no combined score.",
            "",
            "| Axis | Current Registry state | Boundary |",
            "| --- | --- | --- |",
            f"| Architecture authority | `{status.architecture_authority}` | "
            "Authority classification only. |",
            f"| Implementation status | `{status.implementation_status}` | "
            "Implementation declaration only. |",
            f"| Technical verification | `{status.verification_status}` | "
            "Technical verification only. |",
            "",
        ]
    )
    if subject.type == "MeasurementPoint":
        lines.extend(
            [
                "## Measurement boundary",
                "",
                "This MeasurementPoint identifies a registered technical measurement target "
                "relation only.",
                "",
                "- Measurement validity: **not established here**.",
                "- Scientific evidence or effect: **not established here**.",
                "- Accepted scientific claim: **none created or implied**.",
                "",
            ]
        )
    evidence_edges = [
        edge
        for edge in model.direct_relationships
        if atlas.entities[edge.source].type == "Evidence"
    ]
    lines.extend(
        [
            "## Evidence / implementation provenance",
            "",
            "Only the existing accepted historical technical Evidence selection is shown. "
            "It is implementation provenance, not scientific evidence or claim promotion.",
            "",
        ]
    )
    if evidence_edges:
        for edge in evidence_edges:
            lines.append(
                f"- {_technical_link(atlas, edge.source)} — `{edge.relation}` → "
                f"{_technical_link(atlas, edge.target)}."
            )
    else:
        lines.append("- No accepted historical technical Evidence relation is selected.")
    lines.extend(
        [
            "",
            "## Exact direct Registry relations",
            "",
            "Each row preserves Registry source → relation → target direction. Canvas edges "
            "encode this same curated set; no reverse meaning is inferred.",
            "",
        ]
    )
    if model.direct_relationships:
        for edge in model.direct_relationships:
            lines.append(
                f"- {_technical_link(atlas, edge.source)} — `{edge.relation}` → "
                f"{_technical_link(atlas, edge.target)}"
            )
    else:
        lines.append("- No direct technical Registry relations are registered for this endpoint.")
    lines.extend(
        [
            "",
            "## Scoped Canvas map",
            "",
            f"- {_canvas_link(canvas_path, 'Open the matching native Canvas map')}",
            "- The Canvas is a derived visualization, not technical authority.",
            "",
            "## Return navigation",
            "",
        ]
    )
    for hub_id in model.originating_hub_ids:
        paths = COMPONENT_HUB_PATHS[hub_id]
        lines.append(f"- {_derived_link(paths.overview, 'Back to Hub Overview')}")
        lines.append(f"- {_derived_link(paths.technical, 'Back to Hub Technical view')}")
    lines.extend(
        [
            f"- {_derived_link(HIERARCHY, 'Technical Hierarchy')}",
            f"- {_technical_surface_link(TECHNICAL_ANATOMY, 'Agent Anatomy')}",
            f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}",
            "",
        ]
    )
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        k3_view_schema_version=K3_VIEW_SCHEMA_VERSION,
        k3_surface="technical-detail-workbench",
        k3_subject=subject.id,
        k3_registry_type=subject.type,
        k3_originating_hubs=list(model.originating_hub_ids),
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(lines)).encode()


def _render_status_axes(
    atlas: Atlas, subject: TechnicalIdentity, measurement_ids: tuple[str, ...]
) -> list[str]:
    if measurement_ids:
        measurement_presence = _markdown_table_cell(
            "; ".join(_technical_link(atlas, identity) for identity in measurement_ids)
        )
    else:
        measurement_presence = "No directly related MeasurementPoint is selected for this Component"
    return [
        "## Status axes — kept separate",
        "",
        "These states are separate projections, not one overall badge, score or maturity claim.",
        "",
        "| Axis | Projected state | Boundary |",
        "| --- | --- | --- |",
        f"| Target architecture / basis | `{subject.technical.architecture_authority}` | "
        "Architecture classification only; not an implementation claim. |",
        f"| Implementation declaration | `{subject.technical.implementation_status}` | "
        "Does not imply technical verification. |",
        f"| Technical verification | `{subject.technical.verification_status}` | "
        "Does not imply measurement validity or scientific evidence. |",
        f"| Measurement presence | {measurement_presence} | "
        "A MeasurementPoint does not establish measurement validity. |",
        "| Measurement validity | Not established by this view | No stronger state is inferred. |",
        "| Scientific evidence | No private scientific evidence is shown by this Technical view | "
        "Historical technical Evidence remains implementation provenance only. |",
        "| Accepted scientific claim | None created or implied by this view | "
        "Scientific acceptance requires a separate record. |",
        "",
    ]


def _render_lane(
    atlas: Atlas,
    title: str,
    identities: tuple[str, ...],
    *,
    detail_workbenches: bool = False,
) -> list[str]:
    lines = [f"## {title}", ""]
    for identity in identities:
        node = _k3_node(atlas, identity)
        if isinstance(node, TechnicalIdentity):
            status = node.technical
            lines.append(
                f"- {_technical_link(atlas, identity)} — implementation "
                f"`{status.implementation_status}`; technical verification "
                f"`{status.verification_status}`."
            )
        else:
            lines.append(f"- {_technical_link(atlas, identity)}")
        if detail_workbenches:
            workbench_path, canvas_path = technical_detail_paths(identity)
            lines.append(
                "  - "
                + _derived_link(workbench_path, "Open technical detail workbench")
                + " · "
                + _canvas_link(canvas_path, "Open scoped Canvas map")
            )
    if len(lines) == 2:
        lines.append("- None selected.")
    lines.append("")
    return lines


def _render_exact_relationships(atlas: Atlas, identities: tuple[str, ...]) -> list[str]:
    edges = _k3_relationships(atlas, identities)
    technical = [edge for edge in edges if edge.relation != "presented_in_domain"]
    presentation = [edge for edge in edges if edge.relation == "presented_in_domain"]
    lines = [
        "## Exact Registry technical relationships",
        "",
        "Only existing typed Registry edges among the selected anchors are shown.",
        "",
    ]
    for edge in technical:
        lines.append(
            f"- {_technical_link(atlas, edge.source)} — `{edge.relation}` → "
            f"{_technical_link(atlas, edge.target)}"
        )
    if not technical:
        lines.append("- None selected.")
    lines.extend(
        [
            "",
            "## Presentation grouping (not technical `part_of`)",
            "",
            "`presented_in_domain` is navigation grouping only; it does not define ancestry.",
            "",
        ]
    )
    for edge in presentation:
        lines.append(
            f"- {_technical_link(atlas, edge.source)} — `presented_in_domain` → "
            f"{_technical_link(atlas, edge.target)}"
        )
    if not presentation:
        lines.append("- No selected presentation grouping edge.")
    lines.append("")
    return lines


def _render_historical_evidence(atlas: Atlas, identities: tuple[str, ...]) -> list[str]:
    evidence = _historical_technical_evidence(atlas, identities)
    lines = [
        "## Evidence — historical technical provenance",
        "",
        "These accepted historical technical Evidence records document implementation inspection. "
        "They are not scientific evidence, measurement validation or accepted claims.",
        "",
    ]
    for source, edge in evidence:
        lines.append(
            f"- {_technical_link(atlas, source.id)} — historical technical provenance; "
            f"existing Registry relation `{edge.relation}` → `{edge.target}`."
        )
    if not evidence:
        lines.append("- No accepted historical technical Evidence link is selected.")
    lines.append("")
    return lines


def _component_research_link(
    atlas: Atlas,
    identifier: str,
    locators: dict[str, PurePosixPath],
    source_path: PurePosixPath,
) -> str:
    relative = locators.get(identifier)
    if identifier in atlas.entities:
        relative = TECHNICAL_ROOT / private_path(atlas.entities[identifier])
    if relative is None:
        return reference_plain(identifier)
    raw = str(relative)
    if (
        relative.is_absolute()
        or PureWindowsPath(raw).drive
        or "\\" in raw
        or ".." in relative.parts
        or not relative.parts
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in raw)
    ):
        raise ProjectionError("Unsafe Component Research locator")
    target = posixpath.relpath(raw, start=source_path.parent.as_posix())
    return f"[{identifier}]({quote(target, safe='/')})"


def _component_identity_display(
    identity: Identity,
    atlas: Atlas,
    locators: dict[str, PurePosixPath],
    source_path: PurePosixPath,
) -> str:
    revision = "none" if identity.record_version is None else f"v{identity.record_version}"
    profile = identity.profile or "none"
    record_type = identity.resolved_type or "none"
    link = _component_research_link(atlas, identity.identifier, locators, source_path)
    return (
        f"{link} (`{identity.resolution_status}`; type `{record_type}`; "
        f"record version `{revision}`; profile `{profile}`)"
    )


def _component_via_edge_lines(
    edge: Via,
    atlas: Atlas,
    locators: dict[str, PurePosixPath],
    source_path: PurePosixPath,
    number: int,
) -> list[str]:
    declared_target = Identity(
        identifier=edge.declared_target_identifier,
        resolution_status=edge.declared_target_resolution_status,
        resolved_type=edge.declared_target_type,
        record_version=edge.declared_target_record_version,
        profile=edge.declared_target_profile,
    )
    declaring = _component_research_link(atlas, edge.declaring_wiki_id, locators, source_path)
    return [
        f"{number}. Edge `{edge.edge_id}` · direction `{edge.traversal_direction}`",
        "   - Traversal: "
        + _component_identity_display(edge.traverse_from, atlas, locators, source_path)
        + " → "
        + _component_identity_display(edge.traverse_to, atlas, locators, source_path),
        "   - Declaration: "
        + f"{declaring} · type `{edge.declaring_doc_type}` · "
        + f"revision `v{edge.declaring_record_version}` · "
        + f"property `{edge.property}` · role `{edge.role or 'none'}`",
        "   - Declared target: "
        + _component_identity_display(declared_target, atlas, locators, source_path),
    ]


def _render_private_state(snapshot: Snapshot, source_projection_present: bool) -> list[str]:
    count = len(snapshot.records)
    lines = [
        "## Research and source availability",
        "",
        "This view displays exact Registry relationships and declared-reference paths. "
        "It does not establish scientific evidence, support, literature coverage, novelty, "
        "a gap, completeness, priority, or an accepted scientific claim.",
        "",
        "No automatic paper ranking, synthesis generation, novelty score, evidence score, "
        "maturity score or coverage score is produced.",
        "",
        "### Existing research navigation and audit",
        "",
        "The Declared Literature Navigation page retains the complete index inventory and "
        "Direct Reference Audit, including unresolved and wrong-type declarations.",
        f"- {_derived_link(NAVIGATION, 'Open Declared Literature Navigation')} — "
        "Direct Reference Audit",
        f"- {_derived_link(INDEX, 'Open Direct Views Index')}",
        "",
        "### Authored private research availability",
        "",
        f"- Authored private research record count: `{count}`.",
    ]
    if count == 0:
        lines.extend(
            [
                "- No authored private research records are present in this snapshot.",
                "- This availability state says nothing about research completeness or the field.",
            ]
        )
    else:
        lines.append(
            "- Record bodies are not projected here; only identities and declared references "
            "needed for this view are shown."
        )
    lines.extend(["", "### Literature / source availability", ""])
    if source_projection_present:
        lines.append(
            "- A source/Zotero projection exists outside this view; its source details and PDF "
            "content are not rendered here."
        )
    else:
        lines.extend(
            [
                "- No populated source/Zotero projection is available in this snapshot.",
                "- This source-availability state is not a scientific finding.",
            ]
        )
    lines.extend(
        [
            "",
            "### Scientific evidence and claim state",
            "",
            "- No private evidence body is shown by this navigation view.",
            "- No accepted scientific claim is created or implied by this Hub view.",
            "- Historical technical Evidence appears only in the Technical view and remains "
            "implementation provenance.",
            "",
        ]
    )
    return lines


def _render_component_hub_research(
    atlas: Atlas,
    hub: ComponentHubModel,
    snapshot: Snapshot,
    source_projection_present: bool,
    research: ComponentResearchModel,
    locators: dict[str, PurePosixPath],
) -> list[str]:
    if research.subject_id != hub.subject_id:
        raise ProjectionError("Component Research model subject does not match its Hub")
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity) or subject.type != "Component":
        raise ProjectionError(f"Component Hub subject is not a Component: {hub.subject_id}")
    source_path = OWNED_ROOT / hub.paths.research
    lines = _render_hub_header(atlas, hub, "research")
    lines.extend(
        [
            "## Component research scope",
            "",
            f"- Component: {_technical_link(atlas, subject.id)}",
            f"- Stable ID: `{subject.id}`",
            f"- Hub return: {_derived_link(hub.paths.overview, 'Overview')} · "
            f"{_derived_link(hub.paths.technical, 'Technical')}",
            "",
            "## Declared Research Questions",
            "",
            "Only current Registry `related_to_research_question` edges declared by this exact "
            "Component are shown. These public relations are not literature coverage or a "
            "scientific result.",
            "",
        ]
    )
    if research.research_question_relationships:
        for edge in research.research_question_relationships:
            question = atlas.entities[edge.target]
            lines.append(
                f"- {_technical_link(atlas, edge.source)} — `{edge.relation}` → "
                f"{_technical_link(atlas, edge.target)} — {question.name} · `{question.id}`"
            )
    else:
        lines.append(
            "No current Registry Research Question relation is declared for this Component."
        )
    lines.extend(
        [
            "",
            "## Declared literature paths to this Component",
            "",
            "These are all eligible current N-C navigation rows terminating at this exact "
            "Component in the Declared Reference Index. Each row retains its ordered edge "
            "provenance and actual terminal declaration; the index remains the path authority.",
            "",
        ]
    )
    if research.literature_paths:
        for path_number, row in enumerate(research.literature_paths, start=1):
            if row.navigation_start is None:
                raise ProjectionError(
                    "Eligible Component navigation row has no Paper/source identity"
                )
            target = Identity(
                identifier=row.target_identifier,
                resolution_status=row.target_resolution_status,
                resolved_type=row.resolved_target_type,
                record_version=row.target_record_version,
                profile=row.target_profile,
            )
            lines.extend(
                [
                    f"### Path {path_number} · `{row.path_kind}`",
                    "",
                    f"- Index row: `{row.row_kind}` · view `{row.navigation_view}` · "
                    f"eligible `{str(row.path_eligible).lower()}`",
                    "- Paper/source identity: "
                    + _component_identity_display(
                        row.navigation_start, atlas, locators, source_path
                    ),
                    f"- Recipe: `{row.recipe}`",
                    "- Declaring record: "
                    + _component_research_link(atlas, row.source_wiki_id, locators, source_path)
                    + f" · type `{row.source_doc_type}` · revision `v{row.source_record_version}`",
                    f"- Originating property: `{row.originating_property}`",
                    f"- Originating role: `{row.originating_role or 'none'}`",
                    "- Target Component: "
                    + _component_identity_display(target, atlas, locators, source_path),
                    f"- Final reference type check: `{row.type_check}`; expected target types: "
                    + (", ".join(f"`{item}`" for item in row.expected_target_types) or "none"),
                    "- Index diagnostics: "
                    + (", ".join(f"`{item}`" for item in row.diagnostic_codes) or "none"),
                    "- Ordered `via` edges:",
                ]
            )
            for edge_number, edge in enumerate(row.via, start=1):
                lines.extend(
                    "  " + line
                    for line in _component_via_edge_lines(
                        edge, atlas, locators, source_path, edge_number
                    )
                )
            lines.append("- Prerequisite references:")
            if row.prerequisite_refs:
                for prerequisite_number, edge in enumerate(row.prerequisite_refs, start=1):
                    lines.extend(
                        "  " + line
                        for line in _component_via_edge_lines(
                            edge, atlas, locators, source_path, prerequisite_number
                        )
                    )
            else:
                lines.append("  - None.")
            lines.extend([f"- Index row ID: `{row.row_id}`", ""])
    else:
        lines.extend(
            [
                "No matching declared Component literature paths are present in this snapshot.",
                "",
            ]
        )
    lines.extend(_render_private_state(snapshot, source_projection_present))
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def _landscape_inline(value: str) -> str:
    """Keep structured labels readable and prevent Markdown from changing their meaning."""
    value = " ".join(value.split())
    for character in ("\\", "`", "[", "]", "|"):
        value = value.replace(character, "\\" + character)
    return value


def _landscape_authored_link(
    record: EpistemicRecord,
    locators: dict[str, PurePosixPath],
    source_path: PurePosixPath,
) -> str:
    relative = locators.get(record.wiki_id)
    if relative is None:
        raise ProjectionError("RA-2 Landscape record has no authored-note locator")
    raw = str(relative)
    if (
        relative.is_absolute()
        or PureWindowsPath(raw).drive
        or "\\" in raw
        or ".." in relative.parts
        or not relative.parts
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in raw)
    ):
        raise ProjectionError("Unsafe RA-2 Landscape locator")
    target = posixpath.relpath(raw, start=source_path.parent.as_posix())
    return f"[{_landscape_inline(record.title)}]({quote(target, safe='/')}) · ID `{record.wiki_id}`"


def landscape_private_records(properties: list[dict], atlas: Atlas) -> tuple[EpistemicRecord, ...]:
    """Return only validated RA-2 records for the structured Landscape inventory."""
    try:
        records = validate_wiki_records(properties, atlas.entities.keys())
    except ValueError as exc:
        raise ProjectionError(
            "Invalid private identity or profile; repair declared records"
        ) from exc
    return tuple(record for record in records if isinstance(record, EpistemicRecord))


def _render_public_landscape(atlas: Atlas) -> list[str]:
    lines = [
        "## Public Research Atlas inventory",
        "",
        "This section reflects public Registry identities and their existing declared fields. "
        "A listed identity or relation is not evidence of research coverage, support, or outcome.",
        "",
    ]
    for record_type in LANDSCAPE_PUBLIC_TYPES:
        records = sorted(
            (node for node in atlas.entities.values() if node.type == record_type),
            key=lambda node: (node.name.casefold(), node.id),
        )
        lines.extend([f"### {record_type}", ""])
        if not records:
            lines.extend(
                ["No current records are present for this record class in this snapshot.", ""]
            )
            continue
        for node in records:
            lines.append(f"- {_technical_link(atlas, node.id)} · type `{node.type}`")
            for field in ("research_mapping", "research_direction"):
                if field in node.model_fields_set:
                    lines.append(f"  - `{field}`: `{getattr(node, field)}`")
            if node.type == "Decision":
                lines.append(f"  - `decision_scope`: `{node.decision_scope}`")
            if node.type == "ResearchThread":
                lines.append("  - Registry-declared `ordered_refs` (listed order):")
                for index, identity in enumerate(node.ordered_refs, start=1):
                    lines.append(f"    {index}. {_technical_link(atlas, identity)}")
            description = _landscape_inline(node.description)
            if description:
                lines.append(f"  - Registry description: {description}")
        lines.append("")

    relations = sorted(
        (edge for edge in atlas.relationships if edge.relation == "related_to_research_question"),
        key=lambda edge: (
            atlas.entities[edge.target].name.casefold(),
            atlas.entities[edge.source].name.casefold(),
            edge.source,
            edge.target,
        ),
    )
    lines.extend(
        [
            "### Exact `related_to_research_question` Registry declarations",
            "",
            "Only direct Registry edges are listed. No parent, Domain, role, or other "
            "relationship is expanded into research relevance.",
            "",
        ]
    )
    if not relations:
        lines.extend(
            [
                "No current declared relationships are present in this snapshot.",
                "",
            ]
        )
    else:
        for edge in relations:
            source = atlas.entities[edge.source]
            target = atlas.entities[edge.target]
            lines.append(
                f"- {_technical_link(atlas, source.id)} · `{source.type}` — "
                f"`{edge.relation}` → {_technical_link(atlas, target.id)} · `{target.type}`"
            )
        lines.append("")
    return lines


def _render_private_landscape(
    snapshot: Snapshot,
    locators: dict[str, PurePosixPath],
    records: tuple[EpistemicRecord, ...],
) -> list[str]:
    by_type: dict[str, list[EpistemicRecord]] = {
        doc_type: [] for doc_type in LANDSCAPE_PRIVATE_TYPES
    }
    for record in records:
        if record.doc_type not in by_type:
            raise ProjectionError("RA-2 Landscape class is missing from the accepted class list")
        by_type[record.doc_type].append(record)
    snapshot_records = {
        record.wiki_id: record for record in snapshot.records if record.profile == "ra2"
    }
    if set(snapshot_records) != {record.wiki_id for record in records}:
        raise ProjectionError("RA-2 Landscape inventory does not match the validated snapshot")
    lines = [
        "## Private authored RA-2 inventory",
        "",
        "Only typed RA-2 metadata and declared properties exposed by the current direct-view "
        "contract are listed. Record bodies and unmodeled prose are not read into this view.",
        "",
    ]
    source_path = OWNED_ROOT / RESEARCH_LANDSCAPE
    for doc_type in LANDSCAPE_PRIVATE_TYPES:
        class_records = sorted(
            by_type[doc_type], key=lambda record: (record.title.casefold(), record.wiki_id)
        )
        label = LANDSCAPE_PRIVATE_LABELS[doc_type]
        lines.extend([f"### {label}", ""])
        if not class_records:
            lines.extend(
                [
                    "No current RA-2 records are present for this record class in this snapshot.",
                    "",
                ]
            )
            continue
        for record in class_records:
            lines.append(f"- {_landscape_authored_link(record, locators, source_path)}")
            lines.append(
                f"  - Record class: `{record.doc_type}` · Record version: `{record.record_version}`"
            )
            lines.append(f"  - Document maturity: `{record.document_maturity}`")
            for field in LANDSCAPE_PRIVATE_STATUS_FIELDS.get(record.doc_type, ()):
                lines.append(f"  - `{field}`: `{getattr(record, field)}`")
            references = snapshot_records[record.wiki_id].references
            declared = [(name, values) for name, values in references.items() if values]
            if declared:
                lines.append("  - Existing declared properties:")
                for name, values in declared:
                    rendered = ", ".join(f"`{value}`" for value in values)
                    lines.append(f"    - `{name}`: {rendered}")
        lines.append("")
    return lines


def _literature_literal(value: object) -> str:
    """Render one accepted scalar/list losslessly inside a Markdown code span."""
    if isinstance(value, date):
        value = value.isoformat()
    elif isinstance(value, tuple):
        value = list(value)
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    runs = re.findall(r"`+", encoded)
    fence = "`" * (max((len(run) for run in runs), default=0) + 1)
    return f"{fence} {encoded} {fence}"


def _render_literature_record(
    record: Paper | ReadingNote,
    fields: tuple[str, ...],
    locators: dict[str, PurePosixPath],
) -> list[str]:
    authored = _landscape_authored_link(record, locators, OWNED_ROOT / LITERATURE_INSPECTION)
    lines = [
        f"- {authored}",
        f"  - Record class: `{record.doc_type}` · Record version: `{record.record_version}`",
        f"  - Document maturity: `{record.document_maturity}`",
        "  - Profile: `RA-2` · Epistemic schema version: "
        + _literature_literal(record.epistemic_schema_version),
    ]
    present_fields = []
    model_fields = type(record).model_fields
    for field in fields:
        if field not in model_fields:
            raise ProjectionError("Literature Inspection field is outside the accepted schema")
        value = getattr(record, field)
        if value is None or (isinstance(value, (list, tuple)) and not value):
            continue
        present_fields.append((field, value))
    if present_fields:
        lines.append("  - Existing accepted structured fields:")
        for field, value in present_fields:
            lines.append(f"    - `{field}`: {_literature_literal(value)}")
    return lines


def render_literature_inspection(
    commit: str,
    snapshot: Snapshot,
    locators: dict[str, PurePosixPath],
    records: tuple[EpistemicRecord, ...],
) -> bytes:
    """Render current accepted Paper and ReadingNote fields without reading note bodies."""
    snapshot_records = {
        record.wiki_id: record for record in snapshot.records if record.profile == "ra2"
    }
    if set(snapshot_records) != {record.wiki_id for record in records}:
        raise ProjectionError("Literature Inspection records do not match the validated snapshot")

    paper_records = sorted(
        (record for record in records if isinstance(record, Paper)),
        key=lambda record: (record.title.casefold(), record.wiki_id),
    )
    reading_records = sorted(
        (record for record in records if isinstance(record, ReadingNote)),
        key=lambda record: (record.title.casefold(), record.wiki_id),
    )
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        inspection_schema_version="1.0",
        inspection_surface="existing-literature-records",
    )
    body = _render_orientation_header(
        title="Literature Inspection",
        surface="Current accepted Paper and ReadingNote structured records",
        home=_derived_link(RESEARCH_LANDSCAPE, "Research Landscape"),
        broader_context=_derived_link(K3_HOME, "Research Knowledge Home"),
        research_fallback=(
            _derived_link(NAVIGATION, "Declared Literature Navigation")
            + " · "
            + _derived_link(INDEX, "Direct Views Index")
        ),
        authority=(
            "Displayed values come from current authored private RA-2 records; this generated "
            "view does not create source or scientific authority."
        ),
    )
    body.extend(
        [
            "A generated inspection of accepted RA-2 Paper and ReadingNote records in this "
            "snapshot. Structured values are displayed as stored. This page does not read "
            "ReadingNote bodies, interpret prose, resolve source identities, or assess "
            "research quality, evidence, coverage, relevance, novelty, or priority.",
            "",
            "## Paper/source records",
            "",
        ]
    )
    if not paper_records:
        body.extend(["No current matching records are present in this snapshot.", ""])
    else:
        for record in paper_records:
            body.extend(_render_literature_record(record, LITERATURE_PAPER_FIELDS, locators))
        body.append("")
    body.extend(["## ReadingNote records", ""])
    if not reading_records:
        body.extend(["No current matching records are present in this snapshot.", ""])
    else:
        for record in reading_records:
            body.extend(_render_literature_record(record, LITERATURE_READING_NOTE_FIELDS, locators))
        body.append("")
    body.extend(
        [
            "## Existing reference navigation and audit",
            "",
            f"- {_derived_link(NAVIGATION, 'Declared Literature Navigation')}",
            f"- [[{OWNED_ROOT / NAVIGATION.with_suffix('')}#Direct Reference Audit|"
            "Open Direct Reference Audit]]",
            f"- {_derived_link(INDEX, 'Direct Views Index')}",
            "",
            "These existing routes retain their current deterministic reference and audit "
            "semantics. This page adds no source-resolution or reference-traversal behavior.",
            "",
            "## Return navigation",
            "",
            f"- {_derived_link(RESEARCH_LANDSCAPE, 'Research Landscape')}",
            f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}",
            "",
        ]
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(body)).encode()


def render_research_landscape(
    commit: str,
    atlas: Atlas,
    snapshot: Snapshot,
    locators: dict[str, PurePosixPath],
    private_records: tuple[EpistemicRecord, ...],
) -> bytes:
    """Render the global Markdown research inventory from accepted structured inputs."""
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        landscape_schema_version="1.0",
        landscape_surface="global-research-navigation",
    )
    body = _render_orientation_header(
        title="Research Landscape",
        surface="Global Research Landscape over current structured records",
        home=_derived_link(K3_HOME, "Research Knowledge Home"),
        broader_context=(
            _technical_surface_link(TECHNICAL_ANATOMY, "Agent Anatomy")
            + " · "
            + _derived_link(HIERARCHY, "Technical Hierarchy")
        ),
        research_fallback=(
            _derived_link(NAVIGATION, "Declared Literature Navigation")
            + " · "
            + _derived_link(INDEX, "Direct Views Index")
        ),
    )
    body.extend(
        [
            "This generated page is a navigation and inventory surface. It does not create "
            "research authority, rank records, or infer scientific relationships.",
            "",
            "## Literature Inspection",
            "",
            f"- {_derived_link(LITERATURE_INSPECTION, 'Open Literature Inspection')}",
            "Inspect existing accepted Paper and ReadingNote structured fields and open their "
            "authored records.",
            "",
        ]
    )
    body.extend(_render_public_landscape(atlas))
    body.extend(_render_private_landscape(snapshot, locators, private_records))
    audit_label = "Declared Literature Navigation · Direct Reference Audit"
    body.extend(
        [
            "## Declared-reference navigation and audit",
            "",
            f"- {_derived_link(NAVIGATION, audit_label)}",
            f"- {_derived_link(INDEX, 'Direct Views Index')}",
            "",
            "These pages retain their existing deterministic navigation and audit contracts. "
            "No paths or reference semantics are reconstructed here.",
            "",
            "## Technical and research navigation",
            "",
            f"- {_derived_link(HIERARCHY, 'Technical Hierarchy')}",
            "- Existing W06 Component Research views:",
        ]
    )
    for subject_id, paths in sorted(
        COMPONENT_HUB_PATHS.items(),
        key=lambda item: (atlas.entities[item[0]].name.casefold(), item[0]),
    ):
        subject = atlas.entities[subject_id]
        if subject.type != "Component":
            raise ProjectionError("W06 Landscape entry does not identify a Component")
        body.append(f"  - {_derived_link(paths.research, subject.name)} · Component `{subject.id}`")
    body.extend(
        [
            "",
            "These are entry links to existing views. They add no technical attachment or "
            "parent, Domain, member, or role-based research relevance.",
            "",
            "## Empty-state meaning",
            "",
            "An empty class or relationship section describes this generated snapshot only. "
            "It does not state research absence, a gap, novelty, completeness, saturation, "
            "maturity, priority, confidence, or scientific quality.",
            "",
            "## Return navigation",
            "",
            f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}",
            f"- {_technical_surface_link(TECHNICAL_ANATOMY, 'Agent Anatomy')}",
            "",
        ]
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(body)).encode()


def render_k3_home(commit: str, atlas: Atlas) -> bytes:
    for identity in COMPONENT_HUB_PATHS:
        _component_hub_model(atlas, identity)
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        k3_view_schema_version=K3_VIEW_SCHEMA_VERSION,
        k3_surface="agent-anatomy-navigation",
    )
    body = _render_orientation_header(
        title="Research Knowledge Home",
        surface="Workspace home and current Agent Anatomy entry",
        home="Current page; no parent is asserted.",
        broader_context=(
            _technical_surface_link(TECHNICAL_ANATOMY, "Agent Anatomy")
            + "; "
            + _technical_surface_link(TECHNICAL_MAP, "System Anatomy reference")
            + "; "
            + _technical_surface_link(TECHNICAL_HOME, "Technical Atlas Index")
            + "."
        ),
        research_fallback=_derived_link(INDEX, "Direct Views Index") + ".",
    )
    body.extend(
        [
            "Maintained workspace entry. Agent Anatomy is the primary rich visual surface; "
            "the Domain slice provides one scoped drill-down.",
            "",
            "## Research Landscape",
            "",
            f"- {_derived_link(RESEARCH_LANDSCAPE, 'Open the Global Research Landscape')}",
            "A direct research entry point independent of Component Hub navigation.",
            "",
            "## Agent Anatomy",
            "",
            f"- {_technical_surface_link(TECHNICAL_ANATOMY, 'Open the primary Agent Anatomy')}",
            "- "
            + _technical_surface_link(
                TECHNICAL_DOMAIN_SLICE,
                "Evidence, Memory & Retrieval · representative Domain slice",
            ),
            "",
            "## Markdown fallback and rollback",
            "",
            "If Excalidraw is unavailable, continue with the Technical Hierarchy and linked "
            "technical records below. The previous System Anatomy stays available for direct "
            "comparison and rollback during G6.",
            f"- {_technical_surface_link(TECHNICAL_MAP, 'System Anatomy · reference / rollback')}",
            "",
            "## System and Functional Context",
            "",
            "- " + _identity_page_human_link(atlas, "SYS-AGA"),
            *[
                "- Functional context: " + _identity_page_human_link(atlas, identity)
                for identity, node in sorted(atlas.entities.items())
                if node.type == "Function"
            ],
            "Function membership is explicit non-containment and creates no Research relevance.",
            "",
            "## Preferred Component identities",
            "",
            "- "
            + _derived_link(
                COMPONENT_HUB_PATHS["CMP-MEM-RETRIEVAL"].overview,
                "Memory Retrieval · CMP-MEM-RETRIEVAL",
            ),
            "- "
            + _derived_link(
                COMPONENT_HUB_PATHS["CMP-INDEPENDENT-VERIFIER"].overview,
                "Independent Verifier · CMP-INDEPENDENT-VERIFIER",
            ),
            "",
            "Each Component Hub opens a complete Identity Page with same-page Technical and "
            "Research; its retained subfiles are auxiliary views of that same identity.",
            "",
            "## Technical hierarchy",
            "",
            f"- {_derived_link(HIERARCHY, 'Browse technical ancestry and presentation grouping')}",
            "",
            "## Navigation contract",
            "",
            "Use stable Atlas IDs for identity. `part_of` is technical hierarchy; "
            "`presented_in_domain` is presentation grouping only. "
            "No visual relation is invented here.",
            "",
            "Each Hub keeps architecture authority, implementation, technical verification, "
            "measurement validity, research availability and scientific claims separate.",
            "",
            "Research panels retain explicit empty/unavailable states. They do not couple the "
            "Research Wiki to runtime Agent Memory, Retrieval or Cortex.",
            "",
        ]
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(body)).encode()


def _render_component_hub_overview(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"Component Hub subject is not technical: {hub.subject_id}")
    lines = _render_hub_header(atlas, hub, "overview")
    lines.extend(
        [
            "## What this Component does",
            "",
            subject.description,
            "",
            f"- Component record: {_technical_link(atlas, subject.id)}",
            "",
        ]
    )
    lines.extend(_render_presentation_context(atlas, hub))
    lines.extend(_render_overview_status(subject))
    lines.extend(_render_mechanism_summary(atlas, hub))
    lines.extend(
        [
            "## Choose a view",
            "",
            "- **Open Technical** — "
            + _derived_link(hub.paths.technical, "exact Registry structure and technical status"),
            "- **Open Research** — "
            + _derived_link(hub.paths.research, "declared Research Questions and literature paths"),
            "",
        ]
    )
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def _render_component_hub_interface_lane(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    if hub.interface_ids:
        return _render_lane(atlas, "Interface lane", hub.interface_ids, detail_workbenches=True)
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"Component Hub subject is not technical: {hub.subject_id}")
    if subject.id == "CMP-INDEPENDENT-VERIFIER":
        explanation = (
            "No corresponding `IF-*` Registry record exists for this Independent Verifier slice "
            "in the current Registry selection."
        )
    else:
        explanation = (
            "No corresponding `IF-*` Registry record is directly related to this Component in "
            "the current Registry selection."
        )
    return [
        "## Interface lane",
        "",
        f"- **Explicitly empty.** {explanation}",
        "- No Interface is invented. No other relation type is rendered as an Interface, "
        "and no placeholder is generated.",
        "",
    ]


def _render_component_hub_technical(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"Component Hub subject is not technical: {hub.subject_id}")
    lines = _render_hub_header(atlas, hub, "technical")
    lines.extend(
        [
            "## Component identity and role",
            "",
            f"- Component: {_technical_link(atlas, subject.id)}",
            f"- Role: {subject.description}",
            "",
            "## Direct Component hierarchy",
            "",
            "Only Registry `part_of` edges define the technical parent/child relationship.",
            "",
            "### Technical parent(s)",
            "",
        ]
    )
    for identity in hub.technical_parent_ids:
        lines.append(
            f"- {_technical_link(atlas, subject.id)} — `part_of` → "
            f"{_technical_link(atlas, identity)}"
        )
    if not hub.technical_parent_ids:
        lines.append("- No technical parent is declared in the Registry.")
    lines.extend(["", "### Direct Component subcomponents", ""])
    for identity in hub.child_component_ids:
        lines.append(
            f"- {_technical_link(atlas, identity)} — `part_of` → "
            f"{_technical_link(atlas, subject.id)}"
        )
    if not hub.child_component_ids:
        lines.append("- No direct Component subcomponents are declared by `part_of`.")
    lines.extend(["", ""])
    lines.extend(_render_component_hub_interface_lane(atlas, hub))
    lines.extend(_render_lane(atlas, "Contract lane", hub.contract_ids, detail_workbenches=True))
    lines.extend(
        _render_lane(atlas, "Data Artifact lane", hub.data_artifact_ids, detail_workbenches=True)
    )
    lines.extend(
        _render_lane(atlas, "Measurement lane", hub.measurement_point_ids, detail_workbenches=True)
    )
    lines.extend(_render_status_axes(atlas, subject, hub.measurement_point_ids))
    lines.extend(_render_exact_relationships(atlas, hub.selected_ids))
    lines.extend(_render_historical_evidence(atlas, hub.selected_ids))
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def render_component_hub_view(
    commit: str,
    atlas: Atlas,
    hub: ComponentHubModel,
    view: Literal["overview", "technical", "research"],
    snapshot: Snapshot,
    source_projection_present: bool,
    research: ComponentResearchModel | None = None,
    locators: dict[str, PurePosixPath] | None = None,
) -> bytes:
    """Render one of three views from the same typed Component Hub contract."""
    subject = _k3_node(atlas, hub.subject_id)
    if not isinstance(subject, TechnicalIdentity) or subject.type != "Component":
        raise ProjectionError(f"Component Hub subject is invalid: {hub.subject_id}")
    if view == "overview":
        lines = _render_component_hub_overview(atlas, hub)
    elif view == "technical":
        lines = _render_component_hub_technical(atlas, hub)
    else:
        if research is None:
            raise ProjectionError("Component Research rendering requires its accepted index model")
        lines = _render_component_hub_research(
            atlas, hub, snapshot, source_projection_present, research, locators or {}
        )
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        k3_view_schema_version=K3_VIEW_SCHEMA_VERSION,
        k3_surface=f"component-hub-{view}",
        k3_subject=hub.subject_id,
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(lines)).encode()


def render_k3_workbench(
    commit: str,
    atlas: Atlas,
    subject_id: str,
    snapshot: Snapshot,
    source_projection_present: bool,
) -> bytes:
    """Retain the human-first K3 entry path as the Component Hub Overview."""
    hub = _component_hub_model(atlas, subject_id)
    return render_component_hub_view(
        commit, atlas, hub, "overview", snapshot, source_projection_present
    )


class OwnedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    sha256: SHA256


class OwnedFileV21(OwnedFile):
    ownership: Literal["strict-bytes", "obsidian-base-semantics"]
    semantic_sha256: SHA256 | None = None


class SourceDigests(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    public_atlas_base: SHA256
    research_wiki_direct_base: SHA256


class ManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    view_schema_version: Literal["1.0"]
    generated_by: Literal["research-wiki-derived"]
    source_repository: Literal["Planton361/autonomous-game-agent"]
    source_commit: COMMIT
    source_atlas_schema: AtlasSourceSchema
    source_sha256: SourceDigests
    owned_files: list[OwnedFile]


class Manifest(ManifestV1):
    view_schema_version: Literal["2.0"]
    reference_index_schema_version: Literal["1.0"]
    private_input_fingerprint: SHA256


class ManifestV21(Manifest):
    view_schema_version: Literal["2.1"]
    owned_files: list[OwnedFileV21]


class ManifestV22(ManifestV21):
    view_schema_version: Literal["2.2"]


class ManifestV23(ManifestV21):
    view_schema_version: Literal["2.3"]


class ManifestV24(ManifestV21):
    view_schema_version: Literal["2.4"]


class ManifestV25(ManifestV21):
    view_schema_version: Literal["2.5"]


class ManifestV26(ManifestV21):
    view_schema_version: Literal["2.6"]


class ManifestV27(ManifestV21):
    view_schema_version: Literal["2.7"]


class ManifestV28(ManifestV21):
    view_schema_version: Literal["2.8"]


class ManifestV29(ManifestV21):
    view_schema_version: Literal["2.9"]


class ManifestV210(ManifestV21):
    view_schema_version: Literal["2.10"]


def _canonical_property_id(value: object) -> object:
    if isinstance(value, str) and value.startswith("note."):
        return value.removeprefix("note.")
    return value


def _base_semantics(data: bytes) -> dict:
    """Canonicalize only documented/observed Obsidian Base serialization equivalences."""
    base = read_yaml(utf8(data))
    canonical = dict(base)
    properties = base.get("properties")
    if isinstance(properties, dict):
        normalized_properties = {}
        for key, value in properties.items():
            normalized = _canonical_property_id(key)
            if normalized in normalized_properties:
                raise ProjectionError("Ambiguous property identities in prior-owned Base")
            normalized_properties[normalized] = value
        canonical["properties"] = normalized_properties
    configured_views = base.get("views")
    if isinstance(configured_views, list):
        normalized_views = []
        for configured_view in configured_views:
            if not isinstance(configured_view, dict):
                normalized_views.append(configured_view)
                continue
            view = dict(configured_view)
            order = configured_view.get("order")
            if isinstance(order, list):
                view["order"] = [_canonical_property_id(item) for item in order]
            group = configured_view.get("groupBy")
            if isinstance(group, dict) and "property" in group:
                view["groupBy"] = dict(group)
                view["groupBy"]["property"] = _canonical_property_id(group["property"])
            sorts = configured_view.get("sort")
            if isinstance(sorts, list):
                view["sort"] = []
                for configured_sort in sorts:
                    if isinstance(configured_sort, dict) and "property" in configured_sort:
                        normalized_sort = dict(configured_sort)
                        normalized_sort["property"] = _canonical_property_id(
                            configured_sort["property"]
                        )
                        view["sort"].append(normalized_sort)
                    else:
                        view["sort"].append(configured_sort)
            normalized_views.append(view)
        canonical["views"] = normalized_views
    return canonical


def _base_semantic_digest(data: bytes) -> str:
    return digest(yaml_text(_base_semantics(data)).encode())


def _base_semantically_matches(actual: bytes, expected: bytes) -> bool:
    return _base_semantics(actual) == _base_semantics(expected)


def views_tree(
    commit: str,
    public_base: bytes,
    direct_base: bytes,
    source_atlas_schema: AtlasSourceSchema,
) -> dict[PurePosixPath, bytes]:
    """Retained v1 renderer; later manifests extend its Bases under the same owner."""
    technical = read_yaml(utf8(public_base))
    direct = read_yaml(utf8(direct_base))
    for base in (technical, direct):
        if (
            not isinstance(base.get("filters"), dict)
            or not isinstance(base.get("views"), list)
            or not base["views"]
            or any(
                not isinstance(view, dict)
                or view.get("type") != "table"
                or not isinstance(view.get("name"), str)
                for view in base["views"]
            )
        ):
            raise ProjectionError("Invalid source Base structure; restore committed table views")
    # Preserve every public view/filter; scope its dataset to the RA-1 projection.
    technical["filters"] = {
        "and": ['file.inFolder("_generated/technical-atlas")', technical["filters"]]
    }
    tree = {
        TECHNICAL_BASE: (BASE_OWNER + yaml_text(technical)).encode(),
        DIRECT_BASE: BASE_OWNER.encode() + direct_base,
    }
    props = dict(generated_by=OWNER, source_repository=REPOSITORY, source_commit=commit)
    body = "# Direct Views Index\n\nNavigation only; no scientific data index.\n\n"
    for path in (TECHNICAL_BASE, DIRECT_BASE):
        body += f"- [[{OWNED_ROOT / path}|{path.stem}]]\n"
    body += "\nPublic-safe copy sources and capability limits at this source commit:\n\n"
    for label, path in (
        ("Direct View Capability Matrix", "Wiki Views/Direct View Capability Matrix.md"),
        ("Process seed sources", "Process Seeds"),
    ):
        route = "blob" if path.endswith(".md") else "tree"
        url = f"https://github.com/{REPOSITORY}/{route}/{commit}/docs/research-atlas/{quote(path)}"
        body += f"- [{label}]({url})\n"
    body += (
        "\nViews display declared properties, not verified scientific conclusions. "
        "No automatic acceptance, private-to-public promotion or Wiki-to-Agent-Memory path.\n"
    )
    tree[INDEX] = ("---\n" + yaml_text(props) + "---\n" + body).encode()
    manifest = ManifestV1(
        view_schema_version="1.0",
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        source_atlas_schema=source_atlas_schema,
        source_sha256=SourceDigests(
            public_atlas_base=digest(public_base),
            research_wiki_direct_base=digest(direct_base),
        ),
        owned_files=[
            OwnedFile(path=str(path), sha256=digest(data)) for path, data in sorted(tree.items())
        ],
    )
    tree[MANIFEST] = yaml_text(manifest.model_dump()).encode()
    return tree


def reference_views_tree(
    commit: str,
    public_base: bytes,
    direct_base: bytes,
    reference: ReferenceIndex,
    atlas: Atlas,
    locators: dict[str, PurePosixPath],
    snapshot: Snapshot,
    source_projection_present: bool,
    private_records: tuple[EpistemicRecord, ...] = (),
) -> dict[PurePosixPath, bytes]:
    if reference.source_atlas_schema != atlas.source_atlas_schema:
        raise ProjectionError("Reference index source Atlas schema does not match loaded Atlas")
    tree = views_tree(commit, public_base, direct_base, atlas.source_atlas_schema)
    old = ManifestV1.model_validate(read_yaml(utf8(tree.pop(MANIFEST))))
    tree[REFERENCE_INDEX] = render_index(reference)
    tree[NAVIGATION] = render_navigation(reference, atlas, locators)
    tree[K3_HOME] = render_k3_home(commit, atlas)
    tree[RESEARCH_LANDSCAPE] = render_research_landscape(
        commit, atlas, snapshot, locators, private_records
    )
    tree[LITERATURE_INSPECTION] = render_literature_inspection(
        commit, snapshot, locators, private_records
    )
    hubs = {
        subject_id: _component_hub_model(atlas, subject_id) for subject_id in COMPONENT_HUB_PATHS
    }
    research_models = {
        subject_id: _component_research_model(atlas, reference, subject_id)
        for subject_id in COMPONENT_HUB_PATHS
    }
    for subject_id, paths in COMPONENT_HUB_PATHS.items():
        hub = hubs[subject_id]
        for view, path in (
            ("overview", paths.overview),
            ("technical", paths.technical),
            ("research", paths.research),
        ):
            tree[path] = render_component_hub_view(
                commit,
                atlas,
                hub,
                view,
                snapshot,
                source_projection_present,
                research_models[subject_id] if view == "research" else None,
                locators,
            )
    for detail in technical_detail_models(atlas):
        workbench_path, canvas_path = technical_detail_paths(detail.endpoint_id)
        tree[workbench_path] = render_technical_detail_workbench(commit, atlas, detail)
        tree[canvas_path] = render_technical_detail_canvas(atlas, detail)
    revision = registry_content_revision(atlas)
    page_paths = identity_page_paths(atlas)
    for page in identity_page_models(atlas, reference, page_paths=page_paths):
        if page.path in tree and (
            page.subject.id not in COMPONENT_HUB_PATHS
            or page.path != COMPONENT_HUB_PATHS[page.subject.id].overview
        ):
            raise ProjectionError("Identity Page path collision with existing derived surface")
        tree[page.path] = render_identity_page(
            commit, atlas, page, registry_revision=revision, page_paths=page_paths
        )
    research_rows = _observe_research_navigation_lines(atlas, reference, locators)
    detail_markdown, detail_canvas = technical_detail_paths("DAT-OBSERVATION")

    def observe_identity_link(identity: str, label: str) -> str:
        path = page_paths.get(identity)
        if path is not None:
            return _derived_link(path, label)
        return private_link(private_path(atlas.entities[identity]), label)

    observe_body = render_observe_scope(
        atlas,
        identity_link=observe_identity_link,
        back_link=_relative_markdown_link(
            OWNED_ROOT / OBSERVE_SCOPE,
            TECHNICAL_ROOT / TECHNICAL_ANATOMY,
            "← Agent Anatomy",
        ),
        source_revision=revision,
        source_commit=commit,
        detail_links=(
            _derived_link(detail_markdown, "Observation · W05 Technical Detail"),
            _canvas_link(detail_canvas, "Observation · W05 native Canvas"),
        ),
        research_lines=research_rows,
        research_empty_note=(
            "No eligible current N-C navigation path terminates at one of the listed Component "
            "subjects in this source snapshot. Observation is a DataArtifact; no Component "
            "terminal path is inferred for it."
        ),
    )
    if "FUNC-OBSERVE" in page_paths:
        heading, separator, remainder = observe_body.partition("\n")
        observe_body = (
            heading + separator + "\nLegacy Assembly compatibility surface; "
            "not technical ancestry or a preferred Function identity.\n\n"
            + "Functional context: "
            + observe_identity_link("FUNC-OBSERVE", "Observe · FUNC-OBSERVE")
            + "\n"
            + remainder
        )
    observe_properties = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        observe_scope_view_schema_version="1.0",
        source_registry_revision=revision,
    )
    observe_metadata = OBSERVE_SCOPE_METADATA_MARKER + yaml_text(observe_properties) + "-->\n"
    tree[OBSERVE_SCOPE] = (observe_body + "\n" + observe_metadata).encode()
    hierarchy = hierarchy_tree(commit, atlas)
    if tree.keys() & hierarchy.keys():
        raise ProjectionError("Duplicate generated hierarchy path")
    tree.update(hierarchy)
    text = utf8(tree[INDEX]).replace(
        "Navigation only; no scientific data index.",
        "Declared structured reference index for navigation/audit; no scientific adjudication.",
    )
    tree[INDEX] = (
        text
        + f"\n- [[{OWNED_ROOT / NAVIGATION}|Declared Literature Navigation]]\n"
        + f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}\n"
        + f"- {_derived_link(RESEARCH_LANDSCAPE, 'Research Landscape')}\n"
        + f"- {_derived_link(LITERATURE_INSPECTION, 'Literature Inspection')}\n"
        + f"- {_derived_link(HIERARCHY, 'Technical Hierarchy')}\n"
    ).encode()
    data = old.model_dump()
    owned_files = []
    for path, payload in sorted(tree.items()):
        obsidian_managed = path in OBSIDIAN_MANAGED_BASES
        owned_files.append(
            OwnedFileV21(
                path=str(path),
                sha256=digest(payload),
                ownership=OBSIDIAN_BASE_OWNERSHIP if obsidian_managed else STRICT_OWNERSHIP,
                semantic_sha256=(_base_semantic_digest(payload) if obsidian_managed else None),
            )
        )
    data.update(
        view_schema_version="2.10",
        reference_index_schema_version="1.0",
        private_input_fingerprint=reference.private_input_fingerprint,
        owned_files=owned_files,
    )
    tree[MANIFEST] = yaml_text(
        ManifestV210.model_validate(data).model_dump(exclude_none=True)
    ).encode()
    return tree


def _observe_research_navigation_lines(
    atlas: Atlas,
    reference: ReferenceIndex,
    locators: dict[str, PurePosixPath],
) -> tuple[str, ...]:
    """Reuse only eligible W06 N-C paths terminating at an exact Observe Component."""
    source_path = OWNED_ROOT / OBSERVE_SCOPE
    rows = tuple(
        sorted(
            (
                row
                for identity in OBSERVE_COMPONENT_IDS
                for row in component_navigation_rows(reference, identity)
            ),
            key=lambda row: (
                row.target_identifier,
                row.navigation_start.identifier if row.navigation_start else "",
                row.originating_property,
                row.source_wiki_id,
                row.row_id,
            ),
        )
    )
    if not rows:
        return ()
    lines: list[str] = []
    for number, row in enumerate(rows, start=1):
        if row.navigation_start is None:
            raise ProjectionError("Eligible Observe Component path has no source identity")
        target = atlas.entities[row.target_identifier]
        navigation_start = _component_identity_display(
            row.navigation_start, atlas, locators, source_path
        )
        terminal_subject = _technical_link(atlas, target.id)
        declaring_record = _component_research_link(
            atlas, row.source_wiki_id, locators, source_path
        )
        lines.extend(
            [
                f"### {target.name} · `{row.target_identifier}` · path {number}",
                "",
                f"- Navigation start: {navigation_start}",
                f"- Exact terminal subject: {terminal_subject} · type `{target.type}`",
                f"- Declaring record: {declaring_record} · type `{row.source_doc_type}` "
                f"· revision `v{row.source_record_version}`",
                f"- Originating property / role: `{row.originating_property}` "
                f"/ `{row.originating_role or 'none'}`",
                f"- Path kind / recipe: `{row.path_kind}` / `{row.recipe}`",
                "- Ordered declared-reference path:",
            ]
        )
        for edge_number, edge in enumerate(row.via, start=1):
            lines.extend(
                "  " + line
                for line in _component_via_edge_lines(
                    edge, atlas, locators, source_path, edge_number
                )
            )
        lines.extend([f"- Index row: `{row.row_id}`", ""])
    lines.append(
        "Current W06 N-C navigation has Component terminal subjects; "
        "no DataArtifact path is inferred for `DAT-OBSERVATION`."
    )
    return tuple(lines)


def authored_snapshot(
    vault: Path, atlas: Atlas
) -> tuple[Snapshot, dict[str, PurePosixPath], tuple[EpistemicRecord, ...]]:
    """RA-1 discovery semantics, excluding all generated content; locators are not identity."""
    properties: list[dict] = []
    paths: list[PurePosixPath] = []
    try:
        for parent, directories, names in os.walk(
            vault, followlinks=False, onerror=unreadable_tree
        ):
            directories[:] = sorted(
                name
                for name in directories
                if Path(parent) / name != vault / "_generated"
                and not (Path(parent) / name).is_symlink()
            )
            for name in sorted(names):
                path = Path(parent) / name
                if path.suffix.lower() != ".md" or path.is_symlink():
                    continue
                if not path.is_file():
                    raise ProjectionError("Authored Markdown must be a readable regular file")
                text = path.read_text(encoding="utf-8")
                if not text.startswith("---\n"):
                    continue
                header = text[4:].split("\n---\n", 1)[0]
                try:
                    props = yaml.load(header, Loader=UniqueKeyLoader)
                except (ValueError, yaml.YAMLError, TypeError) as exc:
                    if re.search(r"wiki_schema_version|wiki_id", header):
                        raise ProjectionError("Invalid declared Wiki frontmatter") from exc
                    continue
                if not isinstance(props, dict) or not (
                    {"wiki_schema_version", "wiki_id"} & props.keys()
                ):
                    continue
                props, _ = markdown_parts(text)
                properties.append(props)
                paths.append(PurePosixPath(path.relative_to(vault).as_posix()))
    except (OSError, UnicodeError) as exc:
        raise ProjectionError("Cannot read authored Wiki snapshot") from exc
    snapshot = make_snapshot(properties, atlas)
    private_records = landscape_private_records(properties, atlas)
    locators = {props["wiki_id"]: path for props, path in zip(properties, paths, strict=True)}
    return snapshot, locators, private_records


def validate_prior(root: Path) -> dict[PurePosixPath, OwnedFile]:
    path = target_path(root, MANIFEST)
    if not path.exists():
        return {}
    if not path.is_file():
        raise ProjectionError("Prior direct-views manifest must be a regular file")
    try:
        data = read_yaml(utf8(path.read_bytes()))
        if data.get("view_schema_version") == "1.0":
            manifest = ManifestV1.model_validate(data)
        elif data.get("view_schema_version") == "2.0":
            manifest = Manifest.model_validate(data)
        elif data.get("view_schema_version") == "2.1":
            manifest = ManifestV21.model_validate(data)
        elif data.get("view_schema_version") == "2.2":
            manifest = ManifestV22.model_validate(data)
        elif data.get("view_schema_version") == "2.3":
            manifest = ManifestV23.model_validate(data)
        elif data.get("view_schema_version") == "2.4":
            manifest = ManifestV24.model_validate(data)
        elif data.get("view_schema_version") == "2.5":
            manifest = ManifestV25.model_validate(data)
        elif data.get("view_schema_version") == "2.6":
            manifest = ManifestV26.model_validate(data)
        elif data.get("view_schema_version") == "2.7":
            manifest = ManifestV27.model_validate(data)
        elif data.get("view_schema_version") == "2.8":
            manifest = ManifestV28.model_validate(data)
        elif data.get("view_schema_version") == "2.9":
            manifest = ManifestV29.model_validate(data)
        elif data.get("view_schema_version") == "2.10":
            manifest = ManifestV210.model_validate(data)
        else:
            raise ProjectionError("Unsupported direct-views manifest version")
    except ValidationError as exc:
        raise ProjectionError("Invalid direct-views manifest; restore owner/schema/fields") from exc
    prior = {}
    for item in manifest.owned_files:
        target_path(root, item.path)
        relative = PurePosixPath(item.path)
        if relative == MANIFEST or relative in prior:
            raise ProjectionError("Duplicate/self-owned direct-views manifest path")
        # V1 cannot claim YAML; later versions add one fixed YAML payload, not a subtree.
        if not (
            len(relative.parts) == 2
            and (
                (relative.parent == PurePosixPath("bases") and relative.suffix == ".base")
                or (
                    relative.parent == PurePosixPath("indexes")
                    and relative.suffix == ".md"
                    and (
                        relative not in W07_PAYLOADS
                        or manifest.view_schema_version
                        in {"2.5", "2.6", "2.7", "2.8", "2.9", "2.10"}
                    )
                    and (manifest.view_schema_version != "2.5" or relative in V25_INDEX_PAYLOADS)
                    and (manifest.view_schema_version != "2.6" or relative in V26_INDEX_PAYLOADS)
                    and (manifest.view_schema_version != "2.7" or relative in V27_INDEX_PAYLOADS)
                    and (
                        manifest.view_schema_version not in {"2.8", "2.9", "2.10"}
                        or relative in V27_INDEX_PAYLOADS
                    )
                )
            )
            or (
                manifest.view_schema_version
                in {"2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10"}
                and relative == REFERENCE_INDEX
            )
            or (
                manifest.view_schema_version in {"2.0", "2.1", "2.2"}
                and relative in K3_PRIOR_PAYLOADS
            )
            or (
                manifest.view_schema_version in {"2.3", "2.4"}
                and relative in (K3_PRE_W07_PAYLOADS | K3_PRIOR_PAYLOADS)
            )
            or (
                manifest.view_schema_version == "2.5"
                and relative in (K3_PAYLOADS | K3_PRIOR_PAYLOADS)
            )
            or (
                manifest.view_schema_version in {"2.6", "2.7", "2.8", "2.9", "2.10"}
                and relative in (K3_PAYLOADS | K3_PRIOR_PAYLOADS | W10_PAYLOADS)
            )
            or (
                manifest.view_schema_version in {"2.7", "2.8", "2.9", "2.10"}
                and relative in OBSERVE_SCOPE_PAYLOADS
            )
            or (
                manifest.view_schema_version
                in {"2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10"}
                and relative == HIERARCHY
            )
            or (
                manifest.view_schema_version
                in {"2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10"}
                and relative.parent == HIERARCHY_DIR
                and relative.suffix == ".md"
                and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", relative.stem)
            )
            or (
                manifest.view_schema_version in {"2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "2.10"}
                and relative in TECHNICAL_DETAIL_PAYLOADS
            )
            or (manifest.view_schema_version == "2.8" and relative in IDENTITY_PAGE_PAYLOADS)
            or (
                manifest.view_schema_version == "2.9"
                and _identity_page_subject_for_path(relative) is not None
            )
            or (manifest.view_schema_version == "2.10" and _is_identity_page_path(relative))
        ):
            raise ProjectionError("Invalid direct-view ownership path/type")
        if isinstance(item, OwnedFileV21):
            obsidian_managed = relative.suffix == ".base"
            if (
                obsidian_managed
                and (item.ownership != OBSIDIAN_BASE_OWNERSHIP or item.semantic_sha256 is None)
            ) or (
                not obsidian_managed
                and (item.ownership != STRICT_OWNERSHIP or item.semantic_sha256 is not None)
            ):
                raise ProjectionError("Invalid direct-view ownership classification")
        prior[relative] = item
    return prior


def source_bytes(repo: Path, relative: PurePosixPath) -> bytes:
    path = repo / relative
    no_symlink_boundary(path)
    if not path.is_file():
        raise ProjectionError("Missing direct-view source; restore the committed Base")
    git(repo, "ls-files", "--error-unmatch", "--", str(relative))
    return path.read_bytes()


def project(
    repo_root: Path, vault_root: Path, source_ref: str, *, check: bool = False
) -> dict[PurePosixPath, bytes]:
    # RA-1 performs all topology/marker/Git/Atlas/RA-2 checks, strictly without writes.
    # Inspect our boundary first so symlinks never reach the authored-note scanner.
    no_symlink_boundary(vault_root.absolute())
    vault = vault_root.resolve()
    root = vault / OWNED_ROOT
    actual = inspect_owned(root)
    prior = validate_prior(root)
    for relative in actual:
        # Convert invalid owned Markdown encoding into an actionable validation error
        # before RA-1 reads this otherwise unmodeled navigation note.
        if relative.suffix.lower() == ".md":
            utf8(target_path(root, relative).read_bytes())
    try:
        technical = technical_projection(repo_root, vault_root, source_ref, check=True)
    except (OSError, UnicodeError) as exc:
        raise ProjectionError("Cannot read projection preconditions") from exc
    commit = read_yaml(utf8(technical[PurePosixPath("manifest/projection.yaml")]))["source_commit"]
    repo = repo_root.resolve()
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *SOURCE_PATHS):
        raise ProjectionError(
            "Direct-view sources are dirty; commit or resolve source changes first"
        )
    atlas = load_registry(repo / "docs/research-atlas")
    snapshot, locators, private_records = authored_snapshot(vault, atlas)
    reference = build_index(atlas, snapshot, commit)
    tree = reference_views_tree(
        commit,
        source_bytes(repo, PUBLIC_SOURCE),
        source_bytes(repo, DIRECT_SOURCE),
        reference,
        atlas,
        locators,
        snapshot,
        (vault / PurePosixPath("_generated/zotero/manifest/projection.yaml")).is_file(),
        private_records,
    )
    if actual - prior.keys() - {MANIFEST}:
        raise ProjectionError("Unknown/unowned derived files; move them out before generation")
    # Complete preflight before any mkdir, deletion, or atomic replace.
    for relative in tree.keys() | prior.keys():
        target = target_path(root, relative)
        if target.exists() and not target.is_file():
            raise ProjectionError("Direct-view output path is occupied by a directory")
        for parent in target.parents:
            if parent == vault:
                break
            if parent.exists() and not parent.is_dir():
                raise ProjectionError("Direct-view output parent is not a directory")
    for relative, item in prior.items():
        if relative not in actual:
            continue
        data = target_path(root, relative).read_bytes()
        if relative.suffix == ".base":
            if isinstance(item, OwnedFileV21):
                owned = _base_semantic_digest(data) == item.semantic_sha256
            else:
                exact_legacy = data.startswith(BASE_OWNER.encode()) and digest(data) == item.sha256
                migration_bridge = (
                    relative in tree
                    and item.sha256 == digest(tree[relative])
                    and _base_semantically_matches(data, tree[relative])
                )
                owned = exact_legacy or migration_bridge
            if not owned:
                raise ProjectionError(
                    "Prior-owned Base changed semantically; preserve or restore it"
                )
        elif relative == REFERENCE_INDEX:
            metadata = read_yaml(utf8(data))
            owned = (
                metadata.get("generated_by") == OWNER
                and metadata.get("index_schema_version") == "1.0"
            )
        elif relative.suffix == ".canvas":
            try:
                canvas = json.loads(utf8(data))
            except (ValueError, TypeError):
                canvas = None
            owned = (
                isinstance(canvas, dict)
                and canvas.get("generated_by") == OWNER
                and canvas.get("canvas_view_schema_version") == "1.0"
            )
        elif relative == OBSERVE_SCOPE:
            owned = _observe_scope_generated_metadata(utf8(data)).get("generated_by") == OWNER
        elif _is_identity_page_path(relative):
            metadata = _identity_page_generated_metadata(utf8(data), relative)
            legacy_hub = next(
                (
                    identity
                    for identity, hub in COMPONENT_HUB_PATHS.items()
                    if relative == hub.overview
                ),
                None,
            )
            legacy = markdown_parts(utf8(data))[0] if legacy_hub is not None else {}
            legacy_owned = (
                legacy.get("generated_by") == OWNER
                and legacy.get("k3_subject") == legacy_hub
                and legacy.get("k3_surface") == "component-hub-overview"
            )
            if metadata.get("generated_by") != OWNER and not legacy_owned:
                owned = False
            elif digest(data) != item.sha256 and data != tree.get(relative):
                raise ProjectionError(
                    "Prior-owned Identity Page was edited; preserve or restore it"
                )
            else:
                owned = True
        else:
            owned = markdown_parts(utf8(data))[0].get("generated_by") == OWNER
        if not owned:
            raise ProjectionError("Prior-owned view lost its owner marker; preserve or restore it")
        if relative.suffix != ".base" and relative not in tree and digest(data) != item.sha256:
            raise ProjectionError("Obsolete owned view was edited; preserve edits before cleanup")
    if check:
        if actual != tree.keys() or any(
            (
                not _base_semantically_matches(target_path(root, p).read_bytes(), data)
                if p in OBSIDIAN_MANAGED_BASES
                else target_path(root, p).read_bytes() != data
            )
            for p, data in tree.items()
        ):
            raise ProjectionError("Direct-view drift; regenerate with the same source-ref")
        return tree
    for relative in sorted(prior.keys() - tree.keys()):
        target_path(root, relative).unlink(missing_ok=True)
    for relative, data in sorted(tree.items()):
        if relative != MANIFEST:
            atomic_write(root, relative, data)
    atomic_write(root, MANIFEST, tree[MANIFEST])
    return tree


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument(
        "--check", action="store_true", help="Validate owned view state without any writes"
    )
    args = parser.parse_args(argv)
    try:
        project(args.repo_root, args.vault_root, args.source_ref, check=args.check)
    except ProjectionError as exc:
        print(f"Direct views: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
