"""Phase-D presentation only; process arrows never create Registry facts.

The tree is a pinned DOT→SVG render. Other panels reuse the supplied palette
with explicit geometry. Generation requires no renderer dependency or I/O.
"""

import hashlib
import json
import textwrap
from html import escape
from pathlib import PurePosixPath

from .preferred_paths import PRODUCT
from .private_projection import ProjectionError
from .validator import Atlas

SVG_NAMES = (
    "System Overview",
    "Architecture Tree",
    "Interaction Map",
    "Experience to Knowledge",
    "Scientific Experiment",
)
PALETTE = {"blue": "#2D6994", "green": "#26776D", "orange": "#B3752F", "purple": "#6552A1"}
LEGEND = (
    "**Normative**: intended responsibilities and conditional "
    "process, not an executed trace. **Implementation**: Registry "
    "status and bounded code/test evidence on preferred pages; no "
    "full-loop or scientific certification. **Design-open**: "
    "unresolved admission or future learning authority. Process "
    "arrows add no Registry relations. The opaque light background "
    "preserves contrast in light and dark themes."
)
INTERACTION_PANELS = (
    (
        "Retrieval, intention and Manager validation",
        (
            ("CMP-MEM-RETRIEVAL", "supplies", "IF-MEM-CORTEX"),
            ("CMP-CORTEX", "consumes", "IF-MEM-CORTEX"),
            ("CMP-CORTEX", "supplies", "CON-PLANNER-OUTPUT"),
            ("CMP-MANAGER", "consumes", "CON-PLANNER-OUTPUT"),
            ("CMP-CORTEX", "proposes_to", "CMP-MANAGER"),
        ),
    ),
    (
        "Contract authority and primitive proposals",
        (
            ("CMP-MANAGER", "supplies", "CON-SKILL-CONTRACT"),
            ("CMP-BODY", "executes", "CON-SKILL-CONTRACT"),
            ("CON-SKILL-CONTRACT", "constrains", "CMP-BODY"),
            ("CMP-BODY", "supplies", "CON-PRIMITIVE-ACTION"),
            ("CMP-INPUT-EXECUTOR", "consumes", "CON-PRIMITIVE-ACTION"),
        ),
    ),
    (
        "One result, separate consumers",
        (
            ("CMP-INDEPENDENT-VERIFIER", "supplies", "CON-VERIFIER-RESULT"),
            ("CMP-MANAGER", "consumes", "CON-VERIFIER-RESULT"),
            ("CMP-MEMORY", "consumes", "CON-VERIFIER-RESULT"),
            ("CMP-REPLAY-BUFFER", "consumes", "CON-VERIFIER-RESULT"),
        ),
    ),
)


def architecture_dot(atlas: Atlas) -> str:
    """Deterministic, presentation-only diagram projection."""
    actors = {i: n for i, n in atlas.entities.items() if n.type in {"System", "Component"}}
    edges = sorted((e.source, e.target) for e in atlas.relationships if e.relation == "part_of")
    if (
        len(actors) != 29
        or len(edges) != 28
        or {i for i, n in actors.items() if n.type == "System"} != {"SYS-AGA"}
        or {child for child, _ in edges} != set(actors) - {"SYS-AGA"}
        or any(parent not in actors for _, parent in edges)
    ):
        raise ProjectionError("AP2 tree requires the reviewed single-root 28-Component hierarchy")
    for child, _ in edges:
        seen = set()
        while child != "SYS-AGA":
            if child in seen:
                raise ProjectionError("AP2 containment cycle")
            seen.add(child)
            child = dict(edges)[child]
    lines = [
        "digraph Architecture {",
        'graph [rankdir=TB, bgcolor="#FFFFFF", pad="0.3", '
        'nodesep="0.25", ranksep="0.8", ordering=out];',
        'node [shape=box, style="rounded,filled", fillcolor="#EDF5FC", '
        'color="#2D6994", fontcolor="#21384B", fontname="Arial", '
        'fontsize=18, margin="0.18,0.12"];',
        'edge [color="#526677", penwidth=1.5, arrowhead=none];',
    ]
    for identity, node in sorted(actors.items()):
        label = "\\n".join(
            textwrap.wrap(node.name, 24) + [identity, node.technical.implementation_status]
        )
        lines.append(f'"{identity}" [id="{identity}", label="{label}"];')
    for child, parent in edges:
        lines.append(f'"{parent}" -> "{child}" [id="part_of:{child}:{parent}"];')
    return "\n".join(lines + ["}", ""])


