"""Disposable Obsidian views of the Atlas; no runtime imports or reverse synchronization."""

import argparse
import hashlib
import json
import re
import textwrap
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import yaml

from .schema import PREFIXES, Entity, Evidence, Relationship, TechnicalIdentity
from .validator import Atlas, load_registry

SCHEMA_VERSION = "0.2"
GENERATED_NOTICE = (
    "Generated from Registry YAML; fully overwriteable. Do not edit structured claims here."
)
FOLDERS = {
    "System": "Home",
    "Domain": "Architecture/Domains",
    "Environment": "Architecture/Environments",
    "Component": "Components",
    "Interface": "Interfaces & Contracts",
    "Contract": "Interfaces & Contracts",
    "DataArtifact": "Data Artifacts",
    "Evidence": "Evidence",
    "ResearchQuestion": "Research Questions",
    "ResearchThread": "Research Threads",
    "Finding": "Findings",
    "Paper": "Literature",
    "Decision": "Decisions",
    "MeasurementPoint": "Measurements",
    "ExperimentLead": "Experiment Leads",
}
HOME_PATH = PurePosixPath("Home/Research Atlas.md")
BASE_PATH = PurePosixPath("Generated/Atlas Views.base")
MAP_PATH = PurePosixPath("Assets/Excalidraw/System Anatomy.excalidraw.md")
WIKILINK = re.compile(r"\[\[([^\]\n]+)\]\]")


def note_path_for(stable_id: str, node_type: str, current_name: str) -> PurePosixPath:
    """One central ID-first type-to-folder mapping; names are presentation only."""
    if node_type not in FOLDERS or not re.fullmatch(
        re.escape(PREFIXES[node_type]) + r"-[A-Z0-9]+(?:-[A-Z0-9]+)*", stable_id
    ):
        raise ValueError("Invalid note identity/type")
    name = re.sub(r'[\\/:*?"<>|#\[\]^\x00-\x1f]', "-", current_name)
    name = " ".join(name.split()).strip(" .") or stable_id
    return PurePosixPath(FOLDERS[node_type]) / f"{stable_id} — {name}.md"


def note_link(node: Entity) -> str:
    path = note_path_for(node.id, node.type, node.name).with_suffix("")
    alias = re.sub(r"[\[\]|\r\n]", " ", node.name)
    return f"[[{path}|{node.id} · {alias}]]"


def source_locator(evidence: Evidence) -> str:
    """Navigable original source plus precise locator; no runtime source import."""
    if evidence.provenance_kind == "github_implementation":
        url = (
            f"https://github.com/{evidence.repository}/blob/{quote(evidence.ref or '', safe='')}/"
            f"{quote(evidence.path or '', safe='/')}"
        )
        if evidence.line:
            url += f"#L{evidence.line}"
        return f"[Source]({url}) · {evidence.symbol or 'line ' + str(evidence.line)}"
    document = evidence.document or ""
    if document.startswith(("https://", "http://")):
        link = f"[Source]({document})"
    elif (
        document.startswith("docs/")
        and evidence.version
        and re.fullmatch(r"[a-f0-9]{40}", evidence.version)
    ):
        link = (
            "[Source](https://github.com/Planton361/autonomous-game-agent/blob/"
            f"{evidence.version}/{quote(document, safe='/')})"
        )
    else:
        link = f"Source document: `{document}`"
    locations = [
        f"{key}: {getattr(evidence, key)}"
        for key in ("version", "section", "page", "figure", "table", "quote_or_paraphrase_location")
        if getattr(evidence, key)
    ]
    return link + " · " + "; ".join(locations)


