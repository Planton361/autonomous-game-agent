"""Finite native Obsidian Graph projection; never a scientific master or renderer."""

import re
from dataclasses import dataclass, replace
from pathlib import PurePosixPath

from .private_projection import ProjectionError, markdown_parts, yaml_text
from .private_reference_index import (
    ReferenceIndex,
    component_navigation_rows,
    technical_attachment_rows,
)
from .research_presentation import eligible, literal, record_link
from .rq_presentation import RQReader
from .validator import Atlas
from .wiki_schema import EpistemicRecord, ResearchQuestion, Synthesis, Topic

ROOT = PurePosixPath("knowledge-graph/memory-retrieval")
DERIVED = PurePosixPath("_generated/derived")
PROFILE = ROOT / "Graph Profile.md"
AUDIT = ROOT / "Edge Audit.md"
DEFAULT_FILTER = f'path:"{DERIVED / ROOT / "nodes"}/"'
OVERLAY_FILTER = f'({DEFAULT_FILTER} OR path:"{DERIVED / ROOT / "optional-rq-overlay"}/")'
MEMORY = "CMP-MEM-RETRIEVAL"
OWNER = "research-wiki-derived"
SCOPES = PurePosixPath("knowledge-graph/components")
MODES = ("architecture", "knowledge-detail", "rq-overlay")


def scope_root(subject: str, mode: str = "architecture") -> PurePosixPath:
    if not re.fullmatch(r"CMP-[A-Z0-9]+(?:-[A-Z0-9]+)*", subject) or mode not in MODES:
        raise ProjectionError("Invalid Component graph scope/profile")
    return SCOPES / subject / mode


TYPES = {
    "paper": "Paper",
    "reading_note": "ReadingNote",
    "finding": "Finding",
    "synthesis": "Synthesis",
    "topic": "Topic",
}
PREFIXES = {
    "CMP": "Component",
    "SYS": "System",
    "WPAPER": "Paper",
    "READ": "ReadingNote",
    "WFIND": "Finding",
    "SYN": "Synthesis",
    "TOPIC": "Topic",
    "WRQ": "ResearchQuestion",
}


@dataclass(frozen=True, order=True)
class Node:
    identity: str
    title: str
    kind: str
    overlay: bool = False
    root: PurePosixPath = ROOT

    @property
    def path(self) -> PurePosixPath:
        # ID supplies uniqueness; human label is disposable presentation, never resolution.
        label = re.sub(r"[^\w .-]", " ", self.title, flags=re.UNICODE)
        label = " ".join(label.split()).strip(" .")[:50] or self.kind
        if self.root.is_relative_to(SCOPES):
            label = self.kind + " - " + label
        return (
            self.root
            / ("optional-rq-overlay" if self.overlay else "nodes")
            / f"{label} — {self.identity}.md"
        )


@dataclass(frozen=True, order=True)
class Declaration:
    source: str
    target: str
    property: str
    origin: str
    edge_class: str = "research / knowledge"


@dataclass(frozen=True)
class Projection:
    nodes: tuple[Node, ...]
    declarations: tuple[Declaration, ...]
    diagnostics: tuple[str, ...]
    root: PurePosixPath = ROOT
    scope: str = MEMORY
    mode: str = "pilot"

    def pairs(self, *, overlay: bool = True) -> dict[tuple[str, str], tuple[Declaration, ...]]:
        ids = {n.identity for n in self.nodes if overlay or not n.overlay}
        keys = sorted(
            {(d.source, d.target) for d in self.declarations if {d.source, d.target} <= ids}
        )
        return {
            key: tuple(d for d in self.declarations if (d.source, d.target) == key) for key in keys
        }


