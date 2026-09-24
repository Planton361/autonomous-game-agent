"""Private declared-reference navigation and direct Bases; no scientific adjudication."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

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
    ReferenceIndex,
    Snapshot,
    build_index,
    make_snapshot,
    render_index,
    render_navigation,
)
from .schema import Evidence, Relationship, TechnicalIdentity
from .validator import Atlas, UniqueKeyLoader, load_registry

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
K3_PAYLOADS = frozenset(
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
K3_VIEW_SCHEMA_VERSION = "1.3"


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


def _derived_link(path: PurePosixPath, label: str) -> str:
    return f"[[{OWNED_ROOT / path.with_suffix('')}|{label}]]"


def _technical_surface_link(path: PurePosixPath, label: str) -> str:
    return f"[[{TECHNICAL_ROOT / path.with_suffix('')}|{label}]]"


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
        entry.append("  " * depth + "- " + _hierarchy_link(atlas, identity))
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
        entry.append(f"- {_hierarchy_link(atlas, identity)} — `{technical[identity].type}`")
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
            + ("; ".join(_hierarchy_link(atlas, i) for i in members) if members else "No members.")
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


def _render_orientation_header(
    *,
    title: str,
    surface: str,
    home: str,
    broader_context: str,
    research_fallback: str,
    stable_id: str | None = None,
    presentation_context: str | None = None,
) -> list[str]:
    opened = surface if stable_id is None else f"{surface}; stable ID `{stable_id}`"
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
            "- **Authority:** Technical structure and status come from the Research Atlas. Current "
            "implementation truth requires current code plus executable or CI evidence; authored "
            "private Research remains separate.",
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


def _render_lane(atlas: Atlas, title: str, identities: tuple[str, ...]) -> list[str]:
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


def _render_private_state(snapshot: Snapshot, source_projection_present: bool) -> list[str]:
    count = len(snapshot.records)
    lines = [
        "## Research and source availability",
        "",
        "No currently supported/assigned research content is shown in this view.",
        "",
        "This view does not infer Research Question or Research Thread associations. "
        "It does not mean the topic is unresearched, literature is absent, a scientific gap "
        "exists, novelty is established, evidence is weak or strong, research is complete, "
        "or the Component should be prioritized.",
        "",
        "No automatic paper ranking, synthesis generation, novelty score, evidence score, "
        "maturity score or coverage score is produced.",
        "",
        "### Existing research navigation",
        "",
        "Existing declared-reference navigation remains a separate, non-adjudicative surface.",
        f"- {_derived_link(NAVIGATION, 'Open Declared Literature Navigation')}",
        f"- {_derived_link(INDEX, 'Open Direct Views Index')}",
        "",
        "### Authored private research availability",
        "",
    ]
    lines.append(f"- Authored private research record count: `{count}`.")
    if count == 0:
        lines.extend(
            [
                "- No authored private research records are present in this snapshot.",
                "- This availability state says nothing about research completeness or the field.",
            ]
        )
    else:
        lines.append("- Private record bodies and identities are not projected into this Hub view.")
    lines.extend(["", "### Literature / source availability", ""])
    if source_projection_present:
        lines.append(
            "- A source/Zotero projection exists outside this view; source identities and "
            "literature claims are not rendered here."
        )
    else:
        lines.extend(
            [
                "- No populated source/Zotero projection is available in this snapshot.",
                "- The source panel is explicitly empty/unavailable; this is not a scientific "
                "finding.",
            ]
        )
    lines.extend(
        [
            "",
            "### Scientific evidence state",
            "",
            "- No private scientific evidence is represented by this view.",
            "- Historical technical Evidence appears only in the Technical view and remains "
            "implementation provenance.",
            "",
            "### Accepted scientific claim state",
            "",
            "- No accepted scientific claim is created or implied by this Hub view.",
            "",
        ]
    )
    return lines


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
            "## Component Hubs",
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
            "Each Component Hub starts with Overview and opens Technical or Research views "
            "of that same Component identity.",
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
            + _derived_link(hub.paths.research, "supported research navigation and availability"),
            "",
        ]
    )
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def _render_component_hub_interface_lane(atlas: Atlas, hub: ComponentHubModel) -> list[str]:
    if hub.interface_ids:
        return _render_lane(atlas, "Interface lane", hub.interface_ids)
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
    lines.extend(_render_lane(atlas, "Contract lane", hub.contract_ids))
    lines.extend(_render_lane(atlas, "Data Artifact lane", hub.data_artifact_ids))
    lines.extend(_render_lane(atlas, "Measurement lane", hub.measurement_point_ids))
    lines.extend(_render_status_axes(atlas, subject, hub.measurement_point_ids))
    lines.extend(_render_exact_relationships(atlas, hub.selected_ids))
    lines.extend(_render_historical_evidence(atlas, hub.selected_ids))
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def _render_component_hub_research(
    atlas: Atlas,
    hub: ComponentHubModel,
    snapshot: Snapshot,
    source_projection_present: bool,
) -> list[str]:
    lines = _render_hub_header(atlas, hub, "research")
    lines.extend(_render_private_state(snapshot, source_projection_present))
    lines.extend(_render_hub_return_navigation(atlas, hub))
    return lines


def render_component_hub_view(
    commit: str,
    atlas: Atlas,
    hub: ComponentHubModel,
    view: Literal["overview", "technical", "research"],
    snapshot: Snapshot,
    source_projection_present: bool,
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
        lines = _render_component_hub_research(atlas, hub, snapshot, source_projection_present)
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
    source_atlas_schema: Literal["0.2"]
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


def views_tree(commit: str, public_base: bytes, direct_base: bytes) -> dict[PurePosixPath, bytes]:
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
        source_atlas_schema="0.2",
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
) -> dict[PurePosixPath, bytes]:
    tree = views_tree(commit, public_base, direct_base)
    old = ManifestV1.model_validate(read_yaml(utf8(tree.pop(MANIFEST))))
    tree[REFERENCE_INDEX] = render_index(reference)
    tree[NAVIGATION] = render_navigation(reference, atlas, locators)
    tree[K3_HOME] = render_k3_home(commit, atlas)
    for subject_id, paths in COMPONENT_HUB_PATHS.items():
        hub = _component_hub_model(atlas, subject_id)
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
            )
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
        view_schema_version="2.3",
        reference_index_schema_version="1.0",
        private_input_fingerprint=reference.private_input_fingerprint,
        owned_files=owned_files,
    )
    tree[MANIFEST] = yaml_text(
        ManifestV23.model_validate(data).model_dump(exclude_none=True)
    ).encode()
    return tree


def authored_snapshot(vault: Path, atlas: Atlas) -> tuple[Snapshot, dict[str, PurePosixPath]]:
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
    locators = {props["wiki_id"]: path for props, path in zip(properties, paths, strict=True)}
    return snapshot, locators


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
                or (relative.parent == PurePosixPath("indexes") and relative.suffix == ".md")
            )
            or (
                manifest.view_schema_version in {"2.0", "2.1", "2.2", "2.3"}
                and relative == REFERENCE_INDEX
            )
            or (
                manifest.view_schema_version in {"2.0", "2.1", "2.2"}
                and relative in K3_PRIOR_PAYLOADS
            )
            or (
                manifest.view_schema_version == "2.3"
                and relative in (K3_PAYLOADS | K3_PRIOR_PAYLOADS)
            )
            or (manifest.view_schema_version in {"2.2", "2.3"} and relative == HIERARCHY)
            or (
                manifest.view_schema_version in {"2.2", "2.3"}
                and relative.parent == HIERARCHY_DIR
                and relative.suffix == ".md"
                and re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", relative.stem)
            )
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
    snapshot, locators = authored_snapshot(vault, atlas)
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