def record_properties(atlas: Atlas, node: Entity) -> dict[str, object]:
    """All note Properties are derived, including reverse and research-view mappings."""
    props: dict[str, object] = {
        "atlas_id": node.id,
        "atlas_type": node.type,
        "atlas_name": node.name,
        "atlas_level": node.atlas_level,
        "atlas_generated": True,
        "registry_schema_version": SCHEMA_VERSION,
        "overview_visibility": node.overview_visibility,
        "overview_order": node.overview_order,
        "research_mapping": node.research_mapping,
        "research_direction": node.research_direction,
    }
    if isinstance(node, TechnicalIdentity):
        props.update(node.technical.model_dump(mode="json"))
    if node.type == "Decision":
        props["decision_scope"] = node.decision_scope
    if isinstance(node, Evidence):
        for key, value in node.model_dump(mode="json", exclude_none=True).items():
            if key not in {"id", "type", "name", "description"}:
                props[key] = value
    # Expose each authored relation in both directions without changing its meaning.
    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    for edge in sorted(atlas.relationships, key=lambda e: (e.relation, e.source, e.target)):
        if edge.source == node.id:
            outgoing.setdefault(edge.relation, []).append(note_link(atlas.entities[edge.target]))
        if edge.target == node.id:
            incoming.setdefault(edge.relation + "_from", []).append(
                note_link(atlas.entities[edge.source])
            )
    props.update(outgoing)
    props.update(incoming)
    for field in (
        "part_of",
        "presented_in_domain",
        "measured_at",
        "studied_by",
        "supersedes",
        "supersedes_from",
        "decomposed_into",
        "decomposed_into_from",
        "contradicts",
    ):
        props.setdefault(field, [])
    props["supported_by"] = incoming.get("supports_from", [])
    props["contradicted_by"] = incoming.get("contradicts_from", [])
    props["research_questions"] = outgoing.get("related_to_research_question", [])
    subjects = [
        atlas.entities[e.source]
        for e in sorted(atlas.relationships, key=lambda e: e.source)
        if e.relation == "related_to_research_question" and e.target == node.id
    ]
    for kind in ("Component", "Interface"):
        props["research_" + kind.lower() + "s"] = [note_link(n) for n in subjects if n.type == kind]
    props["research_threads"] = [
        note_link(n)
        for n in sorted(atlas.entities.values(), key=lambda n: n.id)
        if n.type == "ResearchThread" and node.id in n.ordered_refs
    ]
    if node.type == "ResearchThread":
        props["ordered_refs"] = [note_link(atlas.entities[ref]) for ref in node.ordered_refs]
    return props


def frontmatter(properties: Mapping[str, object]) -> str:
    return "---\n" + yaml.safe_dump(dict(properties), sort_keys=False, allow_unicode=True) + "---\n"


def technical_sections(atlas: Atlas, node: TechnicalIdentity) -> list[str]:
    """Readable dossier projections; edge directions remain explicit and unmodified."""
    edges = sorted(
        (e for e in atlas.relationships if node.id in {e.source, e.target}),
        key=lambda e: (e.relation, e.source, e.target),
    )
    lines: list[str] = []

    def section(title: str, selected: list[Relationship]) -> None:
        lines.extend(["## " + title, ""])
        for edge in selected:
            outgoing = edge.source == node.id
            other = atlas.entities[edge.target if outgoing else edge.source]
            labels = {
                "part_of": ("Technical parent", "Technical child"),
                "presented_in_domain": ("Presentation Domain", "Presented record"),
                "consumes": ("Input", "Consumed by"),
                "supplies": ("Output", "Supplied by"),
                "constrains": ("Constrains", "Constrained by"),
                "supports": ("Supports", "Supporting"),
                "contradicts": ("Contradicts", "Contradicting"),
                "measured_at": ("Measurement target", "Measurement point"),
                "related_to_research_question": ("Research question", "Research subject"),
                "studied_by": ("Studied by", "Studies"),
                "supersedes": ("Supersedes", "Superseded by"),
                "decomposed_into": ("Decomposed into", "Decomposed from"),
                "research_suggests_decomposition": ("Proposed decomposition target", "Proposal"),
            }
            label = labels.get(edge.relation, (edge.relation, edge.relation + " from"))[
                0 if outgoing else 1
            ]
            lines.append(f"- {label}: {note_link(other)}")
            if edge.decision_id:
                lines.append(f"  Approval: {note_link(atlas.entities[edge.decision_id])}")
        if not selected:
            lines.append("None mapped.")
        lines.append("")

    def adjacent_types(edge: Relationship) -> set[str]:
        return {atlas.entities[id].type for id in (edge.source, edge.target) if id != node.id}

    section("Technical structure", [e for e in edges if e.relation == "part_of"])
    lines += ["Technical parents are outgoing `part_of`; children are incoming `part_of`.", ""]
    section("Presentation", [e for e in edges if e.relation == "presented_in_domain"])
    lines += [f"L-level: {node.atlas_level}. Overview visibility: {node.overview_visibility}.", ""]
    section("Inputs and outputs", [e for e in edges if e.relation in {"supplies", "consumes"}])
    for title, types in (
        ("Interfaces and contracts", {"Interface", "Contract"}),
        ("Data artifacts", {"DataArtifact"}),
        ("Measurement points", {"MeasurementPoint"}),
        ("Evidence", {"Evidence"}),
        ("Research questions", {"ResearchQuestion"}),
    ):
        section(title, [e for e in edges if adjacent_types(e) & types])
    lines += ["## Research threads", ""]
    threads = record_properties(atlas, node)["research_threads"]
    lines += [f"- {link}" for link in threads] or ["None mapped."]
    lines.append("")
    for title, types in (
        ("Papers", {"Paper"}),
        ("Findings and contradictions", {"Finding"}),
        ("Decisions", {"Decision"}),
        ("Experiment leads", {"ExperimentLead"}),
    ):
        section(
            title,
            [
                e
                for e in edges
                if adjacent_types(e) & types
                or (title == "Findings and contradictions" and e.relation == "contradicts")
            ],
        )
    section("History", [e for e in edges if e.relation in {"supersedes", "decomposed_into"}])
    lines += [
        "Outgoing/incoming edges show supersedes / superseded by and decomposed into / from.",
        "",
        "## Review / proposals",
        "",
        "No accepted proposal is mapped unless represented by the Registry decisions above. "
        "Keep authored proposals in separate notes; accepted changes must enter through Registry "
        "review. Generated notes do not accept changes or claims.",
        "",
    ]
    return lines


