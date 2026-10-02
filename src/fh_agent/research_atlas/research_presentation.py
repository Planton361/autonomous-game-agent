"""G3 literal private presentation; selection never creates Research attachment truth."""

import hashlib
import json
import posixpath
import re
import unicodedata
from collections.abc import Callable
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

from .private_projection import ProjectionError
from .private_reference_index import PROPERTIES, Role, Row
from .wiki_schema import EpistemicRecord, Finding, Paper, ReadingNote, Synthesis

ROLE_LABELS: dict[Role, str] = {
    "research_direct_subject_refs": "Direct subject",
    "research_method_or_baseline_refs": "Method / baseline",
    "research_measurement_relevance_refs": "Measurement relevance",
    "research_project_transfer_refs": "Project transfer",
    "research_adjacent_context_refs": "Adjacent context",
}
ORIGIN_LABELS = {
    "authors_result": "Source-reported finding",
    "authors_limitation": "Author-reported limitation",
    "our_inference": "Project inference",
    "own_empirical_result": "Project empirical result",
}
PRESENTATION_FINGERPRINT_VERSION = "1.1"
COMMON_FIELDS = {
    "wiki_id",
    "doc_type",
    "title",
    "record_version",
    "document_maturity",
    "epistemic_schema_version",
    "review_refs",
}
TYPE_FIELDS = {
    "synthesis": {"rq_refs", "finding_refs"},
    "search_record": {"target_refs", "search_date", "result_refs"},
    "journal_entry": {"resulting_object_refs", "entry_date", "source_refs"},
    "paper": {"source_refs", "doi", "url", "authors", "publication_year", "venue"},
    "reading_note": {"version_read", "read_date", "reading_depth", "checked_sections"},
    "finding": {"claim_origin", "review_state", "reading_note_refs"},
    "research_question": {
        "question_stage",
        "decision_state",
        "search_refs",
        "synthesis_refs",
        "decision_refs",
    },
    "experiment_lead": {"question_stage", "decision_state"},
    "decision_draft": {
        "decision_record_state",
        "decision_scope",
        "decision_type",
        "subject_refs",
        "authority_refs",
    },
}


