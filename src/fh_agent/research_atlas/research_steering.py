"""Three record inventories over existing RQ, technical and source projections."""

import json
import posixpath
from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import quote

from .private_projection import ProjectionError, yaml_text
from .research_presentation import eligible, literal, record_link
from .rq_presentation import RQReader
from .source_presentation import DIAGNOSTIC_LABELS
from .wiki_schema import Finding, Paper, ReadingNote, ResearchQuestion, Synthesis

STEERING_BASE = PurePosixPath("bases/Research Steering.base")
ROOT = PurePosixPath("_generated/derived")
PAGE = ROOT / "indexes/Research Landscape.md"
GAP_STATES = (
    "unassessed",
    "insufficient_evidence",
    "covered_by_prior_art",
    "narrowing_required",
    "candidate_gap",
)
UNAVAILABLE = "Current conclusion unavailable"


@dataclass(frozen=True)
class Link:
    label: str
    destination: str


Cell = str | int | tuple[Link, ...]


@dataclass(frozen=True)
class InventoryRow:
    path: PurePosixPath | None
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Inventory:
    name: str
    columns: tuple[str, ...]
    rows: tuple[InventoryRow, ...]


def paper_membership(reader: RQReader, rq: ResearchQuestion) -> frozenset[str]:
    """Exact selected existing Papers, plus eligible explicit statement-source Papers.

    Missing context/source prose does not erase an explicitly selected Paper identity.
    Search results, generic attachments and family similarity never enter this set.
    """
    a = rq.presentation_analysis
    if not eligible(rq) or a is None:
        return frozenset()
    refs = {row.paper_ref for row in (*a.literature_rows, *a.nearest_work_rows)}
    for item in a.establishes:
        if not reader.statement_ok(rq, item.record_ref):
            continue
        statement = reader.by_id[item.record_ref]
        findings = (
            [reader.by_id[ref] for ref in statement.finding_refs]
            if isinstance(statement, Synthesis)
            else [statement]
        )
        for finding in findings:
            if isinstance(finding, Finding):
                refs.update(finding.source_refs)
    return frozenset(ref for ref in refs if isinstance(reader.by_id.get(ref), Paper))


def inventories(
    reader: RQReader,
    locators: dict[str, PurePosixPath],
    component_paths: dict[str, PurePosixPath],
) -> tuple[Inventory, ...]:
    """No scientific writes, prioritization or inferred technical associations."""
    atlas, records = reader.atlas, reader.records
    rqs = sorted(
        (r for r in records if isinstance(r, ResearchQuestion) and eligible(r)),
        key=lambda r: ((r.presentation_question or r.title).casefold(), r.wiki_id),
    )
    papers = sorted(
        (r for r in records if isinstance(r, Paper)),
        key=lambda r: (r.title.casefold(), r.wiki_id),
    )
    components = sorted(
        (n for n in atlas.entities.values() if n.type == "Component"),
        key=lambda n: (n.name.casefold(), n.id),
    )
    subjects = {r.wiki_id: reader.subjects(r) for r in rqs}
    paper_sets = {r.wiki_id: paper_membership(reader, r) for r in rqs}
    states = {
        r.wiki_id: r.presentation_analysis.conclusion.gap_state
        if reader.conclusion_ok(r)
        else UNAVAILABLE
        for r in rqs
    }

    def technical(ref: str) -> Link:
        path = component_paths.get(ref)
        if path is None:
            raise ProjectionError("Steering technical preferred route unavailable")
        return Link(atlas.entities[ref].name, str(ROOT / path))

    def record_cell(record, label=None) -> Cell:
        # Reuse the existing privacy/path validation even for Base-only navigation.
        record_link(record, locators, PAGE)
        path = locators.get(record.wiki_id)
        title = label or record.title
        return (Link(title, str(path)),) if path else title + " (detail unavailable)"

    rq_rows = tuple(
        InventoryRow(
            locators.get(r.wiki_id),
            (
                record_cell(r, r.presentation_question or r.title),
                tuple(technical(ref) for ref in subjects[r.wiki_id])
                or "No exact technical subject bound",
                len(paper_sets[r.wiki_id]),
                states[r.wiki_id].replace("_", " "),
            ),
        )
        for r in rqs
    )
    component_rows = []
    for component in components:
        mapped = [r for r in rqs if component.id in subjects[r.wiki_id]]
        union = set().union(*(paper_sets[r.wiki_id] for r in mapped))
        distribution = Counter(states[r.wiki_id] for r in mapped)
        summary = (
            " · ".join(
                f"{distribution[state]} {state.replace('_', ' ')}"
                for state in (*GAP_STATES, UNAVAILABLE)
                if distribution[state]
            )
            or "No directly mapped current RQs"
        )
        component_rows.append(
            InventoryRow(
                ROOT / component_paths[component.id],
                ((technical(component.id),), len(mapped), len(union), summary),
            )
        )
    paper_rows = []
    for paper in papers:
        used = [r for r in rqs if paper.wiki_id in paper_sets[r.wiki_id]]
        areas = {
            ref
            for rq in used
            for ref in subjects[rq.wiki_id]
            if atlas.entities[ref].type == "Component"
        }
        # Exact Paper-owned ReadingNote declarations; no family-level retargeting.
        notes = sorted(
            (
                n
                for n in records
                if isinstance(n, ReadingNote) and paper.wiki_id in (n.paper_refs or n.source_refs)
            ),
            key=lambda n: (n.title.casefold(), n.wiki_id),
        )
        read = (
            " · ".join(
                f"{n.title}: {n.reading_depth.replace('_', ' ')} "
                f"({n.document_maturity.replace('_', ' ')})"
                for n in notes
            )
            or "No mapped ReadingNote"
        )
        resolver = reader.source.resolver
        binding = resolver.paper(paper)
        statuses = ["Source family " + binding.family.status]
        resolutions = [*binding.related_versions]
        if binding.family.status == "resolved":
            family = resolver.family(binding.family.target_ref)
            resolutions.append(resolver.preferred(family))
        for result in resolutions:
            statuses.append("Source version " + result.status)
            if result.status == "resolved":
                statuses.extend(
                    DIAGNOSTIC_LABELS[c]
                    for c in resolver.version_diagnostics(resolver.version(result.target_ref))
                )
        for n in notes:
            result = resolver.reading(n, records).version_read
            statuses.append(n.title + ": version read " + result.status)
            if result.status == "resolved":
                statuses.extend(
                    DIAGNOSTIC_LABELS[c]
                    for c in resolver.version_diagnostics(resolver.version(result.target_ref))
                )
        zotero = reader.zotero(paper)
        paper_rows.append(
            InventoryRow(
                locators.get(paper.wiki_id),
                (
                    record_cell(paper),
                    tuple(
                        technical(ref)
                        for ref in sorted(
                            areas, key=lambda ref: (atlas.entities[ref].name.casefold(), ref)
                        )
                    )
                    or "No Component mapped through current RQ use",
                    len(used),
                    read,
                    " · ".join(dict.fromkeys(statuses)),
                    (Link("Open Zotero", zotero),) if zotero else "Unavailable / ambiguous",
                ),
            )
        )
    return (
        Inventory(
            "Research Questions",
            ("Research Question", "Technical subject(s)", "Papers", "Status"),
            rq_rows,
        ),
        Inventory(
            "Technical Components",
            ("Component", "Research Questions", "Papers", "Gap-analysis status"),
            tuple(component_rows),
        ),
        Inventory(
            "Papers",
            ("Paper", "Area / Components", "Used in RQs", "Read state", "Source status", "Zotero"),
            tuple(paper_rows),
        ),
    )


