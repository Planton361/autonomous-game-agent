"""RA-1 private identity/reference envelope; no scientific or runtime semantics."""

import re
from collections.abc import Iterable, Mapping, Set
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

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


def validate_wiki_records(
    properties: Iterable[Mapping[str, object]], atlas_ids: Set[str]
) -> tuple[WikiRecord, ...]:
    """Validate declared notes without mutating Atlas, properties, or authored bytes."""
    records = []
    seen: set[str] = set()
    for props in properties:
        if not ({"wiki_schema_version", "wiki_id"} & props.keys()):
            continue
        if "atlas_id" in props:
            raise ValueError("Private Wiki envelope must not declare atlas_id")
        record = WikiRecord.model_validate(props)
        if record.wiki_id in atlas_ids:
            raise ValueError("wiki_id must be distinct from public Atlas identity")
        if record.wiki_id in seen:
            raise ValueError("Duplicate private wiki_id; assign distinct identities")
        if any(ref not in atlas_ids for ref in record.atlas_refs):
            raise ValueError("Dangling atlas_refs; use current public Atlas IDs")
        seen.add(record.wiki_id)
        records.append(record)
    return tuple(records)