def literal(text: str) -> str:
    """Escape authored text literally; never truncate, flatten, or rewrite wording."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_{}\[\]()#!|~])", r"\\\1", text)


def record_link(
    record: EpistemicRecord, locators: dict[str, PurePosixPath], page: PurePosixPath
) -> str:
    destination = locators.get(record.wiki_id)
    if destination is None:
        return literal(record.title) + " (authored detail unavailable)"
    raw = str(destination)
    if (
        destination.is_absolute()
        or PureWindowsPath(raw).drive
        or "\\" in raw
        or ".." in destination.parts
        or not destination.parts
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in raw)
    ):
        raise ProjectionError("Unsafe private presentation locator")
    relative = posixpath.relpath(raw, start=str(page.parent))
    return f"[{literal(record.title)}]({quote(relative, safe='/.-_')})"


def presentation_inputs(records: tuple[EpistemicRecord, ...]) -> list[dict]:
    """Separate versioned input; reference fingerprint and bodies are untouched."""
    values = []
    for record in sorted(records, key=lambda r: r.wiki_id):
        fields = COMMON_FIELDS | set(PROPERTIES) | TYPE_FIELDS.get(record.doc_type, set())
        if record.doc_type not in {"paper", "reading_note", "finding", "journal_entry"}:
            fields.discard("source_refs")
        fields |= {
            field for field in type(record).model_fields if field.startswith("presentation_")
        }
        # Profile version is consumed by the existing literature inspection view.
        if isinstance(record, (Paper, ReadingNote)):
            fields |= {"epistemic_schema_version", "venue", "related_version_refs"}
        value = record.model_dump(mode="json", include=fields)

        def canonical(value, key=""):
            if isinstance(value, dict):
                return {k: canonical(v, k) for k, v in value.items()}
            if isinstance(value, list):
                items = [canonical(v) for v in value]
                if key.endswith("_refs") or key in {"reviewed_by", "checked_sections"}:
                    return sorted(items)
                if key == "reviewed_inputs":
                    return sorted(items, key=lambda v: v["ref"])
                return items
            return value

        values.append(canonical(value))
    return values


def presentation_fingerprint(records: tuple[EpistemicRecord, ...]) -> str:
    values = presentation_inputs(records)
    encoded = json.dumps(
        {"presentation_fingerprint_version": PRESENTATION_FINGERPRINT_VERSION, "records": values},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def eligible(record: EpistemicRecord) -> bool:
    return record.document_maturity in {"domain_accepted", "in_review"}


def paper_previews(
    target: str,
    attachments: tuple[Row, ...],
    paths: tuple[Row, ...],
    records: tuple[EpistemicRecord, ...],
    link: Callable[[EpistemicRecord], str],
    source_summary: Callable[[Paper, ReadingNote | None], list[str]] | None = None,
) -> list[str]:
    """Join only exact terminal owners to Paper-anchored finite paths and authored contexts."""
    by_id = {record.wiki_id: record for record in records}
    candidates = set()
    for row in attachments:
        owner = by_id.get(row.source_wiki_id)
        if (
            row.target_identifier != target
            or owner is None
            or row.originating_role is None
            or owner.record_version != row.source_record_version
            or target not in getattr(owner, row.originating_role)
        ):
            continue
        if isinstance(by_id.get(row.source_wiki_id), Paper):
            candidates.add((row.source_wiki_id, row.source_wiki_id, row.originating_role))
        for path in paths:
            if path.via[-1] == row.via[-1] and path.navigation_start is not None:
                candidates.add(
                    (path.navigation_start.identifier, row.source_wiki_id, row.originating_role)
                )
    lines = []
    sparse_papers: set[str] = set()
    for paper_id, owner_id, role in sorted(candidates):
        paper = by_id.get(paper_id)
        owner = by_id.get(owner_id)
        if not isinstance(paper, Paper) or owner is None or role is None:
            continue
        context = next(
            (
                c
                for c in getattr(owner, "presentation_contexts", ())
                if c.role == role and c.target_ref == target
            ),
            None,
        )
        if context is None or not eligible(paper) or not eligible(owner):
            if paper_id in sparse_papers:
                continue
            sparse_papers.add(paper_id)
        selected_reading = None
        lines += [f"#### {link(paper)}", ""]
        if paper.authors or paper.publication_year:
            lines += [
                literal(", ".join(paper.authors))
                + (f" ({paper.publication_year})" if paper.publication_year else ""),
                "",
            ]
        lines += [f"**Research role:** {ROLE_LABELS[role]}.", ""]
        if not eligible(paper) or not eligible(owner):
            lines += [
                "Historical or draft record — detail navigation only; no current rich preview.",
                "",
            ]
        elif context is None:
            lines += [
                "No authored relevance context or selected Finding is available for this subject.",
                "",
            ]
        else:
            qualifier = (
                " (in review)"
                if "in_review" in {paper.document_maturity, owner.document_maturity}
                else ""
            )
            lines += [
                f"**Project-authored relevance{qualifier}:** " + literal(context.why_relevant),
                "",
                "Context authored in " + link(owner) + ".",
                "",
            ]
            finding = by_id.get(context.finding_ref)
            if context.finding_ref is None:
                lines += ["No Finding explicitly selected.", ""]
            elif not isinstance(finding, Finding) or paper_id not in finding.source_refs:
                lines += [
                    "Explicitly selected Finding unavailable or not source-matched; "
                    "no replacement selected.",
                    "",
                ]
            else:
                rich = finding.document_maturity == finding.review_state == "domain_accepted"
                in_review = (
                    finding.document_maturity == "in_review" and finding.review_state != "draft"
                )
                lines += [
                    f"**Finding review:** {finding.review_state.replace('_', ' ')}; "
                    f"document {finding.document_maturity.replace('_', ' ')}. " + link(finding),
                    "",
                ]
                if (rich or in_review) and finding.presentation_statement:
                    prefix = ORIGIN_LABELS[finding.claim_origin] + (
                        " (in review)" if in_review else ""
                    )
                    lines += [f"**{prefix}:** " + literal(finding.presentation_statement), ""]
                    if finding.presentation_limitation:
                        # Attribution follows the Finding's origin; an inference is never
                        # an author's limitation.
                        label = (
                            "Author-reported limitation / applicability"
                            if finding.claim_origin.startswith("authors_")
                            else "Project-authored limitation / applicability"
                        )
                        lines += [f"**{label}:** " + literal(finding.presentation_limitation), ""]
                else:
                    lines += [
                        "Selected Finding has no eligible authored statement; no "
                        "replacement selected.",
                        "",
                    ]
            reading = by_id.get(context.reading_note_ref)
            if context.reading_note_ref is None:
                lines += ["No ReadingNote explicitly selected.", ""]
            elif not isinstance(reading, ReadingNote) or paper_id not in (
                reading.paper_refs or reading.source_refs
            ):
                lines += [
                    "Explicitly selected ReadingNote unavailable or not "
                    "source-matched; no replacement selected.",
                    "",
                ]
            else:
                selected_reading = reading
                lines += [
                    "**Reading provenance:** "
                    + link(reading)
                    + "; "
                    + reading.reading_depth.replace("_", " ")
                    + "; document "
                    + reading.document_maturity.replace("_", " ")
                    + ".",
                    "",
                ]
                if reading.version_read is not None and source_summary is None:
                    lines += ["**Version read:** " + literal(reading.version_read) + ".", ""]
                if reading.read_date is not None:
                    lines += [f"**Read date:** {reading.read_date.isoformat()}.", ""]
                if reading.checked_sections:
                    lines += [
                        "**Checked sections:** " + ", ".join(reading.checked_sections) + ".",
                        "",
                    ]
        lines += [
            "**Paper state:** " + paper.document_maturity.replace("_", " ") + ".",
            "",
            ("**Source:** " if source_summary is None else "**Paper detail:** ")
            + link(paper)
            + "; exact source/version references in authored detail and audit.",
            "",
        ]
        if source_summary is not None:
            lines += source_summary(paper, selected_reading)
        # Authored bibliography stays literal; only explicit catalog aliases resolve.
        if paper.url:
            lines += ["**Authored source URL:** " + literal(paper.url), ""]
        if paper.doi:
            lines += ["**Authored DOI:** " + literal(paper.doi), ""]
    return lines


def orientation_previews(
    records: tuple[EpistemicRecord, ...], link: Callable[[EpistemicRecord], str]
) -> list[str]:
    """Independent authored orientation/Synthesis, never constituent technical relevance."""
    by_id = {r.wiki_id: r for r in records}
    lines = []
    for record in sorted(records, key=lambda r: (r.title.casefold(), r.wiki_id)):
        if not eligible(record):
            continue
        if isinstance(record, Synthesis) and not all(
            isinstance(by_id.get(ref), Finding) for ref in record.finding_refs
        ):
            continue
        field = {
            "synthesis": "presentation_summary",
            "dossier": "presentation_overview",
            "topic": "presentation_summary",
            "research_question": "presentation_question",
        }.get(record.doc_type)
        value = getattr(record, field, None) if field else None
        if value:
            lines += [
                f"### {link(record)}",
                "",
                "**Authored "
                + record.doc_type.replace("_", " ")
                + " ("
                + record.document_maturity.replace("_", " ")
                + "):** "
                + literal(value),
                "",
            ]
            if isinstance(record, Synthesis):
                if record.presentation_limitation:
                    lines += [
                        "**Synthesis limitation:** " + literal(record.presentation_limitation),
                        "",
                    ]
                lines += [
                    "**Referenced Findings:** "
                    + ", ".join(link(by_id[ref]) for ref in record.finding_refs),
                    "",
                ]
    return lines
