"""Final Research Map packaging of the validated, semantically distinct projections.

The older renderers are pure intermediate representations and bounded migration
readers. Only this package is written by the supported workspace harness.
"""

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass
from functools import cache
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from . import knowledge_graph as graph
from . import obsidian_semantics as semantics
from . import private_projection as public
from . import private_views as views
from .architecture_explanations import (
    AREAS,
    ExplanationCatalog,
    component_technical,
    guide_pages,
    reference_page,
    typed_page,
)
from .diagram_canvas import (
    CANVAS_NAVIGATION,
    EXECUTION_CANVAS,
    INTERACTION_CANVAS,
    card_height,
    execution_canvas,
    identity_text,
    interaction_canvas,
)
from .diagram_svg import (
    CANDIDATE_DRAWIO,
    CANDIDATE_EXCALIDRAW,
    candidate_navigation,
    managed_drawio,
    managed_system_overview,
    primary_pages,
    secondary_canvases,
    svg_assets,
)
from .preferred_paths import FAMILIES, HOME, INTERNAL, PRODUCT, containment_paths, preferred_paths
from .private_projection import ProjectionError, markdown_parts, read_yaml, utf8, yaml_text
from .private_reference_index import ReferenceIndex
from .research_presentation import ROLE_LABELS, literal, record_link
from .schema import Relationship
from .validator import Atlas
from .wiki_schema import EpistemicRecord, Finding, ReadingNote

MODES = {
    "architecture": "Architecture",
    "knowledge-detail": "Knowledge Detail",
    "rq-overlay": "Questions",
}
MANIFESTS = {
    public.OWNER: INTERNAL / "Manifests/technical-atlas.yaml",
    views.OWNER: INTERNAL / "Manifests/research-map.yaml",
}
LEDGER = INTERNAL / "Migration/routes.yaml"
ARCHITECTURE_TREE = PRODUCT / "Diagrams/Architecture Tree.md"
ARCHITECTURE_CANVAS = PRODUCT / "Diagrams/Architecture Tree.canvas"
EXECUTION_FLOW = PRODUCT / "Diagrams/Execution Flow.md"
EXECUTION_FLOW_ORIENTATION_IDS = (
    "SYS-AGA",
    "CMP-CORTEX",
    "CMP-MANAGER",
    "CMP-BODY",
    "CMP-INDEPENDENT-VERIFIER",
    "FUNC-EXECUTIVE-CONTROL",
)


INTERACTION_MAP = PRODUCT / "Diagrams/Interaction Map.md"
INTERACTION_RELATIONS = frozenset(
    {
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
    }
)
INTERACTION_ORIENTATION_IDS = (
    "SYS-AGA",
    "CMP-CORTEX",
    "CMP-MANAGER",
    "CMP-BODY",
    "CMP-MEM-RETRIEVAL",
    "CMP-INDEPENDENT-VERIFIER",
    "IF-MEM-CORTEX",
    "IF-CORTEX-MANAGER",
    "CON-CORTEX-CONTEXT",
    "CON-PLANNER-OUTPUT",
    "CON-SKILL-CONTRACT",
)


INTERACTION_GROUPS = (
    ("Observation and evidence", {"ENV-GAME-INSTANCE", "DAT-SCREEN-FRAME", "DAT-OBSERVATION"}),
    (
        "Bounded retrieval to Cortex",
        {"IF-MEM-CORTEX", "CON-CORTEX-CONTEXT", "DAT-RETRIEVAL-SNAPSHOT"},
    ),
    ("Cortex intention to Manager", {"CMP-MANAGER", "IF-CORTEX-MANAGER", "CON-PLANNER-OUTPUT"}),
    (
        "Manager contracts and Body / Reflex",
        {"CON-SKILL-CONTRACT", "CMP-BODY", "CMP-BOUNDED-REFLEX"},
    ),
    ("Primitive proposals and guarded input", {"CON-PRIMITIVE-ACTION", "DAT-ACTION-RESULT"}),
    ("Independent verification", {"DAT-VISIBLE-OUTCOME", "CON-VERIFIER-RESULT"}),
    (
        "Evidence-linked memory requests",
        {"CON-MEMORY-UPDATE-REQUEST", "CON-POST-MORTEM-OUTPUT"},
    ),
    (
        "Optional future between-Mission-Run learning",
        {"DAT-REPLAY-TRANSITION", "DAT-CANDIDATE-BODY-VERSION"},
    ),
)

ANATOMY = PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md"
ANATOMY_DIRECTORY = PRODUCT / "Guides/Using the Research Map.md"
ANATOMY_AREAS = dict(
    zip(
        (
            "environment",
            "observation",
            "evidence-memory",
            "cognition",
            "executive",
            "action-safety",
            "verification",
            "between-runs",
        ),
        (AREAS[0], *AREAS),
        strict=True,
    )
)
# Reading routes only. Components use the accepted presentation source's areas;
# these typed counterparts create neither Registry membership nor ancestry.
ANATOMY_COUNTERPARTS = {
    AREAS[0]: (
        "ENV-GAME-INSTANCE",
        "FUNC-ACQUIRE",
        "FUNC-OBSERVE",
        "DAT-SCREEN-FRAME",
        "DAT-OBSERVATION",
    ),
    AREAS[1]: (
        "FUNC-RETAIN-RETRIEVE",
        "IF-MEM-CORTEX",
        "CON-CORTEX-CONTEXT",
        "CON-MEMORY-UPDATE-REQUEST",
        "DAT-RETRIEVAL-SNAPSHOT",
        "MEAS-RETRIEVAL-DELIVERY-001",
    ),
    AREAS[2]: (
        "FUNC-REASON",
        "CON-PLANNER-OUTPUT",
        "CON-POST-MORTEM-OUTPUT",
        "MEAS-CORTEX-PROPOSAL-001",
    ),
    AREAS[3]: (
        "FUNC-EXECUTIVE-CONTROL",
        "IF-CORTEX-MANAGER",
        "CON-SKILL-CONTRACT",
        "MEAS-MANAGER-DISPOSITION-001",
    ),
    AREAS[4]: ("FUNC-ACT", "CON-PRIMITIVE-ACTION", "DAT-ACTION-RESULT"),
    AREAS[5]: (
        "FUNC-VERIFY",
        "CON-VERIFIER-RESULT",
        "DAT-VISIBLE-OUTCOME",
        "MEAS-VERIFIED-OUTCOME-001",
    ),
    AREAS[6]: ("FUNC-BETWEEN-RUNS", "DAT-REPLAY-TRANSITION", "DAT-CANDIDATE-BODY-VERSION"),
    "System und Forschungsprogramm": (
        "SYS-AGA",
        "RQ-PROGRAM-AB-001",
        "THREAD-EXPERIENCE-TO-ACTION-001",
        "DEC-ATLAS-PILOT-001",
    ),
}
ANATOMY_AREA_DESCRIPTIONS = {
    AREAS[0]: (
        "Vom sichtbaren Spielbild zur zulässigen Beobachtung: Aufnahme, Schutz vor "
        "verborgenem Wissen und Zustandsaufbereitung."
    ),
    AREAS[1]: (
        "Von belegter Erfahrung zum begrenzten Planerkontext: Speicherung und Auswahl sind "
        "getrennte Aufgaben."
    ),
    AREAS[2]: (
        "Von Beobachtung und ausgewählter Erfahrung zum Vorschlag: Cortex plant, ohne "
        "primitive Eingaben zu steuern."
    ),
    AREAS[
        3
    ]: "Vom Vorschlag zum begrenzten Auftrag: Manager prüft, erdet und entscheidet über Contracts.",
    AREAS[4]: (
        "Vom aktiven Auftrag zur erlaubten Eingabe: Body und Reflex bleiben begrenzt; "
        "Schutzprüfung und Ausführung sind getrennt."
    ),
    AREAS[5]: (
        "Von Handlung und Beobachtung zur unabhängigen Prüfung: VerifierResult beschreibt "
        "das Urteil, Independent Verifier trägt die Verantwortung."
    ),
    AREAS[6]: (
        "Von gesammelter Erfahrung zu einem möglichen Kandidaten: Training und "
        "Zertifizierung liegen außerhalb des Mission Run und brauchen ein autorisiertes "
        "künftiges Protokoll."
    ),
    "System und Forschungsprogramm": (
        "Systemgrenze, Arbeitsfrage, Lesefaden und "
        "Pilotentscheidung erklären den Kontext; sie belegen "
        "keine neuen Forschungsergebnisse."
    ),
}


def anatomy_directory(
    catalog: ExplanationCatalog, atlas: Atlas, preferred: dict[str, PurePosixPath]
) -> str:
    groups = {
        area: tuple(sorted(i for i, item in catalog.components.items() if item.area == area))
        + ANATOMY_COUNTERPARTS[area]
        for area in AREAS
    }
    groups["System und Forschungsprogramm"] = ANATOMY_COUNTERPARTS["System und Forschungsprogramm"]
    identities = [i for values in groups.values() for i in values]
    if len(identities) != len(set(identities)) or set(identities) != set(preferred):
        raise ProjectionError("Agent Anatomy directory must cover each preferred identity once")
    lines = [
        "## Agent Anatomy Navigation",
        "",
        (
            "Wähle einen Bereich der Illustration oder einen Lesebereich unten. Jede Zeile "
            "öffnet die eine bevorzugte Identitätsseite. Diese Lesebereiche sind keine "
            "technischen Eltern, Domains oder neuen Function-Mitgliedschaften."
        ),
        "",
        " · ".join(f"[[#{area}|{area}]]" for area in groups),
        "",
    ]
    for area, values in groups.items():
        lines += [f"## {area}", "", ANATOMY_AREA_DESCRIPTIONS[area], ""]
        if area in AREAS:
            lines += [
                f"[[Research Map/Guides/System Overview#{area}|Zusammenhang im System Overview]]",
                "",
            ]
        for identity in values:
            node = atlas.entities[identity]
            lines += [
                f"- [[{preferred[identity].with_suffix('')}|{node.name}]] "
                f"— {node.type} · `{identity}`"
            ]
        lines += ["", f"[[{ANATOMY.with_suffix('')}|Zurück zu Agent Anatomy]]", ""]
    lines += [
        "Forschung lesen: [[Research Map/Guides/Scientific Experiment|Scientific Experiment]] · "
        "[[Research Map/Guides/Experience to Knowledge|Experience to Knowledge]]. "
        + (
            "Quellen und Prüfungen stehen auf jeder Identitätsseite; die vollständige "
            "technische Hierarchie und das Relationsregister bleiben separate Inspektionswege."
        ),
        "",
    ]
    return "\n".join(lines)


