"""Phase-D presentation only; process arrows never create Registry facts.

The tree is a pinned DOT→SVG render. Other panels reuse the supplied palette
with explicit geometry. Generation requires no renderer dependency or I/O.
"""

import hashlib
import json
import textwrap
from html import escape
from pathlib import PurePosixPath

from .anatomy import _arrow, _shape, _text_item
from .preferred_paths import PRODUCT, preferred_paths
from .private_projection import OWNER, REPOSITORY, ProjectionError, markdown_parts, yaml_text
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
        "transition",
        "contract",
        ((530, 535), (490, 535), (490, 665), (442, 665)),
        "continue same active",
        (505, 582),
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
    game["GameInstance: visible environment response"]
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
    execute --> game
    game --> outcome
    outcome --> verifier
    verifier --> result
    result --> evaluate""",
        ),
        (
            "Continue a valid active contract",
            """flowchart TD
    evaluate["Manager evaluates VerifierResult"]
    valid{"Contract remains valid?"}
    contract["Same still-active Contract"]
    body["Body continues within that same contract"]
    close["Close / suspend before any replan"]
    evaluate --> valid
    valid -->|"yes: same permissions and budget"| contract
    contract --> body
    valid -->|"no"| close""",
        ),
        (
            "Stop and rejected input",
            (
                (
                    "Before contract authorization",
                    """flowchart TD
    manager["Manager rejects proposal"]
    reject["Log rejection reason"]
    unauthorized["No contract / no new action"]
    manager --> reject
    reject --> unauthorized""",
                    "Unsafe, ambiguous or unavailable proposals are rejected before authorization. "
                    "No new action is authorized; retain prior history.",
                ),
                (
                    "During an active contract",
                    """flowchart TD
    safety["Safety stop"]
    body["Body / Reflex stop"]
    block["Block further input now"]
    close["Manager closes / suspends"]
    history["Retain steps and evidence"]
    safety --> block
    body --> block
    block --> close
    close --> history""",
                    "No focus, unsafe input or unavailable durable logging blocks further input "
                    "immediately, as does a Body / Reflex stop signal. Manager closes or suspends "
                    "the current contract; prior executed steps and evidence remain logged.",
                ),
                (
                    "Firewall or emergency stop",
                    """flowchart TD
    firewall["Firewall incident"]
    emergency["Emergency stop"]
    inhibit["Inhibit input; log incident"]
    present{"Active contract?"}
    block["Active stop path above"]
    unauthorized["No contract / no new action"]
    firewall --> inhibit
    emergency --> inhibit
    inhibit --> present
    present -->|"yes"| block
    present -->|"no"| unauthorized""",
                    "Forbidden access is an integrity incident. Firewall and emergency stops "
                    "inhibit input immediately and log the incident. If a contract is active, "
                    "follow the active stop path above; otherwise no new action is authorized. "
                    "Both paths retain prior history and evidence.",
                ),
            ),
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
            (
                (
                    "Life Episode closure and restart",
                    """flowchart TD
    close["Manager closes contract"]
    episode["Close Life Episode"]
    terminal{"Run terminal?"}
    context["Same-run restart"]
    audit["Mission Run closed"]
    close --> episode
    episode --> terminal
    terminal -->|"no; restart permitted"| context
    terminal -->|"yes"| audit""",
                    "Visible death closes the Life Episode with evidence and post-mortem. "
                    "A permitted restart in a nonterminal Mission Run uses a new Observation "
                    "and admissible Memory continuity: same Mission Run, same frozen identities "
                    "and Body weights. No model/controller replacement occurs between Life "
                    "Episodes. Death, ordinary failure or timeout alone is not a Run terminal. "
                    "Only declared Mission Run terminal conditions close the run, including "
                    "a terminal without death after Manager closes the active contract. "
                    "Application restart requires identity/provenance continuity "
                    "or stops/quarantines.",
                ),
                (
                    "Mission Run closure and independent next run",
                    """flowchart TD
    terminal["Declared Run terminal"]
    close["Manager closes contract"]
    audit["Eligibility audit"]
    next["Next independent Mission Run"]
    terminal --> close
    close --> audit
    audit -->|"eligible prior Body"| next""",
                    "A declared terminal condition closes the Mission Run whether or not death "
                    "occurred; Manager closes any active contract before the eligibility audit. "
                    "An independently eligible next Mission Run can use the already eligible "
                    "Body without retraining. It has protocol-defined fresh experimental state, "
                    "a new identity/manifest and independently frozen identities; Memory "
                    "inheritance and automatic run start are not authorized.",
                ),
                (
                    "Optional between-Mission-Run learning",
                    """flowchart TD
    terminal["Mission Run closed"]
    replay["Admissible replay"]
    train["Train candidate"]
    validate["Held-out validation"]
    certify{"Certify candidate?"}
    activate["Certified version only"]
    retain["Retain eligible prior Body"]
    terminal -.->|"separate authorization"| replay
    replay -.-> train
    train -.-> validate
    validate -.-> certify
    certify -.->|"certified"| activate
    certify -.->|"rejected"| retain""",
                    "This optional future protocol operates only between Mission Runs: collect "
                    "admissible experience with frozen Body vN, verifier-labelled replay / "
                    "demonstrations, train a candidate, perform held-out validation and "
                    "safety/false-success checks, then certify or reject. Only a certified "
                    "candidate may activate for the next independently eligible Mission Run. "
                    "A rejected candidate never activates; the eligible prior Body remains "
                    "available for the independent-run path above. Neither episode restart "
                    "nor knowledge revision activates a candidate.",
                ),
            ),
        ),
    )
    rendered = []
    for title, content in sections:
        if isinstance(content, str):
            body = f"```mermaid\n{content}\n```"
        else:
            body = "\n\n".join(
                f"### {subtitle}\n\n```mermaid\n{code}\n```\n\n{caption}"
                for subtitle, code, caption in content
            )
        rendered.append(f"## {title}\n\n{body}")
    return "\n\n".join(rendered)


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
            f"[[{diagrams / 'Architecture Tree.svg'}|Open SVG structural reference]] · "
            "[[Research Map/Diagrams/Architecture Tree.canvas|Open Canvas to pan/zoom]] · "
            "[[#Linked Markdown tree|Complete linked Markdown hierarchy]]\n\n"
            "For readable branch details, open the secondary historical Canvas, use its "
            "native zoom controls and pan between identity cards. The Canvas repeats the "
            "System root in branch-local panels; these are repeated occurrences of one "
            "identity, not the single-root technical tree. The primary SVG below is the "
            "accurate single-root structural reference; native SVG enlargement is not "
            "verified. The complete linked Markdown hierarchy provides normal identity "
            "navigation.\n\n"
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
        " and linked Markdown fallback. For hierarchy details, "
        "[[Research Map/Diagrams/Architecture Tree.canvas|Open Canvas to pan/zoom]]; "
        "its historical branch panels repeat the System root. The primary SVG is the "
        "single-root reference; native SVG enlargement is not verified.",
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
        " hierarchy and detail routes]] · "
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


# Optional Excalidraw drill-down, migrated from the approved isolated generator.
CANDIDATE_EXCALIDRAW = PRODUCT / "Diagrams/System Overview.excalidraw.md"
CANDIDATE_DRAWIO = PRODUCT / "Diagrams/Grounded Contract.drawio"
COUNTERPARTS = PRODUCT / "Guides/System Overview.md"
# Process arrows are explanatory chronology, NEVER additional Registry triples.
BOXES = (
    ("observation", "DAT-OBSERVATION", 40, 180, "Observation", "Sichtbare Angaben + Belege"),
    ("cortex", "CMP-CORTEX", 40, 330, "Cortex", "Ziel vorschlagen; keine Tasten"),
    ("manager", "CMP-MANAGER", 40, 480, "Manager", "Prüfen · grounden · erlauben"),
    (
        "contract",
        "CON-SKILL-CONTRACT",
        470,
        480,
        "Grounded Contract",
        "Ziel · Grenzen · Stop-Bedingung",
    ),
    ("body", "CMP-BODY", 900, 480, "Body / Bounded Reflex", "Nur im aktiven Contract handeln"),
    (
        "input",
        "CMP-INPUT-EXECUTOR",
        900,
        640,
        "Safety / Input",
        "Fokus · Maske · Rate · Notstopp · Log",
    ),
    ("game", "ENV-GAME-INSTANCE", 900, 800, "GameInstance", "Umgebung reagiert sichtbar"),
    (
        "new-observation",
        "DAT-OBSERVATION",
        470,
        800,
        "Neue Observation",
        "Frische sichtbare Belege",
    ),
    (
        "verifier",
        "CMP-INDEPENDENT-VERIFIER",
        40,
        800,
        "Independent Verifier",
        "Ergebnis unabhängig prüfen",
    ),
    (
        "result",
        "CON-VERIFIER-RESULT",
        40,
        640,
        "VerifierResult",
        "success · progress · failure · abstain",
    ),
    (
        "transition",
        "CMP-MANAGER",
        470,
        640,
        "Manager-Transition",
        "Fortsetzen · abschließen · stoppen",
    ),
    (
        "close",
        "CMP-MANAGER",
        470,
        330,
        "Schließen / suspendieren",
        "Erst danach bedingt neu planen",
    ),
    (
        "retrieval",
        "CMP-MEM-RETRIEVAL",
        470,
        180,
        "Memory Retrieval",
        "Begrenzter Kontext; keine Eingaben",
    ),
    ("memory", "CMP-MEMORY", 900, 180, "Memory", "Erfahrung + Herkunft bewahren"),
)
FLOWS = (
    ("observation", "cortex", ((200, 280), (200, 330)), ""),
    ("cortex", "manager", ((200, 430), (200, 480)), "Vorschlag"),
    ("manager", "contract", ((360, 530), (470, 530)), "Erlaubnis"),
    ("contract", "body", ((790, 530), (900, 530)), ""),
    ("body", "input", ((1060, 580), (1060, 640)), ""),
    ("input", "game", ((1060, 740), (1060, 800)), ""),
    ("game", "new-observation", ((900, 850), (790, 850)), ""),
    ("new-observation", "verifier", ((470, 850), (360, 850)), ""),
    ("verifier", "result", ((200, 800), (200, 740)), ""),
    ("result", "transition", ((360, 690), (470, 690)), "Ergebnis"),
    ("transition", "contract", ((630, 640), (630, 580)), "gültig"),
    ("transition", "close", ((790, 690), (840, 690), (840, 380), (790, 380)), "Stop / Replan"),
    ("close", "cortex", ((470, 380), (360, 380)), "bedingt"),
    ("memory", "retrieval", ((900, 230), (790, 230)), ""),
    (
        "retrieval",
        "cortex",
        ((470, 230), (410, 230), (410, 305), (200, 305), (200, 330)),
        "Kontext",
    ),
)
REGISTRY_TRIPLES = (
    ("CMP-CORTEX", "supplies", "IF-CORTEX-MANAGER"),
    ("CMP-MANAGER", "consumes", "IF-CORTEX-MANAGER"),
    ("CMP-MANAGER", "supplies", "CON-SKILL-CONTRACT"),
    ("CMP-BODY", "executes", "CON-SKILL-CONTRACT"),
    ("CON-SKILL-CONTRACT", "constrains", "CMP-BODY"),
    ("CMP-INDEPENDENT-VERIFIER", "supplies", "CON-VERIFIER-RESULT"),
    ("CMP-MANAGER", "consumes", "CON-VERIFIER-RESULT"),
)


def _excalidraw(atlas: Atlas) -> bytes:
    paths = preferred_paths(atlas)
    elements = [
        _text_item("slice-title", "VOM SEHEN ZUR NÄCHSTEN ENTSCHEIDUNG", 40, 30, 1200, size=32),
        _text_item(
            "slice-subtitle",
            "Soll-Zyklus · jeder Versuch bleibt begrenzt · unabhängige Prüfung",
            40,
            85,
            1200,
            size=22,
        ),
    ]
    for key, identity, x, y, title, detail in BOXES:
        link = f"[[{paths[identity].with_suffix('')}]]"
        color = "#EAF4F0" if key in {"memory", "retrieval"} else "#EDF3FA"
        elements += [
            _shape(
                key,
                (x, y, 320, 100),
                background=color,
                stroke="#426B86",
                link=link,
                custom_data={"card": key, "identity": identity, "prototype": True},
            ),
            _text_item(
                key + "-title",
                title,
                x + 10,
                y + 12,
                300,
                size=20,
                link=link,
                custom_data={"card": key, "role": "title"},
            ),
            _text_item(
                key + "-detail",
                detail,
                x + 14,
                y + 52,
                292,
                size=17,
                custom_data={"card": key, "role": "detail"},
            ),
        ]
    for source, target, points, label in FLOWS:
        element = _arrow(
            source + ":" + target, points[0], points[-1], presentation_flow=(source, target)
        )
        element["points"] = [[x - points[0][0], y - points[0][1]] for x, y in points]
        element["width"] = max(x for x, _ in points) - min(x for x, _ in points)
        element["height"] = max(y for _, y in points) - min(y for _, y in points)
        element["strokeStyle"] = "dashed" if source in {"memory", "retrieval"} else "solid"
        elements.append(element)
        if label:
            x, y = points[0]
            # Place captions in open routing corridors, not over an arrow or node.
            label_positions = {
                ("cortex", "manager"): (235, 442),
                ("manager", "contract"): (372, 496),
                ("result", "transition"): (373, 655),
                ("transition", "contract"): (644, 601),
                ("transition", "close"): (854, 393),
                ("close", "cortex"): (374, 343),
                ("retrieval", "cortex"): (310, 285),
            }
            x, y = label_positions[source, target]
            elements.append(_text_item(source + target + "-caption", label, x, y, 120, size=16))
    for index, text in enumerate(
        (
            "Fortsetzung: nur durch denselben weiterhin aktiven Contract. "
            "Kein neuer Auftrag pro Schritt.",
            "Soll: Prozesspfeile sind keine Registry-Relationen. Ist: siehe verlinkte Seiten; "
            "keine zertifizierte Live-Schleife.",
            "Offen: gerankter Retrieval-Kontext, Consolidation und Admission. "
            "Body-Gewichte bleiben im Mission Run eingefroren.",
            "Stop blockiert weitere Eingaben; "
            "frühere ausgeführte Schritte und Belege bleiben erhalten.",
        )
    ):
        elements.append(_text_item(f"legend-{index}", text, 40, 960 + index * 37, 1200, size=18))
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "AGA #170 isolated prototype",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#FFFFFF", "gridSize": None},
        "files": {},
    }
    text = "---\nexcalidraw-plugin: parsed\ntags: [aga-reference-prototype]\n---\n\n"
    text += (
        "PROTOTYP — keine Produktionsintegration oder neue Architekturautorität.\n\n"
        "%%\n# Excalidraw Data\n\n## Text Elements\n\n"
    )
    text += "\n\n".join(f"{e['rawText']} ^{e['id']}" for e in elements if e["type"] == "text")
    text += "\n\n## Element Links\n\n" + "\n\n".join(
        f"{e['id']}: {e['link']}" for e in elements if e.get("link")
    )
    text += (
        "\n\n## Drawing\n```json\n"
        + json.dumps(scene, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n%%\n"
    )
    return text.encode()


def candidate_navigation(atlas: Atlas) -> str:
    """Ordinary, Vault-local counterparts, also available without either plugin."""
    paths = preferred_paths(atlas)

    def link(identity: str) -> str:
        return f"[[{paths[identity].with_suffix('')}|{atlas.entities[identity].name}]]"

    groups = (
        (
            "Beobachtung und Kontext",
            (
                "DAT-OBSERVATION",
                "CMP-MEMORY",
                "CMP-MEM-RETRIEVAL",
                "CMP-CORTEX",
            ),
        ),
        (
            "Vorschlag, Grounding und Erlaubnis",
            (
                "CMP-CORTEX",
                "CON-PLANNER-OUTPUT",
                "IF-CORTEX-MANAGER",
                "CMP-MANAGER",
                "CMP-MANAGER-GROUNDING",
                "CON-SKILL-CONTRACT",
            ),
        ),
        (
            "Ausführung und unabhängige Prüfung",
            (
                "CON-SKILL-CONTRACT",
                "CMP-BODY",
                "CMP-BOUNDED-REFLEX",
                "CMP-SAFETY-FILTER",
                "CMP-INPUT-EXECUTOR",
                "ENV-GAME-INSTANCE",
                "DAT-OBSERVATION",
                "CMP-INDEPENDENT-VERIFIER",
                "CON-VERIFIER-RESULT",
                "CMP-MANAGER",
            ),
        ),
        (
            "Ablehnung, Stop und bedingtes Replan",
            (
                "CMP-MANAGER",
                "CMP-EVIDENCE-LEDGER",
                "CMP-SAFETY-FILTER",
                "CMP-CORTEX",
            ),
        ),
    )
    lines = [
        "## Diagramm-Gegenstücke",
        "",
        "Agent Anatomy bleibt der primäre visuelle Einstieg. Die vertiefenden Ansichten "
        "erklären den Soll-Zyklus; sie belegen keine vollständige Live-Implementierung. "
        "Die folgenden gewöhnlichen Links öffnen die Identitäten in dieser Vault, "
        "auch ohne Diagrammplugins. Body und Bounded Reflex sowie SafetyFilter und "
        "InputExecutor haben jeweils getrennte Ziele.",
        "",
        "Observation → Cortex → Manager → aktiver begrenzter Contract → Body → "
        "geschützte Eingabe → GameInstance → neue Observation → Independent Verifier → "
        "VerifierResult → Manager. Fortsetzung führt ausschließlich über denselben "
        "weiterhin gültigen Contract. Schließen/Suspendieren geht bedingtem Replan voraus. "
        "Memory Retrieval liefert separat begrenzten Kontext; es autorisiert keine Eingaben.",
        "",
        "Die optionale Visible-State Bridge bleibt deny-by-default und unter dem "
        "No-Spoiler-Schutz; siehe die ursprünglichen Beobachtungsabschnitte. Body-Gewichte "
        "bleiben für den gesamten Mission Run einschließlich Life Episodes eingefroren. "
        "Training und Aktivierung brauchen ein künftiges autorisiertes Protokoll zwischen "
        "Mission Runs.",
        "",
    ]
    for title, identities in groups:
        lines += [f"### {title}", "", " · ".join(link(i) for i in identities), ""]
    lines += [
        "### Deklarierte technische Beziehungen",
        "",
        "Diese Beziehungen sind keine Zeitfolge: `consumes` zeigt vom Verbraucher "
        "zum Datenpaket. Prozesspfeile erzeugen keine Registry-Kanten.",
        "",
        "| Source | Relation | Target |",
        "| --- | --- | --- |",
    ]
    declared = {(e.source, e.relation, e.target) for e in atlas.relationships}
    if not set(REGISTRY_TRIPLES) <= declared:
        raise ProjectionError("Candidate relation differs from Registry")
    lines += [f"| {link(s)} | `{r}` | {link(t)} |" for s, r, t in REGISTRY_TRIPLES]
    lines += [
        "",
        "![[Research Map/Diagrams/System Overview.svg]]",
        "",
        "[[Research Map/Diagrams/Agent Anatomy.excalidraw|Agent Anatomy]] · "
        "[[Research Map/Diagrams/Execution Flow|Vollständiger Ablauf und Markdown-Fallback]] · "
        "[[Research Map/Diagrams/Interaction Map|Alle 47 technischen Beziehungen]]",
        "",
    ]
    return "\n".join(lines)


def candidate_system_overview(atlas: Atlas) -> bytes:
    """Final-path isolated Excalidraw trial; production adds its proven envelope."""
    paths = preferred_paths(atlas)
    text = _excalidraw(atlas).decode()
    scene = json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])
    for key, identities in (
        ("body", ("CMP-BODY", "CMP-BOUNDED-REFLEX")),
        ("input", ("CMP-SAFETY-FILTER", "CMP-INPUT-EXECUTOR")),
    ):
        title = next(
            e for e in scene["elements"] if e.get("customData") == {"card": key, "role": "title"}
        )
        scene["elements"].remove(title)
        x, y = title["x"], title["y"]
        for index, identity in enumerate(identities):
            scene["elements"].append(
                _text_item(
                    f"{key}-identity-{index}",
                    atlas.entities[identity].name,
                    x + index * 150,
                    y,
                    150,
                    size=17,
                    link=f"[[{paths[identity].with_suffix('')}]]",
                    custom_data={"card": key, "role": "identity", "identity": identity},
                )
            )
        shape = next(
            e
            for e in scene["elements"]
            if e.get("customData", {}).get("card") == key and e["type"] == "rectangle"
        )
        shape["link"] = f"[[{COUNTERPARTS.with_suffix('')}#Ausführung und unabhängige Prüfung]]"
        shape["customData"]["identities"] = list(identities)
        shape["customData"].pop("identity")
    text = "---\nexcalidraw-plugin: parsed\ntags: [aga-b2-isolated-candidate]\n---\n\n"
    text += "ISOLIERTER B2-KANDIDAT — noch kein verwaltetes Produktionsdiagramm.\n\n"
    text += candidate_navigation(atlas)
    # Pinned native serializer uses no blank after Text Elements. An extra
    # blank becomes part of the first label on save. Text heights are fractional
    # lineHeight products, not truncated preview estimates.
    for element in scene["elements"]:
        if element["type"] == "text":
            element["height"] = (
                len(element["text"].splitlines()) * element["fontSize"] * element["lineHeight"]
            )
    text += "\n%%\n# Excalidraw Data\n\n## Text Elements\n"
    text += "\n\n".join(
        f"{e['rawText']} ^{e['id']}" for e in scene["elements"] if e["type"] == "text"
    )
    text += "\n\n## Element Links\n\n" + "\n\n".join(
        f"{e['id']}: {e['link']}" for e in scene["elements"] if e.get("link")
    )
    text += "\n\n## Drawing\n```json\n" + json.dumps(
        scene, ensure_ascii=False, sort_keys=True, indent=2
    )
    text += "\n```\n%%\n"
    return text.encode()


def managed_system_overview(atlas: Atlas) -> bytes:
    """One proven Excalidraw surface; Drawio remains outside the owner inventory."""
    _, body = markdown_parts(candidate_system_overview(atlas).decode())
    body = body.replace(
        "ISOLIERTER B2-KANDIDAT — noch kein verwaltetes Produktionsdiagramm.",
        "Generierte erklärende Vertiefung — Agent Anatomy bleibt der primäre visuelle Hub.",
        1,
    ).replace('"source": "AGA #170 isolated prototype"', '"source": "research-atlas"', 1)
    properties = {
        "generated_by": OWNER,
        "source_repository": REPOSITORY,
        "atlas_workspace_generated": True,
        "atlas_visual_surface": "system-overview",
        "excalidraw-plugin": "parsed",
    }
    return ("---\n" + yaml_text(properties) + "---\n" + body).encode()
