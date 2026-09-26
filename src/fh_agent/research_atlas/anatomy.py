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
    "environment": (105, 310, 300, 245),
    "observation": (440, 285, 310, 255),
    "evidence-memory": (610, 605, 330, 260),
    "cognition": (925, 255, 340, 275),
    "executive": (1330, 280, 310, 255),
    "action-safety": (1115, 650, 400, 235),
    "verification": (1640, 610, 350, 265),
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
    "environment": "rectangle",
    "observation": "rectangle",
    "evidence-memory": "rectangle",
    "cognition": "ellipse",
    "executive": "rectangle",
    "action-safety": "rectangle",
    "verification": "ellipse",
}
_REGION_LABELS: Mapping[str, str] = {
    "environment": "ACQUIRE\nsensor intake",
    "observation": "OBSERVE\nperception scanner",
    "evidence-memory": "RETAIN / RETRIEVE\nmemory chamber",
    "cognition": "REASON\nCortex core",
    "executive": "CONTRACT\nManager gate",
    "action-safety": "ACT\nBody + safety",
    "verification": "VERIFY\nindependent pod",
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


def _trace(
    identity: str,
    points: tuple[tuple[int, int], ...],
    *,
    color: str = _INK,
    width: float = 2,
    dashed: bool = False,
    custom_data: dict | None = None,
) -> dict:
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    item = _element(
        "w03:" + identity,
        "line",
        (left, top, max(x for x, _ in points) - left, max(y for _, y in points) - top),
    )
    item.update(
        points=[[x - left, y - top] for x, y in points],
        strokeColor=color,
        strokeWidth=width,
        strokeStyle="dashed" if dashed else "solid",
    )
    if custom_data:
        item["customData"] = custom_data
    return item


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
    custom.update(
        presentation_title=title,
        presentation_summary=subtitle,
        landmark_links={identity: note_link(atlas.entities[identity]) for identity in identities},
    )
    core = {
        "environment": (45, 56, 210, 130),
        "observation": (35, 55, 240, 145),
        "evidence-memory": (50, 34, 230, 175),
        "cognition": (35, 26, 270, 180),
        "executive": (55, 39, 200, 165),
        "action-safety": (132, 17, 138, 154),
        "verification": (68, 24, 212, 175),
    }[key]
    cx, cy, cw, ch = core

    def data(name: str) -> dict:
        return {
            "presentation_assembly": key,
            "figurative_part": name,
            "presentation_only": True,
        }

    def piece(
        name: str,
        box: tuple[int, int, int, int],
        *,
        kind: str = "rectangle",
        fill: str = "#ffffff",
        stroke: str = "#496073",
        stroke_width: float = 2,
    ) -> dict:
        px, py, pw, ph = box
        return _shape(
            f"assembly:{key}:{name}",
            (x + px, y + py, pw, ph),
            kind=kind,
            background=fill,
            stroke=stroke,
            stroke_width=stroke_width,
            custom_data=data(name),
        )

    def line(name: str, *points: tuple[int, int], color: str = "#496073", thick: float = 2) -> dict:
        return _trace(
            f"assembly:{key}:{name}",
            tuple((x + px, y + py) for px, py in points),
            color=color,
            width=thick,
            custom_data=data(name),
        )

    elements = [
        _shape(
            "region:" + key,
            (x + cx, y + cy, cw, ch),
            background=_REGION_COLORS[key],
            stroke="#496073",
            stroke_width=3,
            link=anchor,
            custom_data=custom,
            kind=_REGION_SHAPES[key],
        )
    ]
    if key == "environment":
        elements += [
            piece("sensor-hood", (21, 81, 34, 77), fill="#bed8e0"),
            line("intake-mouth", (10, 91), (28, 104), (28, 137), (10, 150)),
            piece("optic-bezel", (106, 72, 88, 88), kind="ellipse", fill="#ffffff"),
            piece("optic-glass", (121, 87, 58, 58), kind="ellipse", fill="#638fa0"),
            piece("optic-pupil", (142, 108, 16, 16), kind="ellipse", fill="#233f53"),
            piece("antenna-joint", (78, 37, 16, 16), kind="ellipse"),
            line("antenna", (86, 55), (86, 27), (68, 10)),
            line("upper-fin", (199, 58), (247, 32), (257, 49)),
            line("lower-fin", (199, 181), (246, 204), (256, 186)),
            line("sensor-grill", (63, 165), (92, 165), (100, 176)),
        ]
    elif key == "observation":
        elements += [
            piece("visor", (51, 72, 208, 86), fill="#5a718b"),
            piece("scan-window", (66, 87, 178, 56), fill="#c5e9ec", stroke="#698b9c"),
            line(
                "scan-sweep", (69, 137), (118, 89), (155, 137), (207, 91), color="#508c9e", thick=3
            ),
            piece("left-eye", (85, 103, 14, 14), kind="ellipse", fill="#ffffff"),
            piece("right-eye", (214, 103, 14, 14), kind="ellipse", fill="#ffffff"),
            piece("inspection-lamp", (120, 38, 69, 15), fill="#e2f1ee"),
            line("shield-left", (34, 79), (18, 105), (18, 155), (35, 177)),
            line("shield-right", (275, 79), (292, 105), (292, 155), (275, 177)),
        ]
        bridge = atlas.entities["CMP-VISIBLE-STATE-BRIDGE"]
        elements.append(
            _shape(
                "record:CMP-VISIBLE-STATE-BRIDGE",
                (x + 225, y + 165, 31, 25),
                background="#ffffff",
                stroke="#514a70",
                stroke_style="dashed",
                stroke_width=2,
                link=note_link(bridge),
                custom_data={
                    "atlas_id": bridge.id,
                    "atlas_name": bridge.name,
                    "path_style": "optional",
                    "visual_role": "optional-visible-state-bridge",
                },
            )
        )
    elif key == "evidence-memory":
        elements += [
            piece("archive-cap", (67, 17, 196, 26), fill="#c5dfc7"),
            piece("ledger", (67, 51, 58, 132), fill="#ffffff"),
            piece("memory-cells", (136, 53, 74, 128), fill="#eef8ee"),
            piece("retrieval-drawer", (219, 53, 55, 128), fill="#ffffff"),
            line("ledger-pages", (78, 77), (111, 77), (111, 91), (78, 91)),
            line("memory-row-1", (148, 73), (198, 73)),
            line("memory-row-2", (148, 101), (198, 101)),
            line("memory-row-3", (148, 129), (198, 129)),
            piece("retrieval-handle", (232, 101, 27, 24), fill="#c5dfc7"),
            line("archive-foot-left", (83, 210), (83, 223), (120, 223)),
            line("archive-foot-right", (218, 223), (255, 223), (255, 210)),
        ]
    elif key == "cognition":
        elements += [
            piece("left-lobe", (57, 44, 115, 119), kind="ellipse", fill="#fff5de"),
            piece("right-lobe", (165, 44, 115, 119), kind="ellipse", fill="#fff5de"),
            line("left-fold-1", (83, 71), (111, 57), (135, 75), (123, 98), (146, 119)),
            line("left-fold-2", (78, 119), (100, 138), (123, 123)),
            line("right-fold-1", (249, 70), (220, 57), (196, 78), (212, 99), (189, 120)),
            line("right-fold-2", (252, 120), (226, 141), (207, 124)),
            piece("thought-core", (153, 90, 34, 34), kind="ellipse", fill="#f6c27d"),
            piece("neck", (145, 200, 50, 34), fill="#d2dde0"),
            line("cortex-circuit", (170, 204), (170, 233), (194, 242)),
        ]
    elif key == "executive":
        elements += [
            piece("left-relay", (72, 59, 60, 115), fill="#ffffff"),
            piece("right-relay", (178, 59, 60, 115), fill="#ffffff"),
            piece("gate-lock", (130, 76, 50, 66), fill="#eab79c"),
            piece("gate-keyhole", (147, 95, 16, 16), kind="ellipse", fill="#704f51"),
            line("route-in", (81, 96), (108, 96), (128, 115)),
            line("route-out", (181, 115), (201, 96), (228, 96)),
            piece("contract-slot", (123, 157, 67, 24), fill="#fff5eb"),
            line("lever-left", (59, 77), (38, 54), (38, 38)),
            line("lever-right", (252, 77), (272, 54), (272, 38)),
        ]
    elif key == "action-safety":
        elements += [
            piece("chest-guard", (149, 32, 104, 91), fill="#ffffff"),
            piece("contract-socket", (181, 54, 39, 39), kind="diamond", fill="#d5e5f4"),
            line("left-upper-arm", (130, 49), (82, 73), (56, 119)),
            line("left-forearm", (56, 119), (27, 133), (16, 153)),
            line("right-upper-arm", (271, 49), (319, 73), (345, 119)),
            line("right-forearm", (345, 119), (375, 133), (386, 153)),
            piece("left-elbow", (42, 105, 27, 27), kind="ellipse", fill="#b8ccdf"),
            piece("right-elbow", (331, 105, 27, 27), kind="ellipse", fill="#b8ccdf"),
            line("left-gripper", (16, 153), (4, 142), (4, 163)),
            line("right-gripper", (386, 153), (397, 142), (397, 163)),
            line("left-leg", (166, 171), (149, 190), (121, 190)),
            line("right-leg", (235, 171), (252, 190), (280, 190)),
        ]
    elif key == "verification":
        elements += [
            piece("inspection-lens", (99, 49, 149, 126), kind="ellipse", fill="#ffffff"),
            piece("verdict-window", (121, 70, 105, 85), kind="ellipse", fill="#f7e8f3"),
            line("verdict-check", (145, 111), (164, 130), (205, 86), color="#7b4e72", thick=5),
            line("probe-handle", (234, 153), (272, 190), (300, 192), color="#805b77", thick=8),
            piece("replay-reel", (44, 70, 48, 48), kind="ellipse", fill="#ffffff"),
            piece("replay-hub", (60, 86, 16, 16), kind="ellipse", fill="#bc9db5"),
            line("pod-stand", (173, 198), (173, 218), (122, 218), (223, 218)),
        ]
    stage, name = _REGION_LABELS[key].split("\n", 1)
    elements.extend(
        [
            _text_item(f"region-stage:{key}", stage, x + 20, y + height - 44, width - 40, size=19),
            _text_item(
                f"region-name:{key}",
                name,
                x + 20,
                y + height - 19,
                width - 40,
                size=14,
                color=_MUTED,
            ),
        ]
    )
    return elements


def _navigation_button(
    identity: str,
    label: str,
    target: PurePosixPath,
    box: tuple[int, int, int, int],
    *,
    link_label: bool = True,
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
            link=link if link_label else None,
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
        _text_item("anatomy-title", "AGENT ANATOMY", 70, 27, 1090, size=42),
        _text_item(
            "anatomy-subtitle",
            "An exploded view of one autonomous agent",
            74,
            105,
            1120,
            size=20,
            color=_MUTED,
        ),
        _text_item(
            "runtime-boundary-title",
            "MISSION RUN  /  frozen Body version, including Life Episode restarts",
            88,
            198,
            1800,
            size=20,
        ),
    ]
    # Exposed spine, jointed rails, and an offset inspection pod are presentation
    # structure. They assert no Registry part_of or control relation.
    elements.extend(
        [
            _shape(
                "in-run-boundary",
                (45, 180, 2010, 805),
                stroke="#6f8191",
                stroke_style="dashed",
                stroke_width=2,
                link=note_link(atlas.entities["SYS-AGA"]),
                custom_data={"atlas_id": "SYS-AGA", "presentation_boundary": "in-run"},
            ),
            _shape(
                "chassis-spine",
                (1258, 470, 42, 388),
                background="#b4cad0",
                stroke="#627b88",
                stroke_width=3,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "chassis-shoulder",
                (385, 548, 1268, 28),
                background="#a5bdc4",
                stroke="#627b88",
                stroke_width=2,
                custom_data={"presentation_structure": "shared-backplane"},
            ),
            _shape(
                "chassis-hip",
                (760, 889, 835, 25),
                background="#a5bdc4",
                stroke="#627b88",
                stroke_width=2,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "verifier-offset",
                (1594, 577, 417, 314),
                kind="ellipse",
                background="#f9f4f8",
                stroke="#9a718e",
                stroke_width=2.5,
                custom_data={
                    "presentation_structure": "independent-verifier-pod",
                    "outside_decision_authority": True,
                },
            ),
            _trace(
                "chassis-left-arm",
                ((385, 561), (472, 586), (610, 590)),
                color="#627b88",
                width=7,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _trace(
                "chassis-right-arm",
                ((1510, 561), (1606, 590), (1660, 636)),
                color="#627b88",
                width=7,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "chassis-left-joint",
                (741, 533, 57, 57),
                kind="ellipse",
                background="#e5eff0",
                stroke="#627b88",
                stroke_width=3,
                custom_data={"presentation_structure": "shared-chassis"},
            ),
            _shape(
                "chassis-center-joint",
                (1245, 533, 57, 57),
                kind="ellipse",
                background="#e5eff0",
                stroke="#627b88",
                stroke_width=3,
                custom_data={"presentation_structure": "shared-chassis"},
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
                "Optional visible-state bridge · no-spoiler boundary",
                84,
                596,
                520,
                size=16,
                color="#514a70",
            ),
            _text_item(
                "authority-note-planning",
                "Cortex proposes · Manager contracts",
                930,
                922,
                660,
                size=16,
                color=_MUTED,
                custom_data={"presentation_only": "authority-orientation"},
            ),
            _text_item(
                "authority-note-action",
                "Body/Reflex (active contract) → SafetyFilter → InputExecutor",
                930,
                948,
                660,
                size=16,
                color=_MUTED,
                custom_data={"presentation_only": "authority-orientation"},
            ),
            _text_item(
                "verifier-note-boundary",
                "Verifier outside Cortex decision authority",
                1620,
                900,
                390,
                size=14,
                color="#674760",
            ),
            _text_item(
                "verifier-note-outcome",
                "Outcome before replay",
                1620,
                926,
                390,
                size=14,
                color="#674760",
            ),
            _text_item(
                "anatomy-legend",
                "Dashed arrows: orientation only  ·  Solid arrows: Registry relations",
                84,
                991,
                1300,
                size=15,
                color=_MUTED,
            ),
            _shape(
                "between-runs-boundary",
                (45, 1034, 2010, 210),
                background="#f6f0e8",
                stroke="#a87955",
                stroke_style="dashed",
                stroke_width=3,
                custom_data={"presentation_boundary": "between-runs"},
            ),
            _shape(
                "workshop-bench",
                (91, 1205, 1918, 17),
                background="#d7bd9f",
                stroke="#a87955",
                stroke_width=2,
                custom_data={"presentation_structure": "between-run-workshop"},
            ),
            _text_item(
                "between-boundary-title",
                "BETWEEN MISSION RUNS ONLY  /  train candidate · certify · "
                "activate in a future Mission Run",
                84,
                1049,
                1870,
                size=20,
                custom_data={"presentation_only": "between-run-lifecycle"},
            ),
        ]
    )
    between_boxes = {
        "CMP-SKILL-TRAINER": (103, 1095, 460, 105),
        "DAT-CANDIDATE-BODY-VERSION": (817, 1095, 460, 105),
        "CMP-BODY-CERTIFICATION": (1531, 1095, 460, 105),
    }
    for identity, box in between_boxes.items():
        node = atlas.entities[identity]
        x, y, width, height = box
        elements.extend(
            [
                _shape(
                    "record:" + identity,
                    box,
                    background="#fffaf3",
                    stroke="#a87955",
                    stroke_width=2.5,
                    link=note_link(node),
                    custom_data={"atlas_id": identity, "visual_role": "between-run-stage"},
                ),
                _text_item(
                    "record-name:" + identity,
                    node.name,
                    x + 110,
                    y + 38,
                    width - 125,
                    size=18,
                ),
            ]
        )
        if identity == "CMP-SKILL-TRAINER":
            elements.extend(
                [
                    _shape(
                        "workshop:tool-pivot",
                        (x + 37, y + 35, 36, 36),
                        kind="ellipse",
                        background="#d7bd9f",
                    ),
                    _trace(
                        "workshop:tool-arm",
                        ((x + 55, y + 52), (x + 77, y + 25), (x + 89, y + 33)),
                        color="#9b6d49",
                        width=6,
                    ),
                    _trace(
                        "workshop:tool-clamp",
                        ((x + 76, y + 24), (x + 73, y + 11), (x + 88, y + 21), (x + 98, y + 13)),
                        color="#9b6d49",
                        width=4,
                    ),
                ]
            )
        elif identity == "DAT-CANDIDATE-BODY-VERSION":
            elements.extend(
                [
                    _shape(
                        "workshop:cassette",
                        (x + 32, y + 24, 63, 57),
                        background="#ead5bc",
                        stroke="#9b6d49",
                        stroke_width=2,
                    ),
                    _shape(
                        "workshop:cassette-core",
                        (x + 51, y + 41, 25, 24),
                        kind="diamond",
                        background="#fffaf3",
                        stroke="#9b6d49",
                    ),
                    _trace(
                        "workshop:cassette-pins",
                        ((x + 26, y + 87), (x + 101, y + 87)),
                        color="#9b6d49",
                        width=3,
                    ),
                ]
            )
        else:
            elements.extend(
                [
                    _shape(
                        "workshop:seal",
                        (x + 36, y + 23, 62, 62),
                        kind="ellipse",
                        background="#ead5bc",
                        stroke="#9b6d49",
                        stroke_width=3,
                    ),
                    _trace(
                        "workshop:seal-check",
                        ((x + 51, y + 55), (x + 62, y + 66), (x + 85, y + 39)),
                        color="#805d43",
                        width=5,
                    ),
                    _trace(
                        "workshop:seal-ribbon",
                        (
                            (x + 54, y + 81),
                            (x + 46, y + 98),
                            (x + 68, y + 88),
                            (x + 88, y + 98),
                            (x + 80, y + 81),
                        ),
                        color="#9b6d49",
                        width=2,
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
                    sy + 67,
                    100,
                    size=13,
                    color=_MUTED,
                ),
            ]
        )

    elements.extend(
        _navigation_button(
            "research-home",
            "Home / fallback",
            HOME_PATH,
            (76, 917, 360, 56),
            link_label=False,
        )
    )
    elements.extend(
        _navigation_button(
            "domain-slice",
            "Open memory assembly →",
            DOMAIN_SLICE_PATH,
            (457, 917, 435, 56),
            link_label=False,
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
        if element.get("type") not in {"rectangle", "ellipse", "diamond", "text", "arrow", "line"}:
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
    direct_records = {"SYS-AGA", "CMP-VISIBLE-STATE-BRIDGE", *BETWEEN_RUN_IDS}
    if anatomy_records != direct_records or len(record_elements) != len(anatomy_records):
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
            or region["customData"].get("landmark_links")
            != {identity: note_link(atlas.entities[identity]) for identity in identities}
            or region["customData"].get("presentation_only") is not True
        ):
            raise ValueError("Agent Anatomy presentation grouping changed technical landmarks")
    illustrated = {
        key: {
            element.get("customData", {}).get("figurative_part")
            for element in anatomy_elements
            if element.get("customData", {}).get("presentation_assembly") == key
        }
        for key, *_ in ANATOMY_REGIONS
    }
    required_parts = {
        "environment": {"optic-glass", "antenna", "intake-mouth"},
        "observation": {"visor", "scan-sweep", "inspection-lamp"},
        "evidence-memory": {"ledger", "memory-cells", "retrieval-drawer"},
        "cognition": {"left-lobe", "right-lobe", "thought-core"},
        "executive": {"left-relay", "right-relay", "gate-lock"},
        "action-safety": {"chest-guard", "left-upper-arm", "right-upper-arm"},
        "verification": {"inspection-lens", "verdict-check", "replay-reel"},
    }
    if any(not parts <= illustrated[key] for key, parts in required_parts.items()):
        raise ValueError("Agent Anatomy lost a figurative assembly")
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
