"""Deterministic, Registry-grounded W03 Excalidraw navigation surfaces."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import PurePosixPath

from .schema import Relationship
from .validator import Atlas
from .workspace import (
    ANATOMY_PATH,
    DOMAIN_SLICE_PATH,
    GENERATED_NOTICE,
    HOME_PATH,
    MAP_PATH,
    _element,
    _text,
    frontmatter,
    map_record_ids,
    note_link,
    note_path_for,
    parse_frontmatter,
)

ANATOMY_REGIONS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "environment",
        "01  Environment / acquisition",
        "Visible play surface and capture entry",
        ("ENV-GAME-INSTANCE", "CMP-SCREEN-CAPTURE"),
    ),
    (
        "observation",
        "02  Observation integrity / state",
        "All observation paths remain within the No-Spoiler Firewall",
        (
            "CMP-VISIBLE-STATE-BRIDGE",
            "CMP-NO-SPOILER-FIREWALL",
            "CMP-PERCEPTION",
            "DAT-OBSERVATION",
        ),
    ),
    (
        "evidence-memory",
        "03  Evidence / memory / retrieval",
        "Admissible evidence and bounded context",
        ("CMP-EVIDENCE-LEDGER", "CMP-MEMORY", "CMP-MEM-RETRIEVAL"),
    ),
    (
        "cognition",
        "04  Cognition",
        "Cortex proposes goals and constraints; it does not control primitive keys or timing",
        ("CMP-CORTEX", "CON-PLANNER-OUTPUT"),
    ),
    (
        "executive",
        "05  Executive control / contracts",
        "Manager validates proposals, grounds targets, and owns bounded contracts",
        ("CMP-MANAGER", "CMP-MANAGER-GROUNDING", "CON-SKILL-CONTRACT"),
    ),
    (
        "action-safety",
        "06  Action / safety",
        "Body acts only inside an active contract; SafetyFilter and InputExecutor guard input",
        ("CMP-BODY", "CMP-BOUNDED-REFLEX", "CMP-SAFETY-FILTER", "CMP-INPUT-EXECUTOR"),
    ),
    (
        "verification",
        "07  Independent verification / outcome / replay",
        (
            "Verifier is outside Cortex decision authority; "
            "verified outcomes feed replay and memory paths"
        ),
        (
            "CMP-INDEPENDENT-VERIFIER",
            "DAT-VISIBLE-OUTCOME",
            "CMP-REPLAY-BUFFER",
            "CON-MEMORY-UPDATE-REQUEST",
        ),
    ),
)
BETWEEN_RUN_IDS = (
    "CMP-SKILL-TRAINER",
    "DAT-CANDIDATE-BODY-VERSION",
    "CMP-BODY-CERTIFICATION",
)
ANATOMY_RECORD_IDS = frozenset(
    {identity for _, _, _, identities in ANATOMY_REGIONS for identity in identities}
    | set(BETWEEN_RUN_IDS)
    | {"SYS-AGA"}
)
DOMAIN_MEMBER_IDS = frozenset({"CMP-MEMORY", "CMP-MEM-RETRIEVAL", "CMP-EVIDENCE-LEDGER"})
DOMAIN_LINKED_IDS = frozenset(
    {
        "SYS-AGA",
        *DOMAIN_MEMBER_IDS,
        "IF-MEM-CORTEX",
        "DAT-RETRIEVAL-SNAPSHOT",
        "CMP-CORTEX",
        "CON-CORTEX-CONTEXT",
    }
)
DOMAIN_RELATION_KEYS = (
    ("CMP-MEMORY", "part_of", "SYS-AGA"),
    ("CMP-MEM-RETRIEVAL", "part_of", "SYS-AGA"),
    ("CMP-EVIDENCE-LEDGER", "part_of", "SYS-AGA"),
    ("CMP-MEM-RETRIEVAL", "supplies", "IF-MEM-CORTEX"),
    ("CMP-MEM-RETRIEVAL", "supplies", "DAT-RETRIEVAL-SNAPSHOT"),
    ("CMP-CORTEX", "consumes", "IF-MEM-CORTEX"),
    ("CMP-CORTEX", "consumes", "DAT-RETRIEVAL-SNAPSHOT"),
    ("CON-CORTEX-CONTEXT", "constrains", "CMP-MEM-RETRIEVAL"),
)
BETWEEN_RUN_RELATION_KEYS = (
    ("CMP-SKILL-TRAINER", "supplies", "DAT-CANDIDATE-BODY-VERSION"),
    ("CMP-BODY-CERTIFICATION", "verifies", "DAT-CANDIDATE-BODY-VERSION"),
)
FLOW_KEYS = (
    ("environment", "observation"),
    ("observation", "evidence-memory"),
    ("evidence-memory", "cognition"),
    ("cognition", "executive"),
    ("executive", "action-safety"),
    ("action-safety", "verification"),
)

_REGION_BOXES: Mapping[str, tuple[int, int, int, int]] = {
    "environment": (150, 330, 290, 250),
    "observation": (540, 310, 290, 270),
    "evidence-memory": (920, 325, 310, 255),
    "cognition": (1350, 300, 300, 285),
    "executive": (1340, 650, 310, 250),
    "action-safety": (780, 680, 390, 195),
    "verification": (170, 665, 360, 215),
}
_REGION_COLORS: Mapping[str, str] = {
    "environment": "#d8edf2",
    "observation": "#e9e5f6",
    "evidence-memory": "#dcebdd",
    "cognition": "#ffe6ba",
    "executive": "#f8d9c9",
    "action-safety": "#dce5f5",
    "verification": "#f0dfec",
}
_REGION_SHAPES: Mapping[str, str] = {
    "environment": "ellipse",
    "observation": "diamond",
    "evidence-memory": "ellipse",
    "cognition": "ellipse",
    "executive": "diamond",
    "action-safety": "rectangle",
    "verification": "ellipse",
}
_REGION_LABELS: Mapping[str, str] = {
    "environment": "ACQUIRE\nEnvironment",
    "observation": "OBSERVE\nIntegrity + state",
    "evidence-memory": "RETAIN / RETRIEVE\nEvidence + memory",
    "cognition": "REASON\nCortex",
    "executive": "CONTRACT\nManager",
    "action-safety": "ACT\nBody + safety + input",
    "verification": "VERIFY\nIndependent outcome",
}
_NODE_CARD = "#ffffff"
_INK = "#26384b"
_MUTED = "#526477"
_CANVAS_SIZE = (2100, 1270)
_DOMAIN_CANVAS_SIZE = (2800, 1450)


def _shape(
    identity: str,
    box: tuple[int, int, int, int],
    *,
    background: str = "transparent",
    stroke: str = _INK,
    stroke_style: str = "solid",
    stroke_width: float = 1.5,
    link: str | None = None,
    custom_data: dict | None = None,
    rounded: bool = True,
    kind: str = "rectangle",
) -> dict:
    shape = _element("w03:" + identity, kind, box)
    shape.update(
        strokeColor=stroke,
        backgroundColor=background,
        strokeStyle=stroke_style,
        strokeWidth=stroke_width,
        roundness={"type": 3} if rounded and kind == "rectangle" else None,
        link=link,
    )
    if custom_data:
        shape["customData"] = custom_data
    return shape


def _text_item(
    identity: str,
    value: str,
    x: int,
    y: int,
    width: int,
    *,
    size: int = 18,
    color: str = _INK,
    link: str | None = None,
    custom_data: dict | None = None,
) -> dict:
    item = _text("w03:" + identity, value, x, y, width, size=size)
    item["strokeColor"] = color
    item["link"] = link
    if custom_data:
        item["customData"] = custom_data
    return item


def _arrow(
    identity: str,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    relation: Relationship | None = None,
    presentation_flow: tuple[str, str] | None = None,
) -> dict:
    dx, dy = end[0] - start[0], end[1] - start[1]
    arrow = _element(
        "w03:" + identity,
        "arrow",
        (start[0], start[1], abs(dx), abs(dy)),
    )
    arrow.update(
        points=[[0, 0], [dx, dy]],
        startBinding=None,
        endBinding=None,
        startArrowhead=None,
        endArrowhead="arrow",
        elbowed=False,
        strokeColor="#526477" if presentation_flow else _INK,
        strokeStyle="dashed" if presentation_flow else "solid",
        strokeWidth=1.5,
    )
    if relation is not None:
        arrow["customData"] = {"atlas_relation": relation.model_dump(exclude_none=True)}
    elif presentation_flow is not None:
        arrow["customData"] = {
            "presentation_flow": {
                "kind": "runtime-orientation",
                "from": presentation_flow[0],
                "to": presentation_flow[1],
            }
        }
    return arrow


def _registry_relation(atlas: Atlas, key: tuple[str, str, str]) -> Relationship:
    source, relation, target = key
    matches = [
        edge
        for edge in atlas.relationships
        if (edge.source, edge.relation, edge.target) == (source, relation, target)
    ]
    if len(matches) != 1:
        raise ValueError(f"W03 visual relation is not uniquely present in Registry: {key}")
    return matches[0]


def _require_records(atlas: Atlas, identities: frozenset[str] | set[str]) -> None:
    missing = identities - atlas.entities.keys()
    if missing:
        raise ValueError(f"W03 visual surface is missing Registry records: {sorted(missing)}")


def _element_for_record(
    atlas: Atlas,
    identity: str,
    box: tuple[int, int, int, int],
    *,
    optional: bool = False,
) -> list[dict]:
    node = atlas.entities[identity]
    if node.type not in {
        "System",
        "Environment",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
    }:
        raise ValueError(f"W03 technical landmark has an unexpected type: {identity}")
    x, y, width, _ = box
    title = node.name
    shape = _shape(
        "record:" + identity,
        box,
        background=_NODE_CARD,
        stroke_style="dashed" if optional else "solid",
        stroke_width=1.5,
        link=note_link(node),
        custom_data={
            "atlas_id": identity,
            **({"path_style": "optional"} if optional else {}),
        },
    )
    title_element = _text_item(
        "record-name:" + identity,
        title,
        x + 12,
        y + 10,
        width - 24,
        size=15,
        link=note_link(node),
    )
    detail_element = _text_item(
        "record-type:" + identity,
        f"{node.type} · {identity}",
        x + 12,
        y + 13 + title_element["height"],
        width - 24,
        size=9,
        color=_MUTED,
        link=note_link(node),
    )
    return [shape, title_element, detail_element]


def _region(
    atlas: Atlas, key: str, title: str, subtitle: str, identities: tuple[str, ...]
) -> list[dict]:
    x, y, width, height = _REGION_BOXES[key]
    if key == "evidence-memory":
        anchor = f"[[{DOMAIN_SLICE_PATH.with_suffix('')}|Evidence, Memory & Retrieval]]"
        custom = {
            "functional_region": key,
            "domain_slice": "DOM-EVIDENCE-MEMORY",
            "atlas_landmarks": list(identities),
            "presentation_only": True,
        }
    else:
        anchor = note_link(atlas.entities[identities[0]])
        custom = {
            "functional_region": key,
            "atlas_landmarks": list(identities),
            "presentation_only": True,
        }
    custom.update(presentation_title=title, presentation_summary=subtitle)
    elements = [
        _shape(
            "region:" + key,
            (x, y, width, height),
            background=_REGION_COLORS[key],
            stroke="#496073",
            stroke_width=2.5,
            link=anchor,
            custom_data=custom,
            kind=_REGION_SHAPES[key],
        ),
        _text_item(
            "region-stage:" + key,
            _REGION_LABELS[key].split("\n", 1)[0],
            x + 50,
            y + height // 2 - 16,
            width - 100,
            size=19,
            link=anchor,
        ),
        _text_item(
            "region-name:" + key,
            _REGION_LABELS[key].split("\n", 1)[1],
            x + 50,
            y + height // 2 + 15,
            width - 100,
            size=16,
            color=_MUTED,
            link=anchor,
        ),
    ]
    # Layered instrument motifs visually distinguish acquisition, shielding,
    # storage, reasoning, control, guarded action and independent verification.
    motif_specs = {
        "environment": (((0, 0, 84, 58), "rectangle"), ((25, 11, 34, 34), "ellipse")),
        "observation": (((0, 0, 82, 82), "diamond"), ((30, 30, 22, 22), "ellipse")),
        "evidence-memory": (
            ((0, 0, 90, 62), "ellipse"),
            ((12, 9, 66, 44), "ellipse"),
            ((28, 17, 34, 28), "ellipse"),
        ),
        "cognition": (
            ((0, 0, 88, 88), "ellipse"),
            ((16, 16, 56, 56), "ellipse"),
            ((35, 35, 18, 18), "ellipse"),
        ),
        "executive": (((0, 0, 88, 88), "diamond"), ((30, 30, 28, 28), "rectangle")),
        "action-safety": (
            ((0, 0, 90, 56), "rectangle"),
            ((13, 12, 18, 30), "rectangle"),
            ((59, 12, 18, 30), "rectangle"),
        ),
        "verification": (((0, 0, 88, 88), "ellipse"), ((24, 24, 40, 40), "diamond")),
    }
    motif_x = x + (width - 90) // 2
    motif_y = y + (22 if key == "action-safety" else 15 if key == "executive" else 35)
    for index, (offset, motif_kind) in enumerate(motif_specs[key]):
        ox, oy, ow, oh = offset
        elements.append(
            _shape(
                f"motif:{key}:{index}",
                (motif_x + ox, motif_y + oy, ow, oh),
                background="#ffffff" if index == 0 else _REGION_COLORS[key],
                stroke="#496073",
                stroke_width=2,
                link=anchor,
                custom_data={"presentation_motif": key, "part": index},
                kind=motif_kind,
            )
        )
    # Small linked ports retain every W03 technical landmark without turning Home
    # into a matrix of named record cards. Exact names/IDs remain in Registry notes.
    port_width = 28
    gap = 12
    port_span = len(identities) * port_width + (len(identities) - 1) * gap
    for index, identity in enumerate(identities):
        node = atlas.entities[identity]
        optional = identity == "CMP-VISIBLE-STATE-BRIDGE"
        port_x = x + (width - port_span) // 2 + index * (port_width + gap)
        elements.append(
            _shape(
                "record:" + identity,
                (port_x, y + height - 57, 28, 28),
                kind="ellipse",
                background="#ffffff",
                stroke_style="dashed" if optional else "solid",
                stroke_width=2,
                link=note_link(node),
                custom_data={
                    "atlas_id": identity,
                    "atlas_name": node.name,
                    "visual_role": "technical-landmark-port",
                    **({"path_style": "optional"} if optional else {}),
                },
            )
        )
    return elements


def _navigation_button(
    identity: str,
    label: str,
    target: PurePosixPath,
    box: tuple[int, int, int, int],
) -> list[dict]:
    link = f"[[{target.with_suffix('')}|{label}]]"
    x, y, width, height = box
    return [
        _shape(
            "navigation:" + identity,
            box,
            background="#ffffff",
            stroke="#526477",
            stroke_width=1.4,
            link=link,
            custom_data={"navigation": identity},
        ),
        _text_item(
            "navigation-label:" + identity,
            label,
            x + 12,
            y + (height - 24) // 2,
            width - 24,
            size=14,
            link=link,
        ),
    ]


def _encode_scene(elements: list[dict], *, surface: str, width: int, height: int) -> str:
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "research-atlas",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#fbfaf7", "gridSize": None},
        "files": {},
    }
    lines = [
        frontmatter(
            {
                "excalidraw-plugin": "parsed",
                "atlas_workspace_generated": True,
                "atlas_visual_surface": surface,
                "atlas_canvas": {"width": width, "height": height},
            }
        ),
        GENERATED_NOTICE,
        "",
        (
            "Colors group functional regions only; they do not encode status, maturity, "
            "evidence or confidence."
        ),
        "",
        "%%",
        "# Excalidraw Data",
        "",
        "## Text Elements",
        "",
    ]
    lines += [
        f"{element['rawText']} ^{element['id']}\n"
        for element in elements
        if element["type"] == "text"
    ]
    lines += ["## Element Links", ""]
    lines += [
        f"{element['id']}: {element['link']}\n" for element in elements if element.get("link")
    ]
    lines += [
        "## Drawing",
        "```json",
        json.dumps(scene, ensure_ascii=False, sort_keys=True, indent=2),
        "```",
        "%%",
        "",
    ]
    return "\n".join(lines)


def render_agent_anatomy(atlas: Atlas) -> str:
    """Render one exploded system with Registry-grounded linked landmarks."""
    _require_records(atlas, ANATOMY_RECORD_IDS)
    elements = [
        _text_item("anatomy-title", "AGENT ANATOMY", 70, 30, 1060, size=38),
        _text_item(
            "anatomy-subtitle",
            "One system · acquire → observe → retain/retrieve → reason → contract → act → verify",
            73,
            90,
            1480,
            size=19,
            color=_MUTED,
            custom_data={"presentation_only": "runtime-orientation"},
        ),
        _text_item(
            "runtime-boundary-title",
            "MISSION RUN  /  frozen Body version, including Life Episode restarts",
            88,
            190,
            1650,
            size=18,
        ),
    ]
    # The shared plates and rail are explicitly presentation structure. They do not
    # assert part_of or any other Registry relationship.
    elements.extend(
        [
            _shape(
                "in-run-boundary",
                (45, 170, 2010, 795),
                stroke="#6f8191",
                stroke_style="dashed",
                stroke_width=2,
                link=note_link(atlas.entities["SYS-AGA"]),
                custom_data={"atlas_id": "SYS-AGA", "presentation_boundary": "in-run"},
            ),
            _shape(
                "chassis-upper",
                (95, 275, 1600, 365),
                kind="ellipse",
                background="#c4d5db",
                stroke="#627b88",
                stroke_width=3,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "chassis-lower",
                (600, 585, 1150, 340),
                background="#d2dee2",
                stroke="#627b88",
                stroke_width=3,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "chassis-rail",
                (365, 550, 1280, 42),
                background="#8da6b0",
                stroke="#627b88",
                stroke_width=2,
                custom_data={"presentation_structure": "shared-backplane"},
            ),
            _shape(
                "verifier-offset",
                (120, 625, 460, 285),
                kind="ellipse",
                background="#f9f4f8",
                stroke="#9a718e",
                stroke_width=2,
                custom_data={
                    "presentation_structure": "independent-verifier-pod",
                    "outside_decision_authority": True,
                },
            ),
        ]
    )
    # Dashed arrows are operator orientation, never technical Registry edges.
    for source_key, target_key in FLOW_KEYS:
        sx, sy, sw, sh = _REGION_BOXES[source_key]
        tx, ty, tw, th = _REGION_BOXES[target_key]
        if source_key == "cognition":
            start, end = (sx + sw // 2, sy + sh), (tx + tw // 2, ty)
        elif source_key in {"executive", "action-safety"}:
            start, end = (sx, sy + sh // 2), (tx + tw, ty + th // 2)
        else:
            start, end = (sx + sw, sy + sh // 2), (tx, ty + th // 2)
        elements.append(
            _arrow(
                f"runtime-flow:{source_key}:{target_key}",
                start,
                end,
                presentation_flow=(source_key, target_key),
            )
        )
    for key, title, subtitle, identities in ANATOMY_REGIONS:
        elements.extend(_region(atlas, key, title, subtitle, identities))
    elements.extend(
        [
            _text_item(
                "bridge-note",
                "Dashed port = optional visible-state bridge · no-spoiler boundary applies",
                565,
                603,
                700,
                size=13,
                color="#514a70",
            ),
            _text_item(
                "authority-note",
                "Cortex proposes · Manager contracts · Body/Reflex (active contract) → "
                "SafetyFilter → InputExecutor",
                940,
                925,
                930,
                size=14,
                color=_MUTED,
                custom_data={"presentation_only": "authority-orientation"},
            ),
            _text_item(
                "verifier-note",
                "Verifier outside Cortex decision authority · outcome before replay",
                80,
                925,
                810,
                size=13,
                color="#674760",
            ),
            _text_item(
                "anatomy-legend",
                "Dashed arrows: orientation only   ·   solid arrows: Registry relation   ·   "
                "ports: exact records",
                355,
                977,
                1400,
                size=13,
                color=_MUTED,
            ),
            _shape(
                "between-runs-boundary",
                (45, 1030, 2010, 210),
                background="#f3eee7",
                stroke="#a87955",
                stroke_style="dashed",
                stroke_width=3,
                custom_data={"presentation_boundary": "between-runs"},
            ),
            _text_item(
                "between-boundary-title",
                "BETWEEN MISSION RUNS ONLY  /  candidate → certification → future activation",
                83,
                1043,
                1800,
                size=18,
                custom_data={"presentation_only": "between-run-lifecycle"},
            ),
        ]
    )
    between_boxes = {
        "CMP-SKILL-TRAINER": (110, 1100, 420, 90),
        "DAT-CANDIDATE-BODY-VERSION": (840, 1100, 420, 90),
        "CMP-BODY-CERTIFICATION": (1570, 1100, 420, 90),
    }
    for identity, box in between_boxes.items():
        node = atlas.entities[identity]
        elements.extend(
            [
                _shape(
                    "record:" + identity,
                    box,
                    kind="ellipse",
                    background="#fffaf3",
                    stroke="#a87955",
                    stroke_width=2,
                    link=note_link(node),
                    custom_data={"atlas_id": identity, "visual_role": "between-run-stage"},
                ),
                _text_item(
                    "record-name:" + identity,
                    node.name,
                    box[0] + 45,
                    box[1] + 29,
                    box[2] - 90,
                    size=17,
                    link=note_link(node),
                ),
            ]
        )
    for key in BETWEEN_RUN_RELATION_KEYS:
        edge = _registry_relation(atlas, key)
        sx, sy, sw, sh = between_boxes[edge.source]
        tx, ty, tw, th = between_boxes[edge.target]
        if key[1] == "supplies":
            start, end = (sx + sw, sy + sh // 2), (tx, ty + th // 2)
            label_x = (start[0] + end[0]) // 2 - 42
        else:
            start, end = (sx, sy + sh // 2), (tx + tw, ty + th // 2)
            label_x = (start[0] + end[0]) // 2 - 42
        elements.extend(
            [
                _arrow(
                    f"registry:{edge.source}:{edge.relation}:{edge.target}",
                    start,
                    end,
                    relation=edge,
                ),
                _text_item(
                    f"registry-label:{edge.source}:{edge.relation}:{edge.target}",
                    edge.relation,
                    label_x,
                    sy + 61,
                    100,
                    size=10,
                    color=_MUTED,
                ),
            ]
        )

    elements.extend(
        _navigation_button(
            "research-home",
            "Research Knowledge Home",
            HOME_PATH,
            (1630, 30, 405, 54),
        )
    )
    elements.extend(
        _navigation_button(
            "domain-slice",
            "Explore Evidence / Memory / Retrieval",
            DOMAIN_SLICE_PATH,
            (1630, 98, 405, 54),
        )
    )
    return _encode_scene(
        elements,
        surface="agent-anatomy",
        width=_CANVAS_SIZE[0],
        height=_CANVAS_SIZE[1],
    )


def _relation_row(atlas: Atlas, edge: Relationship, row: int) -> list[dict]:
    source = atlas.entities[edge.source]
    target = atlas.entities[edge.target]
    x, y, width, height = 1260, 480 + row * 86, 1380, 76
    elements = [
        _shape(
            f"relation-row:{row}",
            (x, y, width, height),
            background="#ffffff",
            stroke="#91a0ae",
            stroke_width=1.2,
            custom_data={"atlas_relation": edge.model_dump(exclude_none=True)},
        ),
        _text_item(
            f"relation-source:{row}",
            source.name,
            x + 16,
            y + 8,
            475,
            size=16,
            link=note_link(source),
        ),
        _text_item(
            f"relation-source-id:{row}",
            f"{source.type} · {source.id}",
            x + 16,
            y + 40,
            475,
            size=10,
            color=_MUTED,
            link=note_link(source),
        ),
        _text_item(
            f"relation-label:{row}",
            f"{edge.relation}  →",
            x + 510,
            y + 25,
            210,
            size=13,
            color=_MUTED,
        ),
        _text_item(
            f"relation-target:{row}",
            target.name,
            x + 736,
            y + 8,
            628,
            size=16,
            link=note_link(target),
        ),
        _text_item(
            f"relation-target-id:{row}",
            f"{target.type} · {target.id}",
            x + 736,
            y + 40,
            628,
            size=10,
            color=_MUTED,
            link=note_link(target),
        ),
    ]
    return elements


def render_domain_slice(atlas: Atlas) -> str:
    """Render a curated presentation Domain with separate exact Registry relations."""
    _require_records(atlas, DOMAIN_LINKED_IDS)
    domain = atlas.entities.get("DOM-EVIDENCE-MEMORY")
    if domain is None or domain.type != "Domain":
        raise ValueError("W03 Evidence, Memory & Retrieval Domain is missing")
    membership = {
        edge.source
        for edge in atlas.relationships
        if edge.relation == "presented_in_domain" and edge.target == domain.id
    }
    if not DOMAIN_MEMBER_IDS <= membership:
        raise ValueError(
            "W03 Domain members are not supported by presented_in_domain Registry edges"
        )
    edges = [_registry_relation(atlas, key) for key in DOMAIN_RELATION_KEYS]
    elements = [
        _text_item(
            "domain-title",
            "DOMAIN SLICE  ·  Evidence, Memory & Retrieval",
            80,
            28,
            1450,
            size=30,
        ),
        _text_item(
            "domain-subtitle",
            "Curated zoom · presentation grouping only; technical ancestry stays separate",
            84,
            78,
            1650,
            size=17,
            color=_MUTED,
        ),
        _text_item(
            "domain-members-title",
            "PRESENTATION DOMAIN  ·  presented_in_domain membership only",
            100,
            405,
            990,
            size=16,
        ),
        _text_item(
            "domain-members-note",
            (
                "Memory, Memory Retrieval and Evidence Ledger are presented here as a Domain "
                "group; their shared technical parent is shown separately."
            ),
            102,
            444,
            1000,
            size=12,
            color=_MUTED,
        ),
        _text_item(
            "technical-parent-title",
            "COMMON TECHNICAL PARENT  ·  SYS-AGA",
            490,
            196,
            740,
            size=13,
            color=_MUTED,
        ),
        _text_item(
            "connections-title",
            "CONNECTED OBJECTS  ·  typed Registry relations in source → target direction",
            1280,
            402,
            1340,
            size=16,
        ),
        _text_item(
            "connections-note",
            (
                "Solid rows are explicit technical relations. Open a linked label for its exact "
                "record."
            ),
            1282,
            442,
            1330,
            size=12,
            color=_MUTED,
        ),
    ]
    elements.extend(
        [
            _shape(
                "presentation-domain",
                (60, 380, 1080, 520),
                background="#edf6ef",
                stroke="#607c67",
                stroke_style="dashed",
                stroke_width=2,
                link=note_link(domain),
                custom_data={"presentation_domain": domain.id},
            ),
            _shape(
                "connected-registry-objects",
                (1200, 380, 1480, 820),
                background="#f4f6f8",
                stroke="#8695a3",
                stroke_width=1.6,
                custom_data={"visual_role": "registry-relations"},
            ),
        ]
    )

    parent_box = (650, 245, 320, 100)
    member_boxes = {
        "CMP-MEMORY": (105, 545, 290, 110),
        "CMP-MEM-RETRIEVAL": (440, 545, 310, 110),
        "CMP-EVIDENCE-LEDGER": (800, 545, 290, 110),
    }
    elements.extend(_element_for_record(atlas, "SYS-AGA", parent_box))
    for identity, box in member_boxes.items():
        elements.extend(_element_for_record(atlas, identity, box))
    for row, edge in enumerate(edges):
        elements.extend(_relation_row(atlas, edge, row))
    elements.extend(
        _navigation_button(
            "back-to-anatomy",
            "← Back to Agent Anatomy",
            ANATOMY_PATH,
            (80, 1240, 390, 64),
        )
    )
    elements.extend(
        _navigation_button(
            "research-home-detail-navigation",
            (
                "Research Knowledge Home · Memory Retrieval Component Hub / "
                "Technical Hierarchy / exact records"
            ),
            HOME_PATH,
            (500, 1240, 1150, 64),
        )
    )
    elements.extend(
        _navigation_button(
            "memory-retrieval-overview",
            "Memory Retrieval → Overview",
            note_path_for(
                "CMP-MEM-RETRIEVAL",
                atlas.entities["CMP-MEM-RETRIEVAL"].type,
                atlas.entities["CMP-MEM-RETRIEVAL"].name,
            ),
            (1720, 1240, 910, 64),
        )
    )
    elements.extend(
        [
            _text_item(
                "domain-markdown-fallback",
                (
                    "If Excalidraw is unavailable, use the Research Knowledge Home and linked "
                    "Markdown technical records."
                ),
                80,
                1330,
                1700,
                size=13,
                color=_MUTED,
            )
        ]
    )
    return _encode_scene(
        elements,
        surface="domain-slice",
        width=_DOMAIN_CANVAS_SIZE[0],
        height=_DOMAIN_CANVAS_SIZE[1],
    )


def _parse_scene(markdown: str, path: PurePosixPath) -> dict:
    if parse_frontmatter(markdown).get("excalidraw-plugin") != "parsed":
        raise ValueError(f"{path} requires parsed Excalidraw frontmatter")
    if "## Text Elements\n" not in markdown or "## Element Links\n" not in markdown:
        raise ValueError(f"{path} requires Text Elements and Element Links sections")
    match = re.search(r"\n## Drawing\n[^`]*```json\n([\s\S]*?)```\n", markdown)
    if not match:
        raise ValueError(f"{path} requires an uncompressed JSON Drawing section")
    scene = json.loads(match.group(1))
    if scene.get("type") != "excalidraw" or scene.get("version") != 2 or scene.get("files"):
        raise ValueError(f"{path} is not a supported Excalidraw scene")
    elements = scene.get("elements")
    if not isinstance(elements, list) or len({el.get("id") for el in elements}) != len(elements):
        raise ValueError(f"{path} has missing or duplicate Excalidraw element IDs")
    for element in elements:
        if element.get("type") not in {"rectangle", "ellipse", "diamond", "text", "arrow"}:
            raise ValueError(f"{path} contains an unsupported Excalidraw element type")
        if not re.fullmatch(r"[a-f0-9]{8}", element.get("id", "")):
            raise ValueError(f"{path} has a non-deterministic Excalidraw element ID")
        if element.get("type") == "text" and element.get("rawText") != element.get("text"):
            raise ValueError(f"{path} has non-reconstructable text content")
    return scene


def _inside(inner: dict, outer: dict) -> bool:
    return (
        outer["x"] <= inner["x"]
        and outer["y"] <= inner["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def _validate_edges(atlas: Atlas, scene: dict, path: PurePosixPath) -> set[tuple[str, str, str]]:
    registry_edges = {
        (edge.source, edge.relation, edge.target): edge.model_dump(exclude_none=True)
        for edge in atlas.relationships
    }
    rendered: set[tuple[str, str, str]] = set()
    for element in scene["elements"]:
        custom_data = element.get("customData", {})
        if "atlas_relation" in custom_data:
            relation_data = custom_data["atlas_relation"]
            key = (
                relation_data.get("source"),
                relation_data.get("relation"),
                relation_data.get("target"),
            )
            if registry_edges.get(key) != relation_data:
                raise ValueError(f"{path} renders an unsupported Registry relation: {key}")
            rendered.add(key)
        if element.get("type") != "arrow":
            continue
        if "atlas_relation" in custom_data:
            if custom_data.keys() != {"atlas_relation"}:
                raise ValueError(f"{path} mixes technical and presentation arrow semantics")
            continue
        flow = custom_data.get("presentation_flow")
        if (
            set(custom_data) != {"presentation_flow"}
            or flow
            != {
                "kind": "runtime-orientation",
                "from": flow.get("from") if isinstance(flow, dict) else None,
                "to": flow.get("to") if isinstance(flow, dict) else None,
            }
            or (flow.get("from"), flow.get("to")) not in FLOW_KEYS
            or element.get("strokeStyle") != "dashed"
        ):
            raise ValueError(f"{path} has a connector without explicit accepted semantics")
    return rendered


def validate_generated_visuals(atlas: Atlas, tree: Mapping[PurePosixPath, str]) -> None:
    """Validate the finite visual-output set and every rendered edge/record target."""
    expected_paths = {MAP_PATH, ANATOMY_PATH, DOMAIN_SLICE_PATH}
    actual_paths = {path for path in tree if path.name.endswith(".excalidraw.md")}
    if actual_paths != expected_paths:
        raise ValueError("Exactly the legacy System Anatomy and two W03 visual assets are required")
    scenes = {path: _parse_scene(tree[path], path) for path in expected_paths}

    old_ids = {
        element.get("customData", {}).get("atlas_id")
        for element in scenes[MAP_PATH]["elements"]
        if element.get("customData", {}).get("atlas_id") is not None
    }
    if old_ids != map_record_ids(atlas):
        raise ValueError("System Anatomy central-node coverage mismatch")
    legacy_relations = _validate_edges(atlas, scenes[MAP_PATH], MAP_PATH)
    if not legacy_relations:
        raise ValueError("System Anatomy must retain its typed Registry relationships")

    anatomy = scenes[ANATOMY_PATH]
    anatomy_elements = anatomy["elements"]
    record_elements = [
        element
        for element in anatomy_elements
        if element.get("customData", {}).get("atlas_id") is not None
    ]
    anatomy_records = {element["customData"]["atlas_id"] for element in record_elements}
    expected_anatomy_records = ANATOMY_RECORD_IDS & atlas.entities.keys()
    if anatomy_records != expected_anatomy_records or len(record_elements) != len(anatomy_records):
        raise ValueError("Agent Anatomy landmark coverage mismatch")
    region_elements = [
        element
        for element in anatomy_elements
        if element.get("customData", {}).get("functional_region") is not None
    ]
    regions = {element["customData"]["functional_region"]: element for element in region_elements}
    if len(region_elements) != len(ANATOMY_REGIONS) or set(regions) != {
        key for key, *_ in ANATOMY_REGIONS
    }:
        raise ValueError("Agent Anatomy functional-region coverage mismatch")
    for key, _, _, identities in ANATOMY_REGIONS:
        region = regions[key]
        if (
            region.get("type") != _REGION_SHAPES[key]
            or region["customData"].get("atlas_landmarks") != list(identities)
            or region["customData"].get("presentation_only") is not True
        ):
            raise ValueError("Agent Anatomy presentation grouping changed technical landmarks")
    structures = {
        element.get("customData", {}).get("presentation_structure") for element in anatomy_elements
    }
    if not {"shared-chassis", "shared-backplane", "independent-verifier-pod"} <= structures:
        raise ValueError("Agent Anatomy lost its shared chassis or independent Verifier pod")
    verifier_pods = [
        element
        for element in anatomy_elements
        if element.get("customData", {}).get("outside_decision_authority") is True
    ]
    if (
        len(verifier_pods) != 1
        or verifier_pods[0].get("customData", {}).get("presentation_structure")
        != "independent-verifier-pod"
    ):
        raise ValueError("Agent Anatomy Verifier independence metadata mismatch")
    boundaries = {
        element.get("customData", {}).get("presentation_boundary"): element
        for element in anatomy_elements
        if element.get("customData", {}).get("presentation_boundary") is not None
    }
    if set(boundaries) != {"in-run", "between-runs"}:
        raise ValueError("Agent Anatomy run boundaries are incomplete")
    bay = boundaries["between-runs"]
    runtime = boundaries["in-run"]
    for identity in BETWEEN_RUN_IDS:
        element = next(
            element for element in record_elements if element["customData"]["atlas_id"] == identity
        )
        if not _inside(element, bay) or _inside(element, runtime):
            raise ValueError("Between-run stage is not visually separated from the Mission Run")
    anatomy_flows = _validate_edges(atlas, anatomy, ANATOMY_PATH)
    if anatomy_flows != set(BETWEEN_RUN_RELATION_KEYS):
        raise ValueError("Agent Anatomy must retain only the selected between-run Registry edges")
    actual_flows = {
        (
            element["customData"]["presentation_flow"]["from"],
            element["customData"]["presentation_flow"]["to"],
        )
        for element in anatomy_elements
        if element.get("type") == "arrow" and "presentation_flow" in element.get("customData", {})
    }
    if actual_flows != set(FLOW_KEYS):
        raise ValueError("Agent Anatomy runtime orientation path is incomplete or expanded")
    optional = [
        element
        for element in anatomy_elements
        if element.get("customData", {}).get("path_style") == "optional"
    ]
    if (
        len(optional) != 1
        or optional[0].get("customData", {}).get("atlas_id") != "CMP-VISIBLE-STATE-BRIDGE"
    ):
        raise ValueError("Agent Anatomy optional bridge styling mismatch")

    domain_scene = scenes[DOMAIN_SLICE_PATH]
    domain_elements = domain_scene["elements"]
    domain_surfaces = [
        element
        for element in domain_elements
        if element.get("customData", {}).get("presentation_domain") is not None
    ]
    if len(domain_surfaces) != 1:
        raise ValueError("Domain slice must contain exactly one presentation-only Domain group")
    domain_identity = domain_surfaces[0]["customData"]["presentation_domain"]
    if (
        domain_identity != "DOM-EVIDENCE-MEMORY"
        or atlas.entities[domain_identity].type != "Domain"
        or domain_surfaces[0].get("link") != note_link(atlas.entities[domain_identity])
    ):
        raise ValueError("Domain slice group does not resolve to the selected Registry Domain")
    domain_record_ids = {
        element.get("customData", {}).get("atlas_id")
        for element in domain_elements
        if element.get("customData", {}).get("atlas_id") is not None
    }
    if domain_record_ids != {"SYS-AGA", *DOMAIN_MEMBER_IDS}:
        raise ValueError("Domain slice technical-node coverage mismatch")
    domain_edges = _validate_edges(atlas, domain_scene, DOMAIN_SLICE_PATH)
    if domain_edges != set(DOMAIN_RELATION_KEYS):
        raise ValueError("Domain slice relationships differ from the curated Registry subset")
    if (
        "CMP-MEMORY",
        "part_of",
        "CMP-MEM-RETRIEVAL",
    ) in domain_edges or (
        "CMP-MEM-RETRIEVAL",
        "part_of",
        "CMP-MEMORY",
    ) in domain_edges:
        raise ValueError("Memory and Memory Retrieval must not be shown as parent and child")
    if any(
        edge[1] == "presented_in_domain" and edge[2] == domain_identity for edge in domain_edges
    ):
        raise ValueError("Domain grouping cannot be rendered as a technical connector")

    # All linked technical identities must be real and linked by their human-readable record path.
    for path, scene in scenes.items():
        for element in scene["elements"]:
            identity = element.get("customData", {}).get("atlas_id")
            if identity is not None:
                if identity not in atlas.entities or element.get("link") != note_link(
                    atlas.entities[identity]
                ):
                    raise ValueError(
                        f"{path} has an invalid technical-record destination: {identity}"
                    )
