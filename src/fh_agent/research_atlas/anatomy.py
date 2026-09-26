"""Deterministic, Registry-grounded W03 Excalidraw navigation surfaces."""

from __future__ import annotations

import base64
import hashlib
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
    HERO_ASSET_PATH,
    HOME_PATH,
    MAP_PATH,
    _element,
    _text,
    anatomy_hero_svg,
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

_REGION_HOTSPOTS: Mapping[str, tuple[int, int, int, int]] = {
    "environment": (578, 300, 212, 176),
    "observation": (795, 318, 286, 168),
    "evidence-memory": (705, 536, 338, 276),
    "cognition": (1080, 222, 212, 150),
    "executive": (1050, 505, 228, 209),
    "action-safety": (940, 715, 398, 246),
    "verification": (1636, 419, 305, 346),
}
_REGION_CALLOUTS: Mapping[str, tuple[str, str, int, int, int]] = {
    "environment": ("ACQUIRE", "Sensor intake", 85, 260, 420),
    "observation": ("OBSERVE", "Optional bridge · no-spoiler perception", 85, 449, 420),
    "evidence-memory": ("RETAIN / RETRIEVE", "Evidence and bounded context", 85, 685, 420),
    "cognition": ("REASON", "Cortex proposes", 1375, 235, 240),
    "executive": ("CONTRACT", "Manager grounds contracts", 1375, 483, 245),
    "action-safety": ("ACT", "Body acts within contract", 85, 830, 440),
    "verification": ("VERIFY", "Outside Cortex decision authority", 1635, 236, 405),
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


def _hero_image() -> tuple[dict, dict]:
    source = anatomy_hero_svg().encode("utf-8")
    source_sha256 = hashlib.sha256(source).hexdigest()
    file_id = source_sha256[:32]
    image = _element("w03:hero-image", "image", (0, 0, *_CANVAS_SIZE))
    image.update(
        fileId=file_id,
        status="saved",
        scale=[1, 1],
        customData={
            "illustration_source": str(HERO_ASSET_PATH),
            "illustration_sha256": source_sha256,
            "presentation_structure": "shared-agent-silhouette",
            "presentation_only": True,
        },
    )
    file = {
        "id": file_id,
        "mimeType": "image/svg+xml",
        "dataURL": "data:image/svg+xml;base64," + base64.b64encode(source).decode("ascii"),
        "created": 0,
        "lastRetrieved": 0,
    }
    return image, {file_id: file}


def _illustrated_region(
    atlas: Atlas, key: str, subtitle: str, identities: tuple[str, ...]
) -> list[dict]:
    title, short_subtitle, x, y, width = _REGION_CALLOUTS[key]
    assert subtitle
    if key == "evidence-memory":
        anchor = f"[[{DOMAIN_SLICE_PATH.with_suffix('')}|Evidence, Memory & Retrieval]]"
    elif key == "verification":
        node = atlas.entities[identities[0]]
        target = note_path_for(node.id, node.type, node.name)
        anchor = f"[[{target.with_suffix('')}|Independent Verifier → Overview]]"
    else:
        anchor = note_link(atlas.entities[identities[0]])
    custom = {
        "functional_region": key,
        "atlas_landmarks": list(identities),
        "landmark_links": {
            identity: note_link(atlas.entities[identity]) for identity in identities
        },
        "presentation_title": title,
        "presentation_summary": subtitle,
        "presentation_only": True,
        "visual_grammar": "figurative-machine-assembly",
        "navigation_target": anchor,
    }
    if key == "evidence-memory":
        custom["domain_slice"] = "DOM-EVIDENCE-MEMORY"
    if key == "verification":
        custom["outside_decision_authority"] = True
        custom["presentation_structure"] = "independent-verifier-pod"
    elements = [
        _shape(
            "region:" + key,
            _REGION_HOTSPOTS[key],
            stroke="transparent",
            stroke_width=0,
            link=anchor,
            custom_data=custom,
        ),
        _text_item(f"callout-title:{key}", title, x, y, width, size=22),
        _text_item(
            f"callout-subtitle:{key}", short_subtitle, x, y + 30, width, size=15, color=_MUTED
        ),
    ]
    for index, identity in enumerate(identities):
        node = atlas.entities[identity]
        elements.append(
            _text_item(
                f"landmark:{key}:{identity}",
                node.name,
                x + 1,
                y + 59 + 19 * index,
                width - 2,
                size=14,
                color="#9b625e" if node.type == "Contract" else _MUTED,
                custom_data={"landmark_identity": identity, "landmark_type": node.type},
            )
        )
    nav_y = y + 64 + len(identities) * 19
    elements.append(
        _text_item(
            f"navigation:{key}",
            "OPEN ASSEMBLY  →",
            x,
            nav_y,
            width,
            size=13,
            color="#426f7d",
            link=anchor,
            custom_data={"navigation": key, "navigation_target": anchor},
        )
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


def _encode_scene(
    elements: list[dict],
    *,
    surface: str,
    width: int,
    height: int,
    files: dict | None = None,
    embedded_files: Mapping[str, PurePosixPath] | None = None,
) -> str:
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "research-atlas",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#fbfaf7", "gridSize": None},
        "files": files or {},
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
    if embedded_files:
        lines += ["## Embedded Files", ""]
        lines += [f"{file_id}: [[{path}]]\n" for file_id, path in sorted(embedded_files.items())]
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
    """Render the accepted illustrated anatomy with Registry-grounded hotspots."""
    _require_records(atlas, ANATOMY_RECORD_IDS)
    hero, files = _hero_image()
    elements = [
        hero,
        _text_item("anatomy-title", "AGENT ANATOMY", 76, 27, 1000, size=42),
        _text_item(
            "anatomy-subtitle",
            "One agent, opened for inspection",
            80,
            91,
            980,
            size=19,
            color=_MUTED,
        ),
        _text_item(
            "runtime-boundary-title",
            "MISSION RUN  /  frozen Body version through Life Episode restarts",
            83,
            190,
            1640,
            size=17,
        ),
        _shape(
            "in-run-boundary",
            (61, 216, 1977, 788),
            stroke="#b4c0bd",
            stroke_style="dashed",
            stroke_width=1.2,
            link=note_link(atlas.entities["SYS-AGA"]),
            custom_data={"atlas_id": "SYS-AGA", "presentation_boundary": "in-run"},
        ),
        _text_item(
            "navigation:home",
            "←  MARKDOWN HOME / FALLBACK",
            80,
            137,
            430,
            size=14,
            color="#426f7d",
            link=f"[[{HOME_PATH.with_suffix('')}|Markdown Home / fallback]]",
            custom_data={"navigation": "research-home"},
        ),
    ]
    # Short, faint process cues orient the reader. Only the separate workshop
    # carries selected exact Registry arrows; neither cue invents an edge.
    flow_segments = {
        ("environment", "observation"): ((787, 394), (813, 394)),
        ("observation", "evidence-memory"): ((899, 478), (899, 531)),
        ("evidence-memory", "cognition"): ((1023, 558), (1092, 467)),
        ("cognition", "executive"): ((1132, 377), (1132, 495)),
        ("executive", "action-safety"): ((1125, 714), (1125, 751)),
        ("action-safety", "verification"): ((1566, 743), (1630, 665)),
    }
    for source_key, target_key in FLOW_KEYS:
        start, end = flow_segments[source_key, target_key]
        arrow = _arrow(
            f"runtime-flow:{source_key}:{target_key}",
            start,
            end,
            presentation_flow=(source_key, target_key),
        )
        arrow["opacity"] = 45
        elements.append(arrow)
    for key, _, subtitle, identities in ANATOMY_REGIONS:
        elements.extend(_illustrated_region(atlas, key, subtitle, identities))
    # The ghosted optional bridge is a qualified observation path. The five
    # paper shapes in the SVG are typed as Contract/DataArtifact tokens here.
    bridge = atlas.entities["CMP-VISIBLE-STATE-BRIDGE"]
    elements.append(
        _shape(
            "record:CMP-VISIBLE-STATE-BRIDGE",
            (760, 437, 38, 28),
            stroke="#8f82ac",
            stroke_style="dashed",
            stroke_width=1.5,
            link=note_link(bridge),
            custom_data={
                "atlas_id": bridge.id,
                "atlas_name": bridge.name,
                "path_style": "optional",
                "visual_role": "optional-visible-state-bridge",
                "visual_grammar": "ghosted-path",
            },
        )
    )
    token_boxes = {
        "DAT-OBSERVATION": (850, 490, 85, 59),
        "CON-PLANNER-OUTPUT": (1288, 295, 86, 70),
        "CON-SKILL-CONTRACT": (1190, 586, 92, 80),
        "DAT-VISIBLE-OUTCOME": (1660, 777, 91, 70),
        "CON-MEMORY-UPDATE-REQUEST": (1782, 786, 96, 73),
    }
    for identity, box in token_boxes.items():
        node = atlas.entities[identity]
        elements.append(
            _shape(
                "token:" + identity,
                box,
                stroke="transparent",
                stroke_width=0,
                custom_data={
                    "atlas_id": identity,
                    "atlas_type": node.type,
                    "visual_grammar": "contract-token" if node.type == "Contract" else "data-card",
                    "proposal_only": identity == "CON-MEMORY-UPDATE-REQUEST",
                    "presentation_only": True,
                },
            )
        )
    elements.extend(
        [
            _text_item(
                "presentation-legend",
                "Dashed cues: orientation / optional path · Solid bay arrows: Registry relations",
                1367,
                954,
                630,
                size=12,
                color=_MUTED,
            ),
            _text_item(
                "between-boundary-title",
                "BETWEEN MISSION RUNS",
                91,
                1020,
                650,
                size=22,
            ),
            _text_item(
                "between-boundary-subtitle",
                "Train candidate · certify · activate only in a future Mission Run",
                505,
                1026,
                1070,
                size=16,
                color=_MUTED,
            ),
            _shape(
                "between-runs-boundary",
                (77, 1060, 1941, 170),
                stroke="transparent",
                stroke_width=0,
                custom_data={
                    "presentation_boundary": "between-runs",
                    "presentation_structure": "separate-service-bay",
                },
            ),
        ]
    )
    between_boxes = {
        "CMP-SKILL-TRAINER": (317, 1094, 145, 88),
        "DAT-CANDIDATE-BODY-VERSION": (965, 1098, 146, 78),
        "CMP-BODY-CERTIFICATION": (1611, 1089, 108, 93),
    }
    stage_labels = {
        "CMP-SKILL-TRAINER": (184, 1116, 125),
        "DAT-CANDIDATE-BODY-VERSION": (1118, 1116, 225),
        "CMP-BODY-CERTIFICATION": (1727, 1115, 263),
    }
    for identity in BETWEEN_RUN_IDS:
        node = atlas.entities[identity]
        grammar = "data-card" if node.type == "DataArtifact" else "figurative-machine-assembly"
        elements.append(
            _shape(
                "record:" + identity,
                between_boxes[identity],
                stroke="transparent",
                stroke_width=0,
                link=note_link(node),
                custom_data={
                    "atlas_id": identity,
                    "visual_role": "between-run-stage",
                    "visual_grammar": grammar,
                },
            )
        )
        x, y, width = stage_labels[identity]
        elements.append(
            _text_item(
                "stage-name:" + identity,
                node.name,
                x,
                y,
                width,
                size=14,
                color="#7b604d",
                custom_data={"landmark_identity": identity, "landmark_type": node.type},
            )
        )
    for key, start, end, label_x in (
        (BETWEEN_RUN_RELATION_KEYS[0], (469, 1084), (957, 1084), 637),
        (BETWEEN_RUN_RELATION_KEYS[1], (1603, 1084), (1117, 1084), 1370),
    ):
        edge = _registry_relation(atlas, key)
        elements.append(
            _arrow(
                f"registry:{edge.source}:{edge.relation}:{edge.target}",
                start,
                end,
                relation=edge,
            )
        )
        elements.append(
            _text_item(
                f"registry-label:{edge.source}:{edge.relation}:{edge.target}",
                edge.relation,
                label_x,
                1065,
                110,
                size=12,
                color="#7b604d",
            )
        )
    elements.append(
        _text_item(
            "navigation:workshop",
            "OPEN TRAINING RECORD  →",
            1685,
            1027,
            320,
            size=13,
            color="#7b604d",
            link=note_link(atlas.entities["CMP-SKILL-TRAINER"]),
            custom_data={"navigation": "between-runs"},
        )
    )
    return _encode_scene(
        elements,
        surface="agent-anatomy",
        width=_CANVAS_SIZE[0],
        height=_CANVAS_SIZE[1],
        files=files,
        embedded_files={next(iter(files)): HERO_ASSET_PATH},
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
    if scene.get("type") != "excalidraw" or scene.get("version") != 2:
        raise ValueError(f"{path} is not a supported Excalidraw scene")
    if path == ANATOMY_PATH:
        image, expected_files = _hero_image()
        if scene.get("files") != expected_files or (
            f"## Embedded Files\n\n{image['fileId']}: [[{HERO_ASSET_PATH}]]" not in markdown
        ):
            raise ValueError("Agent Anatomy must embed the exact curated public illustration")
    elif scene.get("files"):
        raise ValueError(f"{path} cannot embed an illustration")
    elements = scene.get("elements")
    if not isinstance(elements, list) or len({el.get("id") for el in elements}) != len(elements):
        raise ValueError(f"{path} has missing or duplicate Excalidraw element IDs")
    for element in elements:
        allowed = {"rectangle", "ellipse", "diamond", "text", "arrow", "line"}
        if path == ANATOMY_PATH:
            allowed.add("image")
        if element.get("type") not in allowed:
            raise ValueError(f"{path} contains an unsupported Excalidraw element type")
        if not re.fullmatch(r"[a-f0-9]{8}", element.get("id", "")):
            raise ValueError(f"{path} has a non-deterministic Excalidraw element ID")
        if element.get("type") == "text" and element.get("rawText") != element.get("text"):
            raise ValueError(f"{path} has non-reconstructable text content")
    if path == ANATOMY_PATH and [el for el in elements if el["type"] == "image"] != [image]:
        raise ValueError("Agent Anatomy image placement or ownership metadata differs")
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
    if tree.get(HERO_ASSET_PATH) != anatomy_hero_svg():
        raise ValueError("Generated Agent Anatomy asset differs from curated source")
    if {path for path in tree if path.suffix == ".svg"} != {HERO_ASSET_PATH}:
        raise ValueError("Agent Anatomy must own exactly one generated SVG")
    record_elements = [
        element
        for element in anatomy_elements
        if element.get("customData", {}).get("atlas_id") is not None
    ]
    token_ids = {
        "DAT-OBSERVATION",
        "CON-PLANNER-OUTPUT",
        "CON-SKILL-CONTRACT",
        "DAT-VISIBLE-OUTCOME",
        "CON-MEMORY-UPDATE-REQUEST",
    }
    direct_records = {"SYS-AGA", "CMP-VISIBLE-STATE-BRIDGE", *token_ids, *BETWEEN_RUN_IDS}
    anatomy_records = {element["customData"]["atlas_id"] for element in record_elements}
    if anatomy_records != direct_records or len(record_elements) != len(anatomy_records):
        raise ValueError("Agent Anatomy illustrated landmark coverage mismatch")
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
    for key, _, subtitle, identities in ANATOMY_REGIONS:
        region = regions[key]
        custom = region["customData"]
        labels = [
            item
            for item in anatomy_elements
            if item.get("customData", {}).get("landmark_identity") in identities
            and item.get("id") != region["id"]
        ]
        if (
            region.get("type") != "rectangle"
            or (region["x"], region["y"], region["width"], region["height"])
            != _REGION_HOTSPOTS[key]
            or region.get("strokeColor") != "transparent"
            or custom.get("atlas_landmarks") != list(identities)
            or custom.get("landmark_links")
            != {identity: note_link(atlas.entities[identity]) for identity in identities}
            or custom.get("presentation_summary") != subtitle
            or custom.get("presentation_only") is not True
            or custom.get("visual_grammar") != "figurative-machine-assembly"
            or custom.get("navigation_target") != region.get("link")
            or len(labels) != len(identities)
        ):
            raise ValueError("Agent Anatomy callout or hotspot changed accepted landmarks")
        for identity in identities:
            label = next(
                item for item in labels if item["customData"]["landmark_identity"] == identity
            )
            if (
                label["text"].replace("\n", " ") != atlas.entities[identity].name
                or label["customData"].get("landmark_type") != atlas.entities[identity].type
            ):
                raise ValueError("Agent Anatomy technical landmark label drift")
        nav = [
            item for item in anatomy_elements if item.get("customData", {}).get("navigation") == key
        ]
        if len(nav) != 1 or nav[0].get("link") != region.get("link"):
            raise ValueError("Agent Anatomy assembly navigation changed")
    if (
        regions["verification"]["customData"].get("outside_decision_authority") is not True
        or regions["verification"]["customData"].get("presentation_structure")
        != "independent-verifier-pod"
    ):
        raise ValueError("Independent Verifier lost its external decision boundary")
    image = next(item for item in anatomy_elements if item["type"] == "image")
    if image["customData"].get("presentation_structure") != "shared-agent-silhouette":
        raise ValueError("Agent Anatomy lost its coherent illustrated body")
    tokens = {
        item["customData"]["atlas_id"]: item
        for item in record_elements
        if item["customData"]["atlas_id"] in token_ids
    }
    for identity, token in tokens.items():
        node = atlas.entities[identity]
        grammar = "contract-token" if node.type == "Contract" else "data-card"
        if (
            token["customData"].get("atlas_type") != node.type
            or token["customData"].get("visual_grammar") != grammar
            or token.get("link") is not None
        ):
            raise ValueError("Component and Contract/DataArtifact grammar became ambiguous")
    if tokens["CON-MEMORY-UPDATE-REQUEST"]["customData"].get("proposal_only") is not True:
        raise ValueError("Memory update request must remain a proposal")
    boundaries = {
        item["customData"]["presentation_boundary"]: item
        for item in anatomy_elements
        if "presentation_boundary" in item.get("customData", {})
    }
    if set(boundaries) != {"in-run", "between-runs"}:
        raise ValueError("Agent Anatomy run boundaries are incomplete")
    bay = boundaries["between-runs"]
    runtime = boundaries["in-run"]
    for identity in BETWEEN_RUN_IDS:
        stage = next(item for item in record_elements if item["customData"]["atlas_id"] == identity)
        if not _inside(stage, bay) or _inside(stage, runtime):
            raise ValueError("Between-run stage is not separated from the Mission Run")
        expected_grammar = (
            "data-card"
            if atlas.entities[identity].type == "DataArtifact"
            else "figurative-machine-assembly"
        )
        if stage["customData"].get("visual_grammar") != expected_grammar:
            raise ValueError("Between-run stage visual grammar mismatch")
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
        item
        for item in anatomy_elements
        if item.get("customData", {}).get("path_style") == "optional"
    ]
    if (
        len(optional) != 1
        or optional[0]["customData"].get("atlas_id") != "CMP-VISIBLE-STATE-BRIDGE"
        or optional[0].get("strokeStyle") != "dashed"
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
                token = path == ANATOMY_PATH and identity in token_ids
                if (
                    identity not in atlas.entities
                    or (token and element.get("link") is not None)
                    or (not token and element.get("link") != note_link(atlas.entities[identity]))
                ):
                    raise ValueError(
                        f"{path} has an invalid technical-record destination: {identity}"
                    )
