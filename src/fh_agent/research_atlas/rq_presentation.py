"""Exact RQ-owned scientific reader; authored selections never become authorization."""

import json
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from .private_projection import COMMIT, read_yaml, yaml_text
from .research_presentation import (
    ORIGIN_LABELS,
    eligible,
    literal,
    presentation_inputs,
    record_link,
)
from .rq_schema import LiteratureRow, NearestWorkRow, zotero_pointer
from .source_presentation import SourceReader
from .validator import Atlas
from .wiki_schema import (
    EpistemicRecord,
    Finding,
    JournalEntry,
    Paper,
    PresentationContext,
    ReadingNote,
    ResearchQuestion,
    SearchRecord,
    Synthesis,
)

RQ_METADATA_MARKER = "<!-- aga-rq-reader-generated\n"
RQ_ROOT = PurePosixPath("research-questions")
DERIVED = PurePosixPath("_generated/derived")
TARGET_TYPES = {"System", "Component", "Interface", "Contract", "DataArtifact", "MeasurementPoint"}


class RQMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    generated_by: Literal["research-wiki-derived"]
    rq_reader_schema_version: Literal["1.0"]
    rq_subject: str
    rq_page_path: str
    source_commit: COMMIT
    privacy: Literal["private"]
    export_policy: Literal["deny"]


def is_rq_path(path: PurePosixPath) -> bool:
    return (
        path.parent == RQ_ROOT
        and path.suffix == ".md"
        and len(path.name.encode()) <= 240
        and bool(path.stem.strip())
        and path.stem == path.stem.strip(" .")
        and not re.search(r'[<>:"/\\|?*\[\]#^\x00-\x1f]', path.stem)
    )


def rq_metadata(text: str, path: PurePosixPath) -> dict:
    if not is_rq_path(path):
        return {}
    try:
        _, separator, tail = text.rpartition(RQ_METADATA_MARKER)
        if not separator or not tail.endswith("-->\n"):
            return {}
        props = RQMetadata.model_validate(read_yaml(tail[:-4]))
    except ValidationError:
        return {}
    return (
        props.model_dump()
        if (
            re.fullmatch(r"WRQ-[A-Z0-9]+(?:-[A-Z0-9]+)*", props.rq_subject)
            and props.rq_page_path == str(path)
        )
        else {}
    )