def project_graph(
    atlas: Atlas,
    reference: ReferenceIndex,
    reader: RQReader,
    *,
    scope: str | None = None,
    mode: str = "architecture",
) -> Projection:
    "Bounded accepted N-C prefixes plus one explicit join, never a recursive Research walk."
    subject = scope or MEMORY
    root = scope_root(subject, mode) if scope else ROOT
    if scope and (subject not in atlas.entities or atlas.entities[subject].type != "Component"):
        raise ProjectionError("Graph scope must be a current Component")
    # Explicit containment only. Ancestors orient; only selected subtree selects knowledge.
    subjects = {subject}
    if scope:
        subjects.update(
            ref
            for ref, entity in atlas.entities.items()
            if entity.type == "Component" and subject in atlas.ancestors(ref)
        )
    records = reader.by_id
    diagnostics: set[str] = set()

    def knowledge(ref: str) -> bool:
        record = records.get(ref)
        return record is not None and record.doc_type in TYPES and eligible(record)

    selected = set()
    direct = (r for r in technical_attachment_rows(reference) if r.target_identifier in subjects)
    for row in direct:
        if knowledge(row.source_wiki_id):
            selected.add(row.source_wiki_id)
    # Accepted finite N-C selection, not inherited Paper roles or shortcut graph edges.
    for row in (
        row for target in sorted(subjects) for row in component_navigation_rows(reference, target)
    ):
        ids = {row.navigation_start.identifier} | {
            ref
            for hop in row.via
            for ref in (hop.declaring_wiki_id, hop.declared_target_identifier)
        }
        if all(knowledge(ref) for ref in ids - subjects):
            selected.update(ids - subjects)
    core = frozenset(selected)
    # Exactly one schema-property join to the frozen core. Do not expand its other refs.
    for record in reader.records:
        if eligible(record) and (
            isinstance(record, Synthesis)
            and set(record.finding_refs) & core
            or isinstance(record, Topic)
            and (set(record.paper_refs) | set(record.finding_refs)) & core
        ):
            selected.add(record.wiki_id)
    anchors = {
        ref for ref in subjects if ref in atlas.entities and atlas.entities[ref].type == "Component"
    }
    declarations: set[Declaration] = set()
    for row in reference.rows:
        if row.row_kind != "declared-reference" or row.source_wiki_id not in selected:
            continue
        hop = row.via[0]
        target = hop.declared_target_identifier
        if row.path_eligible and hop.edge_id == "E9":
            node = atlas.entities.get(target)
            if node is not None and node.type == "Component":
                anchors.add(target)
                declarations.add(
                    Declaration(
                        row.source_wiki_id,
                        target,
                        hop.property,
                        f"{hop.edge_id}; {row.source_wiki_id} v{row.source_record_version}; "
                        f"row {row.row_id}",
                    )
                )
            else:
                diagnostics.add(
                    f"{row.source_wiki_id}: knowledge at another exact technical scope ({target}); "
                    "inspect exact attachment, no Component edge"
                )
        elif (
            row.path_eligible
            and hop.edge_id in {"E1", "E2", "E3", "E4", "E5"}
            and target in selected
        ):
            declarations.add(
                Declaration(
                    row.source_wiki_id,
                    target,
                    hop.property,
                    f"{hop.edge_id}; {row.source_wiki_id} v{row.source_record_version}; "
                    f"row {row.row_id}",
                )
            )
        else:
            diagnostics.add(
                f"{row.source_wiki_id}: {hop.property} → {target}; "
                "unresolved, excluded or outside bounded selection "
                f"({', '.join(row.diagnostic_codes) or 'not a projected edge'})"
            )
    for ref in sorted(selected):
        record = records[ref]
        fields = (
            ("finding_refs",)
            if isinstance(record, Synthesis)
            else ("paper_refs", "finding_refs")
            if isinstance(record, Topic)
            else ()
        )
        for field in fields:
            for target in sorted(set(getattr(record, field))):
                expected = "paper" if field == "paper_refs" else "finding"
                if target in core and records[target].doc_type == expected:
                    declarations.add(
                        Declaration(
                            ref,
                            target,
                            field,
                            f"{ref} v{record.record_version}; structured {field}",
                        )
                    )
                else:
                    diagnostics.add(
                        f"{ref}: {field} → {target}; "
                        "unresolved/wrong type or outside bounded core; no expansion"
                    )
    nodes = [Node(ref, records[ref].title, TYPES[records[ref].doc_type]) for ref in selected]
    nodes.extend(Node(ref, atlas.entities[ref].name, "Component") for ref in anchors)
    # Current 0.3 RQ-owned targets only. No literature/question membership inference.
    questions = [
        r
        for r in reader.records
        if isinstance(r, ResearchQuestion) and eligible(r) and set(reader.subjects(r)) & subjects
    ]
    if scope and mode != "rq-overlay":
        questions = []
    for rq in questions:
        nodes.append(
            Node(
                rq.wiki_id,
                "Research Question — " + (rq.presentation_question or rq.title),
                "ResearchQuestion",
                True,
            )
        )
        for target in reader.subjects(rq):
            if atlas.entities[target].type != "Component":
                diagnostics.add(
                    f"{rq.wiki_id}: exact {target} target retained in preferred RQ detail; "
                    "excluded technical anchor class"
                )
                continue
            if target not in anchors:
                anchors.add(target)
                nodes.append(Node(target, atlas.entities[target].name, "Component", True))
            declarations.add(
                Declaration(
                    rq.wiki_id,
                    target,
                    "research_direct_subject_refs",
                    f"{rq.wiki_id} v{rq.record_version}; RA-2 0.3 RQ-owned exact target",
                )
            )
    # Orientation only: explicit Registry containment closure, never Research inheritance.
    default_anchors = {n.identity for n in nodes if n.kind == "Component" and not n.overlay}
    default_skeleton = default_anchors | {
        ancestor for ref in default_anchors for ancestor in atlas.ancestors(ref)
    }
    skeleton = anchors | {ancestor for ref in anchors for ancestor in atlas.ancestors(ref)}
    nodes = [n for n in nodes if n.kind != "Component"]
    for ref in sorted(skeleton):
        entity = atlas.entities[ref]
        if entity.type not in {"Component", "System"}:
            raise ProjectionError("Invalid technical skeleton ancestor")
        nodes.append(Node(ref, entity.name, entity.type, ref not in default_skeleton))
    for edge in atlas.relationships:
        if edge.relation == "part_of" and {edge.source, edge.target} <= skeleton:
            declarations.add(
                Declaration(
                    edge.source,
                    edge.target,
                    "part_of",
                    f"public Registry relationship: {edge.source} part_of {edge.target}",
                    "technical skeleton",
                )
            )
    diagnostics.update(reader.diagnostics)
    if not selected:
        diagnostics.add(f"No matching documented knowledge in the bounded {subject} snapshot.")
    if scope and mode != "rq-overlay":
        diagnostics.add("RQ overlay OFF by default; choose the explicit rq-overlay profile.")
    elif not questions:
        diagnostics.add("RQ overlay: no eligible explicitly targeted current 0.3 questions.")
    if scope:
        # Orientation needs no detail edges between already attached objects. Retain
        # explicit links incident to otherwise unanchored knowledge; never infer E9.
        if mode != "knowledge-detail":
            attached = {
                d.source
                for d in declarations
                if d.target in anchors and d.edge_class == "research / knowledge"
            }
            declarations = {
                d
                for d in declarations
                if d.edge_class == "technical skeleton"
                or d.target in skeleton
                or d.source not in attached
                or d.target not in attached
            }
        nodes = [replace(n, root=root) for n in nodes]
    return Projection(
        tuple(sorted(nodes)),
        tuple(sorted(declarations)),
        tuple(sorted(diagnostics)),
        root,
        subject,
        mode if scope else "pilot",
    )


