"""Legacy identity envelope and opt-in flat RA-2 contracts; no claim adjudication."""

import re
from collections.abc import Iterable, Mapping, Set
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

WIKI_PREFIXES = {
    "dossier": "DOS",
    "process": "PROC",
    "topic": "TOPIC",
    "reading_note": "READ",
    "synthesis": "SYN",
    "search_record": "SEARCH",
    "journal_entry": "JOURNAL",
    "paper": "WPAPER",
    "finding": "WFIND",
    "research_question": "WRQ",
    "experiment_lead": "WLEAD",
    "research_thread": "WTHREAD",
    "decision_draft": "WDEC",
}


class WikiRecord(BaseModel):
    """Only the declared envelope is modeled; other authored properties stay opaque."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    wiki_schema_version: Literal["0.1"]
    wiki_id: str
    doc_type: str
    privacy: Literal["private"]
    export_policy: Literal["deny"]
    atlas_refs: list[str]

    @model_validator(mode="after")
    def identity(self) -> "WikiRecord":
        prefix = WIKI_PREFIXES.get(self.doc_type)
        if prefix is None or not re.fullmatch(prefix + r"-[A-Z0-9]+(?:-[A-Z0-9]+)*", self.wiki_id):
            raise ValueError("wiki_id prefix must match a supported doc_type")
        return self


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Texts = Annotated[list[Text], Field(strict=True)]
NonemptyRefs = Annotated[Texts, Field(min_length=1)]
OneRef = Annotated[Texts, Field(min_length=1, max_length=1)]
QuestionStage = Literal["idea", "researchable", "literature_mapped", "candidate", "needs_closure"]
DecisionState = Literal["none", "accepted", "deprioritized", "killed", "superseded"]


class EpistemicRecord(WikiRecord):
    """Explicit RA-2 profile. Body adequacy and actual review remain human gates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    epistemic_schema_version: Literal["0.1"]
    title: Text
    record_version: int = Field(strict=True, gt=0)
    document_maturity: Literal["draft", "in_review", "domain_accepted", "superseded", "archived"]
    atlas_refs: Texts
    aliases: Texts = Field(default_factory=list)
    tags: Texts = Field(default_factory=list)
    wiki_refs: Texts = Field(default_factory=list)
    supersedes_refs: Texts = Field(default_factory=list)
    review_refs: Texts = Field(default_factory=list)
    research_direct_subject_refs: Texts = Field(default_factory=list)
    research_method_or_baseline_refs: Texts = Field(default_factory=list)
    research_measurement_relevance_refs: Texts = Field(default_factory=list)
    research_project_transfer_refs: Texts = Field(default_factory=list)
    research_adjacent_context_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def lineage(self) -> "EpistemicRecord":
        if self.document_maturity == "superseded" and not self.supersedes_refs:
            raise ValueError("superseded document requires explicit supersedes_refs lineage")
        return self


class Dossier(EpistemicRecord):
    doc_type: Literal["dossier"]
    subject_refs: Texts = Field(default_factory=list)
    process_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)
    finding_refs: Texts = Field(default_factory=list)
    paper_refs: Texts = Field(default_factory=list)
    decision_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def subject(self) -> "Dossier":
        if not (self.atlas_refs or self.subject_refs):
            raise ValueError("Dossier requires atlas_refs or subject_refs")
        return self


class Process(EpistemicRecord):
    doc_type: Literal["process"]
    input_refs: Texts = Field(default_factory=list)
    output_refs: Texts = Field(default_factory=list)
    measurement_refs: Texts = Field(default_factory=list)
    preceding_process_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)


class Topic(EpistemicRecord):
    doc_type: Literal["topic"]
    synonyms: Texts = Field(default_factory=list)
    paper_refs: Texts = Field(default_factory=list)
    finding_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)
    process_refs: Texts = Field(default_factory=list)


class ReadingNote(EpistemicRecord):
    doc_type: Literal["reading_note"]
    paper_refs: Texts = Field(default_factory=list)
    source_refs: Texts = Field(default_factory=list)
    version_read: Text | None
    read_date: date | None
    reading_depth: Literal[
        "lead_only",
        "metadata_checked",
        "abstract_checked",
        "methods_checked",
        "results_checked",
        "relevant_fulltext_checked",
    ]
    checked_sections: Annotated[
        list[
            Literal[
                "metadata",
                "abstract",
                "methods",
                "results",
                "discussion",
                "limitations",
                "supplement",
                "other",
            ]
        ],
        Field(strict=True),
    ]
    finding_refs: Texts = Field(default_factory=list)
    search_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def reading(self) -> "ReadingNote":
        # Presence of both source properties is ambiguous even if one is empty.
        if {"paper_refs", "source_refs"} <= self.model_fields_set or len(self.paper_refs) + len(
            self.source_refs
        ) != 1:
            raise ValueError("ReadingNote requires exactly one paper_refs OR source_refs identity")
        if self.reading_depth == "lead_only":
            if self.checked_sections or self.read_date is not None:
                raise ValueError("lead_only requires empty checked_sections and null read_date")
        else:
            if self.version_read is None or self.read_date is None:
                raise ValueError("Checked reading requires version_read and read_date")
            section = self.reading_depth.removesuffix("_checked")
            if section == "relevant_fulltext":
                if not self.checked_sections:
                    raise ValueError("relevant_fulltext_checked requires checked_sections")
            elif section not in self.checked_sections:
                raise ValueError("reading_depth requires its named checked section")
        return self