def render_record(atlas: Atlas, node: Entity) -> str:
    lines = [
        frontmatter(record_properties(atlas, node)),
        f"# {node.id} — {node.name}",
        "",
        GENERATED_NOTICE,
        "",
        node.description,
        "",
    ]
    if isinstance(node, TechnicalIdentity):
        status = node.technical
        lines += [
            "## Classification",
            "",
            f"Architecture authority: {status.architecture_authority}. "
            f"Implementation: {status.implementation_status}. "
            f"Verification: {status.verification_status}.",
            "",
            f"Research mapping: {node.research_mapping}. "
            f"Research direction: {node.research_direction}.",
            "",
            "Implementation is not live demonstration; integration tests are not measurement "
            "validation. Target-only does not mean a research gap.",
            "",
        ]
    if isinstance(node, Evidence):
        lines += [
            "## Evidence locator",
            "",
            f"Provenance: {node.provenance_kind}. Checked: {node.checked_date.isoformat()}.",
            "",
            source_locator(node),
            "",
        ]
    if isinstance(node, TechnicalIdentity):
        lines += technical_sections(atlas, node)
        lines += ["[[Home/Research Atlas|Research Atlas Home]]", ""]
        return "\n".join(lines)
    lines += ["## Registry relationships", ""]
    edges = sorted(atlas.relationships, key=lambda e: (e.relation, e.source, e.target))
    for edge in edges:
        if node.id not in {edge.source, edge.target}:
            continue
        lines.append(
            f"- {note_link(atlas.entities[edge.source])} — `{edge.relation}` → "
            f"{note_link(atlas.entities[edge.target])}"
        )
        if edge.decision_id:
            lines.append(f"  Approval: {note_link(atlas.entities[edge.decision_id])}")
    if not any(node.id in {e.source, e.target} for e in edges):
        lines.append("No relationships recorded.")
    if node.type == "ResearchThread":
        lines += ["", "## Ordered research path", ""]
        lines += [
            f"{i}. {note_link(atlas.entities[ref])}" for i, ref in enumerate(node.ordered_refs, 1)
        ]
    threads = record_properties(atlas, node)["research_threads"]
    if threads:
        lines += ["", "## Research threads", "", *[f"- {link}" for link in threads]]
    lines += ["", "[[Home/Research Atlas|Research Atlas Home]]", ""]
    return "\n".join(lines)


def ordered_entities(atlas: Atlas) -> list[Entity]:
    return sorted(atlas.entities.values(), key=lambda n: (n.overview_order or 2**31, n.id))