def is_graph_path(path: PurePosixPath) -> bool:
    if path.is_relative_to(SCOPES):
        parts = path.relative_to(SCOPES).parts
        if len(parts) not in {3, 4}:
            return False
        try:
            root = scope_root(parts[0], parts[1])
        except ProjectionError:
            return False
        return is_graph_path(ROOT / path.relative_to(root))
    if path in {PROFILE, AUDIT}:
        return True
    if path.parent not in {ROOT / "nodes", ROOT / "optional-rq-overlay"} or path.suffix != ".md":
        return False
    if len(path.name.encode()) > 240 or re.search(r'[<>:"/\\|?*\[\]#^\x00-\x1f]', path.name):
        return False
    return bool(
        re.fullmatch(
            r".+ — (CMP|SYS|WPAPER|READ|WFIND|SYN|TOPIC|WRQ)-[A-Z0-9]+(?:-[A-Z0-9]+)*", path.stem
        )
    )


def graph_metadata(text: str, path: PurePosixPath) -> dict:
    props, _ = markdown_parts(text)
    expected = {
        "generated_by",
        "graph_projection_version",
        "graph_path",
        "source_commit",
        "privacy",
        "export_policy",
    }
    companion = path.name in {"Graph Profile.md", "Edge Audit.md"}
    if not companion:
        expected |= {"graph_identity", "graph_class"}
    if set(props) != expected or not re.fullmatch(
        r"[0-9a-f]{40}", str(props.get("source_commit", ""))
    ):
        return {}
    if (
        not is_graph_path(path)
        or props.get("generated_by") != OWNER
        or props.get("graph_projection_version")
        != ("1.1" if path.is_relative_to(SCOPES) else "1.0")
        or props.get("graph_path") != str(path)
    ):
        return {}
    if props.get("privacy") != "private" or props.get("export_policy") != "deny":
        return {}
    if not companion:
        identity = path.stem.rsplit(" — ", 1)[1]
        if props.get("graph_identity") != identity or props.get("graph_class") != PREFIXES.get(
            identity.split("-")[0]
        ):
            return {}
        if identity.startswith("WRQ-") and path.is_relative_to(SCOPES):
            if path.relative_to(SCOPES).parts[1] != "rq-overlay":
                return {}
        if identity.startswith("WRQ-") and path.parent.name != "optional-rq-overlay":
            return {}
    return props