class Synthesis(EpistemicRecord):
    doc_type: Literal["synthesis"]
    finding_refs: NonemptyRefs
    search_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)
    decision_refs: Texts = Field(default_factory=list)


class SearchRecord(EpistemicRecord):
    doc_type: Literal["search_record"]
    target_refs: NonemptyRefs
    search_date: date | None
    result_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def execution_date(self) -> "SearchRecord":
        if self.document_maturity != "draft" and self.search_date is None:
            raise ValueError("Non-draft SearchRecord requires search_date")
        return self


class JournalEntry(EpistemicRecord):
    doc_type: Literal["journal_entry"]
    entry_date: date
    participant_refs: Texts = Field(default_factory=list)
    source_refs: Texts = Field(default_factory=list)
    resulting_object_refs: Texts = Field(default_factory=list)


class Paper(EpistemicRecord):
    doc_type: Literal["paper"]
    source_refs: NonemptyRefs
    doi: Text | None = None
    url: Text | None = None
    authors: Texts = Field(default_factory=list)
    publication_year: int | None = Field(default=None, strict=True, gt=0)
    venue: Text | None = None
    reading_note_refs: Texts = Field(default_factory=list)
    related_version_refs: Texts = Field(default_factory=list)


class Finding(EpistemicRecord):
    doc_type: Literal["finding"]
    claim_origin: Literal[
        "authors_result", "authors_limitation", "our_inference", "own_empirical_result"
    ]
    review_state: Literal["draft", "checked", "domain_accepted"]
    source_refs: NonemptyRefs
    reading_note_refs: Texts = Field(default_factory=list)
    supports_refs: Texts = Field(default_factory=list)
    contradicts_refs: Texts = Field(default_factory=list)
    qualifies_refs: Texts = Field(default_factory=list)
    rq_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def author_source(self) -> "Finding":
        if (
            self.claim_origin in {"authors_result", "authors_limitation"}
            and not self.reading_note_refs
        ):
            raise ValueError("Author Finding requires reading_note_refs")
        return self


class Candidate(EpistemicRecord):
    """Structural combinations only, not transition adjudication or authorization."""

    question_stage: QuestionStage
    decision_state: DecisionState
    search_refs: Texts = Field(default_factory=list)
    synthesis_refs: Texts = Field(default_factory=list)
    finding_refs: Texts = Field(default_factory=list)
    decision_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def decision(self) -> "Candidate":
        if self.decision_state != "none" and not self.decision_refs:
            raise ValueError("Candidate decision_state requires decision_refs")
        if self.decision_state == "accepted" and self.question_stage != "candidate":
            raise ValueError("accepted decision_state requires candidate question_stage")
        return self


class ResearchQuestion(Candidate):
    doc_type: Literal["research_question"]
    experiment_lead_refs: Texts = Field(default_factory=list)


class ExperimentLead(Candidate):
    doc_type: Literal["experiment_lead"]
    rq_refs: NonemptyRefs
    measurement_refs: Texts = Field(default_factory=list)


class ResearchThread(EpistemicRecord):
    doc_type: Literal["research_thread"]
    ordered_refs: NonemptyRefs
    rq_refs: Texts = Field(default_factory=list)
    process_refs: Texts = Field(default_factory=list)
    finding_refs: Texts = Field(default_factory=list)


class DecisionDraft(EpistemicRecord):
    doc_type: Literal["decision_draft"]
    decision_type: Text
    decision_scope: Literal[
        "research_candidate", "program", "study_protocol", "technical_reference"
    ]
    subject_refs: OneRef
    decision_record_state: Literal["draft", "recorded"]
    search_refs: Texts = Field(default_factory=list)
    synthesis_refs: Texts = Field(default_factory=list)
    authority_refs: Texts = Field(default_factory=list)
    overrules_refs: Texts = Field(default_factory=list)

    @model_validator(mode="after")
    def authority(self) -> "DecisionDraft":
        if self.decision_record_state == "recorded" and not self.authority_refs:
            raise ValueError("recorded Decision requires authority_refs")
        return self


EpistemicProfile = Annotated[
    Dossier
    | Process
    | Topic
    | ReadingNote
    | Synthesis
    | SearchRecord
    | JournalEntry
    | Paper
    | Finding
    | ResearchQuestion
    | ExperimentLead
    | ResearchThread
    | DecisionDraft,
    Field(discriminator="doc_type"),
]
EPISTEMIC_ADAPTER = TypeAdapter(EpistemicProfile)


def validate_wiki_records(
    properties: Iterable[Mapping[str, object]], atlas_ids: Set[str]
) -> tuple[WikiRecord, ...]:
    """Validate declared notes without mutating Atlas, properties, or authored bytes."""
    records = []
    seen: set[str] = set()
    for props in properties:
        if not ({"wiki_schema_version", "wiki_id", "epistemic_schema_version"} & props.keys()):
            continue
        if "atlas_id" in props:
            raise ValueError("Private Wiki envelope must not declare atlas_id")
        record = (
            EPISTEMIC_ADAPTER.validate_python(props)
            if "epistemic_schema_version" in props
            else WikiRecord.model_validate(props)
        )
        if record.wiki_id in atlas_ids:
            raise ValueError("wiki_id must be distinct from public Atlas identity")
        if record.wiki_id in seen:
            raise ValueError("Duplicate private wiki_id; assign distinct identities")
        if any(ref not in atlas_ids for ref in record.atlas_refs):
            raise ValueError("Dangling atlas_refs; use current public Atlas IDs")
        seen.add(record.wiki_id)
        records.append(record)
    return tuple(records)