def architecture_svg(atlas: Atlas) -> bytes:
    from .graphviz_tree import DOT_SHA256, SVG

    if hashlib.sha256(architecture_dot(atlas).encode()).hexdigest() != DOT_SHA256:
        raise ProjectionError("Graphviz source changed; re-render and review the pinned tree")
    return SVG.encode()


class Drawing:
    """Deterministic, presentation-only diagram projection."""

    def __init__(self, title: str, height: int, subtitle: str):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" '
            f'viewBox="0 0 960 {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
            "<metadata>AGA Phase-D SVG renderer 1; Arial/sans-serif; opaque "
            "light canvas; presentation only; native Obsidian acceptance "
            "pending</metadata>",
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
            'refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" '
            'fill="#526677"/></marker></defs>',
            f'<rect width="960" height="{height}" fill="#FFFFFF"/>',
        ]
        self.text(32, 40, title, size=26, bold=True)
        self.text(32, 72, subtitle, size=17)

    def text(self, x: int, y: int, value: str, *, size: int = 17, bold: bool = False):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'font-weight="{"bold" if bold else "normal"}" fill="#21384B">{escape(value)}</text>'
        )

    def box(
        self,
        key: str,
        x: int,
        y: int,
        title: str,
        lines: tuple[str, ...],
        *,
        width: int = 360,
        height: int = 112,
        color: str = "blue",
        identity: str = "",
    ):
        self.parts.append(f'<g data-node="{escape(key)}" data-identity="{escape(identity)}">')
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" '
            f'fill="#F3F8FD" stroke="{PALETTE[color]}" stroke-width="2"/>'
        )
        self.text(x + 16, y + 30, title, size=20, bold=True)
        for row, line in enumerate(lines):
            self.text(x + 16, y + 57 + 24 * row, line)
        self.parts.append("</g>")

    def arrow(
        self,
        source: str,
        target: str,
        points: tuple[tuple[int, int], ...],
        label: str = "",
        at: tuple[int, int] = (0, 0),
        *,
        relation: str = "",
        optional: bool = False,
    ):
        self.parts.append(
            f'<g data-source="{escape(source)}" data-target="{escape(target)}" '
            f'data-relation="{escape(relation)}" '
            f'data-semantics="{"registry" if relation else "normative"}">'
        )
        self.parts.append(
            '<polyline fill="none" stroke="#526677" stroke-width="2" '
            'marker-end="url(#arrow)" '
            + ('stroke-dasharray="7,5" ' if optional else "")
            + 'points="'
            + " ".join(f"{x},{y}" for x, y in points)
            + '"/>'
        )
        if label:
            x, y = at
            self.parts.append(
                f'<rect data-label="true" x="{x - 4}" y="{y - 18}" '
                f'width="{len(label) * 9 + 8}" height="24" fill="#FFFFFF"/>'
            )
            self.text(x, y, label)
        self.parts.append("</g>")

    def finish(self) -> bytes:
        return ("\n".join(self.parts + ["</svg>"]) + "\n").encode()