class RQReader:
    def __init__(self, atlas: Atlas, records: tuple[EpistemicRecord, ...], source: SourceReader):
        self.atlas = atlas
        self.records = records
        self.by_id = {r.wiki_id: r for r in records}
        self.source = source
        self.diagnostics: set[str] = set()

    def unavailable(self, ref: str, reason: str) -> bool:
        self.diagnostics.add(ref + ": " + reason)
        return False

    def subjects(self, rq: ResearchQuestion) -> list[str]:
        if rq.epistemic_schema_version != "0.3":
            return []
        result = []
        for ref in sorted(rq.research_direct_subject_refs):
            target = self.atlas.entities.get(ref)
            if target is not None and target.type in TARGET_TYPES:
                result.append(ref)
            else:
                self.unavailable(ref, "Exact technical subject unavailable/wrong actual type")
        return result

    def context(self, rq: ResearchQuestion, row: LiteratureRow) -> PresentationContext | None:
        paper = self.by_id.get(row.paper_ref)
        owner = self.by_id.get(row.context_owner_ref)
        matched = (
            isinstance(owner, Paper)
            and owner.wiki_id == row.paper_ref
            or isinstance(owner, ReadingNote)
            and row.paper_ref in (owner.paper_refs or owner.source_refs)
            or isinstance(owner, Finding)
            and row.paper_ref in owner.source_refs
        )
        if not isinstance(paper, Paper) or not matched:
            self.unavailable(
                row.context_owner_ref,
                "Context/Paper unavailable, historical or not exact Paper-matched",
            )
            return None
        context = next(
            (
                c
                for c in owner.presentation_contexts
                if c.role == row.context_role and c.target_ref == rq.wiki_id
            ),
            None,
        )
        if context is None:
            self.unavailable(row.context_owner_ref, "Selected exact owner/role/RQ context missing")
        return context

    def finding_ok(self, finding: Finding, paper_ref: str | None = None) -> bool:
        if paper_ref is not None and paper_ref not in finding.source_refs:
            return self.unavailable(finding.wiki_id, "Finding not exact Paper-matched")
        if not (
            finding.document_maturity == finding.review_state == "domain_accepted"
            or finding.document_maturity == "in_review"
            and finding.review_state != "draft"
        ):
            return self.unavailable(finding.wiki_id, "Finding review/maturity unavailable")
        if finding.claim_origin == "own_empirical_result":
            return self.unavailable(finding.wiki_id, "Own empirical result out of literature scope")
        if finding.claim_origin == "our_inference":
            return True
        if not finding.presentation_source_locations:
            return self.unavailable(finding.wiki_id, "No explicit eligible source locations")
        papers = [self.by_id.get(ref) for ref in finding.source_refs]
        papers = [
            p
            for p in papers
            if isinstance(p, Paper)
            and eligible(p)
            and (paper_ref is None or p.wiki_id == paper_ref)
        ]
        for location in finding.presentation_source_locations:
            note = self.by_id.get(location.reading_note_ref)
            if (
                not isinstance(note, ReadingNote)
                or note.wiki_id not in finding.reading_note_refs
                or not eligible(note)
            ):
                return self.unavailable(
                    finding.wiki_id, "Location ReadingNote unavailable/not declared/current"
                )
            binding = self.source.resolver.reading(note, self.records)
            matching = [
                p
                for p in papers
                if self.source.resolver.paper(p).family.status == "resolved"
                and self.source.resolver.paper(p).family.target_ref == binding.family.target_ref
            ]
            # Paper-specific notes cannot be exchanged for a different Paper of the same family.
            identity = (note.paper_refs or note.source_refs)[0]
            if isinstance(self.by_id.get(identity), Paper):
                matching = [p for p in matching if p.wiki_id == identity]
            if (
                not matching
                or binding.family.status != "resolved"
                or binding.version_read.status != "resolved"
                or note.read_date is None
                or note.reading_depth
                not in {"methods_checked", "results_checked", "relevant_fulltext_checked"}
                or not set(note.checked_sections)
                & {"methods", "results", "discussion", "limitations", "supplement", "other"}
            ):
                return self.unavailable(
                    finding.wiki_id, "Exact checked source version/scope unavailable"
                )
        return True

    def statement_ok(self, rq: ResearchQuestion, ref: str) -> bool:
        record = self.by_id.get(ref)
        if isinstance(record, Finding):
            return (
                ref in rq.finding_refs
                and self.finding_ok(record)
                and bool(record.presentation_statement)
            )
        if isinstance(record, Synthesis):
            return (
                ref in rq.synthesis_refs
                and rq.wiki_id in record.rq_refs
                and eligible(record)
                and bool(record.presentation_summary)
                and all(
                    isinstance(self.by_id.get(f), Finding) and self.finding_ok(self.by_id[f])
                    for f in record.finding_refs
                )
            )
        return self.unavailable(ref, "Selected statement wrong type/dangling; no replacement")

    def dependencies(self, rq: ResearchQuestion) -> set[str]:
        analysis = rq.presentation_analysis
        refs = set(rq.search_refs)
        if analysis is None:
            return refs
        for row in analysis.literature_rows:
            refs.update((row.paper_ref, row.context_owner_ref))
            context = self.context(rq, row)
            if context:
                refs.update(filter(None, (context.finding_ref, context.reading_note_ref)))
        for row in analysis.nearest_work_rows:
            refs.add(row.paper_ref)
            refs.update(row.evidence_refs)
        refs.update(item.record_ref for item in analysis.establishes)
        pending = list(refs)
        while pending:
            record = self.by_id.get(pending.pop())
            extra = (
                record.finding_refs
                if isinstance(record, Synthesis)
                else record.reading_note_refs
                if isinstance(record, Finding)
                else []
            )
            if isinstance(record, Finding):
                extra = [
                    *extra,
                    *(ref for ref in record.source_refs if isinstance(self.by_id.get(ref), Paper)),
                ]
            if isinstance(record, ReadingNote):
                extra = [
                    ref
                    for ref in (record.paper_refs or record.source_refs)
                    if isinstance(self.by_id.get(ref), Paper)
                ]
            for ref in extra:
                if ref not in refs:
                    refs.add(ref)
                    pending.append(ref)
        return refs

    def review_ok(self, rq: ResearchQuestion) -> bool:
        c = rq.presentation_analysis.conclusion
        if c is None or not c.reviewed_by or not rq.review_refs:
            return False
        for ref in rq.review_refs:
            review = self.by_id.get(ref)
            if (
                isinstance(review, JournalEntry)
                and rq.wiki_id in review.resulting_object_refs
                and eligible(review)
            ):
                continue
            if re.fullmatch(
                r"https://github\.com/Planton361/autonomous-game-agent/(?:issues|pull)/[1-9][0-9]*#issuecomment-[1-9][0-9]*",
                ref,
            ):
                continue
            return self.unavailable(
                ref, "Review reference unavailable/wrong explicit authority form"
            )
        a = rq.presentation_analysis
        for row in a.literature_rows:
            context = self.context(rq, row)
            if context is None:
                return self.unavailable(row.paper_ref, "Reviewed context selection unavailable")
            if context.finding_ref:
                finding = self.by_id.get(context.finding_ref)
                if (
                    not isinstance(finding, Finding)
                    or context.finding_ref not in rq.finding_refs
                    or not self.finding_ok(finding, row.paper_ref)
                ):
                    return self.unavailable(
                        context.finding_ref, "Reviewed selected Finding unavailable"
                    )
            if context.reading_note_ref:
                note = self.by_id.get(context.reading_note_ref)
                if not isinstance(note, ReadingNote) or row.paper_ref not in (
                    note.paper_refs or note.source_refs
                ):
                    return self.unavailable(
                        context.reading_note_ref, "Reviewed selected ReadingNote unavailable"
                    )
        for item in a.establishes:
            if not self.statement_ok(rq, item.record_ref):
                return self.unavailable(
                    item.record_ref, "Reviewed establishes selection unavailable"
                )
        for row in a.nearest_work_rows:
            if not self.comparison_ok(rq, row, check_review=False):
                return False
        dependencies = self.dependencies(rq)
        pinned = {i.ref: i.record_version for i in c.reviewed_inputs}
        if dependencies != pinned.keys() or any(
            not isinstance(self.by_id.get(ref), EpistemicRecord)
            or not eligible(self.by_id[ref])
            or self.by_id[ref].record_version != version
            for ref, version in pinned.items()
        ):
            return self.unavailable(
                rq.wiki_id, "Reviewed dependency set/revisions stale or unavailable"
            )
        for ref in rq.search_refs:
            search = self.by_id.get(ref)
            if not isinstance(search, SearchRecord) or rq.wiki_id not in search.target_refs:
                return self.unavailable(ref, "SearchRecord does not explicitly target this RQ")
        return True

    def comparison_ok(
        self, rq: ResearchQuestion, row: NearestWorkRow, *, check_review: bool = True
    ) -> bool:
        paper = self.by_id.get(row.paper_ref)
        if not eligible(rq) or not isinstance(paper, Paper) or not eligible(paper):
            return self.unavailable(row.paper_ref, "Comparison Paper/RQ unavailable or historical")
        c = rq.presentation_analysis.conclusion
        attempted_review = c is not None and bool(c.reviewed_by or c.reviewed_inputs)
        if (
            check_review
            and (rq.document_maturity == "domain_accepted" or attempted_review)
            and not self.review_ok(rq)
        ):
            return False
        for ref in row.evidence_refs:
            f = self.by_id.get(ref)
            if (
                not isinstance(f, Finding)
                or ref not in rq.finding_refs
                or f.claim_origin not in {"authors_result", "authors_limitation"}
                or not self.finding_ok(f, row.paper_ref)
                or not f.presentation_statement
            ):
                return self.unavailable(
                    ref, "Comparison evidence unavailable/not exact source Finding"
                )
        return True

    def conclusion_ok(self, rq: ResearchQuestion) -> bool:
        a = rq.presentation_analysis
        c = a.conclusion if a else None
        if c is None or not eligible(rq):
            return False
        if len(self.subjects(rq)) != len(rq.research_direct_subject_refs):
            return self.unavailable(rq.wiki_id, "Invalid exact technical binding")
        if c.question_version != rq.record_version:
            return self.unavailable(rq.wiki_id, "Question revision stale")
        # Any attempted review is pinned and cannot degrade silently into provisional prose.
        if (
            rq.document_maturity == "domain_accepted" or c.reviewed_by or c.reviewed_inputs
        ) and not self.review_ok(rq):
            return False
        allowed = {i.record_ref for i in a.establishes} | {
            f for row in a.nearest_work_rows for f in row.evidence_refs
        }
        if any(ref not in allowed or not self.statement_ok(rq, ref) for ref in c.evidence_refs):
            return self.unavailable(
                rq.wiki_id, "Conclusion evidence not explicitly selected/eligible"
            )
        if c.gap_state in {"covered_by_prior_art", "narrowing_required", "candidate_gap"} and (
            not c.evidence_refs
            or not any(self.comparison_ok(rq, row) for row in a.nearest_work_rows)
        ):
            return self.unavailable(
                rq.wiki_id, "Gap state needs explicit eligible comparison/evidence"
            )
        if c.gap_state == "candidate_gap" and not self.review_ok(rq):
            return self.unavailable(rq.wiki_id, "Candidate gap requires reviewed current evidence")
        return True

    def zotero(self, paper: Paper) -> str | None:
        resolver = self.source.resolver
        family = resolver.paper(paper).family
        if family.status != "resolved" or resolver.catalog is None:
            return None
        pointers = set()
        for b in resolver.catalog.bindings:
            if (
                b.target_ref == family.target_ref
                and b.scheme in {"opaque", "url"}
                and zotero_pointer(b.value, "item")
            ):
                resolution = resolver.resolve(b.alias, "family")
                if resolution.status == "resolved" and resolution.target_ref == family.target_ref:
                    pointers.add(b.value)
        if len(pointers) != 1:
            self.unavailable(paper.wiki_id, "Zotero item unavailable/ambiguous")
            return None
        return next(iter(pointers))

    def card(
        self, rq: ResearchQuestion, target: str, link: Callable[[EpistemicRecord], str]
    ) -> list[str]:
        question = literal(rq.presentation_question or rq.title)
        if not eligible(rq):
            return ["- " + link(rq) + " — " + rq.document_maturity + "; navigation only.", ""]
        a = rq.presentation_analysis
        reason = (
            next((c.why_matters for c in a.subject_contexts if c.target_ref == target), None)
            if a
            else None
        )
        state = (
            a.conclusion.gap_state.replace("_", " ")
            if self.conclusion_ok(rq)
            else "Current gap state unavailable"
        )
        body = [
            literal(reason) if reason else "Why this matters unavailable.",
            "",
            state + ".",
            "",
            link(rq).replace(literal(rq.title), "Open Research Question"),
        ]
        title = question
        if "\n" in question:
            title = "Research Question"
            body = [question, "", *body]
        return [
            "> [!question]- " + title,
            *("> " + line if line else ">" for item in body for line in item.split("\n")),
            "",
        ]

    def render(
        self,
        rq: ResearchQuestion,
        commit: str,
        locators: dict[str, PurePosixPath],
        technical_link: Callable[[str], str],
        fingerprint: str,
        *,
        authored_locators: dict[str, PurePosixPath] | None = None,
    ) -> bytes:
        self.diagnostics.clear()
        page = locators[rq.wiki_id]
        if not page.is_relative_to(DERIVED) or not is_rq_path(page.relative_to(DERIVED)):
            raise ValueError("RQ reader requires its exact generated preferred route")

        def link(r):
            return record_link(r, locators, page)

        subjects = self.subjects(rq)
        a = rq.presentation_analysis
        active = eligible(rq)
        lines = [
            "# " + literal(rq.title),
            "",
            "## Research Question",
            "",
            literal(rq.presentation_question or rq.title),
            "",
        ]
        if not active:
            lines += [
                "Historical or draft RQ — navigation only; no current scientific analysis.",
                "",
            ]
        lines += [
            " · ".join(technical_link(ref) for ref in subjects)
            if subjects
            else "No exact technical subject bound.",
            "",
            "## Why this matters",
            "",
        ]
        for ref in subjects:
            reason = (
                next((c.why_matters for c in a.subject_contexts if c.target_ref == ref), None)
                if a and active
                else None
            )
            lines += [
                "**"
                + literal(self.atlas.entities[ref].name)
                + ":** "
                + (literal(reason) if reason else "Unavailable — no current authored reason."),
                "",
            ]
        if not subjects:
            lines += ["No exact subject-specific reason available.", ""]
        lines += [
            "## Most relevant literature",
            "",
            "| Paper | Why relevant | Key finding used here | Important limitation | "
            "Read state | Zotero |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in a.literature_rows if a else []:
            paper = self.by_id.get(row.paper_ref)
            context = self.context(rq, row) if active else None
            why = "Unavailable / not explicitly selected"
            statement = limitation = read = why
            if context:
                owner = self.by_id[row.context_owner_ref]
                if eligible(paper) and eligible(owner):
                    why = (
                        "Project-authored"
                        + (
                            " (in review)"
                            if "in_review" in {owner.document_maturity, paper.document_maturity}
                            else ""
                        )
                        + ": "
                        + literal(context.why_relevant)
                    )
                    f = self.by_id.get(context.finding_ref)
                    if (
                        isinstance(f, Finding)
                        and context.finding_ref in rq.finding_refs
                        and self.finding_ok(f, row.paper_ref)
                        and f.presentation_statement
                    ):
                        label = ORIGIN_LABELS[f.claim_origin] + (
                            " (in review)" if f.document_maturity == "in_review" else ""
                        )
                        statement = label + ": " + literal(f.presentation_statement)
                        if f.presentation_limitation:
                            limitation = (
                                (
                                    "Author-reported"
                                    if f.claim_origin.startswith("authors_")
                                    else "Project-authored"
                                )
                                + " limitation: "
                                + literal(f.presentation_limitation)
                            )
                    elif context.finding_ref:
                        self.unavailable(
                            context.finding_ref, "Selected Finding unavailable; no replacement"
                        )
                note = self.by_id.get(context.reading_note_ref)
                if isinstance(note, ReadingNote) and row.paper_ref in (
                    note.paper_refs or note.source_refs
                ):
                    read = (
                        note.reading_depth.replace("_", " ")
                        + "; "
                        + str(note.read_date or "date unavailable")
                        + "; "
                        + ", ".join(sorted(note.checked_sections))
                        + "; "
                        + note.document_maturity.replace("_", " ")
                        + "; Version read: "
                        + self.source.read_label(
                            self.source.resolver.reading(note, self.records), page
                        )
                    )
                elif context.reading_note_ref:
                    self.unavailable(
                        context.reading_note_ref, "Selected ReadingNote unavailable; no replacement"
                    )
            pointer = self.zotero(paper) if isinstance(paper, Paper) else None
            cells = [
                link(paper) if isinstance(paper, Paper) else "Paper unavailable",
                why,
                statement,
                limitation,
                read,
                "[Open Zotero](" + pointer + ")" if pointer else "Unavailable",
            ]
            lines.append("| " + " | ".join(c.replace("\n", "<br>") for c in cells) + " |")
        if not a or not a.literature_rows:
            lines += [
                "",
                "No literature explicitly curated for this RQ. "
                "This does not mean no relevant literature exists.",
            ]
        lines += [
            "",
            "## Nearest work / closest prior art",
            "",
            "Project-authored comparison"
            + (" (in review)." if rq.document_maturity == "in_review" else "."),
            "",
            "| Work | Approach | What it already covers | Remaining difference / limitation | "
            "Competitive relevance |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in a.nearest_work_rows if a else []:
            p = self.by_id.get(row.paper_ref)
            texts = (
                [
                    literal(getattr(row, field)).replace("\n", "<br>")
                    for field in (
                        "approach",
                        "already_covers",
                        "remaining_difference",
                        "competitive_relevance",
                    )
                ]
                if self.comparison_ok(rq, row)
                else ["Unavailable / currently unsupported"] * 4
            )
            lines.append(
                "| "
                + " | ".join([link(p) if isinstance(p, Paper) else "Work unavailable", *texts])
                + " |"
            )
        if not a or not a.nearest_work_rows:
            lines += ["", "No nearest work explicitly compared."]
        lines += ["", "## What the literature currently establishes", ""]
        for item in a.establishes if a else []:
            r = self.by_id.get(item.record_ref)
            if not active or not self.statement_ok(rq, item.record_ref):
                lines += ["- Selected statement unavailable / currently unsupported."]
                continue
            label = (
                ORIGIN_LABELS[r.claim_origin]
                if isinstance(r, Finding)
                else "Project-authored synthesis / inference"
            )
            if r.document_maturity == "in_review":
                label += " (in review)"
            if item.use == "adverse_evidence":
                label += " — Adverse evidence"
            text = r.presentation_statement if isinstance(r, Finding) else r.presentation_summary
            lines += ["- **" + label + ":** " + literal(text) + " (" + link(r) + ")"]
            if r.presentation_limitation:
                limitation_label = (
                    "Author-reported limitation"
                    if isinstance(r, Finding) and r.claim_origin.startswith("authors_")
                    else "Project-authored limitation"
                )
                lines += ["  " + limitation_label + ": " + literal(r.presentation_limitation)]
        if not a or not a.establishes:
            lines += ["No statements explicitly selected."]
        lines += ["", "## Research conclusion", ""]
        current = self.conclusion_ok(rq)
        c = a.conclusion if a else None
        if current:
            lines += [
                literal(c.authored_conclusion),
                "",
                "**Prior work covers:** " + literal(c.prior_work_covers),
                "",
                "**Remaining distinction:** " + literal(c.remaining_distinction),
                "",
                "**Strongest uncertainty / adverse evidence:** " + literal(c.strongest_uncertainty),
                "",
                "**Gap state:** "
                + c.gap_state.replace("_", " ")
                + (
                    " — provisional / in review."
                    if rq.document_maturity == "in_review" and not c.reviewed_by
                    else " — reviewed inputs."
                ),
                "",
            ]
            for field, label in (
                ("falsifiable_test_concept", "Falsifiable test concept"),
                ("contribution_potential", "Contribution potential"),
                ("feasibility_risks", "Feasibility risks"),
                ("project_fit", "Project fit"),
            ):
                if getattr(c, field):
                    lines += ["**" + label + ":** " + literal(getattr(c, field)), ""]
        else:
            lines += [
                "Current research conclusion unavailable / currently unsupported."
                if c
                else "Unassessed — no authored research conclusion.",
                "",
            ]
        lines += [
            "## Next work",
            "",
            literal(c.next_scientific_work)
            if current
            else "No current authored next work available.",
            "",
            "Scientific guidance only; no Research, Experiment or Program authorization.",
            "",
            "## Zotero",
            "",
            "[Open RQ literature corpus](" + a.zotero_corpus.ref + ")"
            if a and a.zotero_corpus
            else "RQ Zotero corpus link unavailable.",
            "",
            "## Sources & audit",
            "",
            "> [!aga-audit]- Full audit",
        ]
        audit = [
            "Source repository: Planton361/autonomous-game-agent; exact commit: " + commit,
            "[Generated manifest / all three input fingerprints](../manifest/direct-views.yaml)",
            "Presentation fingerprint 1.1: " + fingerprint,
            "Authored RQ input: " + record_link(rq, authored_locators or {}, page),
            "Exact RQ binding: "
            + rq.wiki_id
            + "; revision "
            + str(rq.record_version)
            + "; declaring property research_direct_subject_refs (RA-2 0.3 only).",
            *(ref + "; actual Atlas type " + self.atlas.entities[ref].type for ref in subjects),
            "",
            "Diagnostics:",
            *(literal(diagnostic) for diagnostic in sorted(self.diagnostics)),
            "",
            "Exact structured inputs (historical wording retained; no automatic successors):",
            "```json",
            json.dumps(
                [
                    presentation_inputs((r,))[0]
                    for r in sorted(self.records, key=lambda r: r.wiki_id)
                    if r.wiki_id
                    in self.dependencies(rq)
                    | {rq.wiki_id}
                    | set(rq.review_refs)
                    | set(rq.decision_refs)
                ],
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ),
            "```",
            "",
            "Selected source provenance:",
        ]
        visible_warnings = set()
        for ref in sorted(self.dependencies(rq)):
            record = self.by_id.get(ref)
            if isinstance(record, (Paper, ReadingNote)):
                binding = (
                    self.source.resolver.paper(record)
                    if isinstance(record, Paper)
                    else self.source.resolver.reading(record, self.records)
                )
                summary = self.source.summary(binding, page)
                # Warnings are visible alongside authored science; they never mutate it.
                warnings = [line for line in summary if line.startswith("**Warning")]
                visible_warnings.update(warnings)
                audit += [link(record), *summary]
            if isinstance(record, SearchRecord):
                audit += [
                    link(record)
                    + "; search date "
                    + str(record.search_date or "unavailable")
                    + (
                        "; exact RQ target"
                        if rq.wiki_id in record.target_refs
                        else "; unavailable: not exact RQ target"
                    )
                ]
        if visible_warnings:
            insert = lines.index("## Research conclusion")
            lines[insert:insert] = [*sorted(visible_warnings), ""]
        lines += ["> " + line if line else ">" for item in audit for line in item.split("\n")]
        lines += [
            "",
            "## Return Navigation",
            "",
            *("- " + technical_link(ref) for ref in subjects),
            "",
        ]
        metadata = dict(
            generated_by="research-wiki-derived",
            rq_reader_schema_version="1.0",
            rq_subject=rq.wiki_id,
            rq_page_path=str(page.relative_to(DERIVED)),
            source_commit=commit,
            privacy="private",
            export_policy="deny",
        )
        return (
            "\n".join(lines) + "\n" + RQ_METADATA_MARKER + yaml_text(metadata) + "-->\n"
        ).encode()
