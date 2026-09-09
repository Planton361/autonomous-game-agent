"""Closed Atlas vocabulary. Domain membership has presentation authority only."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TechnicalStatus(Record):
    architecture_authority: Literal[
        "canonical-target", "implementation-derived", "project-decision", "unknown"
    ]
    implementation_status: Literal["target-only", "partial", "implemented", "deprecated", "unknown"]
    verification_status: Literal[
        "unverified",
        "unit-tested",
        "integration-tested",
        "live-demonstrated",
        "measurement-validated",
        "unknown",
    ]


class Identity(Record):
    id: Text
    name: Text
    description: Text
    research_mapping: Literal[
        "unmapped", "leads-collected", "primary-partially-checked", "focused-review-complete"
    ] = "unmapped"
    research_direction: (
        Literal["open-lead", "needs-closure", "deprioritized", "killed", "active-candidate"] | None
    ) = None


class TechnicalIdentity(Identity):
    technical: TechnicalStatus


class System(TechnicalIdentity):
    type: Literal["System"]


class Domain(Identity):
    type: Literal["Domain"]
    grouping_semantics: Literal["presentation / navigation grouping"]


class Component(TechnicalIdentity):
    type: Literal["Component"]


class Interface(TechnicalIdentity):
    type: Literal["Interface"]


class Contract(TechnicalIdentity):
    type: Literal["Contract"]


class DataArtifact(TechnicalIdentity):
    type: Literal["DataArtifact"]


class MeasurementPoint(TechnicalIdentity):
    type: Literal["MeasurementPoint"]


class Environment(TechnicalIdentity):
    type: Literal["Environment"]


class ResearchQuestion(Identity):
    type: Literal["ResearchQuestion"]


class ResearchThread(Identity):
    type: Literal["ResearchThread"]
    ordered_refs: tuple[Text, ...]


class Paper(Identity):
    type: Literal["Paper"]


class Finding(Identity):
    type: Literal["Finding"]


class Decision(Identity):
    type: Literal["Decision"]
    decision_scope: Literal["architecture", "research", "project", "tooling"]


class ExperimentLead(Identity):
    type: Literal["ExperimentLead"]


class Evidence(Identity):
    type: Literal["Evidence"]
    provenance_kind: Literal[
        "canonical_project_source",
        "github_implementation",
        "primary_literature",
        "scientific_project_artifact",
        "chat_historical_context",
        "synthesis_inference",
        "project_decision",
    ]
    checked_date: date
    repository: Text | None = None
    ref: Text | None = None
    path: Text | None = None
    symbol: Text | None = None
    line: int | None = Field(default=None, gt=0)
    document: Text | None = None
    version: Text | None = None
    section: Text | None = None
    page: Text | None = None
    figure: Text | None = None
    table: Text | None = None
    quote_or_paraphrase_location: Text | None = None

    @model_validator(mode="after")
    def require_locator(self) -> "Evidence":
        if self.provenance_kind == "github_implementation":
            if not (self.repository and self.ref and self.path and (self.symbol or self.line)):
                raise ValueError("GitHub evidence requires repository/ref/path and symbol or line")
        elif not (
            self.document
            and self.version
            and any(
                (
                    self.section,
                    self.page,
                    self.figure,
                    self.table,
                    self.quote_or_paraphrase_location,
                )
            )
        ):
            raise ValueError("Document evidence requires document/version and concrete locator")
        return self


Node = Annotated[
    System
    | Domain
    | Component
    | Interface
    | Contract
    | DataArtifact
    | MeasurementPoint
    | Environment
    | ResearchQuestion
    | ResearchThread
    | Paper
    | Finding
    | Decision
    | ExperimentLead,
    Field(discriminator="type"),
]
Entity = Node | Evidence

PREFIXES = {
    "System": "SYS",
    "Domain": "DOM",
    "Component": "CMP",
    "Interface": "IF",
    "Contract": "CON",
    "DataArtifact": "DAT",
    "MeasurementPoint": "MEAS",
    "Environment": "ENV",
    "ResearchQuestion": "RQ",
    "ResearchThread": "THREAD",
    "Paper": "PAPER",
    "Finding": "FIND",
    "Evidence": "EVID",
    "Decision": "DEC",
    "ExperimentLead": "LEAD",
}


RelationName = Literal[
    "part_of",
    "supplies",
    "consumes",
    "controls",
    "constrains",
    "proposes_to",
    "grounds",
    "executes",
    "observes",
    "verifies",
    "updates",
    "retrieves_from",
    "measured_at",
    "studied_by",
    "supports",
    "contradicts",
    "derived_from",
    "supersedes",
    "decomposed_into",
    "research_suggests_decomposition",
    "related_to_research_question",
    "presented_in_domain",
]


class Relationship(Record):
    relation: RelationName
    source: Text
    target: Text
    decision_id: Text | None = None


class NodeRegistry(Record):
    atlas_schema_version: Literal["0.1"]
    nodes: tuple[Node, ...]


class EvidenceRegistry(Record):
    atlas_schema_version: Literal["0.1"]
    evidence: tuple[Evidence, ...]


class RelationshipRegistry(Record):
    atlas_schema_version: Literal["0.1"]
    relationships: tuple[Relationship, ...]