def render_graph(
    projection: Projection,
    commit: str,
    atlas: Atlas,
    records: tuple[EpistemicRecord, ...],
    locators: dict[str, PurePosixPath],
    preferred: dict[str, PurePosixPath],
) -> dict[PurePosixPath, bytes]:
    root = projection.root
    profile_path, audit_path = root / "Graph Profile.md", root / "Edge Audit.md"
    default_filter = f'path:"{DERIVED / root / "nodes"}/"'
    overlay_filter = f'({default_filter} OR path:"{DERIVED / root / "optional-rq-overlay"}/")'
    if projection.mode != "pilot":
        question_root = scope_root(projection.scope, "rq-overlay")
        overlay_filter = (
            f'(path:"{DERIVED / question_root / "nodes"}/" OR '
            f'path:"{DERIVED / question_root / "optional-rq-overlay"}/")'
        )
    question_group_root = root if projection.mode == "pilot" else question_root
    nodes = {n.identity: n for n in projection.nodes}
    if len(nodes) != len(projection.nodes):
        raise ProjectionError("Duplicate graph identity")
    pairs = projection.pairs()
    tree = {}

    def note(path: PurePosixPath, body: str, node: Node | None = None) -> bytes:
        if not is_graph_path(path):
            raise ProjectionError("Invalid finite graph path")
        metadata = dict(
            generated_by=OWNER,
            graph_projection_version="1.1" if root.is_relative_to(SCOPES) else "1.0",
            graph_path=str(path),
            source_commit=commit,
            privacy="private",
            export_policy="deny",
        )
        if node:
            metadata.update(graph_identity=node.identity, graph_class=node.kind)
        return ("---\n" + yaml_text(metadata) + "---\n" + body + "\n").encode()

    for identity, node in nodes.items():
        lines = [
            "# " + literal(node.title),
            "",
            "Generated-only disposable Graph proxy. Identity: " + identity + ".",
            "Class: "
            + node.kind
            + ("; optional question overlay, not established knowledge." if node.overlay else "."),
            "",
            (
                "Inspect identity "
                + identity
                + " in companion "
                + str(DERIVED / audit_path)
                + "; navigation is kept outside proxy topology. Use its exact affected "
                "Component routes and preferred/detail sources to return to Anatomy."
            ),
            "",
            "## Declared semantic links",
            "",
        ]
        for source, target in pairs:
            if source == identity:
                destination = nodes[target]
                # Link targets are closed generated paths. Labels cannot inject Markdown links.
                lines.append(
                    f"- [[{DERIVED / destination.path.with_suffix('')}|{destination.path.stem}]]"
                )
        tree[node.path] = note(node.path, "\n".join(lines), node)
    profile = [
        "# Knowledge Graph — "
        + literal(atlas.entities[projection.scope].name)
        + " / "
        + projection.mode,
        "",
        (
            "Bounded navigation projection only. Graph geometry, density and "
            "colors are not scientific authority."
        ),
        "",
        "## Graph profile",
        "",
        (
            "Scope: exact " + projection.scope + " N-C prefixes and direct attachments; "
            "one explicit Synthesis/Topic join to that core. Other Components "
            "appear through exact declarations or required part_of ancestry. Deep "
            "endpoints remain inspection only."
        ),
        "",
        (
            "Default classes: Component, System root context, Paper, ReadingNote, "
            "Finding, Synthesis, "
            "explicitly supported Topic. ResearchQuestion is OFF by default."
        ),
        "",
        (
            "Excluded: Decision/DecisionDraft, Issues/PRs, milestones, "
            "Project/control/orchestration, manifests/indexes/navigation, "
            "technical Evidence, raw SourceFamily/SourceVersion, "
            "Interface/Contract/DataArtifact/MeasurementPoint anchors, "
            "Domain/Function/Assembly, workbench/Canvas/Excalidraw duplicates."
        ),
        "",
        (
            "Component hierarchy provides orientation through explicit Registry part_of. "
            "Research objects remain attached only through explicit scientific declarations. "
            "Tree position does not infer scientific relevance. Overlay-only targets and "
            "their required ancestors appear only with the RQ overlay."
        ),
        "",
        "Native default filter:",
        "",
        "```text",
        default_filter,
        "```",
        "",
        "Explicit RQ overlay filter:",
        "",
        "```text",
        overlay_filter,
        "```",
        "",
        (
            "Manual activation: open native global Graph via the ribbon (not Local "
            "Graph). Open Graph settings → Filters → Search files; paste the "
            "default expression. Set Tags OFF, Attachments OFF, Existing files "
            "only ON, Orphans ON. Enable Arrows for declared direction. Replace "
            "Search files with the overlay expression to enable questions; restore "
            "the default expression to disable them."
        ),
        "",
        "Optional presentation Group for questions: "
        f'`path:"{DERIVED / question_group_root / "optional-rq-overlay"}/" file:"WRQ-"`. '
        "Choose any distinguishable color. Question filenames/classes remain explicit "
        "without color. Groups have no semantic meaning.",
        "",
        (
            "No Graph/workspace/settings file is generated; existing user settings "
            "remain untouched. Native Graph has no typed edge labels and may "
            "collapse reciprocal/parallel relationships visually. Edge Audit "
            "retains every declaration; force-layout positions are not "
            "reproducible semantics. Operator excluded-file patterns can hide "
            "nodes and must be inspected manually if expected nodes are absent."
        ),
        "",
        (
            "Open Edge Audit.md in this folder for the complete Markdown fallback, "
            "inventory and inspection routes."
        ),
    ]
    if projection.mode != "pilot":
        profile += [
            "",
            "## Scoped profile contract",
            "",
            "Primary reading order: System / Component skeleton → exact attached knowledge "
            "→ optional knowledge detail → explicit optional RQ questions.",
            "",
            "Selection: selected Component and explicit part_of subtree; ancestry only "
            "orients. Exact cross-component participants add ancestry, never siblings "
            "or other participants' Research. Accepted N-C prefixes and one explicit "
            "Synthesis/Topic join only; no recursive scientific closure.",
            "",
            "Mode: " + projection.mode + ". RQ OFF except in explicit rq-overlay mode.",
        ]
        if projection.mode == "rq-overlay":
            profile += ["", "For this explicit question profile use:", "", overlay_filter]
        profile += ["", "## Switch profile / Markdown fallback", ""]
        for mode in MODES:
            destination = scope_root(projection.scope, mode)
            profile.append(
                f"- [[{DERIVED / destination / 'Graph Profile'}|{mode}]] · "
                f"[[{DERIVED / destination / 'Edge Audit'}|Edge Audit / detail]]"
            )
    tree[profile_path] = note(profile_path, "\n".join(profile))
    body = profile[:3] + [
        "",
        "## Graph profile",
        "",
        (
            "Component hierarchy provides orientation through explicit Registry part_of. "
            "Research objects remain attached only through explicit scientific declarations. "
            "Tree position does not infer scientific relevance."
        ),
        "",
        "Default: " + default_filter,
        "",
        "RQ overlay (OFF by default): " + overlay_filter,
        "",
        (
            "Classes/exclusions and manual activation are in Graph Profile.md; "
            "only the two node folders enter the filters."
        ),
        "",
        "## Nodes",
        "",
        "| Node | Stable ID | Class | Profile |",
        "| --- | --- | --- | --- |",
    ]
    for node in projection.nodes:
        body.append(
            f"| {literal(node.title)} | {node.identity} | {node.kind} | "
            f"{'Optional RQ' if node.overlay else 'Default'} |"
        )
    body += [
        "",
        "## Edge Audit",
        "",
        (
            "One row per directed identity pair/internal proxy link. Multiple "
            "typed declarations for one pair share that link and retain all "
            "origins below. Native Graph does not display these project-specific "
            "typed names."
        ),
        "",
        "| From | Relation | To | Direction | Origin | Edge class |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for (source, target), declarations in pairs.items():
        relations = "; ".join(sorted({d.property for d in declarations}))
        origins = "; ".join(d.origin + " / " + d.property for d in declarations)
        classes = "; ".join(sorted({d.edge_class for d in declarations}))
        body.append(
            f"| {literal(nodes[source].title)} ({source}) | {relations} | "
            f"{literal(nodes[target].title)} ({target}) | {source} → {target} | "
            f"{origins} | {classes} |"
        )
    body += [
        "",
        "## Navigation / inspection",
        "",
        (
            "All return/source routes live here, outside both filtered node "
            "folders. Proxies contain no navigation links. Click a native Graph "
            "node, read its identity, then use this inventory to inspect the "
            "preferred/detail source."
        ),
        "",
    ]
    by_id = {r.wiki_id: r for r in records}
    for node in projection.nodes:
        if node.identity in by_id:
            route = record_link(by_id[node.identity], locators, DERIVED / audit_path)
        else:
            path = preferred.get(node.identity)
            route = (
                f"[[{DERIVED / path}|{literal(node.title)}]]"
                if path
                else literal(node.title) + " (preferred technical route unavailable)"
            )
        body.append(f"- {node.identity}: {route}")
    if projection.mode != "pilot":
        body += ["", "## Exact technical attachments / detail-only endpoints", ""]
        for record in sorted(records, key=lambda r: r.wiki_id):
            if record.wiki_id not in nodes:
                continue
            for field in (
                "research_direct_subject_refs",
                "research_method_or_baseline_refs",
                "research_measurement_relevance_refs",
                "research_project_transfer_refs",
                "research_adjacent_context_refs",
            ):
                for target in sorted(set(getattr(record, field, ()))):
                    path = preferred.get(target)
                    route = f"[[{DERIVED / path}|{target}]]" if path else literal(target)
                    body.append(
                        f"- {record.wiki_id} v{record.record_version} / {field} → {route}; "
                        "exact authored declaration, no ancestry inheritance. "
                        + (
                            "Detail only; no accepted topology profile for this class."
                            if (record.wiki_id, target) not in pairs
                            else "See semantic pair audit above."
                        )
                    )
        body += ["", f"[[{DERIVED / profile_path.with_suffix('')}|Profile instructions]]", ""]
        for mode in MODES:
            destination = scope_root(projection.scope, mode)
            body.append(f"- [[{DERIVED / destination / 'Graph Profile'}|{mode}]]")
    body += [
        "",
        ("- [[_generated/technical-atlas/system-map/Agent Anatomy.excalidraw.md|Agent Anatomy]]"),
        (
            "- [[_generated/derived/indexes/Declared Literature Navigation|Exact "
            "direct / descendant / related attachment audit]]"
        ),
        "- [[_generated/derived/indexes/Source Details|Source / provenance inspection]]",
        (
            "- [[_generated/derived/indexes/Research Landscape|Research Steering — "
            "complementary inventory, not Graph authority]]"
        ),
        "",
        "## Sparse state",
        "",
        (
            "No matching documented knowledge, unresolved reference, "
            "unsupported/excluded relation, unavailable detail route, knowledge at "
            "another exact scope, and an empty RQ overlay are valid navigation "
            "states. None implies literature absence, novelty, candidate gap, "
            "completeness, saturation, scientific weakness, evidence strength, "
            "research value or project priority. No scientific graph metrics are "
            "calculated."
        ),
        "",
    ]
    body.extend("- " + literal(d) for d in projection.diagnostics)
    tree[audit_path] = note(audit_path, "\n".join(body))
    return tree
