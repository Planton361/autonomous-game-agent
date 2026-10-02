"""Closed #124 opt-in reader inputs; no scientific or operational adjudication."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Text = Annotated[str, StringConstraints(strict=True, min_length=1)]
Ref = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]*$")]
Role = Literal[
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
]
GapState = Literal[
    "unassessed",
    "insufficient_evidence",
    "covered_by_prior_art",
    "narrowing_required",
    "candidate_gap",
]


def zotero_pointer(value: str, kind: str) -> bool:
    segment = {"collection": "collections", "saved_search": "searches", "item": "items"}[kind]
    key = r"[A-Z0-9]{8}"
    native = rf"zotero://select/(?:library|groups/[1-9][0-9]*)/{segment}/{key}"
    web = rf"https://www\.zotero\.org/groups/[1-9][0-9]*/{segment}/{key}"
    return re.fullmatch(native + ("|" + web if kind != "saved_search" else ""), value) is not None


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def literals(self) -> "Closed":
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and (
                not value.strip() or any(ord(c) < 32 and c != "\n" for c in value)
            ):
                raise ValueError("Nonblank safe literal required")
            if name.endswith("_refs") or name == "reviewed_by":
                if len(value) != len(set(value)):
                    raise ValueError("Duplicate set declaration")
        return self


class SubjectContext(Closed):
    target_ref: Ref
    why_matters: Text


class LiteratureRow(Closed):
    paper_ref: Ref
    context_owner_ref: Ref
    context_role: Role


class NearestWorkRow(Closed):
    paper_ref: Ref
    approach: Text
    already_covers: Text
    remaining_difference: Text
    competitive_relevance: Text
    evidence_refs: Annotated[list[Ref], Field(strict=True, min_length=1)]


class EstablishesItem(Closed):
    record_ref: Ref
    use: Literal["knowledge", "adverse_evidence"]


class ReviewedInput(Closed):
    ref: Ref
    record_version: int = Field(strict=True, gt=0)


class Conclusion(Closed):
    question_version: int = Field(strict=True, gt=0)
    gap_state: GapState
    authored_conclusion: Text
    prior_work_covers: Text
    remaining_distinction: Text
    strongest_uncertainty: Text
    next_scientific_work: Text
    evidence_refs: list[Ref] = Field(default_factory=list, strict=True)
    falsifiable_test_concept: Text | None = None
    contribution_potential: Text | None = None
    feasibility_risks: Text | None = None
    project_fit: Text | None = None
    as_of: date
    author: Text
    reviewed_by: list[Text] = Field(default_factory=list, strict=True)
    reviewed_inputs: list[ReviewedInput] = Field(default_factory=list, strict=True)

    @field_validator("as_of", mode="before")
    @classmethod
    def iso_date(cls, value):
        if (
            type(value) is date
            or isinstance(value, str)
            and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
        ):
            return value
        raise ValueError("Exact ISO date required")

    @model_validator(mode="after")
    def candidate(self) -> "Conclusion":
        if self.gap_state == "candidate_gap" and not all(
            (
                self.falsifiable_test_concept,
                self.contribution_potential,
                self.feasibility_risks,
                self.project_fit,
            )
        ):
            raise ValueError("candidate_gap requires four authored rationale fields")
        if len({r.ref for r in self.reviewed_inputs}) != len(self.reviewed_inputs):
            raise ValueError("Duplicate reviewed identity")
        return self


class ZoteroCorpus(Closed):
    kind: Literal["collection", "saved_search"]
    ref: Text

    @model_validator(mode="after")
    def pointer(self) -> "ZoteroCorpus":
        if not zotero_pointer(self.ref, self.kind):
            raise ValueError("Unsupported exact Zotero corpus pointer")
        return self


class PresentationAnalysis(Closed):
    subject_contexts: list[SubjectContext] = Field(default_factory=list, strict=True)
    literature_rows: list[LiteratureRow] = Field(default_factory=list, strict=True)
    nearest_work_rows: list[NearestWorkRow] = Field(default_factory=list, strict=True)
    establishes: list[EstablishesItem] = Field(default_factory=list, strict=True)
    conclusion: Conclusion | None = None
    zotero_corpus: ZoteroCorpus | None = None

    @model_validator(mode="after")
    def unique_rows(self) -> "PresentationAnalysis":
        for values in (
            [c.target_ref for c in self.subject_contexts],
            [r.paper_ref for r in self.literature_rows],
            [r.paper_ref for r in self.nearest_work_rows],
            [(r.record_ref, r.use) for r in self.establishes],
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate authored selection")
        return self


class SourceLocation(Closed):
    reading_note_ref: Ref
    page: Text | None = None
    section: Text | None = None

    @model_validator(mode="after")
    def locator(self) -> "SourceLocation":
        if self.page is None and self.section is None:
            raise ValueError("Source location requires page or section")
        return self