def render_home(atlas: Atlas) -> str:
    lines = [
        "# Research Atlas",
        "",
        GENERATED_NOTICE,
        "",
        "Registry = authoritative SOT. Generated notes = views. "
        "Presentation Domain != technical hierarchy: only `part_of` defines technical ancestry.",
        "",
        "Open docs/research-atlas/ as an Obsidian vault. Enable the Bases core plugin. "
        "The Excalidraw community plugin is required only for the visual map; "
        "no personal plugin settings are committed.",
        "",
        "[[Assets/Excalidraw/System Anatomy.excalidraw|System Anatomy]] · "
        "[[Generated/Atlas Views.base|Atlas Views]] · [[overview|Compatibility overview]]",
        "",
        "## Read and maintain",
        "",
        "Follow a technical note to its Evidence notes and source locators. "
        "Historical Evidence refs stay historical. New current-main claims require new records.",
        "",
        "Properties and all generated files are overwriteable, including changes made in Bases. "
        "Keep authored commentary/proposals in separate notes (for example Review Queues/). "
        "Accepted changes go through Registry review; "
        "no reverse sync or automatic status acceptance.",
        "",
        "Zotero/Work remain external proposal boundaries only: no API, automation, import or "
        "reverse sync is implemented. Research overlays do not change technical ancestry or "
        "accept research/architecture claims.",
        "",
        "Regenerate from repository root with "
        "`uv run --no-sync python -m fh_agent.research_atlas.workspace docs/research-atlas`; "
        "append `--check` for drift validation. The old dossiers/ views are migrated and removed.",
        "",
        "File-format references: [Bases syntax](https://obsidian.md/help/bases/syntax), "
        "[Excalidraw writer](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/"
        "master/src/shared/ExcalidrawData.ts) and "
        "[Drawing parser](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/"
        "master/src/shared/excalidrawMarkdownParsing.ts). The generated map uses parsed "
        "frontmatter, Text Elements, Element Links and an uncompressed JSON Drawing section. "
        "Validation is structural; it does not claim an interactive Obsidian plugin test.",
        "",
        "## System and presentation views",
        "",
    ]
    lines += [
        f"- {note_link(n)}"
        for n in ordered_entities(atlas)
        if n.type in {"System", "Domain", "Environment"}
    ]
    lines += ["", "## Research overlays", ""]
    lines += [
        f"- {note_link(n)}"
        for n in ordered_entities(atlas)
        if n.type in {"ResearchQuestion", "ResearchThread"}
    ]
    lines += [
        "",
        "The map includes canonical target paths as well as implementation. "
        "Consult individual notes for scope and status. Verifier is independent of Cortex; "
        "reflection follows verification. Training/candidate/certification are between runs only.",
        "",
    ]
    return "\n".join(lines)


# These columns are the generated Properties contract used by the one Base.
BASE_COLUMNS = (
    "atlas_id",
    "atlas_type",
    "atlas_level",
    "implementation_status",
    "verification_status",
    "research_mapping",
    "research_direction",
    "research_components",
    "research_interfaces",
    "measured_at",
    "contradicted_by",
    "supported_by",
    "part_of",
    "presented_in_domain",
)


def render_base() -> str:
    views = []

    def view(name: str, filters: list[str], group: str | None = None) -> None:
        item: dict[str, object] = {
            "type": "table",
            "name": name,
            "filters": {"and": filters},
            "order": ["file.name", *["note." + c for c in BASE_COLUMNS]],
            "sort": [{"property": "note.atlas_id", "direction": "ASC"}],
        }
        if group:
            item["groupBy"] = {"property": "note." + group, "direction": "ASC"}
        views.append(item)

    component = 'note.atlas_type == "Component"'
    view("Components by implementation status", [component], "implementation_status")
    for label, status in (
        ("Target-only", "target-only"),
        ("Partial", "partial"),
        ("Implemented", "implemented"),
    ):
        view(label, [f'note.implementation_status == "{status}"'])
    view("Verification status", ["!note.verification_status.isEmpty()"], "verification_status")
    view("Research Mapping Status", ["!note.research_mapping.isEmpty()"], "research_mapping")
    view("Research Direction Status", ["!note.research_direction.isEmpty()"], "research_direction")
    view(
        "Research Questions by Component",
        ['note.atlas_type == "ResearchQuestion"', "!note.research_components.isEmpty()"],
        "research_components",
    )
    view(
        "Research Questions by Interface",
        ['note.atlas_type == "ResearchQuestion"', "!note.research_interfaces.isEmpty()"],
        "research_interfaces",
    )
    view("Measurement Points", ['note.atlas_type == "MeasurementPoint"'], "measured_at")
    view(
        "Open Leads",
        [
            'note.atlas_type == "ExperimentLead"',
            'note.research_direction == "open-lead" || '
            'note.research_direction == "needs-closure" || '
            'note.research_direction == "active-candidate"',
        ],
    )
    view(
        "Decisions / History",
        [
            'note.atlas_type == "Decision" || !note.supersedes.isEmpty() || '
            "!note.supersedes_from.isEmpty() || !note.decomposed_into.isEmpty() || "
            '!note.decomposed_into_from.isEmpty() || (note.atlas_type == "ExperimentLead" && '
            '(note.research_direction == "killed" || note.research_direction == "deprioritized"))'
        ],
    )
    view(
        "Findings with contradictions",
        [
            'note.atlas_type == "Finding"',
            "!note.contradicted_by.isEmpty() || !note.contradicts.isEmpty()",
        ],
    )
    view("Unmapped research areas", [component, 'note.research_mapping == "unmapped"'])
    return yaml.safe_dump(
        {
            "filters": {"and": ["note.atlas_generated == true", "!note.atlas_id.isEmpty()"]},
            "properties": {"note." + c: {"displayName": c.replace("_", " ")} for c in BASE_COLUMNS},
            "views": views,
        },
        sort_keys=False,
        allow_unicode=True,
    )


