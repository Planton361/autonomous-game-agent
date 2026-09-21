"""Private declared-reference navigation and direct Bases; no scientific adjudication."""

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

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

K3_HOME = PurePosixPath("indexes/Research Knowledge Home.md")
MEMORY_WORKBENCH = PurePosixPath("workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL.md")
VERIFIER_WORKBENCH = PurePosixPath("workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER.md")
LEGACY_MEMORY_WORKBENCH = PurePosixPath("workbenches/CMP-MEM-RETRIEVAL — Memory Retrieval.md")
LEGACY_VERIFIER_WORKBENCH = PurePosixPath(
    "workbenches/CMP-INDEPENDENT-VERIFIER — Independent Verifier.md"
)
K3_PAYLOADS = frozenset((K3_HOME, MEMORY_WORKBENCH, VERIFIER_WORKBENCH))
LEGACY_K3_PAYLOADS = frozenset((LEGACY_MEMORY_WORKBENCH, LEGACY_VERIFIER_WORKBENCH))
K3_PRIOR_PAYLOADS = K3_PAYLOADS | LEGACY_K3_PAYLOADS
K3_VIEW_SCHEMA_VERSION = "1.1"

MEMORY_IDS = (
    "CMP-MEM-RETRIEVAL",
    "SYS-AGA",
    "DOM-EVIDENCE-MEMORY",
    "IF-MEM-CORTEX",
    "CON-CORTEX-CONTEXT",
    "DAT-RETRIEVAL-SNAPSHOT",
    "MEAS-RETRIEVAL-DELIVERY-001",
)
VERIFIER_IDS = (
    "CMP-INDEPENDENT-VERIFIER",
    "SYS-AGA",
    "DOM-VERIFY-LEARN",
    "DAT-OBSERVATION",
    "DAT-VISIBLE-OUTCOME",
    "CON-VERIFIER-RESULT",
)


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


def _render_workbench_orientation(atlas: Atlas, subject_id: str, title: str) -> list[str]:
    parents = _relationship_targets(atlas, subject_id, "part_of")
    groups = _relationship_targets(atlas, subject_id, "presented_in_domain")
    broader = (
        "; ".join(_technical_link(atlas, identity) for identity in parents)
        + " — exact Registry `part_of`."
        if parents
        else "No technical parent is declared in the Registry; none is inferred."
    )
    presentation = (
        "; ".join(_technical_link(atlas, identity) for identity in groups)
        + " — Registry navigation grouping only, not technical ancestry."
        if groups
        else "No Registry presentation group is declared; none is inferred."
    )
    return _render_orientation_header(
        title=title,
        surface="Component workbench",
        stable_id=subject_id,
        home=_derived_link(K3_HOME, "Research Knowledge Home") + ".",
        broader_context=broader,
        presentation_context=presentation,
        research_fallback=_derived_link(INDEX, "Direct Views Index") + ".",
    )


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


def _render_status_table(atlas: Atlas, identities: tuple[str, ...]) -> list[str]:
    lines = [
        "## Registry status fields (kept separate)",
        "",
        "These are public Registry fields, not a combined score or maturity claim.",
        "",
        "| Stable ID | Type | Architecture authority | Implementation | Technical verification |",
        "| --- | --- | --- | --- | --- |",
    ]
    for identity in identities:
        node = _k3_node(atlas, identity)
        if not isinstance(node, TechnicalIdentity):
            continue
        status = node.technical
        lines.append(
            f"| `{node.id}` | `{node.type}` | `{status.architecture_authority}` | "
            f"`{status.implementation_status}` | `{status.verification_status}` |"
        )
    lines.append("")
    return lines


def _render_status_axes(
    atlas: Atlas, subject: TechnicalIdentity, measurement_ids: tuple[str, ...]
) -> list[str]:
    if measurement_ids:
        measurement_presence = _markdown_table_cell(
            "; ".join(_technical_link(atlas, identity) for identity in measurement_ids)
        )
    else:
        measurement_presence = "No MeasurementPoint selected for this workbench"
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
        "| Scientific evidence | No private scientific evidence represented by this K3 baseline | "
        "Historical technical Evidence remains implementation provenance only. |",
        "| Accepted scientific claim | None created or implied by this view | "
        "An empty panel does not mean the topic is unresearched. |",
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
    lines = ["## Research and literature state", "", "### Authored private research", ""]
    lines.append(f"- Authored private research record count: `{count}`.")
    if count == 0:
        lines.extend(
            [
                "- No authored private research records in this baseline.",
                "- This is an empty/unavailable research panel, not evidence that literature is "
                "absent, "
                "exhausted, complete or scientifically resolved.",
            ]
        )
    else:
        lines.append(
            "- Private record bodies and identities are not projected into this technical "
            "workbench."
        )
    lines.extend(["", "### Literature / source state", ""])
    if source_projection_present:
        lines.append(
            "- A source/Zotero projection exists outside this K3 slice; K3 does not render source "
            "identities or make literature claims."
        )
    else:
        lines.extend(
            [
                "- No populated source/Zotero projection in this baseline.",
                "- The source panel is explicitly empty/unavailable; this is not a scientifically "
                "negative finding.",
            ]
        )
    lines.extend(
        [
            "",
            "### Scientific evidence state",
            "",
            "- No private scientific evidence is represented by this K3 baseline.",
            "- Historical technical Evidence below remains implementation provenance only.",
            "",
            "### Accepted scientific claim state",
            "",
            "- No accepted scientific claim is created or implied by this workbench.",
            "",
        ]
    )
    return lines


