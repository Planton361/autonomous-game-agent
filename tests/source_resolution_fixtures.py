"""Committed fictional G4 inputs, never actual Research/source data."""

import json
from pathlib import Path, PurePosixPath

from fh_agent.research_atlas.source_resolution import SourceCatalog
from fh_agent.research_atlas.wiki_schema import validate_wiki_records

FIXTURE = Path(__file__).parent / "fixtures/source-resolution/catalog.json"


def synthetic_catalog() -> SourceCatalog:
    return SourceCatalog.model_validate(json.loads(FIXTURE.read_text()))


def synthetic_records():
    envelope = dict(
        wiki_schema_version="0.1",
        epistemic_schema_version="0.2",
        record_version=1,
        document_maturity="domain_accepted",
        privacy="private",
        export_policy="deny",
        atlas_refs=[],
    )
    paper = dict(
        envelope,
        wiki_id="WPAPER-SOURCE-PROOF",
        doc_type="paper",
        title="Synthetic — Hierarchical Visual State Representations",
        source_refs=["srcf-a7k2"],
        related_version_refs=["srcv-b8q3", "srcv-c9r4"],
        authors=["Mira Example", "Theo Fiction"],
        publication_year=2025,
        reading_note_refs=["READ-SOURCE-PROOF"],
        research_direct_subject_refs=["CMP-OBSERVATION-BUILDER"],
        presentation_contexts=[
            dict(
                role="research_direct_subject_refs",
                target_ref="CMP-OBSERVATION-BUILDER",
                why_relevant=(
                    "Fictional example for inspecting exact visual-state source provenance."
                ),
                reading_note_ref="READ-SOURCE-PROOF",
                finding_ref="WFIND-SOURCE-PROOF",
            )
        ],
    )
    reading = dict(
        envelope,
        wiki_id="READ-SOURCE-PROOF",
        doc_type="reading_note",
        title="Synthetic — Reading Preprint v1",
        paper_refs=["WPAPER-SOURCE-PROOF"],
        version_read="srcv-b8q3",
        read_date="2026-09-25",
        reading_depth="methods_checked",
        checked_sections=["methods"],
        finding_refs=["WFIND-SOURCE-PROOF"],
    )
    finding = dict(
        envelope,
        wiki_id="WFIND-SOURCE-PROOF",
        doc_type="finding",
        title="Synthetic — Attributed observation",
        source_refs=["WPAPER-SOURCE-PROOF"],
        reading_note_refs=["READ-SOURCE-PROOF"],
        claim_origin="authors_result",
        review_state="domain_accepted",
        presentation_statement="Fictional source-reported observation.",
        presentation_limitation="Synthetic illustration; no scientific result is asserted.",
    )
    unresolved = dict(
        envelope,
        wiki_id="WPAPER-SOURCE-UNRESOLVED",
        doc_type="paper",
        title="Synthetic — Unresolved source reference",
        source_refs=["opaque-source-unresolved"],
    )
    conflict = dict(
        envelope,
        wiki_id="WPAPER-SOURCE-CONFLICT",
        doc_type="paper",
        title="Synthetic — Conflicting exact aliases",
        source_refs=["doi:10.9999/fictional-collision"],
    )
    cross = dict(
        envelope,
        wiki_id="WPAPER-SOURCE-CROSS",
        doc_type="paper",
        title="Synthetic — Rejected cross-family preference",
        source_refs=["srcf-f6p3"],
    )
    return tuple(
        validate_wiki_records([paper, reading, finding, unresolved, conflict, cross], set())
    )


def synthetic_locators(records):
    return {r.wiki_id: PurePosixPath("authored") / (r.wiki_id + ".md") for r in records}