# Fixed semantic placement is presentation code, never an alternate technical hierarchy.
# (x, y, width, height); new main nodes receive deterministic expansion rows below.
MAP_BOXES = {
    "ENV-GAME-INSTANCE": (20, 320, 300, 160),
    "CMP-SCREEN-CAPTURE": (470, 310, 300, 140),
    "DAT-SCREEN-FRAME": (840, 310, 300, 140),
    "CMP-VISIBLE-STATE-BRIDGE": (470, 520, 300, 150),
    "CMP-NO-SPOILER-FIREWALL": (840, 520, 300, 150),
    "CMP-PERCEPTION": (1210, 310, 300, 140),
    "DAT-OBSERVATION": (1580, 310, 300, 140),
    "CMP-TEMPORAL-STATE": (1580, 520, 300, 150),
    "CMP-EVIDENCE-LEDGER": (470, 760, 300, 150),
    "CMP-MEMORY": (470, 1010, 300, 180),
    "CMP-MEM-RETRIEVAL": (840, 760, 300, 150),
    "IF-MEM-CORTEX": (840, 1010, 300, 150),
    "DAT-RETRIEVAL-SNAPSHOT": (470, 1270, 300, 150),
    "CON-CORTEX-CONTEXT": (1210, 760, 300, 150),
    "CMP-CORTEX": (1210, 1010, 300, 150),
    "CON-PLANNER-OUTPUT": (1210, 1270, 300, 140),
    "IF-CORTEX-MANAGER": (1580, 1270, 300, 140),
    "CMP-MANAGER": (1210, 1510, 670, 240),
    "CMP-MANAGER-GROUNDING": (1230, 1620, 295, 110),
    "CMP-MANAGER-SCHED-COMP": (1555, 1620, 295, 110),
    "CON-SKILL-CONTRACT": (840, 1570, 300, 150),
    "CMP-BODY": (840, 1840, 300, 280),
    "CMP-BOUNDED-REFLEX": (860, 1990, 260, 110),
    "CON-PRIMITIVE-ACTION": (1210, 1900, 300, 160),
    "CMP-SAFETY-FILTER": (1210, 2210, 300, 150),
    "CMP-INPUT-EXECUTOR": (840, 2210, 300, 150),
    "DAT-ACTION-RESULT": (470, 2210, 300, 150),
    "DAT-VISIBLE-OUTCOME": (2040, 2210, 300, 150),
    "CMP-INDEPENDENT-VERIFIER": (2040, 1840, 300, 170),
    "CON-VERIFIER-RESULT": (2040, 1540, 300, 150),
    "CON-MEMORY-UPDATE-REQUEST": (2040, 1010, 300, 180),
    "CON-POST-MORTEM-OUTPUT": (2040, 760, 300, 150),
    "CMP-REPLAY-BUFFER": (2410, 1840, 300, 170),
    "DAT-REPLAY-TRANSITION": (2410, 2210, 300, 150),
    "CMP-SKILL-TRAINER": (2280, 2690, 300, 160),
    "DAT-CANDIDATE-BODY-VERSION": (1580, 2690, 300, 160),
    "CMP-BODY-CERTIFICATION": (840, 2690, 300, 160),
}
BETWEEN_RUNS = frozenset(
    {"CMP-SKILL-TRAINER", "DAT-CANDIDATE-BODY-VERSION", "CMP-BODY-CERTIFICATION"}
)
MAP_CONTAINED_IDS = frozenset({"CMP-MANAGER-GROUNDING", "CMP-BOUNDED-REFLEX"})


def map_record_ids(atlas: Atlas) -> set[str]:
    """Registry visibility selects ordinary records; only two contained details override it."""
    return {
        n.id
        for n in atlas.entities.values()
        if isinstance(n, TechnicalIdentity)
        and n.type != "MeasurementPoint"
        and (n.overview_visibility == "main" or n.id in MAP_CONTAINED_IDS)
    }


def element_id(identity: str) -> str:
    # Plugin block references use eight-character alphanumeric text IDs.
    return hashlib.sha256(identity.encode()).hexdigest()[:8]


def _element(identity: str, kind: str, box: tuple[int, int, int, int]) -> dict:
    x, y, width, height = box
    return {
        "id": element_id(identity),
        "type": kind,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "angle": 0,
        "strokeColor": "#243447",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": int(element_id(identity), 16) % (2**31),
        "version": 1,
        "versionNonce": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": 0,
        "link": None,
        "locked": False,
    }