def overview_svg() -> bytes:
    d = Drawing(
        "System Overview · a closed Agent loop",
        1360,
        "Normative process · independent verification · bounded retrieval",
    )
    left = (
        (
            "observation",
            "Observation (t)",
            ("Visible, admissible evidence", "Perception / Temporal State"),
        ),
        (
            "cortex",
            "Cortex",
            ("Evidence-linked goal / capability", "Intention; no primitive control"),
        ),
        ("manager", "Manager", ("Validate, ground, authorize", "Sole contract authority")),
        (
            "contract",
            "Grounded Skill Contract",
            ("Allowed actions, targets, budget", "Bounded success / stop criteria"),
        ),
        (
            "body",
            "Body / eligible Reflex",
            ("Contract-allowed primitives only", "Body weights frozen this Mission Run"),
        ),
        (
            "input",
            "SafetyFilter / InputExecutor",
            ("Contract, focus, mask, rate, stop", "Durable before / after logging"),
        ),
        ("game", "GameInstance", ("External environment", "Visible response to guarded input")),
    )
    for row, (key, title, lines) in enumerate(left):
        y = 126 + 158 * row
        d.box(key, 32, y, title, lines, width=410)
        if row:
            d.arrow(left[row - 1][0], key, ((237, y - 46), (237, y)))
    d.box(
        "retrieval",
        530,
        126,
        "Memory Retrieval",
        ("Admissible Memory → context", "Separate path; partial implementation"),
        width=398,
        color="green",
    )
    d.arrow(
        "retrieval",
        "cortex",
        ((530, 182), (490, 182), (490, 340), (442, 340)),
        "retrieval",
        (452, 270),
    )
    d.box(
        "transition",
        530,
        442,
        "Manager transition",
        ("VerifierResult + evidence", "Continue / close / suspend / stop"),
        width=398,
    )
    d.box(
        "result",
        530,
        632,
        "VerifierResult",
        ("Typed visible outcome and evidence", "A changed screenshot is not success"),
        width=398,
    )
    d.box(
        "verifier",
        530,
        822,
        "Independent Verifier",
        ("Determines visible outcome", "Independent of Cortex"),
        width=398,
    )
    d.box(
        "newobs",
        530,
        1074,
        "New Observation",
        ("Visible response becomes evidence", "No hidden-state authority"),
        width=398,
    )
    d.arrow("game", "newobs", ((442, 1130), (530, 1130)))
    d.arrow("newobs", "verifier", ((729, 1074), (729, 934)), "visible evidence", (744, 998))
    d.arrow("verifier", "result", ((729, 822), (729, 744)), "outcome", (744, 790))
    d.arrow("result", "transition", ((729, 632), (729, 554)), "VerifierResult", (744, 600))
    d.arrow("transition", "manager", ((530, 498), (442, 498)))
    d.arrow(
        "manager",
        "body",
        ((442, 535), (475, 535), (475, 814), (442, 814)),
        "continue valid",
        (463, 765),
    )
    d.arrow(
        "transition",
        "cortex",
        ((850, 442), (850, 375), (442, 375)),
        "close / suspend → replan",
        (550, 367),
        optional=True,
    )
    d.text(
        32,
        1250,
        "Replan uses fresh Observation + retrieved context; continue "
        "retains a valid active contract.",
    )
    d.text(
        32,
        1280,
        "Process steps are not new Components or Registry edges. Status evidence: preferred pages.",
    )
    d.text(
        32,
        1310,
        "No implemented screen-only full-loop claim. Ordinary death closes a Life Episode.",
    )
    return d.finish()