def render_k3_home(commit: str, atlas: Atlas) -> bytes:
    for identity in (*MEMORY_IDS, *VERIFIER_IDS):
        _k3_node(atlas, identity)
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        k3_view_schema_version=K3_VIEW_SCHEMA_VERSION,
        k3_surface="system-anatomy-navigation",
    )
    body = _render_orientation_header(
        title="Research Knowledge Home",
        surface="Workspace home and current System Anatomy entry",
        home="Current page; no parent is asserted.",
        broader_context=(
            _technical_surface_link(TECHNICAL_MAP, "System Anatomy")
            + "; "
            + _technical_surface_link(TECHNICAL_HOME, "Technical Atlas Index")
            + "."
        ),
        research_fallback=_derived_link(INDEX, "Direct Views Index") + ".",
    )
    body.extend(
        [
            "Maintained K3 entry/navigation surface for the accepted two-subject visual slice.",
            "",
            "## Component workbenches",
            "",
            f"- {_derived_link(MEMORY_WORKBENCH, 'Memory Retrieval · CMP-MEM-RETRIEVAL')}",
            "- "
            + _derived_link(VERIFIER_WORKBENCH, "Independent Verifier · CMP-INDEPENDENT-VERIFIER"),
            "",
            "## Navigation contract",
            "",
            "Use stable Atlas IDs for identity. `part_of` is technical hierarchy; "
            "`presented_in_domain` is presentation grouping only. "
            "No visual relation is invented here.",
            "",
            "Each workbench separates target architecture, implementation, technical verification, "
            "measurement validity, literature, scientific evidence and accepted claims.",
            "",
            "The K3 workbenches retain explicit empty/unavailable research and source states. "
            "They do not couple the Research Wiki to runtime Agent Memory, Retrieval or Cortex.",
            "",
        ]
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(body)).encode()


def render_k3_workbench(
    commit: str,
    atlas: Atlas,
    subject_id: str,
    snapshot: Snapshot,
    source_projection_present: bool,
) -> bytes:
    if subject_id == "CMP-MEM-RETRIEVAL":
        identities = MEMORY_IDS
        interface_ids = ("IF-MEM-CORTEX",)
        contract_ids = ("CON-CORTEX-CONTEXT",)
        data_ids = ("DAT-RETRIEVAL-SNAPSHOT",)
        measurement_ids = ("MEAS-RETRIEVAL-DELIVERY-001",)
        title = "Memory Retrieval"
        receiver = (
            f"- Receiver context for direction only: {_technical_link(atlas, 'CMP-CORTEX')}. "
            "This context link does not assert a new Registry relationship."
        )
    elif subject_id == "CMP-INDEPENDENT-VERIFIER":
        identities = VERIFIER_IDS
        interface_ids = ()
        contract_ids = ("CON-VERIFIER-RESULT",)
        data_ids = ("DAT-OBSERVATION", "DAT-VISIBLE-OUTCOME")
        measurement_ids = ()
        title = "Independent Verifier"
        receiver = ""
    else:
        raise ProjectionError(f"Unsupported K3 workbench subject: {subject_id}")

    subject = _k3_node(atlas, subject_id)
    if not isinstance(subject, TechnicalIdentity):
        raise ProjectionError(f"K3 workbench subject is not a technical identity: {subject_id}")
    for identity in identities:
        _k3_node(atlas, identity)
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        k3_view_schema_version=K3_VIEW_SCHEMA_VERSION,
        k3_surface="component-workbench",
        k3_subject=subject_id,
    )
    lines = _render_workbench_orientation(atlas, subject_id, title)
    lines.extend(
        [
            "## Component identity and role",
            "",
            f"- Stable Atlas ID: `{subject.id}`",
            f"- Component: {_technical_link(atlas, subject.id)}",
            f"- Role: {subject.description}",
            "",
        ]
    )
    lines.extend(_render_status_axes(atlas, subject, measurement_ids))
    if receiver:
        lines.extend(["## Direction context", "", receiver, ""])
    if interface_ids:
        lines.extend(_render_lane(atlas, "Interface lane", interface_ids))
    else:
        lines.extend(
            [
                "## Interface lane",
                "",
                "- **Explicitly empty.** No corresponding `IF-*` Registry record exists for this "
                "Independent Verifier slice in the accepted K2 selection.",
                "- No Interface is invented, and another relationship type is not rendered as an "
                "Interface.",
                "",
            ]
        )
    lines.extend(_render_lane(atlas, "Contract lane", contract_ids))
    lines.extend(_render_lane(atlas, "Data lane", data_ids))
    lines.extend(_render_lane(atlas, "Measurement lane", measurement_ids))
    lines.extend(_render_exact_relationships(atlas, identities))
    lines.extend(_render_status_table(atlas, identities))
    lines.extend(
        [
            "## Measurement validity",
            "",
        ]
    )
    if measurement_ids:
        lines.append(
            f"- Measurement anchor: {_technical_link(atlas, measurement_ids[0])}. "
            "The anchor is not proof of measurement validity or an accepted claim."
        )
    else:
        lines.append(
            "- No measurement anchor is selected for this workbench; measurement validity is "
            "not established here."
        )
    lines.extend(["", ""])
    lines.extend(_render_historical_evidence(atlas, identities))
    lines.extend(_render_private_state(snapshot, source_projection_present))
    lines.extend(
        [
            "## Boundary reminders",
            "",
            "- Technical implementation markers are not scientific evidence.",
            "- Technical verification is not measurement validity.",
            "- Literature/source absence in this baseline is an unavailable panel, not a claim "
            "about "
            "the field.",
            "- K3 does not create private records, source identities, interfaces, claims or "
            "runtime "
            "coupling.",
            "",
            f"{_derived_link(K3_HOME, 'Back to Research Knowledge Home')}",
            "",
        ]
    )
    return ("---\n" + yaml_text(props) + "---\n" + "\n".join(lines)).encode()


class OwnedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    sha256: SHA256


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


def views_tree(commit: str, public_base: bytes, direct_base: bytes) -> dict[PurePosixPath, bytes]:
    """Retained v1 renderer; v2 extends its exact Base payloads under the same owner."""
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
    tree[MEMORY_WORKBENCH] = render_k3_workbench(
        commit,
        atlas,
        "CMP-MEM-RETRIEVAL",
        snapshot,
        source_projection_present,
    )
    tree[VERIFIER_WORKBENCH] = render_k3_workbench(
        commit,
        atlas,
        "CMP-INDEPENDENT-VERIFIER",
        snapshot,
        source_projection_present,
    )
    text = utf8(tree[INDEX]).replace(
        "Navigation only; no scientific data index.",
        "Declared structured reference index for navigation/audit; no scientific adjudication.",
    )
    tree[INDEX] = (
        text
        + f"\n- [[{OWNED_ROOT / NAVIGATION}|Declared Literature Navigation]]\n"
        + f"- {_derived_link(K3_HOME, 'Research Knowledge Home')}\n"
    ).encode()
    data = old.model_dump()
    data.update(
        view_schema_version="2.0",
        reference_index_schema_version="1.0",
        private_input_fingerprint=reference.private_input_fingerprint,
        owned_files=[OwnedFile(path=str(p), sha256=digest(b)) for p, b in sorted(tree.items())],
    )
    tree[MANIFEST] = yaml_text(Manifest.model_validate(data).model_dump()).encode()
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
        # V1 cannot claim YAML; V2 adds exactly one fixed YAML payload, not a subtree.
        if not (
            len(relative.parts) == 2
            and (
                (relative.parent == PurePosixPath("bases") and relative.suffix == ".base")
                or (relative.parent == PurePosixPath("indexes") and relative.suffix == ".md")
            )
            or (manifest.view_schema_version == "2.0" and relative == REFERENCE_INDEX)
            or (manifest.view_schema_version == "2.0" and relative in K3_PRIOR_PAYLOADS)
        ):
            raise ProjectionError("Invalid direct-view ownership path/type")
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
        if relative == REFERENCE_INDEX:
            metadata = read_yaml(utf8(data))
            owned = (
                metadata.get("generated_by") == OWNER
                and metadata.get("index_schema_version") == "1.0"
            )
        elif relative.suffix == ".base":
            owned = data.startswith(BASE_OWNER.encode())
        else:
            owned = markdown_parts(utf8(data))[0].get("generated_by") == OWNER
        if not owned:
            raise ProjectionError("Prior-owned view lost its owner marker; preserve or restore it")
        if relative not in tree and digest(data) != item.sha256:
            raise ProjectionError("Obsolete owned view was edited; preserve edits before cleanup")
    if check:
        if actual != tree.keys() or any(
            target_path(root, p).read_bytes() != data for p, data in tree.items()
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
        "--check", action="store_true", help="Validate exact views without any writes"
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
