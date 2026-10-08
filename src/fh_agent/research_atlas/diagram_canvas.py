"""Native Canvas projections; presentation regions never declare architecture."""

import json
import math
import textwrap
from pathlib import PurePosixPath

from . import private_views as views
from .preferred_paths import PRODUCT
from .validator import Atlas

EXECUTION_CANVAS = PRODUCT / "Diagrams/Execution Flow.canvas"
INTERACTION_CANVAS = PRODUCT / "Diagrams/Interaction Map.canvas"
REPOSITORY = "https://github.com/Planton361/autonomous-game-agent/blob/main/"
ARCHITECTURE = REPOSITORY + "docs/canonical/02_ARCHITECTURE_CANONICAL.md"
OVERLAY = REPOSITORY + "docs/orchestration/releases/ALIGN-2026-09-19-v1.0/README.md"

CANVAS_NAVIGATION = (
    "[[Research Map/Diagrams/Architecture Tree.canvas|Hierarchy Canvas]] · "
    "[[Research Map/Diagrams/Execution Flow.canvas|Execution Canvas]] · "
    "[[Research Map/Diagrams/Interaction Map.canvas|Interaction Canvas]]"
)


def card_height(text: str, width: int = 440) -> int:
    """Reserve wrapping and paragraph space at normal Canvas text size."""
    columns = max(20, (width - 48) // 9)
    lines = sum(max(1, len(textwrap.wrap(line, columns))) for line in text.splitlines())
    return max(260, 64 + lines * 26)


def identity_text(atlas: Atlas, preferred: dict[str, PurePosixPath], identity: str) -> str:
    node = atlas.entities[identity]
    status = getattr(node, "technical", None)
    return (
        f"[[{preferred[identity].with_suffix('')}|{node.name}]]\n"
        f"`{identity}` · {node.type}\n\n{node.description}\n\n"
        + (
            f"{status.implementation_status} · verification: {status.verification_status}\n"
            f"Authority: {status.architecture_authority}"
            if status
            else "Context; no implementation status"
        )
    )


def canvas_bytes(nodes: list[dict], edges: list[dict]) -> bytes:
    return (
        json.dumps(
            dict(
                generated_by=views.OWNER, canvas_view_schema_version="1.0", nodes=nodes, edges=edges
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()


def interaction_canvas(
    atlas: Atlas, preferred: dict[str, PurePosixPath], relations: frozenset[str], groups: tuple
) -> bytes:
    """One exact edge per declared row; repeated cards retain one preferred identity."""
    selected = sorted(
        (e for e in atlas.relationships if e.relation in relations),
        key=lambda e: (e.relation, e.source, e.target),
    )
    panels = [[] for _ in groups] + [[]]
    for edge in selected:
        index = (
            4
            if edge.source == "CMP-INPUT-EXECUTOR"
            else next(
                (i for i, (_, targets) in enumerate(groups) if edge.target in targets), len(groups)
            )
        )
        panels[index].append(edge)
    legend = (
        "# Interaction Map · declared technical relations\n\n"
        "Arrows are exact Registry source → target, labelled with the exact relation. "
        "consumes remains actor → payload. Shared artifacts create no direct Component links. "
        "Regions are presentation only: no hierarchy or time order. Repeated "
        "IDs open one preferred page.\n\n"
        "Cards show type, responsibility, implementation, verification and authority. "
        "No status proves a full live loop. Sparse/absent relations imply no "
        "capability conclusion.\n\n"
        "supplies / consumes: payload; proposes_to: intention; controls: authority; "
        "constrains: limit; grounds: target binding; executes: contract execution; "
        "observes / verifies: distinct evidence roles; updates / "
        "retrieves_from: only if declared.\n\n"
        "[[Research Map Home|Home]] · [[Research Map/Diagrams/Interaction "
        "Map|Complete linked relation ledger]]"
    )
    legend += "\n\n" + CANVAS_NAVIGATION
    nodes = [dict(id="legend", type="text", x=0, y=-740, width=1360, height=680, text=legend)]
    edges = []
    row_y = 0
    titles = [title for title, _ in groups] + ["Additional declared technical interactions"]
    # Two columns of bounded regions. Keep all declarations, including future targets.
    for start in range(0, len(panels), 2):
        row_height = 0
        for index in range(start, min(start + 2, len(panels))):
            panel = panels[index]
            if index == len(groups) and not panel:
                continue
            x = (index % 2) * 1680
            identities = sorted(
                {i for e in panel for i in (e.source, e.target)},
                key=lambda i: (atlas.entities[i].type, atlas.entities[i].name, i),
            )
            cards = [(i, identity_text(atlas, preferred, i)) for i in identities]
            height = max((card_height(text) for _, text in cards), default=260)
            region_height = max(400, math.ceil(len(cards) / 3) * (height + 100) + 120)
            nodes.append(
                dict(
                    id=f"group-{index}",
                    type="group",
                    x=x - 40,
                    y=row_y - 60,
                    width=1580,
                    height=region_height,
                    label=titles[index],
                    color="5",
                )
            )
            if not panel:
                nodes.append(
                    dict(
                        id=f"empty-{index}",
                        type="text",
                        x=x,
                        y=row_y + 20,
                        width=440,
                        height=260,
                        text="No selected Registry relations in this panel; "
                        "no connection inferred.",
                    )
                )
            for n, (identity, text) in enumerate(cards):
                nodes.append(
                    dict(
                        id=f"{index}-{identity}",
                        type="text",
                        x=x + n % 3 * 510,
                        y=row_y + 20 + n // 3 * (height + 100),
                        width=440,
                        height=height,
                        text=text,
                        color={
                            "Component": "4",
                            "Contract": "3",
                            "Interface": "6",
                            "DataArtifact": "2",
                            "Environment": "1",
                        }.get(atlas.entities[identity].type, "5"),
                    )
                )
            for edge in panel:
                edges.append(
                    dict(
                        id=f"{index}-{edge.relation}-{edge.source}-{edge.target}",
                        fromNode=f"{index}-{edge.source}",
                        toNode=f"{index}-{edge.target}",
                        fromSide="right",
                        toSide="left",
                        fromEnd="none",
                        toEnd="arrow",
                        label=edge.relation,
                    )
                )
            row_height = max(row_height, region_height)
        row_y += row_height + 180
    mentioned = {i for e in selected for i in (e.source, e.target)}
    detached = sorted(
        i
        for i, n in atlas.entities.items()
        if n.type in {"Component", "Interface", "Contract", "DataArtifact", "Environment"}
        and i not in mentioned
    )
    if detached:
        texts = [
            (
                i,
                identity_text(atlas, preferred, i)
                + "\n\nNo selected interaction row; no link inferred.",
            )
            for i in detached
        ]
        height = max(card_height(text) for _, text in texts)
        nodes.append(
            dict(
                id="group-detached",
                type="group",
                x=-40,
                y=row_y - 60,
                width=1580,
                height=math.ceil(len(texts) / 3) * (height + 100) + 120,
                label="Technical context without declared selected interactions",
                color="6",
            )
        )
        for index, (identity, text) in enumerate(texts):
            nodes.append(
                dict(
                    id="context-" + identity,
                    type="text",
                    x=index % 3 * 510,
                    y=row_y + 20 + index // 3 * (height + 100),
                    width=440,
                    height=height,
                    text=text,
                    color="6",
                )
            )
    return canvas_bytes(nodes, edges)


# Stage records are normative prerequisites/conditional transitions, NEVER Registry triples.
# Coordinates are local to numbered reading regions; cycles are explicitly labelled.
# (id, title, detail, preferred identities, source section)
FLOW_REGIONS = (
    (
        "01 · Mission Run / observation integrity",
        (
            (
                "mission",
                "Independently eligible Mission Run",
                "Explicit applicable authorization; protocol-defined fresh "
                "experimental state, new mission ID/manifest. Freeze mode, "
                "budgets, Cortex/model/prompt/config, Body weights/version, "
                "harness and safety identities before first observation. No "
                "default inherited cross-Mission-Run memory.",
                ("SYS-AGA",),
                "overlay:mission-run-identity-and-mutable-state",
            ),
            (
                "capture",
                "GameInstance → Screen Capture",
                "Primary research path is screen-only. Capture admissible "
                "screenshots/frame sequences and visible text with "
                "timestamps, hashes and run provenance.",
                ("ENV-GAME-INSTANCE", "CMP-SCREEN-CAPTURE", "DAT-SCREEN-FRAME"),
                "3-perception-and-observation",
            ),
            (
                "bridge",
                "Optional bridge-assisted cohort",
                "Separate declared run classification. Only allowlisted "
                "information simultaneously visible to an ordinary player; "
                "never maps, switches, variables, databases, RAM or hidden "
                "state.",
                ("CMP-VISIBLE-STATE-BRIDGE",),
                "3-perception-and-observation",
            ),
            (
                "firewall",
                "Deny-by-default No-Spoiler Firewall",
                "Admit only visible allowlisted evidence. Forbidden access is"
                " an integrity incident; preserve provenance, run-"
                "mode/network separation and contamination quarantine.",
                ("CMP-NO-SPOILER-FIREWALL",),
                "3-perception-and-observation",
            ),
            (
                "observation",
                "Observation / Perception",
                "Report visible text, UI, position/candidates, confidence and"
                " evidence references. No goal selection, hidden semantics or"
                " success judgement.",
                ("CMP-OBSERVATION-BUILDER", "CMP-PERCEPTION", "DAT-OBSERVATION"),
                "3-perception-and-observation",
            ),
            (
                "temporal",
                "Temporal State",
                "Short-horizon motion/UI continuity, target visibility, "
                "hazards, progress/no-progress and repeated-state/action "
                "evidence. Do not assume persistent semantic identity.",
                ("CMP-TEMPORAL-STATE",),
                "4-temporal-state",
            ),
            (
                "evidence",
                "Evidence Ledger / admissible memory",
                "Immutable screenshot/text/action/outcome/bridge receipt "
                "links. Facts retain provenance; hypotheses retain "
                "uncertainty/contradictions; topology records observed "
                "connections only.",
                ("CMP-EVIDENCE-LEDGER", "CMP-MEMORY"),
                "5-memory-architecture",
            ),
            (
                "retrieval",
                "Bounded retrieval → CortexContext",
                "Current goal, skills, budgets/risk, prior outcome and open "
                "questions plus relevant "
                "evidence/facts/hypotheses/episodes/topology/competence. "
                "Bounded snapshot, not entire database.",
                ("CMP-MEM-RETRIEVAL", "IF-MEM-CORTEX", "CON-CORTEX-CONTEXT"),
                "6-cortex-contract",
            ),
        ),
    ),
    (
        "02 · Event-driven intention / Manager authority",
        (
            (
                "event",
                "Meaningful event gate",
                "New evidence, completion/failure, contradiction, death, "
                "deadlock, risk/resource alarm or relevant uncertainty. "
                "Initial planning has no prior contract; replanning requires "
                "prior contract closed/suspended. Never per-frame Cortex "
                "invocation.",
                (),
                "2-multi-timescale-control",
            ),
            (
                "cortex",
                "Cortex proposes intention",
                "Evidence-grounded belief/hypothesis updates, information "
                "needs, one goal, one universal skill, constraints/risk and "
                "testable success criteria. No primitive keys/timings or "
                "InputExecutor calls.",
                ("CMP-CORTEX", "CON-PLANNER-OUTPUT", "IF-CORTEX-MANAGER"),
                "6-cortex-contract",
            ),
            (
                "validate",
                "Manager validates schema / policy",
                "Manager alone owns execution authority. Validate typed "
                "proposal and no-spoiler policy; reject invalid/unsafe "
                "intention.",
                ("CMP-MANAGER",),
                "7-manager--executive-contract",
            ),
            (
                "capability",
                "Executable capability gate",
                "Check requested universal skill against currently available "
                "executable set and competence. Unavailable capability "
                "rejects; no game-specific quest/room/enemy/ending shortcut.",
                ("CMP-SKILL-COMPETENCE",),
                "7-manager--executive-contract",
            ),
            (
                "ground",
                "Visible target grounding",
                "Bind a typed target to admissible visible evidence IDs. "
                "Ambiguity/insufficient evidence rejects; Body must not "
                "guess.",
                ("CMP-MANAGER-GROUNDING",),
                "7-manager--executive-contract",
            ),
            (
                "contract",
                "Manager opens bounded Skill Contract",
                "Bind target, skill, allowed actions, action/risk budgets, "
                "independent verifier, timeout, termination and "
                "logging/evidence requirements. At most one active contract.",
                ("CON-SKILL-CONTRACT",),
                "8-skill-abstraction",
            ),
            (
                "schedule",
                "Manager schedules Body / Reflex",
                "Declare Reflex triggers, eligibility, cooldown, action mask "
                "and termination. Contract must remain active and valid.",
                ("CMP-MANAGER-SCHED-COMP",),
                "10-reflex",
            ),
        ),
    ),
    (
        "03 · Contract execution / separate input safety",
        (
            (
                "body",
                "Body policy / reusable skill",
                "Current visual/temporal state, grounded target, skill "
                "representation, short action history and contract action "
                "mask. Body/controller weights remain frozen throughout this "
                "Mission Run.",
                ("CMP-BODY",),
                "9-body-design",
            ),
            (
                "reflex",
                "Eligible bounded Reflex",
                "Fast Body path for declared immediate visible conditions "
                "only. No new goals, unavailable skill, memory truth changes,"
                " budget extension, stop/replan suppression or safety bypass.",
                ("CMP-BOUNDED-REFLEX",),
                "10-reflex",
            ),
            (
                "proposal",
                "One primitive proposal",
                "Propose one contract-allowed primitive at a time. "
                "Insufficient evidence requires wait/stop/replan. Proposal is"
                " not execution.",
                ("CON-PRIMITIVE-ACTION",),
                "9-body-design",
            ),
            (
                "safety",
                "SafetyFilter: contract / action / budget",
                "Require valid active Manager contract, allowed action mask, "
                "remaining action/risk budgets. Recheck on every proposal.",
                ("CMP-SAFETY-FILTER",),
                "14-safetyinput",
            ),
            (
                "focus",
                "Input gate: verified target focus",
                "Verify intended game window identity/focus. Wrong-window "
                "input is a hard failure; lost focus rejects/stops.",
                (),
                "14-safetyinput",
            ),
            (
                "capacity",
                "Input gate: rate limit / emergency stop",
                "Require available rate-limit capacity and functional "
                "emergency stop. Exhaustion or failed stop prevents "
                "execution.",
                (),
                "14-safetyinput",
            ),
            (
                "logging",
                "Durable evidence / logging gate",
                "Record observation, proposed/executed/rejected action, "
                "contract and skill result. Require before/after evidence "
                "linkage; unloggable action rejects.",
                (),
                "14-safetyinput",
            ),
            (
                "execute",
                "InputExecutor guarded execution",
                "Execute only after every prerequisite passes. Safety/input "
                "is separate enforcement; Cortex cannot bypass it.",
                ("CMP-INPUT-EXECUTOR", "DAT-ACTION-RESULT"),
                "14-safetyinput",
            ),
        ),
    ),
    (
        "04 · Independent verification / outcome evaluation",
        (
            (
                "outcome",
                "Visible outcome + fresh observation",
                "Capture resulting visible evidence and link "
                "before/action/after records. Changed screenshot/hash alone "
                "is not success.",
                ("DAT-VISIBLE-OUTCOME", "DAT-OBSERVATION"),
                "11-independent-verification-and-reward",
            ),
            (
                "verifier",
                "Independent Verifier",
                "Cortex never grades itself. Prefer deterministic visible "
                "success/failure, then progress; calibrated learned "
                "perception if necessary; separately evaluated judge only "
                "where required; manual audit.",
                ("CMP-INDEPENDENT-VERIFIER",),
                "11-independent-verification-and-reward",
            ),
            (
                "result",
                "Typed result / validated rewards",
                "Visible success, failure, progress plus evidence IDs. "
                "Rewards derive from validated events, not free-form Cortex "
                "scores. Distinguish uncertainty, "
                "grounding/capability/planning/skill failures, timeout, "
                "target loss, safety/focus, death and contamination.",
                ("CON-VERIFIER-RESULT",),
                "11-independent-verification-and-reward",
            ),
            (
                "evaluate",
                "Manager evaluates outcome",
                "Continue only a still-valid active contract with refreshed "
                "state and all input gates repeated. Otherwise close/suspend "
                "on success/failure, timeout, no-progress, target loss, "
                "safety, contamination, death or contradiction.",
                ("CMP-MANAGER",),
                "7-manager--executive-contract",
            ),
            (
                "reject",
                "Reject / stop record",
                "Log reason and evidence; do not label rejection as an "
                "executed action or fabricate Verifier success. Integrity "
                "incidents require stop/quarantine review.",
                (),
                "14-safetyinput",
            ),
            (
                "close",
                "Manager closes / suspends prior contract",
                "Auditable closure/suspension, if active, before Cortex "
                "replanning. Nonterminal meaningful events return via fresh "
                "admissible observation/retrieval.",
                ("CMP-MANAGER",),
                "7-manager--executive-contract",
            ),
            (
                "memory",
                "Evidence-linked memory / post-mortem",
                "Store trajectories, outcomes and requested updates with "
                "provenance. Separate observation from inferred cause. "
                "Hypotheses never silently become facts; memory grants no "
                "execution authority.",
                ("CON-MEMORY-UPDATE-REQUEST", "CON-POST-MORTEM-OUTPUT"),
                "5-memory-architecture",
            ),
        ),
    ),
    (
        "05 · Life Episode / Mission Run boundaries",
        (
            (
                "episode",
                "Close Life Episode",
                "Visible death or episode stop: close transient state, retain"
                " evidence/post-mortem. Ordinary death, contract failure or "
                "timeout does not itself terminate Mission Run.",
                (),
                "overlay:nested-experimental-units",
            ),
            (
                "restart",
                "Permitted restart: same Mission Run",
                "If nonterminal and restart permitted, open next Life Episode"
                " with same frozen identities/Body weights. Admissible "
                "evidence/memory can persist across Life Episodes. No "
                "training/replacement here.",
                (),
                "overlay:restart-and-terminal-semantics",
            ),
            (
                "continuity",
                "Application/process restart integrity",
                "Preserve manifest, frozen identities and provenance. "
                "Recreate transient handles only. If continuity cannot be "
                "established, stop/quarantine; never relabel as clean new "
                "run.",
                (),
                "overlay:restart-and-terminal-semantics",
            ),
            (
                "terminal",
                "Declared Mission Run terminal condition",
                "Independently verified mission success; frozen "
                "time/action/cost/life budget exhaustion; explicit authorized"
                " manual stop; unrecoverable safety/integrity or "
                "environment/harness failure. Ordinary death is insufficient.",
                (),
                "overlay:restart-and-terminal-semantics",
            ),
        ),
    ),
    (
        "06 · Optional future learning BETWEEN Mission Runs",
        (
            (
                "replay",
                "Admissible frozen-version experience",
                "Retain verifier-labelled trajectories, demonstrations and "
                "failure subsets with frozen Body vN and full provenance. "
                "Training requires separately authorized future protocol "
                "after Mission Run termination.",
                ("CMP-REPLAY-BUFFER", "DAT-REPLAY-TRANSITION"),
                "12-learning-lifecycle",
            ),
            (
                "train",
                "SkillTrainer trains candidate vN+1",
                "Between Mission Runs only. Trainer may propose curricula "
                "from deficiencies; cannot silently deploy a controller.",
                ("CMP-SKILL-TRAINER", "DAT-CANDIDATE-BODY-VERSION"),
                "12-learning-lifecycle",
            ),
            (
                "heldout",
                "Held-out validation",
                "Validate candidate on held-out scenarios; safety and false-"
                "success checks. Candidate is not active Body.",
                ("CMP-BODY-CERTIFICATION",),
                "12-learning-lifecycle",
            ),
            (
                "certify",
                "Certify or reject candidate",
                "Only certified candidate may activate for next independently"
                " eligible Mission Run. Rejected candidate never activates; "
                "already eligible prior Body remains available.",
                ("CMP-BODY-CERTIFICATION",),
                "12-learning-lifecycle",
            ),
            (
                "next",
                "Next independently eligible Mission Run",
                "May reuse eligible Body without retraining. New mission "
                "identity/manifest, fresh protocol-defined experimental state"
                " and independently frozen identities. No automatic start or "
                "default inherited memory.",
                (),
                "overlay:mission-run-identity-and-mutable-state",
            ),
        ),
    ),
)


def execution_canvas(atlas: Atlas, preferred: dict[str, PurePosixPath]) -> bytes:
    legend = (
        "# Execution Flow · normative control lifecycle\n\n"
        "Read numbered regions top to bottom; pan/zoom, follow labelled conditional arrows. "
        "This is intended authority/control, not a demonstrated runtime trace"
        " or per-frame schedule. "
        "Asynchronous subsystem work need not execute in this drawing order. "
        "Arrows are not Registry relations or containment.\n\n"
        "Optional paths are labelled; all training/certification is outside "
        "the running Mission Run. "
        "Linked identities show Registry implementation context, not proof "
        "that every gate exists.\n\n"
        "[[Research Map Home|Home]] · [[Research Map/Diagrams/Execution "
        "Flow|Sources, implementation limits and Markdown fallback]]"
    )
    legend += "\n\n" + CANVAS_NAVIGATION
    nodes = [dict(id="legend", type="text", x=0, y=-640, width=1580, height=560, text=legend)]
    positions = {}
    top = 0
    for region, stages in FLOW_REGIONS:
        texts = []
        for identity, title, detail, identities, section in stages:
            source = (
                OVERLAY + "#" + section.removeprefix("overlay:")
                if section.startswith("overlay:")
                else ARCHITECTURE + "#" + section
            )
            links = "\n".join(
                identity_text(atlas, preferred, i).split("\n\n")[0]
                + "\n"
                + f"Registry: {atlas.entities[i].technical.implementation_status}"
                for i in identities
                if i in preferred
            )
            text = f"### {title}\n\n{detail}\n\n{links}\n\n[Source]({source})"
            texts.append((identity, text))
        height = max(card_height(text, 480) for _, text in texts)
        region_height = math.ceil(len(texts) / 3) * (height + 140) + 120
        nodes.append(
            dict(
                id="group-" + stages[0][0],
                type="group",
                x=-40,
                y=top - 60,
                width=1780,
                height=region_height,
                label=region,
                color="5",
            )
        )
        for index, (identity, text) in enumerate(texts):
            x, y = index % 3 * 600, top + index // 3 * (height + 140)
            nodes.append(
                dict(
                    id=identity,
                    type="text",
                    x=x,
                    y=y,
                    width=480,
                    height=height,
                    text=text,
                    color="3"
                    if identity in {"validate", "safety", "evaluate", "certify", "firewall"}
                    else "4",
                )
            )
            positions[identity] = (x, y)
        top += region_height + 240
    arrows = []

    def edge(source: str, target: str, label: str = "prerequisite") -> None:
        arrows.append((source, target, label))

    chains = (
        (
            "mission",
            "capture",
            "firewall",
            "observation",
            "temporal",
            "evidence",
            "retrieval",
            "event",
            "cortex",
            "validate",
            "capability",
            "ground",
            "contract",
            "schedule",
            "body",
        ),
        (
            "body",
            "proposal",
            "safety",
            "focus",
            "capacity",
            "logging",
            "execute",
            "outcome",
            "verifier",
            "result",
            "evaluate",
        ),
        ("train", "heldout", "certify"),
    )
    for chain in chains:
        for source, target in zip(chain, chain[1:], strict=False):
            edge(source, target)
    for source, target, label in (
        ("bridge", "firewall", "optional allowlisted visible feed"),
        ("firewall", "reject", "forbidden access: integrity incident"),
        ("schedule", "reflex", "optional declared immediate trigger / eligibility"),
        ("reflex", "proposal", "contract-allowed primitive only"),
        ("proposal", "close", "insufficient evidence: wait / stop / replan"),
        ("evaluate", "body", "continue valid active contract; refreshed state"),
        ("evaluate", "close", "contract terminal / stop condition"),
        ("reject", "close", "Manager stop authority; if contract active"),
        ("close", "observation", "nonterminal meaningful replan: fresh evidence"),
        ("close", "memory", "evidence-linked consolidation / requests"),
        ("result", "memory", "verified outcomes and provenance"),
        ("close", "episode", "visible death / episode stop"),
        ("close", "terminal", "declared Mission Run terminal condition"),
        ("episode", "restart", "nonterminal; restart permitted"),
        ("episode", "terminal", "declared terminal condition reached"),
        ("restart", "capture", "new Life Episode; same Mission Run / frozen Body"),
        ("continuity", "capture", "identities / provenance preserved"),
        ("continuity", "reject", "continuity lost: stop / quarantine"),
        ("terminal", "next", "already eligible Body; no retraining"),
        ("result", "replay", "collect verifier labels; not training"),
        ("terminal", "replay", "optional future between-run protocol authorized"),
        ("replay", "train", "only after termination + separate authorization"),
        ("certify", "next", "activate certified candidate only"),
        ("certify", "next", "candidate rejected: retain eligible prior Body"),
        ("next", "mission", "independent eligibility / authorization; no automatic start"),
    ):
        edge(source, target, label)
    for source in ("validate", "capability", "ground", "safety", "focus", "capacity", "logging"):
        edge(source, "reject", "gate failed: no executed action")
    edges = []
    seen = set()
    for index, (source, target, label) in enumerate(arrows):
        _, sy = positions[source]
        _, ty = positions[target]
        vertical = sy != ty
        parallel = (source, target) in seen
        seen.add((source, target))
        edges.append(
            dict(
                id=f"flow-{index}",
                fromNode=source,
                toNode=target,
                fromSide="bottom"
                if parallel
                else (("bottom" if ty > sy else "left") if vertical else "right"),
                toSide="bottom"
                if parallel
                else (("top" if ty > sy else "left") if vertical else "left"),
                fromEnd="none",
                toEnd="arrow",
                label=label,
            )
        )
    return canvas_bytes(nodes, edges)