def interaction_svg(atlas: Atlas) -> bytes:
    declared = {(e.source, e.relation, e.target) for e in atlas.relationships}
    selected = {e for _, edges in INTERACTION_PANELS for e in edges}
    if not selected <= declared:
        raise ProjectionError("Phase-D interaction subset changed; review required")
    d = Drawing(
        "Interaction Map · three exact mechanisms",
        1880,
        "14 Registry triples · consumes is actor → payload · full 47-row ledger in Markdown",
    )
    for panel, (title, edges) in enumerate(INTERACTION_PANELS):
        top = 130 + panel * 540
        d.text(32, top, title, size=22, bold=True)
        if panel < 2:
            ids = (
                (
                    "CMP-MEM-RETRIEVAL",
                    "IF-MEM-CORTEX",
                    "CMP-CORTEX",
                    "CON-PLANNER-OUTPUT",
                    "CMP-MANAGER",
                )
                if panel == 0
                else (
                    "CMP-MANAGER",
                    "CON-SKILL-CONTRACT",
                    "CMP-BODY",
                    "CON-PRIMITIVE-ACTION",
                    "CMP-INPUT-EXECUTOR",
                )
            )
            positions = (
                (32, top + 26),
                (572, top + 26),
                (32, top + 186),
                (572, top + 186),
                (32, top + 346),
            )
            for identity, (x, y) in zip(ids, positions, strict=True):
                n = atlas.entities[identity]
                d.box(
                    f"p{panel}-{identity}",
                    x,
                    y,
                    n.name,
                    (identity, n.type),
                    width=356,
                    identity=identity,
                    color="blue" if n.type == "Component" else "green",
                )
            routes = (
                (
                    (((388, top + 82), (572, top + 82)), (433, top + 73)),
                    (
                        ((388, top + 214), (470, top + 214), (470, top + 116), (572, top + 116)),
                        (403, top + 190),
                    ),
                    (((388, top + 242), (572, top + 242)), (433, top + 233)),
                    (
                        ((388, top + 402), (515, top + 402), (515, top + 278), (572, top + 278)),
                        (404, top + 387),
                    ),
                    (((210, top + 298), (210, top + 346)), (230, top + 330)),
                )
                if panel == 0
                else (
                    (((388, top + 82), (572, top + 82)), (433, top + 73)),
                    (
                        ((388, top + 198), (572, top + 120)),
                        (415, top + 144),
                    ),
                    (
                        ((572, top + 136), (388, top + 228)),
                        (470, top + 202),
                    ),
                    (((388, top + 242), (572, top + 242)), (433, top + 233)),
                    (
                        ((388, top + 402), (515, top + 402), (515, top + 278), (572, top + 278)),
                        (404, top + 387),
                    ),
                )
            )
        else:
            ids = (
                "CMP-INDEPENDENT-VERIFIER",
                "CON-VERIFIER-RESULT",
                "CMP-MANAGER",
                "CMP-MEMORY",
                "CMP-REPLAY-BUFFER",
            )
            positions = (
                (32, top + 26),
                (572, top + 26),
                (32, top + 166),
                (32, top + 306),
                (32, top + 446),
            )
            for identity, (x, y) in zip(ids, positions, strict=True):
                n = atlas.entities[identity]
                d.box(
                    f"p{panel}-{identity}",
                    x,
                    y,
                    n.name,
                    (identity, n.type),
                    width=356,
                    identity=identity,
                    color="blue" if n.type == "Component" else "green",
                )
            routes = ((((388, top + 82), (572, top + 82)), (433, top + 73)),)
            routes += tuple(
                (
                    (
                        (388, top + 222 + 140 * r),
                        (620 + 110 * r, top + 222 + 140 * r),
                        (620 + 110 * r, top + 138),
                    ),
                    (430, top + 213 + 140 * r),
                )
                for r in range(3)
            )
        for (source, relation, target), (points, at) in zip(edges, routes, strict=True):
            d.arrow(source, target, points, relation, at, relation=relation)
    d.text(32, 1820, "Shared payloads imply no additional direct Component edges or authority.")
    d.text(
        32,
        1850,
        "Declarations do not certify execution, fact admission, training "
        "or scientific effectiveness.",
    )
    return d.finish()


