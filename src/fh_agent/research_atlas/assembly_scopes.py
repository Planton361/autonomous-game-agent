"""Registry-derived, presentation-only Assembly Scope navigation surfaces."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from pathlib import PurePosixPath

from .schema import TechnicalIdentity
from .validator import Atlas

PUBLIC_OBSERVE_SCOPE_PATH = PurePosixPath("Assembly Scopes/Observe.md")
OBSERVE_SCOPE_RELATIVE_PATH = PurePosixPath("assembly-scopes/Observe.md")
PRIVATE_OBSERVE_SCOPE_PATH = PurePosixPath("_generated/derived") / OBSERVE_SCOPE_RELATIVE_PATH

OBSERVE_LANDMARK_IDS = (
    "CMP-VISIBLE-STATE-BRIDGE",
    "CMP-NO-SPOILER-FIREWALL",
    "CMP-PERCEPTION",
    "DAT-OBSERVATION",
)
OBSERVE_CARD_ORDER = (
    "CMP-NO-SPOILER-FIREWALL",
    "CMP-VISIBLE-STATE-BRIDGE",
    "CMP-PERCEPTION",
    "DAT-OBSERVATION",
)
OBSERVE_LANDMARK_TYPES = {
    "CMP-VISIBLE-STATE-BRIDGE": "Component",
    "CMP-NO-SPOILER-FIREWALL": "Component",
    "CMP-PERCEPTION": "Component",
    "DAT-OBSERVATION": "DataArtifact",
}
OBSERVE_COMPONENT_IDS = tuple(
    identity for identity in OBSERVE_LANDMARK_IDS if OBSERVE_LANDMARK_TYPES[identity] == "Component"
)

_CARD_ACTIONS = {
    "CMP-NO-SPOILER-FIREWALL": "Open No-Spoiler Firewall",
    "CMP-VISIBLE-STATE-BRIDGE": "Open Visible-State Bridge",
    "CMP-PERCEPTION": "Open Perception",
    "DAT-OBSERVATION": "Open Observation",
}
_LANE_RELATIONS = {
    "Interface": frozenset({"supplies", "consumes"}),
    "Contract": frozenset({"supplies", "consumes", "constrains", "executes", "verifies"}),
    "DataArtifact": frozenset(
        {"supplies", "consumes", "observes", "updates", "retrieves_from", "derived_from"}
    ),
    "MeasurementPoint": frozenset({"measured_at"}),
}


def registry_content_revision(atlas: Atlas) -> str:
    """Return a stable content revision for the Registry model used by this projection."""
    payload = {
        "entities": [
            atlas.entities[identity].model_dump(mode="json") for identity in sorted(atlas.entities)
        ],
        "relationships": [
            edge.model_dump(mode="json")
            for edge in sorted(
                atlas.relationships,
                key=lambda item: (item.source, item.relation, item.target),
            )
        ],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _expected_landmarks(atlas: Atlas) -> None:
    for identity, expected_type in OBSERVE_LANDMARK_TYPES.items():
        node = atlas.entities.get(identity)
        if not isinstance(node, TechnicalIdentity) or node.type != expected_type:
            raise ValueError(f"Observe landmark identity/type drift: {identity}")


def _safe_link_label(value: str) -> str:
    return re.sub(r"[\[\]|\r\n]", " ", value)


def public_identity_link(atlas: Atlas, identity: str, label: str) -> str:
    """Build a public Atlas wikilink through the existing ID/type path resolver."""
    from .workspace import note_path_for

    try:
        node = atlas.entities[identity]
    except KeyError as exc:
        raise ValueError(f"Observe link endpoint is missing: {identity}") from exc
    path = note_path_for(node.id, node.type, node.name).with_suffix("")
    return f"[[{path}|{_safe_link_label(label)}]]"


def render_observe_scope(
    atlas: Atlas,
    *,
    identity_link: Callable[[str, str], str],
    back_link: str,
    source_revision: str,
    source_commit: str | None,
    detail_links: Sequence[str],
    research_lines: Sequence[str],
    research_empty_note: str,
) -> str:
    """Render one Observe-only scope from exact Registry facts and supplied navigation rows."""
    _expected_landmarks(atlas)
    selected = set(OBSERVE_LANDMARK_IDS)
    edges = sorted(
        (
            edge
            for edge in atlas.relationships
            if edge.source in selected or edge.target in selected
        ),
        key=lambda edge: (edge.source, edge.relation, edge.target),
    )

    lines = [
        (
            f"{back_link} · **Navigation location:** Agent Anatomy / Observe "
            "(static presentation breadcrumb)"
        ),
        "",
        "**OBSERVE — Observation Integrity / State**",
        "",
        "Visible observation boundary, processing and payload.",
        "",
        "**Presentation context:** Acquire · **Observe** · Retain / Retrieve",
        "*Presentation-only navigation; it does not describe technical dependencies.*",
        "",
        "## Observe landmarks",
        "",
    ]

    firewall = atlas.entities["CMP-NO-SPOILER-FIREWALL"]
    firewall_action = identity_link(
        "CMP-NO-SPOILER-FIREWALL", _CARD_ACTIONS["CMP-NO-SPOILER-FIREWALL"]
    )
    bridge_action = identity_link(
        "CMP-VISIBLE-STATE-BRIDGE", _CARD_ACTIONS["CMP-VISIBLE-STATE-BRIDGE"]
    )
    lines.extend(
        [
            f"### {firewall.name}",
            f"Type: `{firewall.type}` · Stable ID: `CMP-NO-SPOILER-FIREWALL` — "
            f"Enforces the visible-data and no-spoiler boundary. **Action:** {firewall_action}",
            "",
            "> **Visible-State Bridge — OPTIONAL**",
            ">",
            (
                "> Type: `Component` · Stable ID: `CMP-VISIBLE-STATE-BRIDGE` — Optional "
                "screenshot-bound, allowlisted bridge assistance remains subject to the "
                f"no-spoiler boundary. **Action:** {bridge_action}"
            ),
            ">",
            (
                "> Reduced emphasis and proximity are presentation-only; they do not claim "
                "Firewall containment."
            ),
            "",
        ]
    )
    perception = atlas.entities["CMP-PERCEPTION"]
    observation = atlas.entities["DAT-OBSERVATION"]
    perception_action = identity_link("CMP-PERCEPTION", _CARD_ACTIONS["CMP-PERCEPTION"])
    observation_action = identity_link("DAT-OBSERVATION", _CARD_ACTIONS["DAT-OBSERVATION"])
    lines.extend(
        [
            f"### {perception.name}",
            f"Type: `{perception.type}` · Stable ID: `CMP-PERCEPTION` — "
            f"Assembles signals from visible observations. **Action:** {perception_action}",
            "",
            f"### {observation.name}",
            f"Type: `{observation.type}` · Stable ID: `DAT-OBSERVATION` — "
            "Typed visible-observation payload carrying visible signals and evidence "
            f"references. **Action:** {observation_action}",
            "",
            "## Exact Registry relations",
            "",
            (
                "Each row preserves the Registry direction. `part_of` is technical parenthood; "
                "`presented_in_domain` is presentation grouping."
            ),
            "",
            "| Source | Predicate | Target |",
            "| --- | --- | --- |",
        ]
    )
    for edge in edges:
        source = atlas.entities[edge.source]
        target = atlas.entities[edge.target]
        lines.append(
            f"| {identity_link(source.id, f'{source.name} · {source.id}')} "
            f"| `{edge.relation}` "
            f"| {identity_link(target.id, f'{target.name} · {target.id}')} |"
        )
    lines.extend(
        [
            "",
            (
                "The Registry declares no Bridge → Firewall → Perception pipeline edge. "
                "The order above is presentation-only."
            ),
            "",
            "## Technical endpoint lanes",
            "",
            (
                "Only direct Registry relations from the four selected landmarks can populate "
                "these lanes."
            ),
            "",
        ]
    )
    for endpoint_type in ("Interface", "Contract", "DataArtifact", "MeasurementPoint"):
        lines.extend([f"### {endpoint_type}s", ""])
        lane_rows: list[str] = []
        for edge in edges:
            if edge.relation not in _LANE_RELATIONS[endpoint_type]:
                continue
            if edge.source in selected:
                neighbor_id = edge.target
            elif edge.target in selected:
                neighbor_id = edge.source
            else:
                continue
            neighbor = atlas.entities[neighbor_id]
            if neighbor.type != endpoint_type:
                continue
            source = atlas.entities[edge.source]
            target = atlas.entities[edge.target]
            lane_rows.append(
                f"- {identity_link(neighbor_id, f'{neighbor.name} · {neighbor.id}')} · "
                f"`{neighbor.type}` — {identity_link(source.id, f'{source.name} · {source.id}')} "
                f"`{edge.relation}` → {identity_link(target.id, f'{target.name} · {target.id}')}"
            )
        lines.extend(
            lane_rows
            or [
                (
                    "No directly related endpoint of this type is mapped for the four selected "
                    "landmarks."
                )
            ]
        )
        lines.append("")

    lines.extend(["## Existing W05 Observation detail", ""])
    if detail_links:
        lines.extend(
            [
                "The existing W05 Technical Details Markdown and native Canvas are reused.",
                "",
                *[f"- {link}" for link in detail_links],
                "",
            ]
        )
    else:
        lines.extend(
            [
                (
                    "The W05 detail files are available in the private derived Workspace; this "
                    "public-safe fallback does not link into that private output."
                ),
                "",
            ]
        )

    question_edges = [
        edge
        for edge in edges
        if edge.relation == "related_to_research_question"
        and (edge.source in selected or edge.target in selected)
    ]
    lines.extend(
        [
            "## Research attached to listed technical subjects",
            "",
            (
                "Research navigation is derived from exact listed technical subjects. No "
                "Research → Observe edge, Domain inheritance, descendant expansion, or "
                "Assembly-level relevance is created."
            ),
            "",
            "### Direct Registry Research Question relations",
            "",
        ]
    )
    if question_edges:
        for edge in question_edges:
            source = atlas.entities[edge.source]
            target = atlas.entities[edge.target]
            lines.append(
                f"- {identity_link(source.id, f'{source.name} · {source.id}')} "
                f"`{edge.relation}` → {identity_link(target.id, f'{target.name} · {target.id}')}"
            )
    else:
        lines.append(
            "No direct Registry Research Question relation is declared for these exact subjects."
        )
    lines.extend(["", "### Eligible declared literature navigation", ""])
    lines.extend(research_lines or [research_empty_note])
    lines.extend(
        [
            "",
            (
                "These paths are navigation only; they do not establish evidence, coverage, "
                "novelty, completeness, consensus, a gap, or an accepted scientific claim."
            ),
            "",
            "## Authority, revision and limitations",
            "",
            f"- Generated Registry model revision: `{source_revision}`.",
        ]
    )
    if source_commit is not None:
        lines.append(f"- Generated source commit: `{source_commit}`.")
    lines.extend(
        [
            (
                "- This Markdown scope is a presentation/navigation view, not a Registry identity, "
                "technical parent or Component Hub."
            ),
            (
                "- Exact Registry records and relations remain authoritative; this view creates no "
                "technical relation or scientific status."
            ),
            (
                "- The four-landmark selection is fixed for this reference slice; Temporal State "
                "is not an Observe landmark."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_public_observe_scope(atlas: Atlas) -> str:
    """Render the public-safe Markdown fallback from Registry content only."""
    from .workspace import ANATOMY_PATH, frontmatter

    body = render_observe_scope(
        atlas,
        identity_link=lambda identity, label: public_identity_link(atlas, identity, label),
        back_link=f"[[{ANATOMY_PATH.with_suffix('')}|← Agent Anatomy]]",
        source_revision=registry_content_revision(atlas),
        source_commit=None,
        detail_links=(),
        research_lines=(),
        research_empty_note=(
            "Private declared-reference paths are unavailable in this public-safe fallback; "
            "no private Research content is read or copied here."
        ),
    )
    metadata = {
        "atlas_workspace_generated": True,
        "atlas_presentation_view": "assembly-scope",
        "atlas_presentation_only": True,
        "atlas_registry_revision": registry_content_revision(atlas),
    }
    return frontmatter(metadata) + body
