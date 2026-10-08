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
from .preferred_paths import FAMILIES, HOME, INTERNAL, PRODUCT, containment_paths, preferred_paths
from .private_projection import ProjectionError, markdown_parts, read_yaml, utf8, yaml_text
from .validator import Atlas

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
        "[[Research Map Home|Home]] · [[#Markdown fallback|Markdown fallback]] · "
        "[[#Current implementation and preferred pages|Implementation and preferred pages]]",
        "",
        "## Normative control lifecycle",
        "",
        "This is the normative/target architecture, not a trace of a demonstrated live loop. "
        "Arrows express authority prerequisites and conditional transitions, not a per-frame "
        "schedule or a strictly sequential order for asynchronous subsystem work. "
        "Process arrows never declare Registry relations or `part_of` ancestry. "
        "The Architecture Tree remains the composition view; the Interaction Map is not "
        "implemented by this page.",
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
        '    next["Next eligible Mission Run<br/>certified Body only"]',
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
        '    terminal -.->|"between Mission Runs; separately authorized"| learn',
        '    learn -.->|"certified version only; reject blocks activation"| next',
        "```",
        "",
        "Legend: rectangles describe bounded responsibilities; diamonds are validation or "
        "evaluation gates. Solid arrows are conditional control prerequisites. Dotted "
        "arrows are optional paths. A rejected proposal is never an executed action. "
        "All boundary records are typed, logged and evidence-linked. Learning is outside "
        "the running Mission Run. Visual labels are short; the fallback supplies the "
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
        "9. **Optional future learning outside the loop.** Only between Mission Runs, "
        "under a separately authorized future protocol: collect admissible experience "
        "with frozen Body vN → verifier-labelled replay/demonstrations → train candidate "
        "vN+1 → held-out validation and safety/false-success checks → certify or reject → "
        "activate only a certified version for the next eligible Mission Run. Neither "
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
        "Read left to right: parent → contained Component. Lines mean containment only; "
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
            y=-260,
            width=880,
            height=200,
            text="**Architecture Tree · technical containment**\n\n"
            "Read parent → child, left to right. Only Registry part_of creates lines. "
            "No runtime sequence, control or data flow is implied.\n\n"
            f"[[{ARCHITECTURE_TREE.with_suffix('')}|Linked Markdown tree and context]] · "
            "[[Research Map Home|Home]]",
        )
    ]
    edges = []
    row = 0

    def visit(trail: tuple[str, ...]) -> float:
        nonlocal row
        identity = trail[-1]
        node = atlas.entities[identity]
        depth = len(trail) - 1
        body.append(
            "  " * depth + f"- {link(identity)} — {node.type} · `{identity}` · "
            f"{node.technical.implementation_status}"
        )
        descendants = children.get(trail, [])
        positions = [visit(child) for child in descendants]
        if positions:
            y = (positions[0] + positions[-1]) / 2
        else:
            y = row * 200
            row += 1
        nodes.append(
            dict(
                id=token(trail),
                type="text",
                x=depth * 480,
                y=y,
                width=400,
                height=160,
                color="5" if node.type == "System" else "4",
                text=f"**{node.type}**\n\n{link(identity)}\n\n"
                f"`{identity}` · {node.technical.implementation_status}",
            )
        )
        if depth:
            edges.append(
                dict(
                    id="edge-" + token(trail),
                    fromNode=token(trail[:-1]),
                    toNode=token(trail),
                    fromSide="right",
                    toSide="left",
                    fromEnd="none",
                    toEnd="none",
                    label="contains",
                )
            )
        return y

    roots = children.get((), [])
    for kind, heading in (
        ("System", "System composition"),
        ("Component", "No System containment chain"),
    ):
        matching = [trail for trail in roots if atlas.entities[trail[0]].type == kind]
        if not matching:
            continue
        body += [f"### {heading}", ""]
        if kind == "Component":
            body += ["These roots have no declared System ancestor; no attachment is inferred.", ""]
            row += 1
        for trail in matching:
            visit(trail)
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


def package(atlas: Atlas, technical: dict, derived: dict) -> ProductTree:
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
        "technical composition, native Canvas and linked Markdown fallback.\n\n"
        f"Open [[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]] for normative control "
        "and verification gates, native Mermaid and the complete Markdown fallback; "
        "individual Registry statuses do not establish a demonstrated live loop.\n\n"
        "Technical / Research / Sources sections share one preferred page. "
        "Audits are collapsed.\n\n"
        "Graph modes Architecture, Knowledge Detail and Questions are separate projections.\n\n"
        "Private RQ Readers are reading projections; edit the authored master. All other private "
        "scientific records retain their exact authored routes.\n\n"
        "Generated pages are disposable; Git Registry and authored Research remain their "
        "respective authorities.\n\n"
        "Internal storage has no landing page. Agent Anatomy and Evidence, Memory & Retrieval "
        "are secondary diagrams.",
    )
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
    system_paths = [p for i, p in preferred.items() if atlas.entities[i].type == "System"]
    home += ["## Start here", ""]
    home += [
        f"- Explore technical composition: [[{p.with_suffix('')}|System]]" for p in system_paths
    ]
    home += [
        "- See the complete technical hierarchy: "
        f"[[{ARCHITECTURE_TREE.with_suffix('')}|Architecture Tree]]",
        "- Understand bounded control and verification: "
        f"[[{EXECUTION_FLOW.with_suffix('')}|Ablaufdiagramm]]",
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
            PRODUCT / "Diagrams/Agent Anatomy.excalidraw.md",
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
        home += [f"> [!info]- {labels[kind]}", ">", f"> ## {labels[kind]}", ">"]
        home += [
            f"> - [[{path.with_suffix('')}|{atlas.entities[i].name}]]"
            for i, path in preferred.items()
            if atlas.entities[i].type == kind
        ]
        home.append("")
    properties = markdown_parts(utf8(files[HOME]))[0]
    files[HOME] = ("---\n" + yaml_text(properties) + "---\n" + "\n".join(home) + "\n").encode()

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