def _text(identity: str, text: str, x: int, y: int, width: int, *, size: int = 18) -> dict:
    wrapped = "\n".join(
        textwrap.fill(line, max(12, int(width / (size * 0.62)))) for line in text.splitlines()
    )
    item = _element(identity, "text", (x, y, width, int(len(wrapped.splitlines()) * size * 1.25)))
    item.update(
        text=wrapped,
        rawText=wrapped,
        originalText=wrapped,
        fontSize=size,
        fontFamily=2,
        textAlign="left",
        verticalAlign="top",
        containerId=None,
        autoResize=False,
        lineHeight=1.25,
    )
    return item


def render_map(atlas: Atlas) -> str:
    visible = map_record_ids(atlas) - {"SYS-AGA"}
    boxes = {id: box for id, box in MAP_BOXES.items() if id in visible}
    extra = [n for n in ordered_entities(atlas) if n.id in visible and n.id not in boxes]
    for i, node in enumerate(extra):
        boxes[node.id] = (470 + (i % 5) * 460, 3060 + (i // 5) * 230, 350, 160)
    elements = []
    for identity, title, box in (
        ("agent-boundary", "Agent boundary — in-run responsibilities", (400, 170, 2380, 2270)),
        (
            "between-runs",
            "Between runs only — training / candidate / certification",
            (400, 2570, 2380, 350),
        ),
    ):
        shape = _element(identity, "rectangle", box)
        shape.update(strokeStyle="dashed", strokeColor="#7b8794")
        if identity == "agent-boundary" and "SYS-AGA" in atlas.entities:
            shape.update(
                link=note_link(atlas.entities["SYS-AGA"]), customData={"atlas_id": "SYS-AGA"}
            )
        elements.extend(
            [
                shape,
                _text(identity + "-title", title, box[0] + 20, box[1] + 20, box[2] - 40, size=24),
            ]
        )
    elements.extend(
        [
            _text(
                "map-title",
                f"{atlas.entities['SYS-AGA'].name} — Technical Spine",
                400,
                20,
                2300,
                size=34,
            ),
            _text(
                "map-legend",
                "Registry view · target paths and implementation coexist · consult note status · "
                "selected typed arrows; full graph in notes",
                400,
                85,
                2300,
            ),
            _text(
                "bridge-boundary",
                "Optional ingress: Bridge must pass Firewall; no bypass",
                460,
                690,
                690,
                size=16,
            ),
            _text(
                "independent-verification",
                "Independent verification / Memory-Replay return\n"
                "Outside Cortex decision path\nReflection after verification",
                2020,
                480,
                700,
                size=22,
            ),
            _text(
                "reflection-boundary",
                "Cortex supplies reflection contracts; Verifier alone supplies verified outcomes",
                2030,
                1230,
                690,
                size=17,
            ),
        ]
    )
    # Draw only typed work relationships; neither Domain nor part_of adds a flow arrow.
    flow_relations = {
        "supplies",
        "consumes",
        "observes",
        "controls",
        "grounds",
        "executes",
        "verifies",
        "proposes_to",
        "retrieves_from",
        "updates",
    }
    for edge in sorted(atlas.relationships, key=lambda e: (e.source, e.relation, e.target)):
        if (
            edge.relation not in flow_relations
            or edge.source not in boxes
            or edge.target not in boxes
        ):
            continue
        sx, sy, sw, sh = boxes[edge.source]
        tx, ty, tw, th = boxes[edge.target]
        # Only adjacent, non-overlapping boxes get arrows on the main map. Full
        # relationships remain in notes; routing long edges through other actors
        # would falsely imply intermediate authority or hide labels.
        overlap_x = min(sx + sw, tx + tw) - max(sx, tx)
        overlap_y = min(sy + sh, ty + th) - max(sy, ty)
        if overlap_y > 0 and (sx + sw <= tx or tx + tw <= sx):
            y = (max(sy, ty) + min(sy + sh, ty + th)) // 2
            start, end = ((sx + sw, y), (tx, y)) if sx < tx else ((sx, y), (tx + tw, y))
        elif overlap_x > 0 and (sy + sh <= ty or ty + th <= sy):
            x = (max(sx, tx) + min(sx + sw, tx + tw)) // 2
            start, end = ((x, sy + sh), (x, ty)) if sy < ty else ((x, sy), (x, ty + th))
        else:
            continue
        if abs(end[0] - start[0]) + abs(end[1] - start[1]) > 440:
            continue
        dx, dy = end[0] - start[0], end[1] - start[1]
        identity = f"{edge.source}:{edge.relation}:{edge.target}"
        arrow = _element(identity, "arrow", (*start, abs(dx), abs(dy)))
        arrow.update(
            points=[[0, 0], [dx, dy]],
            startBinding=None,
            endBinding=None,
            startArrowhead=None,
            endArrowhead="arrow",
            elbowed=False,
            customData={"atlas_relation": edge.model_dump(exclude_none=True)},
        )
        elements.append(arrow)
        elements.append(
            _text(
                identity + "-label",
                edge.relation,
                (start[0] + end[0]) // 2 + (8 if dy else -30),
                (start[1] + end[1]) // 2 - 18,
                150 if dy else 90,
                size=12,
            )
        )
    for id, box in boxes.items():
        node = atlas.entities[id]
        shape = _element(id, "rectangle", box)
        status = node.technical.implementation_status if isinstance(node, TechnicalIdentity) else ""
        shape.update(
            link=note_link(node),
            customData={"atlas_id": id},
            backgroundColor={
                "implemented": "#e6f4ea",
                "partial": "#fff4d6",
                "target-only": "#edf0f5",
            }.get(status, "#edf0f5"),
        )
        elements.append(shape)
        label = f"{node.name}\n{node.type} · {status}"
        text = _text(id + "-text", label, box[0] + 12, box[1] + 12, box[2] - 24, size=17)
        text.update(link=note_link(node))
        elements.append(text)
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "research-atlas",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
        "files": {},
    }
    lines = [
        frontmatter({"excalidraw-plugin": "parsed", "atlas_workspace_generated": True}),
        GENERATED_NOTICE,
        "",
        "%%",
        "# Excalidraw Data",
        "",
        "## Text Elements",
        "",
    ]
    lines += [f"{el['rawText']} ^{el['id']}\n" for el in elements if el["type"] == "text"]
    lines += ["## Element Links", ""]
    lines += [f"{el['id']}: {el['link']}\n" for el in elements if el["link"]]
    lines += [
        "## Drawing",
        "```json",
        json.dumps(scene, ensure_ascii=False, sort_keys=True, indent=2),
        "```",
        "%%",
        "",
    ]
    return "\n".join(lines)


def workspace_tree(atlas: Atlas) -> dict[PurePosixPath, str]:
    from .render import render_overview

    tree = {
        note_path_for(n.id, n.type, n.name): render_record(atlas, n)
        for n in sorted(atlas.entities.values(), key=lambda n: n.id)
    }
    if len(tree) != len(atlas.entities):
        raise ValueError("Generated note path collision")
    tree.update(
        {
            HOME_PATH: render_home(atlas),
            BASE_PATH: render_base(),
            MAP_PATH: render_map(atlas),
            PurePosixPath("overview.md"): render_overview(atlas),
        }
    )
    validate_workspace_tree(atlas, tree)
    return tree


def validate_links(tree: Mapping[PurePosixPath, str]) -> None:
    targets = {str(path.with_suffix("")) if path.suffix == ".md" else str(path) for path in tree}
    for path, content in tree.items():
        for match in WIKILINK.finditer(content):
            target = match.group(1).split("|", 1)[0].split("#", 1)[0]
            if target not in targets:
                raise ValueError(f"Unresolved generated link in {path}: {target}")


def validate_workspace_tree(atlas: Atlas, tree: Mapping[PurePosixPath, str]) -> None:
    """Validate record coverage, Base property contract and map identity before writing."""
    validate_links(tree)
    records: dict[str, dict] = {}
    for path, text in tree.items():
        if path.suffix != ".md":
            continue
        props = parse_frontmatter(text)
        if props.get("atlas_generated") is not True:
            continue
        identity = props.get("atlas_id")
        if identity not in atlas.entities or identity in records:
            raise ValueError("Unknown or duplicate generated atlas_id")
        node = atlas.entities[identity]
        if path != note_path_for(identity, node.type, node.name):
            raise ValueError("Generated path/frontmatter mismatch")
        if props != record_properties(atlas, node):
            raise ValueError("Generated Properties differ from Registry")
        records[identity] = props
    if set(records) != set(atlas.entities):
        raise ValueError("Generated record coverage mismatch")
    base = yaml.safe_load(tree[BASE_PATH])
    if base.get("filters") != {"and": ["note.atlas_generated == true", "!note.atlas_id.isEmpty()"]}:
        raise ValueError("Base must isolate generated Atlas record notes")
    properties = set().union(*(p.keys() for p in records.values()))
    referenced = set(re.findall(r"note\.([a-z_]+)", tree[BASE_PATH]))
    if not referenced <= properties:
        raise ValueError(f"Base references undeclared Properties: {referenced - properties}")
    drawing = tree[MAP_PATH]
    if parse_frontmatter(drawing).get("excalidraw-plugin") != "parsed":
        raise ValueError("Map requires parsed Excalidraw frontmatter")
    if "## Text Elements\n" not in drawing or "## Element Links\n" not in drawing:
        raise ValueError("Map requires Text Elements and Element Links sections")
    match = re.search(r"\n## Drawing\n[^`]*```json\n([\s\S]*?)```\n", drawing)
    if not match:
        raise ValueError("Map requires uncompressed JSON Drawing section")
    scene = json.loads(match.group(1))
    elements = scene["elements"]
    if scene.get("type") != "excalidraw" or scene.get("version") != 2 or scene.get("files"):
        raise ValueError("Invalid basic Excalidraw scene")
    if len({el["id"] for el in elements}) != len(elements):
        raise ValueError("Duplicate Excalidraw element ID")
    map_records = set()
    relations = [e.model_dump(exclude_none=True) for e in atlas.relationships]
    for element in elements:
        if element["type"] not in {"rectangle", "text", "arrow"}:
            raise ValueError("Unsupported Excalidraw element type")
        if element["type"] == "arrow":
            if element.get("customData", {}).get("atlas_relation") not in relations:
                raise ValueError("Map arrow must correspond to a typed Registry relationship")
        identity = element.get("customData", {}).get("atlas_id")
        if identity is not None:
            if identity not in atlas.entities or identity in map_records:
                raise ValueError("Invalid or duplicate map record ID")
            if element.get("link") != note_link(atlas.entities[identity]):
                raise ValueError("Map record link mismatch")
            map_records.add(identity)
    required = map_record_ids(atlas)
    if required != map_records:
        raise ValueError(f"Map central-node coverage mismatch: {required ^ map_records}")


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("Malformed generated frontmatter")
    data = yaml.safe_load(parts[0][4:])
    return data if isinstance(data, dict) else {}


def validate_workspace(atlas: Atlas, root: Path) -> None:
    """Check complete content, identity/path coverage, links and disposable-view drift."""
    expected = workspace_tree(atlas)
    seen = set()
    for path in root.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        props = parse_frontmatter(content)
        if props.get("atlas_generated") is not True:
            continue
        id = props.get("atlas_id")
        if id not in atlas.entities:
            raise ValueError(f"Unknown generated atlas_id: {id}")
        if id in seen:
            raise ValueError(f"Duplicate generated atlas_id: {id}")
        seen.add(id)
        node = atlas.entities[id]
        relative = PurePosixPath(path.relative_to(root).as_posix())
        if relative != note_path_for(id, node.type, node.name):
            raise ValueError(f"Generated note path/frontmatter mismatch: {path}")
        if props != record_properties(atlas, node):
            raise ValueError(f"Generated Properties drift: {id}")
    if seen != set(atlas.entities):
        raise ValueError("Generated record coverage mismatch")
    if any((root / "dossiers").glob("*.md")):
        raise ValueError("Stale active pilot dossiers")
    for path, content in expected.items():
        full = root / path
        if not full.is_file() or full.read_text(encoding="utf-8") != content:
            raise ValueError(f"Generated workspace drift: {path}")
    bases = {PurePosixPath(p.relative_to(root).as_posix()) for p in root.rglob("*.base")}
    maps = {PurePosixPath(p.relative_to(root).as_posix()) for p in root.rglob("*.excalidraw.md")}
    if bases != {BASE_PATH} or maps != {MAP_PATH}:
        raise ValueError("Exactly one central Base and map required")


def write_workspace(atlas: Atlas, root: Path) -> None:
    """Replace generated views, pruning obsolete generated filenames after a rename."""
    tree = workspace_tree(atlas)
    for path in root.rglob("*.md"):
        if parse_frontmatter(path.read_text(encoding="utf-8")).get("atlas_generated") is True:
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if relative not in tree:
                path.unlink()
    # Explicit one-time migration of v0.1 generated/reference-only views, not authored notes.
    for id in ("CMP-CORTEX", "CMP-MANAGER", "CMP-MEM-RETRIEVAL"):
        (root / "dossiers" / f"{id}.md").unlink(missing_ok=True)
    for relative, content in tree.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    validate_workspace(atlas, root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Atlas vault root")
    parser.add_argument("--check", action="store_true", help="Validate committed view drift")
    args = parser.parse_args()
    atlas = load_registry(args.root)
    if args.check:
        validate_workspace(atlas, args.root)
    else:
        write_workspace(atlas, args.root)


if __name__ == "__main__":
    main()