def experience_svg() -> bytes:
    d = Drawing(
        "Experience to Knowledge · three separate processes",
        1470,
        "Evidence revision ≠ Life Episode continuity ≠ optional parameter training",
    )
    panels = (
        (
            "Within one Mission Run · knowledge revision",
            "green",
            (
                (
                    "evidence",
                    "Visible evidence",
                    ("IDs, admissibility, provenance", "No hidden-state facts"),
                ),
                (
                    "request",
                    "Hypothesis / update request",
                    ("MemoryUpdateRequest / post-mortem", "Proposal is not an accepted fact"),
                ),
                (
                    "admission",
                    "Consolidation / Admission",
                    ("Design-open ownership and policy", "No automatic fact gate"),
                ),
                (
                    "memory",
                    "Memory revision → retrieval",
                    ("Evidence-linked state can evolve", "Bounded context for later Cortex"),
                ),
            ),
        ),
        (
            "Same Mission Run · Life Episode continuity",
            "blue",
            (
                (
                    "episode1",
                    "Life Episode ends",
                    ("Ordinary death / episode stop", "Does not itself end Mission Run"),
                ),
                (
                    "continuity",
                    "Post-mortem / continuity",
                    ("Preserve admissible evidence", "Memory retains provenance"),
                ),
                (
                    "episode2",
                    "Permitted Life Episode restart",
                    ("Same frozen model, prompt, Body", "No parameter / weight refresh"),
                ),
            ),
        ),
        (
            "Between Mission Runs · optional learning",
            "purple",
            (
                (
                    "terminal",
                    "Mission Run terminal",
                    ("Close records; audit eligibility", "Learning needs separate authorization"),
                ),
                (
                    "candidate",
                    "Eligible replay → candidate",
                    ("Train between Mission Runs only", "Held-out validation; certify / reject"),
                ),
                (
                    "next",
                    "Independent next Mission Run",
                    (
                        "Certified candidate or eligible prior Body",
                        "Fresh state; no automatic memory transfer",
                    ),
                ),
            ),
        ),
    )
    for p, (title, color, boxes) in enumerate(panels):
        top = 128 + p * 442
        d.text(32, top, title, size=22, bold=True)
        # Four knowledge steps form two rows; other lanes have three vertical steps.
        if p == 0:
            locations = ((32, top + 24), (568, top + 24), (568, top + 208), (32, top + 208))
            for (key, name, lines), (x, y) in zip(boxes, locations, strict=True):
                d.box(key, x, y, name, lines, color=color)
            d.arrow("evidence", "request", ((392, top + 80), (568, top + 80)))
            d.arrow("request", "admission", ((748, top + 136), (748, top + 208)), optional=True)
            d.arrow("admission", "memory", ((568, top + 264), (392, top + 264)), optional=True)
            d.text(
                32,
                top + 366,
                "Hypotheses remain hypotheses until independently supported and reviewed.",
            )
        else:
            for row, (key, name, lines) in enumerate(boxes):
                d.box(key, 32, top + 24 + row * 128, name, lines, width=620, color=color)
                if row:
                    d.arrow(
                        boxes[row - 1][0],
                        key,
                        ((342, top + 8 + row * 128), (342, top + 24 + row * 128)),
                        optional=p == 2,
                    )
            if p == 2:
                d.arrow(
                    "terminal",
                    "next",
                    ((652, top + 80), (890, top + 80), (890, top + 336), (652, top + 336)),
                    "no retraining",
                    (724, top + 198),
                    optional=True,
                )
            else:
                d.text(682, top + 180, "Restart is conditional.")
                d.text(682, top + 210, "Mission Run remains")
                d.text(682, top + 240, "the experiment unit.")
    d.text(
        32,
        1440,
        "Memory history transfer across independent runs requires a separately accepted protocol.",
    )
    return d.finish()


def experiment_svg() -> bytes:
    d = Drawing(
        "Scientific Experiment · units and provenance",
        1190,
        "Accepted Mission Run / Life Episode overlay · explanation, no executed experiment",
    )
    d.box(
        "protocol",
        32,
        112,
        "Study version / frozen protocol",
        (
            "Treatment, comparator, endpoint, eligibility, budgets",
            "This diagram does not create a new scientific freeze",
        ),
        width=896,
    )
    d.box(
        "screen",
        32,
        266,
        "screen-only cohort",
        ("Primary official cohort", "Pixels / OCR; isolated local inference"),
        width=410,
    )
    d.box(
        "bridge",
        518,
        266,
        "bridge-assisted cohort",
        ("Separate diagnostic cohort", "Allowlisted, simultaneously visible data"),
        width=410,
        color="orange",
    )
    d.text(
        32,
        420,
        "Never pool cohorts. Debug / networked / contaminated records stay separately classified.",
    )
    d.parts.append(
        '<rect x="32" y="460" width="896" height="472" rx="16" '
        'fill="#F3F8FD" stroke="#2D6994" stroke-width="2"/>'
    )
    d.text(52, 498, "Mission Run · independent outer experiment unit", size=23, bold=True)
    d.text(
        52,
        535,
        "Frozen: model, prompt, Body weights/version, run mode, manifest and declared budgets.",
    )
    d.text(
        52,
        565,
        "Mutable: admissible evidence, hypotheses, strategies and "
        "contract state; no silent expansion.",
    )
    for n, x in enumerate((52, 518), 1):
        d.parts.append(
            f'<rect x="{x}" y="592" width="390" height="254" rx="12" '
            'fill="#FFFFFF" stroke="#26776D" stroke-width="2"/>'
        )
        d.text(
            x + 16,
            624,
            f"Life Episode {n}" + (" · if permitted" if n == 2 else ""),
            size=21,
            bold=True,
        )
        d.box(
            f"contract{n}",
            x + 16,
            650,
            "Grounded Skill Contract",
            ("Bounded targets, actions, stop criteria",),
            width=358,
            height=184,
            color="green",
        )
        d.box(
            f"action{n}",
            x + 36,
            756,
            "Primitive action",
            ("Only inside an active contract",),
            width=318,
            height=72,
        )
    d.text(
        52,
        888,
        "Death closes the Life Episode. Restart preserves this Mission Run's frozen identity.",
    )
    d.text(
        32,
        978,
        "Terminal condition → eligibility audit → analysis at Mission Run level.",
        size=20,
        bold=True,
    )
    d.text(
        32,
        1016,
        "Provenance: observation/evidence IDs, actions/rejections, "
        "contracts, outcomes, version hashes.",
    )
    d.text(
        32,
        1046,
        "Missing mandatory provenance blocks eligibility. Process "
        "restart needs continuity evidence.",
    )
    d.text(
        32,
        1090,
        "Next independent Mission Run: fresh experimental state; no automatic memory inheritance.",
    )
    d.text(
        32,
        1132,
        "Research originals are authored once; generated Component "
        "projections are links, not findings.",
    )
    d.text(
        32,
        1162,
        "Research Steering / Literature Inspection retain claim and source authority boundaries.",
    )
    return d.finish()


