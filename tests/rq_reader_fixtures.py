"""Fictional #125 reader inputs; never production research or scientific evidence."""

from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.source_presentation import SourceReader
from fh_agent.research_atlas.source_resolution import SourceCatalog, SourceResolver
from fh_agent.research_atlas.wiki_schema import validate_wiki_records


def fictional_catalog():
    return SourceCatalog.model_validate(
        dict(
            source_catalog_schema_version="1.0",
            privacy="private",
            export_policy="deny",
            families=[
                dict(
                    source_family_id="srcf-cedar",
                    title="Cedar — fictional prior art",
                    preferred_version_ref="srcv-cedar2",
                )
            ],
            versions=[
                dict(
                    source_version_id="srcv-cedar1",
                    source_family_ref="srcf-cedar",
                    label="Checked version 1",
                    kind="preprint",
                    status="available",
                    availability="available",
                ),
                dict(
                    source_version_id="srcv-cedar2",
                    source_family_ref="srcf-cedar",
                    label="Navigation version 2",
                    kind="published",
                    status="available",
                    availability="available",
                ),
            ],
            bindings=[
                dict(
                    scheme="opaque",
                    value="zotero://select/library/items/CEDAR001",
                    target_ref="srcf-cedar",
                )
            ],
        )
    )


def fictional_properties(gap="narrowing_required"):
    common = dict(
        wiki_schema_version="0.1",
        epistemic_schema_version="0.3",
        record_version=1,
        document_maturity="domain_accepted",
        privacy="private",
        export_policy="deny",
        atlas_refs=[],
    )
    rq_id = "WRQ-OBSERVER"
    paper = dict(
        common,
        wiki_id="WPAPER-CEDAR",
        doc_type="paper",
        title="Cedar — fictional observer",
        source_refs=["srcf-cedar"],
        research_direct_subject_refs=[rq_id],
        presentation_contexts=[
            dict(
                role="research_direct_subject_refs",
                target_ref=rq_id,
                why_relevant="Tests recovery from short visible interruptions.",
                finding_ref="WFIND-CEDAR",
                reading_note_ref="READ-CEDAR",
            )
        ],
    )
    note = dict(
        common,
        wiki_id="READ-CEDAR",
        doc_type="reading_note",
        title="Cedar reading",
        paper_refs=["WPAPER-CEDAR"],
        version_read="srcv-cedar1",
        read_date="2026-10-01",
        reading_depth="results_checked",
        checked_sections=["results", "limitations"],
    )
    finding = dict(
        common,
        wiki_id="WFIND-CEDAR",
        doc_type="finding",
        title="Cedar recovery result",
        source_refs=["WPAPER-CEDAR"],
        reading_note_refs=["READ-CEDAR"],
        claim_origin="authors_result",
        review_state="domain_accepted",
        presentation_statement="Cedar recovers after short observation interruptions.",
        presentation_limitation="The fictional evaluation excludes prolonged disappearance.",
        presentation_source_locations=[
            dict(reading_note_ref="READ-CEDAR", page="4", section="Results")
        ],
    )
    inference = dict(
        common,
        wiki_id="WFIND-INFERENCE",
        doc_type="finding",
        title="Project interpretation",
        source_refs=["WPAPER-CEDAR"],
        claim_origin="our_inference",
        review_state="domain_accepted",
        presentation_statement="Broad recovery alone does not isolate a distinction.",
    )
    synthesis = dict(
        common,
        wiki_id="SYN-OBSERVER",
        doc_type="synthesis",
        title="Observer synthesis",
        finding_refs=["WFIND-CEDAR", "WFIND-INFERENCE"],
        rq_refs=[rq_id],
        presentation_summary="The proposed question needs one bounded observable condition.",
    )
    conclusions = {
        "narrowing_required": "The broad recovery question needs a narrower observable condition.",
        "candidate_gap": (
            "One bounded observable-only condition remains unresolved under "
            "this reviewed comparison."
        ),
        "covered_by_prior_art": "Cedar already covers the stated short-interruption question.",
        "insufficient_evidence": (
            "The available curated evidence is insufficient for a gap assessment."
        ),
        "unassessed": "The question has not yet been scientifically assessed.",
    }
    c = dict(
        question_version=1,
        gap_state=gap,
        authored_conclusion=conclusions[gap],
        prior_work_covers="Recovery after a fixed short interruption.",
        remaining_distinction="Prolonged missing visible evidence remains unassessed.",
        strongest_uncertainty="Cedar may cover the narrowed condition upon further checking.",
        next_scientific_work=(
            "Compare the exact missing-evidence condition with the checked source."
        ),
        evidence_refs=["WFIND-CEDAR", "SYN-OBSERVER"],
        as_of="2026-10-01",
        author="Fictional analyst",
        reviewed_by=["Fictional reviewer"],
        reviewed_inputs=[],
    )
    if gap == "candidate_gap":
        c.update(
            falsifiable_test_concept=(
                "No calibration advantage may remain under matched restrictions."
            ),
            contribution_potential="Clarify calibration under a visible-only restriction.",
            feasibility_risks="Suitable evaluation access remains uncertain.",
            project_fit="Relates to the observer's visible-evidence responsibility.",
        )
    rq = dict(
        common,
        wiki_id=rq_id,
        doc_type="research_question",
        title="Recovery under missing observations",
        presentation_question=(
            "Can a visible-only observer recover state after a prolonged interruption?"
        ),
        question_stage="literature_mapped",
        decision_state="none",
        research_direct_subject_refs=["CMP-OBSERVATION-BUILDER", "CMP-TEMPORAL-STATE"],
        finding_refs=["WFIND-CEDAR", "WFIND-INFERENCE"],
        synthesis_refs=["SYN-OBSERVER"],
        review_refs=["JOURNAL-OBSERVER"],
        presentation_analysis=dict(
            subject_contexts=[
                dict(
                    target_ref="CMP-OBSERVATION-BUILDER",
                    why_matters=(
                        "Observation assembly must preserve uncertainty when visible "
                        "evidence disappears."
                    ),
                ),
                dict(
                    target_ref="CMP-TEMPORAL-STATE",
                    why_matters=(
                        "Temporal state must distinguish stale evidence from current observations."
                    ),
                ),
            ],
            literature_rows=[
                dict(
                    paper_ref="WPAPER-CEDAR",
                    context_owner_ref="WPAPER-CEDAR",
                    context_role="research_direct_subject_refs",
                )
            ],
            nearest_work_rows=[
                dict(
                    paper_ref="WPAPER-CEDAR",
                    approach="Retains the latest visible observation.",
                    already_covers="Short fixed interruptions.",
                    remaining_difference="Prolonged disappearance is outside the checked scope.",
                    competitive_relevance="Covers much of the broad baseline.",
                    evidence_refs=["WFIND-CEDAR"],
                )
            ],
            establishes=[
                dict(record_ref="WFIND-CEDAR", use="adverse_evidence"),
                dict(record_ref="WFIND-INFERENCE", use="knowledge"),
                dict(record_ref="SYN-OBSERVER", use="knowledge"),
            ],
            conclusion=c,
            zotero_corpus=dict(
                kind="collection", ref="zotero://select/library/collections/OBSRV001"
            ),
        ),
    )
    review = dict(
        common,
        wiki_id="JOURNAL-OBSERVER",
        doc_type="journal_entry",
        title="Fictional review attestation",
        entry_date="2026-10-01",
        resulting_object_refs=[rq_id],
    )
    return [rq, paper, note, finding, inference, synthesis, review]


def fictional_records(atlas, gap="narrowing_required"):
    data = fictional_properties(gap)
    records = validate_wiki_records(data, atlas.entities.keys())
    reader = RQReader(atlas, records, SourceReader(SourceResolver(fictional_catalog())))
    data[0]["presentation_analysis"]["conclusion"]["reviewed_inputs"] = [
        dict(ref=ref, record_version=reader.by_id[ref].record_version)
        for ref in sorted(reader.dependencies(records[0]))
    ]
    return validate_wiki_records(data, atlas.entities.keys())