def anatomy_hub(body: str, atlas: Atlas, preferred: dict[str, PurePosixPath]) -> str:
    """Project navigation only; preserve illustration, geometry and semantic edges."""
    match = re.search(r"(?ms)^## Drawing\n```json\n(.*?)\n```", body)
    if match is None:
        raise ProjectionError("Agent Anatomy drawing is missing")
    scene = json.loads(match[1])
    for item in scene["elements"]:
        custom = item.get("customData", {})
        identity = custom.get("landmark_identity")
        link = item.get("link")
        if identity is not None and (
            identity not in preferred
            or custom.get("landmark_type") != atlas.entities[identity].type
            or not isinstance(link, str)
            or link.split("|", 1)[0] != f"[[{preferred[identity].with_suffix('')}"
        ):
            raise ProjectionError("Agent Anatomy preferred landmark/type cannot be proven")
        key = custom.get("functional_region") or custom.get("navigation")
        if key == "identity-directory":
            item["link"] = (
                f"[[{ANATOMY_DIRECTORY.with_suffix('')}#Agent Anatomy Navigation|Alle Bereiche]]"
            )
        if key in ANATOMY_AREAS:
            target = f"[[{ANATOMY_DIRECTORY.with_suffix('')}#{ANATOMY_AREAS[key]}|Bereich öffnen]]"
            item["link"] = target
            custom["navigation_target"] = target
            if item["type"] == "text":
                item.update(
                    text="BEREICH ÖFFNEN  →",
                    rawText="BEREICH ÖFFNEN  →",
                    originalText="BEREICH ÖFFNEN  →",
                )
    # Regenerate both native caches from the same scene. Embedded-file bindings
    # and all existing envelope/source/owner fields retain their exact bytes.
    prefix, _, cache = body.partition("## Text Elements\n")
    embedded = cache.split("## Embedded Files\n", 1)[1].split("## Drawing\n", 1)[0]
    text = "## Text Elements\n\n" + "\n".join(
        f"{item['rawText']} ^{item['id']}\n" for item in scene["elements"] if item["type"] == "text"
    )
    links = "\n## Element Links\n\n" + "\n".join(
        f"{item['id']}: {item['link']}\n" for item in scene["elements"] if item.get("link")
    )
    fallback = [
        "## Ohne Diagrammplugin",
        "",
        (
            "Beginne mit einem Bereich. Beschriftungen öffnen einzelne Identitäten; Bereich "
            "öffnen führt zu den zugehörigen Components und typisierten Gegenstücken. "
            "Function-Titel beschreiben Beiträge, keine Elternschaft."
        ),
        "",
    ]
    fallback += [
        f"- [[{ANATOMY_DIRECTORY.with_suffix('')}#{area}|{area}]] "
        f"— {ANATOMY_AREA_DESCRIPTIONS[area]}"
        for area in ANATOMY_COUNTERPARTS
    ]
    fallback += [
        "",
        f"[[{HOME.with_suffix('')}|Home]] · "
        f"[[{ARCHITECTURE_TREE.with_suffix('')}|Vollständige Hierarchie]] · "
        f"[[{INTERACTION_MAP.with_suffix('')}|47 technische Relationen]]",
        "",
    ]
    prefix = (
        prefix.removesuffix("%%\n# Excalidraw Data\n\n")
        + "\n".join(fallback)
        + "\n%%\n# Excalidraw Data\n\n"
    )
    return (
        prefix
        + text
        + links
        + "\n## Embedded Files\n"
        + embedded
        + "## Drawing\n```json\n"
        + json.dumps(scene, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n%%\n"
    )


def interaction_map(atlas: Atlas, preferred: dict[str, PurePosixPath]) -> str:
    """Render only declared directed technical rows; panels add no facts."""
    edges = sorted(
        (e for e in atlas.relationships if e.relation in INTERACTION_RELATIONS),
        key=lambda e: (e.relation, e.source, e.target),
    )
    groups = INTERACTION_GROUPS
    body = [
        "# Interaction Map",
        "",
        f"[[{INTERACTION_CANVAS}|Open Interaction Map Canvas]]"
        " — primary visual; pan/zoom and follow identity links.",
        "",
        f"![[{INTERACTION_CANVAS}]]",
        "",
        "[[Research Map Home|Home]] · "
        f"[[{ARCHITECTURE_TREE.with_suffix('')}|Composition hierarchy]] · "
        f"[[{EXECUTION_FLOW.with_suffix('')}|Execution sequence]] · "
        "[[#Complete linked relation ledger|Markdown fallback]]",
        "",
        "## Reading the map",
        "",
        "Arrows preserve Registry source → target and the exact relation name. "
        "In particular, consumes points from actor to payload; there is no presentation "
        "inversion. Shared payloads never imply a direct Component connection. "
        "These arrows are technical declarations, not temporal ordering. Architecture Tree "
        "alone shows part_of ancestry; Ablaufdiagramm explains control prerequisites. "
        "contributes_to_function is functional context, not ancestry or interaction. "
        "supports and other research/evidence/provenance relations are excluded.",
        "",
        "Legend: each node names its actual Registry type and stable ID; System/Component "
        "labels also show Registry implementation status. supplies / consumes describe "
        "payload declarations; controls is authority, proposes_to is intention, constrains "
        "is a limit, grounds binds a target, executes declares contract execution, observes "
        "and verifies remain distinct. updates / retrieves_from are shown only if declared. "
        "Panels are presentation-only and their order is not a schedule.",
        "",
        "Native Obsidian Mermaid requires no community plugin. Native visual rendering and "
        "laptop legibility remain unverified until inspected in app. Every relation and "
        "identity can be read and opened in the linked Markdown ledger without Mermaid.",
        "",
        "## Authority and implementation limits",
        "",
        "Cortex proposes evidence-grounded intention, never primitive keys/timings or direct "
        "InputExecutor control. Manager alone validates, grounds and opens/closes/suspends "
        "bounded contracts. Body and fast Reflex act only within an active Manager contract; "
        "Reflex cannot invent goals, extend budgets or suppress stop/replan. Safety/input "
        "requires valid contract, verified target-window focus, allowed action, rate-limit "
        "capacity, functional emergency stop and durable before/after evidence logging. "
        "Independent Verifier determines visible outcomes; Cortex never grades itself and "
        "a screenshot/hash change alone is not success.",
        "",
        "Optional Bridge is deny-by-default, allowlisted and simultaneously visible to a "
        "player; hidden-state access is an integrity incident. No absent firewall edge is "
        "invented. Memory requests retain evidence/provenance and grant no execution "
        "authority. Future learning/certification requires separate authorization between "
        "Mission Runs; Body weights remain frozen across Life Episodes within a Mission Run. "
        "No in-run replacement or candidate activation edge is inferred.",
        "",
        "Boundary explanations: "
        "[Canonical Architecture §§6–14](https://github.com/Planton361/autonomous-game-agent/"
        "blob/main/docs/canonical/02_ARCHITECTURE_CANONICAL.md#6-cortex-contract); "
        "[accepted Mission Run overlay](https://github.com/Planton361/autonomous-game-agent/"
        "blob/main/docs/orchestration/releases/ALIGN-2026-09-19-v1.0/README.md"
        "#mission-run-identity-and-mutable-state).",
        "",
        "Individual implemented / partial / target-only statuses do not certify a working "
        "full loop, scientific finding or phase exit. Missing or unmapped relations imply "
        "no capability, completeness or novelty conclusion. Preferred pages retain current "
        "verification, implementation references and limitations.",
        "",
        "## Coverage",
        "",
        f"Selected Registry set: **{len(edges)} directed relations**, "
        f"**{len({e.relation for e in edges})} populated relation types**. "
        "Every selected row is drawn exactly once and appears exactly once in the ledger. "
        "No selected edge is intentionally omitted. Unrecognized presentation targets go "
        "in bounded additional panels; empty panels state their sparse Registry status.",
        "",
        "Source: [validated Registry relationships](https://github.com/Planton361/"
        "autonomous-game-agent/blob/main/docs/research-atlas/registry/relationships.yaml). "
        "Selected vocabulary: " + ", ".join(f"`{r}`" for r in sorted(INTERACTION_RELATIONS)) + ".",
        "",
    ]

    def token(identity: str) -> str:
        return identity.replace("-", "_")

    def panel_index(edge: Relationship) -> int:
        # Keep guarded input's declared Environment control beside its vocabulary.
        if edge.source == "CMP-INPUT-EXECUTOR":
            return 4
        return next((i for i, (_, targets) in enumerate(groups) if edge.target in targets), -1)

    panels = [
        (title, [e for e in edges if panel_index(e) == i]) for i, (title, _) in enumerate(groups)
    ]
    remaining = [e for e in edges if panel_index(e) == -1]
    # Bound future additions as well as today's panels, without dropping relations.
    if remaining:
        panels.append(("Additional declared technical interactions", remaining))
    for title, selected in panels:
        body += [f"### {title}", "", f"{len(selected)} declared relations; source → target.", ""]
        if not selected:
            body += ["No selected Registry relations in this panel; no connection inferred.", ""]
        for start in range(0, len(selected), 8):
            chunk = selected[start : start + 8]
            body += ["```mermaid", "flowchart LR"]
            for identity in sorted({i for e in chunk for i in (e.source, e.target)}):
                node = atlas.entities[identity]
                label = node.name.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
                status = (
                    " · " + node.technical.implementation_status
                    if node.type in {"System", "Component"}
                    else ""
                )
                body.append(
                    f'    {token(identity)}["{label}<br/>{node.type}{status}<br/>{identity}"]'
                )
            for edge in chunk:
                body.append(f'    {token(edge.source)} -->|"{edge.relation}"| {token(edge.target)}')
            body += [
                "```",
                "",
                "Exact row identities and preferred links: "
                "[[#Complete linked relation ledger|ledger]].",
                "",
            ]
    body += [
        "## Complete linked relation ledger",
        "",
        "Exact (relation, source, target) tuples. Types and statuses are Registry values; "
        "both endpoints open their one existing preferred page.",
        "",
        "| Relation | Source identity / type / status | Target identity / type / status |",
        "| --- | --- | --- |",
    ]

    def endpoint(identity: str) -> str:
        node = atlas.entities[identity]
        status = node.technical.implementation_status
        return (
            f"[[{preferred[identity].with_suffix('')}\\|{node.name}]] "
            f"· `{identity}` · {node.type} · {status}"
        )

    for edge in edges:
        body.append(f"| `{edge.relation}` | {endpoint(edge.source)} | {endpoint(edge.target)} |")
    if not edges:
        body += ["", "No selected technical relations; no interaction inferred."]
    body += ["", "[[Research Map Home|Return Home]]"]
    return "\n".join(body)


def execution_flow(atlas: Atlas, preferred: dict[str, PurePosixPath]) -> str:
    """Explain canonical control gates, independently of Registry containment."""
    repository = "https://github.com/Planton361/autonomous-game-agent/blob/main/"
    architecture = repository + "docs/canonical/02_ARCHITECTURE_CANONICAL.md"
    overlay = repository + "docs/orchestration/releases/ALIGN-2026-09-19-v1.0/README.md"

    def source(label: str, anchor: str) -> str:
        return f"[{label}]({architecture}#{anchor})"

    body = [
        "# Ablaufdiagramm",
        "",
        f"[[{EXECUTION_CANVAS}|Open Execution Flow Canvas]]"
        " — primary visual; pan/zoom and follow identity links.",
        "",
        f"![[{EXECUTION_CANVAS}]]",
        "",
        "[[Research Map Home|Home]] · [[#Markdown fallback|Markdown fallback]] · "
        "[[#Current implementation and preferred pages|Implementation and preferred pages]]",
        "",
        "## Normative control lifecycle",
        "",
        "This is the normative/target architecture, not a trace of a demonstrated live loop. "
        "Arrows express authority prerequisites and conditional transitions, not a per-frame "
        "schedule or a strictly sequential order for asynchronous subsystem work. "
        "Process arrows never declare Registry relations or `part_of` ancestry. "
        "The Architecture Tree remains composition; Interaction Map "
        "separately shows technical declarations.",
        "",
        "Native Obsidian Mermaid needs no community plugin. If it is unavailable, the "
        "complete ordered/conditional Markdown fallback below retains all gates, branches, "
        "sources and preferred-page navigation. Native visual rendering remains unverified "
        "until inspected in Obsidian.",
        "",
        "```mermaid",
        "flowchart TD",
        '    capture["GameInstance / Screen Capture"]',
        '    bridge["Optional visible-only Bridge"]',
        '    firewall{"No-Spoiler Firewall"}',
        '    context["Observation / Perception<br/>Temporal State + evidence / retrieval"]',
        '    cortex["Event-driven Cortex<br/>typed evidence-linked intention"]',
        '    manager{"Manager validation<br/>policy / target / capability"}',
        '    contract["Valid bounded Skill Contract"]',
        '    body["Body / eligible Reflex<br/>one allowed primitive proposal"]',
        '    safety{"Separate SafetyFilter / input gate<br/>focus / action mask / budget<br/>'
        'rate limit / stop / logging"}',
        '    execute["InputExecutor: guarded execution"]',
        '    outcome["Visible outcome / observation"]',
        '    verifier["Independent Verifier<br/>typed result + evidence"]',
        '    evaluate{"Manager evaluates outcome"}',
        '    reject["Reject / stop<br/>log reason; no executed action"]',
        '    close["Manager closes / suspends<br/>prior contract, if active"]',
        '    episode["Death: close Life Episode<br/>evidence + post-mortem"]',
        '    terminal["Declared Mission Run termination"]',
        '    learn["Optional future protocol<br/>replay / train / validate / certify"]',
        '    next["Next independently eligible Mission Run<br/>eligible Body; fresh state<br/>'
        'independently frozen identity"]',
        "    capture --> firewall",
        '    bridge -.->|"optional allowlisted visible feed"| firewall',
        '    firewall -->|"admissible evidence"| context',
        '    firewall -->|"forbidden access: integrity stop"| reject',
        '    context -->|"meaningful event; no active prior contract"| cortex',
        "    cortex --> manager",
        '    manager -->|"valid and grounded"| contract',
        '    manager -->|"ambiguous / unsafe / unavailable"| reject',
        "    contract --> body",
        "    body --> safety",
        '    safety -->|"all checks pass"| execute',
        '    safety -->|"no focus / unsafe / unloggable"| reject',
        "    execute --> outcome",
        "    outcome --> verifier",
        "    verifier --> evaluate",
        '    evaluate -->|"continue valid active contract"| body',
        '    evaluate -->|"terminal contract result / stop"| close',
        '    reject -->|"Manager stop authority"| close',
        '    close -->|"nonterminal nondeath replan event; fresh evidence"| context',
        '    close -->|"visible death"| episode',
        '    close -->|"other declared Mission Run terminal condition"| terminal',
        '    episode -->|"permitted restart; same Mission Run / frozen Body"| context',
        '    episode -->|"declared Mission Run terminal condition"| terminal',
        '    terminal -->|"already eligible Body; no retraining"| next',
        '    terminal -.->|"between Mission Runs; separately authorized"| learn',
        '    learn -.->|"activate certified candidate only"| next',
        '    learn -.->|"candidate rejected; retain eligible prior Body"| next',
        "```",
        "",
        "Legend: rectangles describe bounded responsibilities; diamonds are validation or "
        "evaluation gates. Solid arrows are conditional control prerequisites. Dotted "
        "arrows are optional paths. A rejected proposal is never an executed action. "
        "All boundary records are typed, logged and evidence-linked. Learning is outside "
        "the running Mission Run. Post-terminal paths require independent run eligibility, "
        "not automatic start: the already eligible Body can be reused without retraining, "
        "and candidate rejection never activates that candidate or forbids an eligible "
        "prior version. Visual labels are short; the fallback supplies the "
        "complete conditions. Use the preferred-page table below for identity navigation.",
        "",
        "## Markdown fallback",
        "",
        "1. **Observation entry.** GameInstance → Screen Capture; optionally an allowlisted "
        "visible-only Bridge supplies information simultaneously visible to a player. "
        "Both pass the deny-by-default No-Spoiler Firewall before Observation/Perception → "
        "Temporal State → evidence and bounded retrieval. Hidden game state is never "
        "authority; forbidden access is an integrity incident and stops admissible "
        "continuation. These are conceptual prerequisites, not a subsystem clock. "
        + source("Architecture §§1–5", "1-normative-architecture")
        + ".",
        "",
        "2. **Event-driven intention.** On meaningful new evidence, completion/failure, "
        "contradiction, death, deadlock, resource/risk alarm or relevant uncertainty, "
        "Cortex receives bounded evidence/retrieval context and proposes a typed "
        "evidence-linked goal, universal capability, constraints and success criteria. "
        "It is not invoked per frame. Cortex cannot directly call InputExecutor or emit "
        "primitive keys, timings or low-level action sequences. For replanning, the prior "
        "Manager contract must first be closed/suspended; initial planning needs no prior "
        "active contract. "
        + source("Architecture §2", "2-multi-timescale-control")
        + "; "
        + source("§6", "6-cortex-contract")
        + "; "
        + source("§7", "7-manager--executive-contract")
        + ".",
        "",
        "3. **Manager validation and contracting.** Validate schema/no-spoiler policy, "
        "available executable capability and typed visible evidence-linked target. "
        "Ambiguous, insufficiently grounded, unsafe or unavailable proposals reject/stop; "
        "Body must not guess. Only Manager opens a valid bounded Skill Contract: target, "
        "universal skill, allowed actions, budget, risk, independent verifier, timeout, "
        "termination and evidence/logging requirements. No execution before that gate. "
        + source("Architecture §§7–8", "7-manager--executive-contract")
        + ".",
        "",
        "4. **One authorized proposal.** Body uses current visual/temporal state within "
        "the active contract and proposes one primitive at a time. Optional fast Reflex "
        "is inside Body/Manager authority: Manager declares immediate visible triggers, "
        "eligibility, cooldown, action mask and termination. Reflex cannot invent goals, "
        "extend budgets, change memory truth, suppress stop/replan or bypass safety/logging. "
        "Insufficient evidence means wait/stop/replan. "
        + source("Architecture §9", "9-body-design")
        + "; "
        + source("§10", "10-reflex")
        + ".",
        "",
        "5. **Separate enforcement gate.** SafetyFilter/InputExecutor requires an active "
        "valid Manager contract, verified target-window focus, contract-allowed action, "
        "action/risk budgets and rate-limit capacity, functional emergency stop and durable "
        "proposal/execution/rejection logging with before/after evidence linkage. Only "
        "when all checks pass may InputExecutor execute. No focus, unsafe action, exhausted "
        "budget, failed stop or unavailable logging rejects/stops; record the rejection "
        "without labelling it an executed action. Wrong-window input is a hard failure. "
        + source("Architecture §14", "14-safetyinput")
        + ".",
        "",
        "6. **Independent outcome and Manager evaluation.** Execution → visible outcome "
        "and new observation → independent Verifier → typed result and evidence → Manager. "
        "Cortex never grades itself; a screenshot/hash change alone is not success. "
        "Manager may continue only a still-valid active contract using refreshed visible "
        "state, returning to step 4 and checking step 5 again for each proposal. "
        "Success, failure, timeout, no-progress, target loss, safety event, contamination, "
        "death or contradiction closes/suspends the contract. A pre-execution rejection "
        "takes the Manager stop path directly; it does not fabricate a visible Verifier "
        "success or an action outcome. "
        + source("Architecture §7", "7-manager--executive-contract")
        + "; "
        + source("§11", "11-independent-verification-and-reward")
        + ".",
        "",
        "7. **Closure before replanning.** Manager closes/suspends the prior contract, "
        "if active, before invoking Cortex again. If the Mission Run is nonterminal and "
        "a meaningful event warrants replanning, return through fresh admissible "
        "observation/evidence/retrieval to step 2. No deterministic per-frame replan loop "
        "is implied. Evidence-backed memory/post-mortem updates retain provenance and "
        "separate observations from inferred causes; memory never grants execution authority. "
        + source("Architecture §§5,7", "7-manager--executive-contract")
        + "; "
        + f"[Overlay: mutable state]({overlay}#mission-run-identity-and-mutable-state).",
        "",
        "8. **Mission Run / Life Episode branch.** Visible death closes the Life Episode "
        "with evidence and post-mortem. An authorized/permitted restart may open another "
        "Life Episode in the same nonterminal Mission Run with the same frozen identities. "
        "There is no between-Life-Episode model/controller replacement or Body-weight "
        "update. Death, ordinary failure or timeout alone does not terminate a Mission Run. "
        "Declared terminal conditions are independently verified mission success, frozen "
        "budget exhaustion, explicit manual stop, unrecoverable safety/integrity stop or "
        "unrecoverable environment/harness failure. An application restart preserves "
        "identity/provenance or stops/quarantines when continuity cannot be established. "
        + f"[Overlay: nested units]({overlay}#nested-experimental-units); "
        + f"[identity freeze]({overlay}#mission-run-identity-and-mutable-state); "
        + f"[restart and terminals]({overlay}#restart-and-terminal-semantics).",
        "",
        "9. **Independent Mission Runs and optional future learning.** A new independently "
        "eligible Mission Run may begin without retraining using the already eligible Body "
        "version. It starts with protocol-defined fresh experimental state, a new mission "
        "identity/manifest and independently frozen identities, including Body version and "
        "weights. Neither path authorizes automatic run start or within-Mission-Run "
        "parameter/controller replacement. Only between Mission Runs, "
        "under a separately authorized future protocol: collect admissible experience "
        "with frozen Body vN → verifier-labelled replay/demonstrations → train candidate "
        "vN+1 → held-out validation and safety/false-success checks → certify or reject → "
        "activate only a certified version for the next eligible Mission Run. A rejected "
        "candidate must never activate; rejection does not prevent a new independently "
        "eligible Mission Run with the already eligible Body version. Neither "
        "ordinary episode restart nor memory consolidation activates a candidate. "
        "Independent Mission Runs begin with protocol-defined fresh experimental state; "
        "cross-Mission-Run inherited memory is not enabled by default. "
        + source("Architecture §12", "12-learning-lifecycle")
        + "; "
        + f"[Overlay: precedence]({overlay}"
        "#explicit-precedence-mapping-to-canonical-architecture-and-protocol).",
        "",
        "## Current implementation and preferred pages",
        "",
        "Registry statuses below describe individual identities, not coverage of every "
        "normative gate or proof that the full lifecycle has been demonstrated live. "
        "Open preferred pages for current implementation references, verification and "
        "limitations. Functions describe context and have no implementation status field. "
        "A missing Registry mapping implies no omitted capability or scientific weakness. "
        "This drawing establishes neither Phase-D nor Phase-H exit: "
        f"[Roadmap status rule]({repository}"
        "docs/canonical/03_RESEARCH_ROADMAP_CANONICAL.md#status-rule).",
        "",
        "Current code provides bounded hierarchical attempts and replanning in "
        f"[hierarchical_step.py]({repository}src/fh_agent/manager/hierarchical_step.py) and "
        f"[replan_loop.py]({repository}src/fh_agent/manager/replan_loop.py). "
        f"[SkillRunner]({repository}src/fh_agent/manager/skill_runner.py) connects "
        "contract action checks, evidence-linked action records, independent verification "
        "and Manager stops. "
        f"[InputExecutor]({repository}src/fh_agent/game/input_executor.py) checks "
        "focus, rate limit and stop state; emergency-stop checking is configurable and "
        "logging/contract checks also live in callers. Its existence alone does not "
        "certify the complete normative enforcement gate. These code surfaces and "
        "Registry labels are implementation context, not scientific results or Live evidence.",
        "",
        "| Lifecycle context | Preferred identity / type | Registry implementation status |",
        "| --- | --- | --- |",
    ]
    groups = (
        ("System", ("SYS-AGA",)),
        (
            "Observation entry",
            (
                "CMP-SCREEN-CAPTURE",
                "CMP-VISIBLE-STATE-BRIDGE",
                "CMP-NO-SPOILER-FIREWALL",
                "CMP-PERCEPTION",
                "CMP-TEMPORAL-STATE",
                "CMP-EVIDENCE-LEDGER",
                "CMP-MEM-RETRIEVAL",
                "DAT-OBSERVATION",
            ),
        ),
        ("Intention", ("CMP-CORTEX", "CON-CORTEX-CONTEXT", "CON-PLANNER-OUTPUT")),
        ("Authority", ("CMP-MANAGER", "FUNC-EXECUTIVE-CONTROL", "CON-SKILL-CONTRACT")),
        (
            "Execution",
            (
                "CMP-BODY",
                "CMP-BOUNDED-REFLEX",
                "CMP-SAFETY-FILTER",
                "CMP-INPUT-EXECUTOR",
                "DAT-ACTION-RESULT",
            ),
        ),
        (
            "Verification",
            ("CMP-INDEPENDENT-VERIFIER", "CON-VERIFIER-RESULT", "DAT-VISIBLE-OUTCOME"),
        ),
        ("Evidence and post-mortem", ("CMP-MEMORY", "CON-POST-MORTEM-OUTPUT")),
        (
            "Between Mission Runs",
            (
                "CMP-REPLAY-BUFFER",
                "CMP-SKILL-TRAINER",
                "DAT-CANDIDATE-BODY-VERSION",
                "CMP-BODY-CERTIFICATION",
            ),
        ),
    )
    for context, identities in groups:
        for identity in identities:
            if identity not in preferred:
                continue
            node = atlas.entities[identity]
            technical = getattr(node, "technical", None)
            status = technical.implementation_status if technical else "not applicable (context)"
            body.append(
                f"| {context} | [[{preferred[identity].with_suffix('')}\\|{node.name}]] "
                f"· {node.type} · `{identity}` | {status} |"
            )
    body += ["", "[[Research Map Home|Return Home]]"]
    return "\n".join(body)


def architecture_tree(atlas: Atlas, preferred: dict[str, PurePosixPath]) -> tuple[str, bytes]:
    """Render the same exact containment forest as Markdown and native Canvas.

    Multiple ancestry paths repeat an identity, never choose a preferred parent.
    Each occurrence opens the one preferred identity page. Unrooted Components
    remain visible without an invented System edge.
    """
    trails = {
        trail
        for identity, node in atlas.entities.items()
        if node.type in {"System", "Component"}
        for trail in containment_paths(atlas, identity)
    }

    def order(trail: tuple[str, ...]) -> tuple:
        return tuple((atlas.entities[i].name.casefold(), i) for i in trail)

    children: dict[tuple[str, ...], list[tuple[str, ...]]] = {}
    for trail in sorted(trails, key=order):
        children.setdefault(trail[:-1], []).append(trail)

    def link(identity: str) -> str:
        title = re.sub(r"[\r\n`*_[\]#<>|]", " ", atlas.entities[identity].name)
        title = " ".join(title.split())
        return f"[[{preferred[identity].with_suffix('')}|{title}]]"

    def token(trail: tuple[str, ...]) -> str:
        return hashlib.sha256("\0".join(trail).encode()).hexdigest()[:16]

    body = [
        "# Architecture Tree",
        "",
        "[[Research Map Home|Home]] · [[#Linked Markdown tree|Linked Markdown tree]]",
        "",
        "Technical composition of the System and its Components. Only Registry `part_of` "
        "creates ancestry; siblings are ordered by title, not runtime order or priority.",
        "",
        "The tree includes implemented, partial and target-only identities. "
        "It does not certify capability or scientific results. Open an identity for its "
        "responsibility, verification and limitations.",
        "",
        "## Visual tree",
        "",
        f"[[{ARCHITECTURE_CANVAS}|Open Architecture Tree Canvas]] — pan/zoom to inspect; "
        "follow each card's identity link.",
        "",
        "The embed previews shapes only. Open the Canvas directly for card labels and "
        "identity navigation, or use the linked Markdown tree below.",
        "",
        f"![[{ARCHITECTURE_CANVAS}]]",
        "",
        "Read top to bottom: parent → contained Component. Local branch regions repeat "
        "the same System identity for clarity. Lines mean containment only; "
        "the Registry declaration is child `part_of` parent. No control or data-flow "
        "arrows are shown. Native Canvas is optional for reading this page; the complete "
        "linked Markdown tree below needs no visual plugin.",
        "",
        "## Linked Markdown tree",
        "",
        "Indentation means exact technical containment. Every repeated identity has the "
        "same preferred page; multiple paths do not select an architectural parent.",
        "",
    ]
    nodes = [
        dict(
            id="legend",
            type="text",
            x=0,
            y=-520,
            width=1360,
            height=440,
            text="**Architecture Tree · technical containment**\n\n"
            "Read parent → child, top to bottom. Local branches repeat the SAME System "
            "identity to keep connections local; open one preferred page. "
            "Only Registry part_of creates lines. "
            "No runtime sequence, control or data flow is implied.\n\n"
            f"[[{ARCHITECTURE_TREE.with_suffix('')}|Linked Markdown tree and context]] · "
            "[[Research Map Home|Home]]\n\n" + CANVAS_NAVIGATION,
        )
    ]
    edges = []

    def width(trail: tuple[str, ...]) -> int:
        return max(500, sum(width(child) for child in children.get(trail, [])))

    def height(trail: tuple[str, ...]) -> int:
        own = card_height(identity_text(atlas, preferred, trail[-1]), 420)
        return own + 140 + max((height(child) for child in children.get(trail, [])), default=0)

    def card(trail: tuple[str, ...], x: float, y: float, span: int, card_id: str) -> int:
        node = atlas.entities[trail[-1]]
        text = identity_text(atlas, preferred, trail[-1])
        size = card_height(text, 420)
        nodes.append(
            dict(
                id=card_id,
                type="text",
                x=x + (span - 420) / 2,
                y=y,
                width=420,
                height=size,
                color="5" if node.type == "System" else "4",
                text=text,
            )
        )
        return size

    def visit(trail: tuple[str, ...], x: float, y: float, parent: str | None = None) -> None:
        node = atlas.entities[trail[-1]]
        depth = len(trail) - 1
        body.append(
            "  " * depth + f"- {link(trail[-1])} — {node.type} · `{trail[-1]}` · "
            f"{node.technical.implementation_status}"
        )
        size = card(trail, x, y, width(trail), token(trail))
        if parent:
            edges.append(
                dict(
                    id="edge-" + token(trail),
                    fromNode=parent,
                    toNode=token(trail),
                    fromSide="bottom",
                    toSide="top",
                    fromEnd="none",
                    toEnd="none",
                    label="contains",
                )
            )
        child_x = x
        for child in children.get(trail, []):
            visit(child, child_x, y + size + 140, token(trail))
            child_x += width(child)

    # Repeat the SAME System identity above each local branch, avoiding long
    # connections across unrelated cards. These are occurrences, not new parents.
    x = top = row_height = 0
    for kind, heading in (
        ("System", "System composition"),
        ("Component", "No System containment chain"),
    ):
        roots = [trail for trail in children.get((), []) if atlas.entities[trail[0]].type == kind]
        if not roots:
            continue
        body += [f"### {heading}", ""]
        if kind == "Component":
            body += ["These roots have no declared System ancestor; no attachment is inferred.", ""]
            top += row_height + 200
            x = row_height = 0
        for root in roots:
            branches = children.get(root, []) if kind == "System" else []
            if branches:
                node = atlas.entities[root[-1]]
                body.append(
                    f"- {link(root[-1])} — {node.type} · `{root[-1]}` · "
                    f"{node.technical.implementation_status}"
                )
            for branch in branches or [root]:
                span = width(branch)
                root_height = (
                    card_height(identity_text(atlas, preferred, root[-1]), 420) + 140
                    if branches
                    else 0
                )
                region_height = height(branch) + root_height + 80
                if x and x + span > 3100:
                    top += row_height + 180
                    x = row_height = 0
                nodes.append(
                    dict(
                        id="group-" + token(branch),
                        type="group",
                        x=x - 20,
                        y=top - 50,
                        width=span + 40,
                        height=region_height,
                        label=atlas.entities[branch[-1]].name,
                        color="5",
                    )
                )
                parent = None
                if branches:
                    parent = token(root) + "-" + token(branch)
                    card(root, x, top, span, parent)
                visit(branch, x, top + root_height, parent)
                x += span + 100
                row_height = max(row_height, region_height)
            body.append("")
    body += [
        "## Context outside ancestry",
        "",
        "Functions, Interfaces, Contracts, Data Artifacts, Measurements and Environments "
        "are typed context, not Component parents. Function participation, Domain grouping, "
        "control, evidence and Research relations add no depth here. Inspect those relations "
        "on the preferred identity pages or the existing "
        "[[Research Map/Views/Graphs|Component Graph guides]].",
        "",
        "[[Research Map Home#Functions|Functions]] · "
        "[[Research Map Home#Interfaces|Interfaces]] · "
        "[[Research Map Home#Contracts|Contracts]] · "
        "[[Research Map Home#Data Artifacts|Data Artifacts]] · "
        "[[Research Map Home#Measurements|Measurements]] · "
        "[[Research Map Home#Environments|Environments]]",
        "",
        "[[Research Map Home|Return Home]]",
    ]
    canvas = dict(
        generated_by=views.OWNER,
        canvas_view_schema_version="1.0",
        nodes=nodes,
        edges=edges,
    )
    return "\n".join(body), (
        json.dumps(canvas, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


@dataclass(frozen=True)
class ProductTree:
    files: dict[PurePosixPath, bytes]
    owners: dict[PurePosixPath, str]
    routes: dict[PurePosixPath, PurePosixPath]


def retired_graph_audit_owners(tree: ProductTree) -> dict[PurePosixPath, str]:
    """Finite previous-product paths with a currently emitted audit replacement."""
    return {
        path: views.OWNER
        for path, replacement in tree.routes.items()
        if path.name == "Edge Audit.md"
        and path.parent.parent == INTERNAL / "Graphs"
        and replacement == PRODUCT / "Graphs" / (path.parent.name + ".md")
        and tree.owners.get(replacement) == views.OWNER
        and path not in tree.files
    }


def component_research_links(
    atlas: Atlas,
    reference: ReferenceIndex,
    records: tuple[EpistemicRecord, ...],
    locators: dict[str, PurePosixPath],
) -> dict[PurePosixPath, str]:
    """Final-product navigation to actual direct records, never a Finding preview.

    Older reader/Graph projections remain unchanged. This uses the accepted
    attachment resolver and literal record status, not ancestry or inferred relevance.
    """
    by_id = {r.wiki_id: r for r in records}
    attachments = views.attachment_index(reference)
    preferred = preferred_paths(atlas)
    sections = {}
    for identity, page in preferred.items():
        if atlas.entities[identity].type != "Component":
            continue
        model = views.identity_page_model(atlas, reference, identity, attachments=attachments)
        owners: dict[str, set[str]] = {}
        for row in model.direct_attachments:
            owners.setdefault(row.source_wiki_id, set()).add(row.originating_role)
        if not owners:
            continue
        lines = ["### Declared Research records", ""]
        for owner, roles in sorted(owners.items()):
            record = by_id.get(owner)
            if record is None:
                raise ProjectionError("Declared Component research record is unavailable")
            status = record.doc_type + " · " + record.document_maturity
            if isinstance(record, Finding):
                status += " · review " + record.review_state
            if isinstance(record, ReadingNote):
                status += " · " + record.reading_depth.replace("_", " ")
                if record.version_read is not None:
                    status += " · version read " + literal(record.version_read)
            lines += [
                "- "
                + record_link(record, locators, page)
                + " — "
                + status
                + "; "
                + ", ".join(ROLE_LABELS[r] for r in sorted(roles))
                + ".",
            ]
        sections[page] = "\n".join(lines) + "\n\n"
    return sections


def consolidate_graph_audits(
    tree: ProductTree, *, research_links: dict[PurePosixPath, str] | None = None
) -> ProductTree:
    """Fold only the finite generated Component audits into their Graph guides.

    The AP2 package remains a reproducible intermediate product. Graph proxies,
    filters and scientific originals are untouched by this final presentation pass.
    Ownership validation and retirement belong to the existing workspace pipeline.
    """
    files, owners, routes = dict(tree.files), dict(tree.owners), dict(tree.routes)
    for page, section in (research_links or {}).items():
        if owners.get(page) != views.OWNER:
            raise ProjectionError("Component research navigation has no owned identity page")
        text = utf8(files[page])
        marker = "\n## Sources & verification\n"
        if text.count(marker) != 1:
            raise ProjectionError("Component reader source section is missing or ambiguous")
        files[page] = text.replace(marker, "\n" + section + marker, 1).encode()
    audits = {
        path: PRODUCT / "Graphs" / (path.parent.name + ".md")
        for path in files
        if path.name == "Edge Audit.md" and path.parent.parent == INTERNAL / "Graphs"
    }

    def target(path: PurePosixPath, anchor: str) -> tuple[PurePosixPath, str]:
        return audits[path], (
            anchor + " audit" if anchor in MODES.values() else anchor or "Edge audits"
        )

    def rewrite(
        data: bytes, source: PurePosixPath, destination: PurePosixPath | None = None
    ) -> bytes:
        destination = destination or source
        text = utf8(data)

        def wiki(match: re.Match) -> str:
            route, delimiter, label = match[1].partition("|")
            escaped = route.endswith("\\")
            path, _, anchor = route.rstrip("\\").partition("#")
            old = PurePosixPath(path) if path else source
            if old.suffix != ".md":
                old = PurePosixPath(str(old) + ".md")
            if old not in audits:
                return match[0]
            new, anchor = target(old, anchor)
            if not path.endswith(".md"):
                new = new.with_suffix("")
            delimiter = "\\|" if escaped else delimiter
            return "[[" + str(new) + "#" + anchor + (delimiter + label if delimiter else "") + "]]"

        def markdown(match: re.Match) -> str:
            url = urlsplit(match[2])
            if url.scheme or url.netloc:
                return match[0]
            old = (
                PurePosixPath(posixpath.normpath(str(source.parent / unquote(url.path))))
                if url.path
                else source
            )
            if old not in audits and source == destination:
                return match[0]
            new, anchor = (
                target(old, unquote(url.fragment))
                if old in audits
                else (old, unquote(url.fragment))
            )
            relative = posixpath.relpath(str(new), str(destination.parent))
            suffix = ("?" + url.query if url.query else "") + (
                "#" + quote(anchor) if anchor else ""
            )
            return match[1] + quote(relative, safe="/.") + suffix + ")"

        text = re.sub(r"\[\[([^\]]+)\]\]", wiki, text)
        text = re.sub(r"(\[[^\]\n]*\]\()([^\)\n]+)\)", markdown, text)
        return text.encode()

    for audit, guide in sorted(audits.items()):
        if guide not in files or owners[audit] != views.OWNER or owners[guide] != views.OWNER:
            raise ProjectionError("Graph audit has no same-owner guide replacement")
        body = markdown_parts(utf8(rewrite(files[audit], audit, guide)))[1]
        intro, separator, rest = body.partition("\n## Architecture\n")
        if not separator:
            raise ProjectionError("Graph audit mode sections are missing")
        _, _, intro = intro.partition("\n")  # Title only; identity and mode contract remain.
        sections = ["\n## Edge audits\n", intro]
        remainder = "\n## Architecture\n" + rest
        for title in MODES.values():
            _, separator, remainder = remainder.partition("\n## " + title + "\n")
            if not separator:
                raise ProjectionError("Graph audit mode sections are missing")
            content = remainder.split("\n## ", 1)[0]
            sections += [
                "\n## " + title + " audit\n",
                "> [!info]- Complete "
                + title
                + " edge audit\n>\n"
                + "\n".join("> " + line for line in content.splitlines()),
            ]
        files[guide] += ("\n".join(sections) + "\n").encode()
        del files[audit], owners[audit]
    for path, data in list(files.items()):
        if path.suffix in {".md", ".canvas", ".base"}:
            files[path] = rewrite(data, path)
    routes = {
        source: audits.get(destination, destination) for source, destination in routes.items()
    }
    routes.update(audits)  # Exact accepted-AP2 retired routes, never a wildcard alias.
    files[LEDGER] = yaml_text(
        dict(
            migration_schema_version="1.0",
            generated_by=views.OWNER,
            routes={str(s): str(t) for s, t in sorted(routes.items())},
        )
    ).encode()
    for owner, manifest in MANIFESTS.items():
        metadata = read_yaml(utf8(files[manifest]))
        metadata["owned_files"] = [
            dict(path=str(path), **semantics.record(data, path, owner))
            for path, data in sorted(files.items())
            if owners[path] == owner and path != manifest
        ]
        files[manifest] = yaml_text(metadata).encode()
    public.validate_portable_paths(files)
    return ProductTree(files, owners, routes)


def package(
    atlas: Atlas,
    technical: dict,
    derived: dict,
    *,
    explanations: ExplanationCatalog | None = None,
) -> ProductTree:
    """Inventory every old path before rendering; preserve all mode audit sections."""
    preferred = preferred_paths(atlas)
    old_pages = views.identity_page_paths(atlas)
    old = {public.OWNED_ROOT / p: data for p, data in technical.items()}
    old.update({views.OWNED_ROOT / p: data for p, data in derived.items()})
    routes: dict[PurePosixPath, PurePosixPath] = {}
    retained: dict[PurePosixPath, PurePosixPath] = {}

    def route(source: PurePosixPath, target: PurePosixPath, *, keep: bool = True) -> None:
        routes[source] = target
        if keep:
            if target in retained.values():
                raise ProjectionError("Duplicate preferred destination")
            retained[source] = target

    public_fixed = {
        public.INDEX: INTERNAL / "Indexes/atlas-id-index.yaml",
        public.ANATOMY: PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md",
        public.DOMAIN_SLICE: PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md",
        public.HERO_ASSET: INTERNAL / "Assets/Agent Anatomy Hero.svg",
        public.MANIFEST: MANIFESTS[public.OWNER],
    }
    for path in technical:
        source = public.OWNED_ROOT / path
        if path in {public.HOME, public.MAP}:
            route(source, HOME if path == public.HOME else public_fixed[public.ANATOMY], keep=False)
        elif path in public_fixed:
            route(source, public_fixed[path])
        else:
            node = atlas.entities[path.stem]
            route(
                source,
                INTERNAL
                / "Registry"
                / ("Evidence" if node.type == "Evidence" else "Records")
                / path.name,
            )
    fixed = {
        views.MANIFEST: MANIFESTS[views.OWNER],
        views.K3_HOME: HOME,
        views.REFERENCE_INDEX: INTERNAL / "Indexes/declared-reference-index.yaml",
        views.SOURCE_INDEX: INTERNAL / "Indexes/source-resolution-index.yaml",
        views.NAVIGATION: INTERNAL / "Audit/Declared References.md",
        views.SOURCE_DETAIL: INTERNAL / "Audit/Source Details.md",
        views.RESEARCH_LANDSCAPE: PRODUCT / "Views/Research Steering.md",
        views.LITERATURE_INSPECTION: PRODUCT / "Views/Literature Inspection.md",
    }
    page_ids = {path: identity for identity, path in old_pages.items()}
    hub_aux = {
        path: identity
        for identity, hub in views.COMPONENT_HUB_PATHS.items()
        for path in (hub.technical, hub.research)
    }
    for path in derived:
        source = views.OWNED_ROOT / path
        if path in fixed:
            route(source, fixed[path])
        elif path in page_ids:
            route(source, preferred[page_ids[path]])
        elif path in hub_aux:
            route(source, preferred[hub_aux[path]], keep=False)
        elif path.parent == views.HIERARCHY_DIR:
            route(
                source,
                preferred.get(
                    path.stem,
                    routes[public.OWNED_ROOT / public.private_path(atlas.entities[path.stem])],
                ),
                keep=False,
            )
        elif path in {views.INDEX, views.HIERARCHY}:
            route(source, HOME, keep=False)
        elif path == views.OBSERVE_SCOPE:
            route(source, preferred["FUNC-OBSERVE"], keep=False)
        elif path.parent == views.TECHNICAL_DETAIL_ROOT:
            route(
                source,
                PRODUCT / "Diagrams/Technical Relations" / path.name
                if path.suffix == ".canvas"
                else preferred[path.stem],
                keep=path.suffix == ".canvas",
            )
        elif path.parent == views.RQ_ROOT:
            route(source, PRODUCT / "Research/Question Readers" / path.name)
        elif path.suffix == ".base":
            route(source, PRODUCT / "Tables" / path.name)
        elif path.is_relative_to(graph.SCOPES):
            component, mode, *rest = path.relative_to(graph.SCOPES).parts
            if rest == ["Graph Profile.md"]:
                route(source, PRODUCT / "Graphs" / (component + ".md"), keep=False)
            elif rest == ["Edge Audit.md"]:
                route(source, INTERNAL / "Graphs" / component / "Edge Audit.md", keep=False)
            else:
                folder = "Question Overlay" if rest[0] == "optional-rq-overlay" else "Nodes"
                route(source, INTERNAL / "Graphs" / component / MODES[mode] / folder / rest[1])
        elif path.is_relative_to(graph.ROOT):
            target = (
                INTERNAL / "Graphs" / graph.MEMORY / "Edge Audit.md"
                if path.name == "Edge Audit.md"
                else PRODUCT / "Graphs" / (graph.MEMORY + ".md")
            )
            route(source, target, keep=False)
        else:
            raise ProjectionError(f"Unclassified generated path: {path}")

    # Finite supported pre-human-filename Hub aliases, never wildcard ownership.
    for source, identity in (
        (views.LEGACY_MEMORY_WORKBENCH, "CMP-MEM-RETRIEVAL"),
        (views.LEGACY_VERIFIER_WORKBENCH, "CMP-INDEPENDENT-VERIFIER"),
    ):
        routes[views.OWNED_ROOT / source] = preferred[identity]

    # Extensionless WikiLinks, explicit suffix routes, and folder Graph/Base filters.
    replacements = {str(s): str(t) for s, t in routes.items()}
    replacements.update(
        {
            str(s.with_suffix("")): str(t.with_suffix(""))
            for s, t in routes.items()
            if s.suffix == ".md"
        }
    )
    replacements[str(public.OWNED_ROOT / "records")] = str(INTERNAL / "Registry/Records")
    replacements[str(public.OWNED_ROOT / "evidence")] = str(INTERNAL / "Registry/Evidence")
    for identity in preferred:
        if atlas.entities[identity].type != "Component":
            continue
        for mode, title in MODES.items():
            old_root = views.OWNED_ROOT / graph.scope_root(identity, mode)
            new_root = INTERNAL / "Graphs" / identity / title
            replacements[str(old_root / "nodes")] = str(new_root / "Nodes")
            replacements[str(old_root / "optional-rq-overlay")] = str(new_root / "Question Overlay")
    pattern = re.compile(
        "|".join(re.escape(s) for s in sorted(replacements, key=lambda s: (-len(s), s)))
    )

    hub_aux_paths = {views.OWNED_ROOT / path for path in hub_aux}
    hub_overviews = {
        views.OWNED_ROOT / paths.overview for paths in views.COMPONENT_HUB_PATHS.values()
    }
    raw_identities = {
        routes[public.OWNED_ROOT / public.private_path(node)].with_suffix(""): identity
        for identity, node in atlas.entities.items()
    }

    # Reuse pure link normalization only within this exact product build.
    @cache
    def navigation(link: str) -> str:
        value, separator, label = link[2:-2].partition("|")
        escaped_separator = value.endswith("\\")
        if escaped_separator:
            value = value[:-1]
        path, fragment, anchor = value.partition("#")
        old_path = PurePosixPath(path)
        if old_path not in routes:
            old_path = PurePosixPath(path + ".md")
        target = routes.get(old_path)
        if target is None:
            return link
        if old_path.is_relative_to(views.OWNED_ROOT / graph.SCOPES):
            _, mode, *rest = old_path.relative_to(views.OWNED_ROOT / graph.SCOPES).parts
            if rest in (["Graph Profile.md"], ["Edge Audit.md"]):
                anchor = MODES[mode]
                fragment = "#"
                if label in graph.MODES:
                    label = MODES[label]
                if rest == ["Edge Audit.md"] and label == "Edge Audit / detail":
                    label = anchor + " Edge Audit"
        elif old_path.is_relative_to(views.OWNED_ROOT / graph.ROOT):
            fragment, anchor = "#", MODES["architecture"]
            label = (
                "Architecture Edge Audit"
                if old_path.name == "Edge Audit.md"
                else "Architecture Graph guide"
            )
        if target == HOME:
            label = "Home"
            fragment = anchor = ""
        elif old_path == views.OWNED_ROOT / views.RESEARCH_LANDSCAPE:
            label = "Research Steering"
        elif old_path in hub_overviews and label in {
            "Hub Overview",
            "Open Overview",
            "Back to Hub Overview",
        }:
            name = atlas.entities[page_ids[old_path.relative_to(views.OWNED_ROOT)]].name
            label = ("Back to " if label.startswith("Back to ") else "") + name
        elif old_path in hub_aux_paths:
            label = "Consolidated detail audit"
            fragment, anchor = "#", "Consolidated detail audit"
        elif old_path.parent == views.OWNED_ROOT / views.TECHNICAL_DETAIL_ROOT:
            if old_path.suffix == ".md":
                label = "Open " + atlas.entities[old_path.stem].name
        route_text = str(
            target.with_suffix("")
            if old_path.suffix == ".md" and not path.endswith(".md")
            else target
        )
        delimiter = "\\|" if escaped_separator else "|"
        return (
            "[[" + route_text + fragment + anchor + (delimiter + label if separator else "") + "]]"
        )

    def rewrite(data: bytes, source: PurePosixPath, destination: PurePosixPath) -> bytes:
        text = utf8(data)
        if (
            source.is_relative_to(views.OWNED_ROOT)
            and source.relative_to(views.OWNED_ROOT) in page_ids
        ):
            # Retire primary pilot shortcuts before normalizing their old aliases.
            text = re.sub(r"(?m)^.*Historical Memory pilot (?:profile|audit).*$", "", text)

        # Navigation aliases/sections are rewritten separately from machine paths.
        text = re.sub(r"\[\[([^\]]+)\]\]", lambda match: navigation(match[0]), text)

        # Relative authored routes are rebased, never rewritten at their masters.
        def markdown(match: re.Match) -> str:
            value = match[1]
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or value.startswith(("/", "#")):
                return match[0]
            absolute = PurePosixPath(posixpath.normpath(str(source.parent / unquote(parsed.path))))
            target = routes.get(absolute, absolute)
            relative = posixpath.relpath(str(target), str(destination.parent))
            suffix = ("?" + parsed.query if parsed.query else "") + (
                "#" + parsed.fragment if parsed.fragment else ""
            )
            return "](" + quote(relative, safe="/.-_") + suffix + ")"

        text = re.sub(r"\]\(([^)\s]+)\)", markdown, text)
        text = pattern.sub(lambda m: replacements[m[0]], text)
        text = text.replace(
            "- [[Research Map Home|Home]]\n- [[Research Map Home|Home]]",
            "- [[Research Map Home|Home]]",
        )
        if destination.suffix == ".base":
            text = text.replace(
                'file.inFolder("_generated/technical-atlas")',
                'file.inFolder("_Research Map Internals/Registry")',
            )
            text = text.replace(
                "'!file.inFolder(\"_generated\")'",
                "'!file.inFolder(\"_generated\")'\n"
                "    - '!file.inFolder(\"Research Map\")'\n"
                "    - '!file.inFolder(\"_Research Map Internals\")'",
            )
        # Machine metadata must describe the final destination, too.
        for key in ("identity_page_path", "rq_page_path", "graph_path"):
            text = re.sub(r"(?m)^" + key + r": .*?$", key + ": " + str(destination), text)
        if destination.suffix == ".canvas":
            canvas = json.loads(text)

            def card_link(match: re.Match) -> str:
                identity = raw_identities.get(PurePosixPath(match[1]))
                if identity is None:
                    return match[0]
                node = atlas.entities[identity]
                if identity not in preferred:
                    return f"[[{match[1]}|Evidence audit / provenance]]"
                return (
                    f"[[{preferred[identity].with_suffix('')}|{node.name}]]\n\n"
                    "> [!info]- Registry audit\n"
                    f"> [[{match[1]}|Raw Registry record]]"
                )

            for card in canvas["nodes"]:
                if card["type"] == "text":
                    card["text"] = re.sub(r"\[\[([^|]+)\|[^\]]+\]\]", card_link, card["text"])
            text = json.dumps(canvas, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        return text.encode()

    files = {}
    owners = {}
    for source, destination in retained.items():
        if destination in MANIFESTS.values():
            continue
        files[destination] = rewrite(old[source], source, destination)
        owners[destination] = (
            public.OWNER if source.is_relative_to(public.OWNED_ROOT) else views.OWNER
        )

    steering = PRODUCT / "Views/Research Steering.md"
    files[steering] = re.sub(
        r"(?ms)^## Graph navigation\n.*?(?=^## )",
        "## Graph navigation\n\n"
        "[[Research Map/Views/Graphs|Graphs — choose a Component and mode]]\n\n",
        utf8(files[steering]),
    ).encode()

    def add(path: PurePosixPath, body: str, owner: str = views.OWNER) -> None:
        if path in files:
            raise ProjectionError("Duplicate final product path")
        files[path] = (
            "---\n"
            + yaml_text(dict(generated_by=owner, privacy="private", export_policy="deny"))
            + "---\n"
            + body
            + "\n"
        ).encode()
        owners[path] = owner

    for identity, page in preferred.items():
        node = atlas.entities[identity]
        if identity not in old_pages:
            raw = public.OWNED_ROOT / public.private_path(node)
            add(
                page,
                f"# {node.name}\n\nType: {node.type}\n\n"
                f"[[{HOME.with_suffix('')}|Home]]\n\n"
                "[Technical](#technical) · [Research](#research) · [Sources](#sources)\n\n"
                f"## Technical\n\n{node.description}\n\n## Research\n\n"
                "Public Registry/program context only; "
                "no private scientific authority inferred.\n\n"
                "## Sources\n\n> [!info]- Complete Registry audit\n"
                + "\n".join("> " + line for line in utf8(files[routes[raw]]).splitlines())
                + f"\n\n[[{HOME.with_suffix('')}|Return Home]]",
            )
        else:
            # Preserve unique retired detail/hub content within the preferred audit.
            companions = [
                views.OWNED_ROOT / p for p, subject in hub_aux.items() if subject == identity
            ]
            detail = views.TECHNICAL_DETAIL_ROOT / (identity + ".md")
            if detail in derived:
                companions.append(views.OWNED_ROOT / detail)
            extras = []
            for companion in companions:
                body = markdown_parts(utf8(rewrite(old[companion], companion, page)))[1]
                body = body.replace("*Component Hub ·", "*Component detail ·")
                body = body.replace("Originating Component Hub(s)", "Originating Components")
                extras += [
                    "> [!info]- Complete consolidated detail audit",
                    ">",
                    *("> " + line for line in body.splitlines()),
                    "",
                ]
            text = utf8(files[page])
            text = text.replace(
                "\n\n---\n",
                f"\n\n[[{HOME.with_suffix('')}|Home]] · [[#Technical|Technical]] · "
                "[[#Research|Research]] · [[#Sources & verification|Sources]]\n\n---\n",
                1,
            )
            files[page] = (
                text
                + ("\n## Consolidated detail audit\n\n" + "\n".join(extras) if extras else "")
                + f"\n[[{HOME.with_suffix('')}|Return Home]]\n"
            ).encode()

        if node.type == "Component" and explanations is not None:
            text = utf8(files[page])
            before, technical_marker, rest = text.partition("## Technical\n")
            old_technical, research_marker, research = rest.partition("## Research\n")
            old_technical = old_technical.replace(
                "No separate mechanism explanation is authored in this snapshot. "
                "Inspect Sources & verification for detail.",
                "The current source-backed mechanism is in Technical above.",
            ).replace(
                "No separate limitation statement is authored here; this does not "
                "establish completeness.",
                "The current source-backed limitations are in Technical above.",
            )
            if not technical_marker or not research_marker:
                raise ProjectionError("Component reader sections are missing")
            item = explanations.components[identity]
            source_marker = "## Sources & verification\n"
            source_panel = explanations.provenance(item.sources)
            preserved = (
                "\n> [!info]- Previous technical presentation / complete detail\n>\n"
                + "\n".join("> " + line for line in old_technical.splitlines())
            )
            research = research.replace(
                source_marker, source_marker + "\n" + source_panel + preserved + "\n\n", 1
            )
            files[page] = (
                before
                + component_technical(
                    explanations, identity, atlas, preferred, INTERACTION_RELATIONS
                )
                + "\n## Research\n\n"
                + item.research_relevance
                + "\n\n"
                + "[[Research Map/Views/Research Steering|Research Steering]] · "
                "[[Research Map/Views/Literature Inspection|Literature Inspection]]\n\n" + research
            ).encode()

        if explanations is not None and identity in explanations.reference_slice:
            files[page] = reference_page(
                utf8(files[page]), identity, explanations, atlas, preferred
            ).encode()

        if explanations is not None and identity in explanations.page_bindings:
            files[page] = typed_page(
                utf8(files[page]), identity, explanations, atlas, preferred
            ).encode()
            files[page] = (
                utf8(files[page])
                .replace(
                    f"[[{HOME.with_suffix('')}|Home]]",
                    f"[[{HOME.with_suffix('')}|Home]] · "
                    f"[[{ANATOMY.with_suffix('')}|Agent Anatomy]]",
                    1,
                )
                .encode()
            )

        if node.type in {"System", "Component"}:
            text = utf8(files[page])
            files[page] = text.replace(
                f"[[{HOME.with_suffix('')}|Home]]",
                f"[[{HOME.with_suffix('')}|Home]] · "
                f"[[{ARCHITECTURE_TREE.with_suffix('')}|Architecture Tree]]",
                1,
            ).encode()

        if identity in EXECUTION_FLOW_ORIENTATION_IDS:
            text = utf8(files[page])
            files[page] = text.replace(
                f"[[{HOME.with_suffix('')}|Home]]",
                f"[[{HOME.with_suffix('')}|Home]] · "
                f"[[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]]",
                1,
            ).encode()

        if identity in INTERACTION_ORIENTATION_IDS:
            text = utf8(files[page])
            files[page] = text.replace(
                f"[[{HOME.with_suffix('')}|Home]]",
                f"[[{HOME.with_suffix('')}|Home]] · "
                f"[[{INTERACTION_MAP.with_suffix('')}|Interaction Map]]",
                1,
            ).encode()

    files[EXECUTION_CANVAS] = execution_canvas(atlas, preferred)
    files[INTERACTION_CANVAS] = interaction_canvas(
        atlas, preferred, INTERACTION_RELATIONS, INTERACTION_GROUPS
    )
    owners[EXECUTION_CANVAS] = owners[INTERACTION_CANVAS] = views.OWNER
    add(INTERACTION_MAP, interaction_map(atlas, preferred))
    add(EXECUTION_FLOW, execution_flow(atlas, preferred))
    tree_body, tree_canvas = architecture_tree(atlas, preferred)
    add(ARCHITECTURE_TREE, tree_body)
    files[ARCHITECTURE_CANVAS] = tree_canvas
    owners[ARCHITECTURE_CANVAS] = views.OWNER

    for identity, node in sorted(atlas.entities.items()):
        if node.type != "Component":
            continue
        guide = PRODUCT / "Graphs" / (identity + ".md")
        audit = INTERNAL / "Graphs" / identity / "Edge Audit.md"
        guide_sections = [
            f"# Graphs — {node.name}",
            f"[[{HOME.with_suffix('')}|Home]] · "
            f"[[{preferred[identity].with_suffix('')}|{node.name}]]",
            " · ".join(f"[[#{title}|{title}]]" for title in MODES.values()),
        ]
        audit_sections = [
            f"# Edge Audit — {node.name}",
            "Effective identity: (Component, mode, directed pair). Modes never union.",
            " · ".join(f"[[#{title}|{title}]]" for title in MODES.values()),
        ]
        bodies: dict[str, dict[str, str]] = {}
        for mode, title in MODES.items():
            root = views.OWNED_ROOT / graph.scope_root(identity, mode)
            bodies[mode] = {}
            for name in ("Graph Profile.md", "Edge Audit.md"):
                source = root / name
                body = markdown_parts(
                    utf8(
                        rewrite(old[source], source, guide if name == "Graph Profile.md" else audit)
                    )
                )[1]
                body = re.sub(r"(?m)^# Knowledge Graph .*\n?", "", body, count=1)
                body = body.replace("Domain/Function/Assembly", "Domain/Function")
                body = body.replace(
                    "Open Edge Audit.md in this folder for the complete Markdown fallback, "
                    "inventory and inspection routes.",
                    f"[[{audit.with_suffix('')}#{title}|{title} Edge Audit]] provides the "
                    "complete Markdown fallback, inventory and inspection routes.",
                )
                body = body.replace(
                    "Classes/exclusions and manual activation are in Graph Profile.md; "
                    "only the two node folders enter the filters.",
                    f"Classes/exclusions and manual activation are in "
                    f"[[{guide.with_suffix('')}#{title}|the {title} guide section]]; "
                    "only the two node folders enter the filters.",
                )
                bodies[mode][name] = body
        # Factor only identical prose, never filters, tables, diagnostics or mode rows.
        first_blocks = bodies["architecture"]["Graph Profile.md"].split("\n\n")
        common = list(
            dict.fromkeys(
                block
                for block in first_blocks
                if block.strip()
                and not block.startswith(("#", "```", "- ", "| "))
                and not block.rstrip().endswith(":")
                and "[[" not in block
                and all(block in bodies[mode]["Graph Profile.md"].split("\n\n") for mode in MODES)
            )
        )
        guide_sections += ["## Shared instructions", *common]
        for mode, title in MODES.items():
            profile = "\n\n".join(
                block
                for block in bodies[mode]["Graph Profile.md"].split("\n\n")
                if block not in common
            )
            guide_sections += [f"\n## {title}\n", re.sub(r"(?m)^(#+) ", r"##\1 ", profile)]
            audit_sections += [
                f"\n## {title}\n",
                re.sub(r"(?m)^(#+) ", r"##\1 ", bodies[mode]["Edge Audit.md"]),
            ]
        add(guide, "\n\n".join(guide_sections))
        add(audit, "\n\n".join(audit_sections))
    add(
        PRODUCT / "Views/Graphs.md",
        "# Graphs\n\n[[Research Map Home|Home]]\n\n"
        + "\n".join(
            f"- [[{PRODUCT / 'Graphs' / identity}|{atlas.entities[identity].name}]]"
            for identity in preferred
            if atlas.entities[identity].type == "Component"
        ),
    )
    add(
        PRODUCT / "Guides/Using the Research Map.md",
        "# Using the Research Map\n\n[[Research Map Home|Home]]\n\n"
        "Navigate System → Component using only Registry part_of. Functions describe context.\n\n"
        f"Open [[{ARCHITECTURE_TREE.with_suffix('')}|Architecture Tree]] for the complete "
        f"technical composition, [[{ARCHITECTURE_CANVAS}|Open Canvas]]"
        " and linked Markdown fallback.\n\n"
        f"Open [[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]] for normative control "
        f"and verification gates, [[{EXECUTION_CANVAS}|Open Canvas]]"
        " and the complete Markdown fallback; "
        "individual Registry statuses do not establish a demonstrated live loop.\n\n"
        f"Open [[{INTERACTION_MAP.with_suffix('')}|Interaction Map]] for exact directed "
        f"technical declarations, [[{INTERACTION_CANVAS}|Open Canvas]]"
        " regions and the complete linked ledger. "
        "Interaction arrows are neither hierarchy nor execution sequence.\n\n"
        "Technical / Research / Sources sections share one preferred page. "
        "Audits are collapsed.\n\n"
        "Graph modes Architecture, Knowledge Detail and Questions are separate projections.\n\n"
        "Private RQ Readers are reading projections; edit the authored master. All other private "
        "scientific records retain their exact authored routes.\n\n"
        "Generated pages are disposable; Git Registry and authored Research remain their "
        "respective authorities.\n\n"
        + (
            (
                "Internal storage has no landing page. Evidence, Memory & Retrieval remains a "
                "scoped diagram."
            )
            if explanations is not None and explanations.page_bindings
            else (
                "Internal storage has no landing page. Agent Anatomy and Evidence, Memory & "
                "Retrieval are secondary diagrams."
            )
        ),
    )
    if explanations is not None:
        for path, body in guide_pages(explanations, atlas, preferred).items():
            add(path, body)
        if explanations.page_bindings:
            for path in files:
                if path.parent == PRODUCT / "Guides":
                    files[path] = (
                        utf8(files[path])
                        .replace(
                            "[[Research Map Home|Home]]",
                            "[[Research Map Home|Home]] · "
                            f"[[{ANATOMY.with_suffix('')}|Agent Anatomy]]",
                            1,
                        )
                        .encode()
                    )
            files[ANATOMY_DIRECTORY] += (
                "\n" + anatomy_directory(explanations, atlas, preferred)
            ).encode()
            files[ANATOMY] = anatomy_hub(utf8(files[ANATOMY]), atlas, preferred).encode()

    home = [
        "# Research Map Home",
        "",
        "Start with the System, then follow Component children. Only Registry part_of creates "
        "technical depth. Functions provide functional context.",
        "",
        "Current state: generated navigation from the checked source revision. "
        "Missing Research mappings imply no novelty, gap or completeness judgment.",
        "",
    ]
    if explanations is not None:
        home += [
            "## Understand the Agent",
            "",
            *(
                [
                    f"**Primärer visueller Einstieg: [[{ANATOMY.with_suffix('')}|Agent Anatomy]]**",
                    "",
                    "Wähle einen Bereich der illustrierten Figur und öffne seine Identitäten. "
                    f"Ohne Diagrammplugin: [[{ANATOMY_DIRECTORY.with_suffix('')}"
                    "#Agent Anatomy Navigation|dieselben Lesebereiche als Markdown]].",
                    "",
                ]
                if explanations.page_bindings
                else []
            ),
            "[[Research Map/Guides/System Overview|System Overview]] · "
            "[[Research Map/Guides/Experience to Knowledge|Experience to Knowledge]]",
            "",
            "Component routes below remain direct entry points.",
            "",
            "## Understand and review Research",
            "",
            "[[Research Map/Guides/Scientific Experiment|Scientific Experiment]] · "
            "[[Research Map/Views/Research Steering|Research Steering]] · "
            "[[Research Map/Views/Literature Inspection|Literature Inspection]]",
            "",
            "## Inspect sources",
            "",
            "Open a preferred Component page for source-backed mechanism, implementation "
            "limits and collapsed complete provenance; use the existing technical diagrams "
            "and linked ledger for exact structure and relations.",
            "",
        ]
        if explanations.optional_essay is not None:
            home += [
                "Optionaler Lesepfad: "
                "[[Research Map/Guides/Das Experiment verstehen|Das Experiment verstehen]] "
                "— die zusammenhängende Geschichte hinter dem Aufbau.",
                "",
            ]
    system_paths = [p for i, p in preferred.items() if atlas.entities[i].type == "System"]
    home += ["## Start here", ""]
    home += [
        f"- Explore technical composition: [[{p.with_suffix('')}|System]]" for p in system_paths
    ]
    home += [
        "- See the complete technical hierarchy: "
        f"[[{ARCHITECTURE_TREE.with_suffix('')}|Architecture Tree]]"
        f" · [[{ARCHITECTURE_CANVAS}|Open Canvas]]",
        "- Understand bounded control and verification: "
        f"[[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]] · [[{EXECUTION_CANVAS}|Open Canvas]]",
        "- Understand declared technical interactions: "
        f"[[{INTERACTION_MAP.with_suffix('')}|Interaction Map]]"
        f" · [[{INTERACTION_CANVAS}|Open Canvas]]",
        "- Explore functional context: [[#Functions|Functions]]",
        "- Read scientific inventories: [[Research Map/Views/Research Steering|Research Steering]]",
        "- Inspect literature: [[Research Map/Views/Literature Inspection|Literature Inspection]]",
        "- Inspect a Component Graph: [[Research Map/Views/Graphs|Graphs]]",
        "- Learn navigation: [[Research Map/Guides/Using the Research Map|Using the Research Map]]",
        "",
        "## Secondary explanatory diagrams",
        "",
    ]
    home += [
        f"- [[{path.with_suffix('')}|{path.stem.removesuffix('.excalidraw')}]]"
        for path in (
            *([] if explanations is not None and explanations.page_bindings else [ANATOMY]),
            PRODUCT / "Diagrams/Evidence, Memory & Retrieval.excalidraw.md",
        )
    ]
    home += [
        "",
        "Markdown fallback: preferred pages and mode-specific Edge Audits remain "
        "readable if Excalidraw, Canvas, native Graph or Bases are unavailable.",
        "",
        "Private Research stays at its authored locations. Private RQ reading projections "
        "are under Research Map/Research/Question Readers; all other scientific masters "
        "are linked at their existing authored paths.",
        "",
        "## Tables",
        "",
    ]
    home += [f"- [[{path}|{path.stem}]]" for path in sorted(files) if path.suffix == ".base"]
    labels = {
        "System": "System",
        "Component": "Components",
        "Function": "Functions",
        "Interface": "Interfaces",
        "Contract": "Contracts",
        "DataArtifact": "Data Artifacts",
        "MeasurementPoint": "Measurements",
        "Environment": "Environments",
        "ResearchQuestion": "Program Research Questions",
        "ResearchThread": "Program Research Threads",
        "Decision": "Project Decisions",
    }
    home += [
        "",
        "## Complete identity inventory",
        "",
        "Flat inventories below are not a hierarchy or a runtime sequence.",
        "",
    ]
    for kind in FAMILIES:
        if explanations is not None and kind in {"Component", "Function"}:
            # Home hash routes must land outside closed Obsidian disclosures.
            home += [f"## {labels[kind]}", ""]
            if kind == "Component":
                home += [
                    " · ".join(
                        f"[[{preferred[i].with_suffix('')}|{atlas.entities[i].name}]]"
                        for i in ("CMP-CORTEX", "CMP-MANAGER", "CMP-MEMORY", "CMP-MEM-RETRIEVAL")
                    ),
                    "",
                ]
            home += [f"> [!info]- Expand all {labels[kind].lower()} identities", ">"]
        else:
            home += [f"> [!info]- {labels[kind]}", ">", f"> ## {labels[kind]}", ">"]
        home += [
            f"> - [[{path.with_suffix('')}|{atlas.entities[i].name}]]"
            for i, path in preferred.items()
            if atlas.entities[i].type == kind
        ]
        home.append("")
    properties = markdown_parts(utf8(files[HOME]))[0]
    files[HOME] = ("---\n" + yaml_text(properties) + "---\n" + "\n".join(home) + "\n").encode()

    if explanations is not None:
        for path, body in primary_pages(files).items():
            files[path] = body.encode()
        files.update(secondary_canvases(files))
        for path, data in svg_assets(atlas).items():
            files[path] = data
            # SVG is the existing strict public presentation asset class. Keep
            # the closed migration owner rule; no derived-owner SVG adoption.
            owners[path] = public.OWNER

    if explanations is not None and len(explanations.page_bindings) == 61:
        # B3 adds exactly the four-page envelope proven in the manual native replay.
        files[CANDIDATE_EXCALIDRAW] = managed_system_overview(atlas)
        owners[CANDIDATE_EXCALIDRAW] = public.OWNER
        files[CANDIDATE_DRAWIO] = managed_drawio(atlas)
        owners[CANDIDATE_DRAWIO] = public.OWNER
        drilldown = (
            "\n\nErklärende Vertiefung: "
            f"[[{CANDIDATE_EXCALIDRAW.with_suffix('')}|System Overview Diagramm]] · "
            f"[[{CANDIDATE_DRAWIO}|Grounded Contract · vier Seiten]] · "
            "[[Research Map/Guides/System Overview#Diagramm-Gegenstücke|"
            "Ablauf und getrennte Identitäten ohne Plugins]].\n"
        )
        files[HOME] += drilldown.encode()
        # Ordinary header navigation leaves every figure element and cache intact.
        files[ANATOMY] = (
            utf8(files[ANATOMY])
            .replace("\n%%\n# Excalidraw Data", drilldown + "\n%%\n# Excalidraw Data", 1)
            .encode()
        )
        overview = PRODUCT / "Guides/System Overview.md"
        files[overview] += (drilldown + "\n" + candidate_navigation(atlas)).encode()
        files[EXECUTION_FLOW] += (
            f"\n\n[[{CANDIDATE_DRAWIO}|Grounded Contract · editierbare Vertiefung]] · "
            "[[Research Map/Guides/System Overview#Diagramm-Gegenstücke|Getrennte Identitäten]] · "
            "[[Research Map/Diagrams/Agent Anatomy.excalidraw|Zurück zum primären Hub]] · "
            "[[Research Map Home|Home]].\n"
        ).encode()

    # Atlas index paths are vault-relative final routes, never old-root-relative paths.
    index = INTERNAL / "Indexes/atlas-id-index.yaml"
    entries = read_yaml(utf8(files[index]))
    for identity, item in entries["entries"].items():
        item["path"] = str(
            routes[public.OWNED_ROOT / public.private_path(atlas.entities[identity])]
        )
        if identity in preferred:
            item["preferred_path"] = str(preferred[identity])
    files[index] = yaml_text(entries).encode()
    files[LEDGER] = yaml_text(
        dict(
            migration_schema_version="1.0",
            generated_by=views.OWNER,
            routes={str(s): str(t) for s, t in sorted(routes.items())},
        )
    ).encode()
    owners[LEDGER] = views.OWNER
    for owner, manifest_path in MANIFESTS.items():
        old_manifest = (
            technical[public.MANIFEST] if owner == public.OWNER else derived[views.MANIFEST]
        )
        provenance = read_yaml(utf8(old_manifest))
        provenance.pop("owned_files")
        inventory = []
        for path, data in sorted(files.items()):
            if owners[path] != owner:
                continue
            row = dict(path=str(path), **semantics.record(data, path, owner))
            inventory.append(row)
        files[manifest_path] = yaml_text(
            dict(
                product_schema_version="1.1",
                generated_by=owner,
                provenance=provenance,
                owned_files=inventory,
            )
        ).encode()
        owners[manifest_path] = owner
    public.validate_portable_paths(files)
    return ProductTree(files, owners, routes)