def svg_assets(atlas: Atlas) -> dict[PurePosixPath, bytes]:
    payloads = (
        overview_svg(),
        architecture_svg(atlas),
        interaction_svg(atlas),
        experience_svg(),
        experiment_svg(),
    )
    return {
        PRODUCT / "Diagrams" / (name + ".svg"): data
        for name, data in zip(SVG_NAMES, payloads, strict=True)
    }


def execution_mermaid() -> str:
    """Main sequence with separate continuation, stop, replan and restart paths."""
    sections = (
        (
            "Main sequence",
            """flowchart TD
    capture["GameInstance / visible capture"]
    firewall["No-Spoiler Firewall"]
    context["Observation + bounded Memory Retrieval"]
    cortex["Event-driven Cortex intention"]
    manager["Manager validates and grounds"]
    contract["Active bounded Skill Contract"]
    body["Body / eligible Reflex"]
    safety["Safety / focus / mask / rate / stop / logging"]
    execute["InputExecutor: guarded input"]
    outcome["New visible Observation"]
    verifier["Independent Verifier"]
    result["VerifierResult + evidence"]
    evaluate["Manager transition"]
    capture --> firewall
    firewall --> context
    context --> cortex
    cortex --> manager
    manager --> contract
    contract --> body
    body --> safety
    safety --> execute
    execute --> outcome
    outcome --> verifier
    verifier --> result
    result --> evaluate""",
        ),
        (
            "Continue a valid active contract",
            """flowchart TD
    evaluate["Manager evaluates VerifierResult"]
    valid{"Contract remains valid?"}
    body["Continue Body within active contract"]
    close["Close / suspend before any replan"]
    evaluate --> valid
    valid -->|"yes: same permissions and budget"| body
    valid -->|"no"| close""",
        ),
        (
            "Stop and rejected input",
            """flowchart TD
    firewall["Firewall: forbidden access"]
    reject["Integrity stop / log rejection"]
    manager["Manager: unsafe / ambiguous / unavailable"]
    safety["Safety: no focus / unsafe / unloggable"]
    body["Body / Reflex stop signal"]
    close["Manager closes / suspends active contract"]
    stop["No executed action for a rejected proposal"]
    firewall --> reject
    manager --> reject
    safety --> reject
    body --> close
    reject --> close
    close --> stop""",
        ),
        (
            "Conditional replan",
            """flowchart TD
    evaluate["Manager: terminal contract / failure / contradiction"]
    close["Manager closes / suspends prior contract"]
    context["Fresh admissible Observation + retrieval"]
    cortex["New Cortex intention"]
    manager["Manager validates anew"]
    evaluate --> close
    close -->|"nonterminal, nondeath replan event"| context
    context --> cortex
    cortex --> manager""",
        ),
        (
            "Life Episode restart and independent Mission Runs",
            """flowchart TD
    close["Manager closes active contract"]
    episode["Visible death: close Life Episode / post-mortem"]
    context["New Observation; admissible Memory continuity"]
    terminal["Mission Run closed; eligibility audit"]
    next["Independent next Mission Run: fresh state / identity"]
    learn["Eligible replay / candidate / held-out validation / certification"]
    close --> episode
    episode -->|"permitted restart; same Mission Run / frozen Body"| context
    close -->|"declared Mission Run terminal condition"| terminal
    episode -->|"declared Mission Run terminal condition"| terminal
    terminal -->|"already eligible Body; no retraining"| next
    terminal -.->|"between Mission Runs; separately authorized"| learn
    learn -.->|"activate certified candidate only"| next
    learn -.->|"candidate rejected; retain eligible prior Body"| next""",
        ),
    )
    return "\n\n".join(f"## {title}\n\n```mermaid\n{code}\n```" for title, code in sections)