def markdown_cell(cell: Cell) -> str:
    if isinstance(cell, tuple):
        links = []
        for link in cell:
            destination = link.destination
            if not destination.startswith(("https://", "zotero://")):
                destination = quote(posixpath.relpath(destination, str(PAGE.parent)), safe="/.-_")
            links.append(f"[{literal(link.label)}]({destination})")
        text = ", ".join(links)
    else:
        text = literal(str(cell))
    return text.replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")


def markdown_tables(values: tuple[Inventory, ...]) -> list[str]:
    lines = []
    for inventory in values:
        lines += [f"## {inventory.name}", ""]
        lines += [
            f"[[{ROOT / STEERING_BASE}#{inventory.name}|Filter / sort in Bases]]",
            "",
            "| " + " | ".join(inventory.columns) + " |",
            "| " + " | ".join("---" for _ in inventory.columns) + " |",
        ]
        lines += ["| " + " | ".join(map(markdown_cell, row.cells)) + " |" for row in inventory.rows]
        if not inventory.rows:
            lines += [
                "",
                "No current mapped records in this snapshot; research absence is not implied.",
            ]
        lines += [""]
    return lines


def base_cell(cell: Cell) -> str:
    if isinstance(cell, tuple):
        return (
            "["
            + ", ".join(
                f"link({json.dumps(link.destination, ensure_ascii=False)}, "
                f"{json.dumps(link.label, ensure_ascii=False)})"
                for link in cell
            )
            + "]"
        )
    return json.dumps(cell, ensure_ascii=False)


def base_output(values: tuple[Inventory, ...], owner: str) -> bytes:
    """Snapshot formulas on preferred pages, never duplicate row/identity files.

    Bases use the same cells as Markdown; optional filtering/sorting is local UI.
    """
    formulas = {}
    properties = {}
    views = []
    paths = set()
    for index, inventory in enumerate(values):
        rows = [row for row in inventory.rows if row.path is not None]
        paths.update(str(row.path) for row in rows)
        order = []
        for column, name in enumerate(inventory.columns):
            key = f"inventory_{index}_{column}"
            expression = '""'
            for row in reversed(rows):
                expression = (
                    f"if(file.path == {json.dumps(str(row.path), ensure_ascii=False)}, "
                    f"{base_cell(row.cells[column])}, {expression})"
                )
            formulas[key] = expression
            property_id = "formula." + key
            properties[property_id] = {"displayName": name}
            order.append(property_id)
        views.append(
            dict(
                type="table",
                name=inventory.name,
                filters={
                    "or": [
                        f"file.path == {json.dumps(str(row.path), ensure_ascii=False)}"
                        for row in rows
                    ]
                    or ["false"]
                },
                order=order,
                sort=[{"property": order[0], "direction": "ASC"}],
            )
        )
    return (
        owner
        + yaml_text(
            dict(
                filters={
                    "and": [
                        'file.ext == "md"',
                        {
                            "or": [
                                f"file.path == {json.dumps(path, ensure_ascii=False)}"
                                for path in sorted(paths)
                            ]
                            or ["false"]
                        },
                    ]
                },
                formulas=formulas,
                properties=properties,
                views=views,
            )
        )
    ).encode()