def primary_pages(files: dict[PurePosixPath, bytes]) -> dict[PurePosixPath, str]:
    """Deterministic, presentation-only diagram projection."""
    diagrams = PRODUCT / "Diagrams"
    result = {}
    for title in ("System Overview", "Experience to Knowledge", "Scientific Experiment"):
        path = PRODUCT / "Guides" / (title + ".md")
        body = files[path].decode()
        at = body.index("\n## ")
        panel = (
            f"\n## Diagram\n\n![[{diagrams / (title + '.svg')}|960]]\n\n"
            f"[[{diagrams / (title + '.svg')}|Open full-size SVG]] · "
            "[[Research Map/Diagrams/Execution Flow|Execution Flow]] · "
            "[[Research Map/Diagrams/Architecture Tree|Architecture Tree]] · "
            "[[Research Map/Diagrams/Interaction Map|Interaction Map]]\n\n" + LEGEND + "\n\n"
            "Caption: "
            + {
                "System Overview": (
                    "Follow the main path, then the visible outcome back to Manager. "
                    "Retrieval and conditional replan are separate paths."
                ),
                "Experience to Knowledge": (
                    "Read the three lanes separately: knowledge revision, same-run "
                    "continuity and optional between-run learning."
                ),
                "Scientific Experiment": (
                    "Nesting identifies the experimental unit; cohorts remain "
                    "separate. Source-backed Guide text and ordinary identity links "
                    "follow."
                ),
            }[title]
            + "\n"
        )
        result[path] = body[:at] + panel + body[at:]
    path = diagrams / "Architecture Tree.md"
    body = files[path].decode()
    start = body.index("## Visual tree")
    stop = body.index("## Linked Markdown tree")
    result[path] = (
        body[:start]
        + (
            "## Visual tree\n\n"
            f"[[{diagrams / 'Architecture Tree.svg'}|Open full-size SVG and zoom]] — "
            "large technical reference; open the asset and zoom to read i"
            "ndividual branches. "
            "The complete linked Markdown tree below is the normal identi"
            "ty navigation fallback.\n\n"
            "One connected top-down System root, 28 unique Components and"
            " 28 exact `part_of` edges. "
            "Drawn parent → child; Registry declaration is child `part_of"
            "` parent. "
            "Siblings have no runtime ordering. No functional area become"
            "s a parent.\n\n"
            "![[Research Map/Diagrams/Architecture Tree.svg]]\n\n" + LEGEND + "\n\n"
            "[[Research Map/Guides/System Overview|System Overview]] · "
            "[[Research Map/Diagrams/Architecture Tree.canvas|Secondary h"
            "istorical Canvas]]\n\n"
        )
        + body[stop:]
    )
    path = diagrams / "Interaction Map.md"
    body = files[path].decode()
    # Keep full authority/source explanation and the exact linked ledger bytes.
    start = body.index("## Reading the map")
    stop = body.index("## Coverage")
    ledger = body[body.index("## Complete linked relation ledger") :]
    explanation = body[start:stop].replace(
        "Native Obsidian Mermaid requires no community plugin.",
        "SVG needs no community plugin; ordinary Markdown links are the identity navigation.",
    )
    result[path] = body[: body.index("# Interaction Map")] + (
        "# Interaction Map\n\n[[Research Map Home|Home]] · "
        "[[Research Map/Guides/System Overview|System Overview]] · "
        "[[#Complete linked relation ledger|Complete linked relation "
        "ledger]]\n\n"
        "![[Research Map/Diagrams/Interaction Map.svg|960]]\n\n"
        "[[Research Map/Diagrams/Interaction Map.svg|Open full-size SVG]] · "
        "[[Research Map/Diagrams/Interaction Map.canvas|Secondary his"
        "torical Canvas]]\n\n"
        "Caption: three Phase-D mechanisms show 14 exact Registry triples. "
        "`consumes` always points actor → payload, even against intui"
        "tive data flow. "
        "Shared payloads add no direct actor edges.\n\n"
        + LEGEND
        + "\n\n"
        + explanation
        + "## Coverage\n\nPrimary SVG: 14 selected triples in three mecha"
        "nism panels. "
        "The complete unchanged ledger contains 47 directed typed relations. "
        "The secondary Canvas retains the larger Registry projection.\n\n" + ledger
    )
    path = diagrams / "Execution Flow.md"
    body = files[path].decode()
    intro = body[body.index("## Normative control lifecycle") : body.index("```mermaid")]
    fallback = body[body.index("Legend: rectangles") :]
    result[path] = body[: body.index("# Ablaufdiagramm")] + (
        "# Execution Flow\n\n[[Research Map Home|Home]] · "
        "[[Research Map/Guides/System Overview|System Overview]] · "
        "[[#Markdown fallback|Markdown fallback]] · "
        "[[#Current implementation and preferred pages|Implementation"
        " and preferred pages]]\n\n"
        "Follow the main sequence first; continue, stop, replan and r"
        "estart have separate diagrams. "
        "Each panel is a normative process, not a Registry relation o"
        "r executed trace.\n\n"
        "[[Research Map/Diagrams/Execution Flow.canvas|Secondary hist"
        "orical Canvas]]\n\n" + LEGEND + "\n\n" + intro + execution_mermaid() + "\n\n" + fallback
    )
    path = PRODUCT / "Guides/Using the Research Map.md"
    body = files[path].decode()
    for title in ("Architecture Tree", "Execution Flow", "Interaction Map"):
        body = body.replace(
            f"[[{diagrams / (title + '.canvas')}|Open Canvas]]",
            f"[[{diagrams / (title + '.canvas')}|Secondary Canvas]]",
        )
    body = body.replace("Ablaufdiagramm", "Execution Flow")
    body = body.replace(
        " and linked Markdown fallback.",
        " and linked Markdown fallback. Open the full-size SVG to zoom.",
    )
    result[path] = body.replace(
        "Navigate System → Component",
        "Start with [[Research Map/Guides/System Overview|System Overview]], "
        "[[Research Map/Guides/Scientific Experiment|Scientific Exper"
        "iment]] or a"
        " direct Component page.\n\n" + LEGEND + "\n\nNavigate System → Component",
    )
    path = PurePosixPath("Research Map Home.md")
    body = files[path].decode()
    for title in ("Architecture Tree", "Execution Flow", "Interaction Map"):
        body = body.replace(f" · [[{diagrams / (title + '.canvas')}|Open Canvas]]", "")
    body = body.replace("Ablaufdiagramm", "Execution Flow")
    body = body.replace(
        "Component routes below remain direct entry points.",
        "[[Research Map/Diagrams/Execution Flow|Execution Flow]] "
        "explains authorization and recovery. [[#Components|Direct "
        "Component entry]] stays available without a required tutorial.",
    )
    body = body.replace("## Inspect sources", "## Inspect sources and evidence")
    body = body.replace(
        "and linked ledger for exact structure and relations.",
        "and linked ledger for exact structure and relations.\n\n"
        "[[Research Map/Diagrams/Architecture Tree|Architecture Tree:"
        " zoomable reference]] · "
        "[[Research Map/Diagrams/Interaction Map#Complete linked rela"
        "tion ledger|"
        "Complete interaction ledger]]",
    )
    result[path] = body
    return result


def secondary_canvases(files: dict[PurePosixPath, bytes]) -> dict[PurePosixPath, bytes]:
    result = {}
    for title in ("Architecture Tree", "Execution Flow", "Interaction Map"):
        path = PRODUCT / "Diagrams" / (title + ".canvas")
        canvas = json.loads(files[path])
        legend = next(n for n in canvas["nodes"] if n.get("type") == "text")
        legend["text"] = (
            f"**Secondary historical Canvas** · [[Research Map/Diagrams/{title}|"
            f"Open primary {title} page]]\n\n" + legend["text"]
        )
        # Allow the additional caption without changing any nodes/relations.
        legend["height"] += 64
        result[path] = (
            json.dumps(canvas, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
    return result
