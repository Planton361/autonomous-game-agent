"""Committed fictional private #119 dataset; serialize only in a disposable vault."""

from test_research_wiki_schema import props

from fh_agent.research_atlas.wiki_schema import validate_wiki_records


def fictional_graph_records(atlas):
    memory = "CMP-MEM-RETRIEVAL"
    return validate_wiki_records(
        [
            props(
                "paper",
                title="Fictional Cedar retrieval",
                document_maturity="in_review",
                reading_note_refs=["READ-FIXTURE", "READ-FIXTURE"],
                research_direct_subject_refs=[memory, "CMP-CORTEX", memory],
                source_refs=["srcf-fiction"],
            ),
            props(
                "reading_note",
                title="Fictional Cedar reading",
                document_maturity="in_review",
                finding_refs=["WFIND-FIXTURE"],
                research_method_or_baseline_refs=[memory],
            ),
            props(
                "finding",
                title="Fictional Cedar limitation",
                document_maturity="in_review",
                source_refs=["WPAPER-FIXTURE"],
                reading_note_refs=["READ-FIXTURE"],
                research_adjacent_context_refs=[memory],
                review_state="checked",
            ),
            props(
                "synthesis", title="Fictional retrieval synthesis", document_maturity="in_review"
            ),
            props(
                "topic",
                title="Fictional explicit retrieval topic",
                document_maturity="in_review",
                paper_refs=["WPAPER-FIXTURE"],
                finding_refs=["WFIND-FIXTURE"],
            ),
            props(
                "research_question",
                title="Fictional multi-target question",
                document_maturity="in_review",
                epistemic_schema_version="0.3",
                research_direct_subject_refs=[
                    memory,
                    "CMP-CORTEX",
                    "CMP-MEM-FACTS",
                    "IF-MEM-CORTEX",
                ],
            ),
            props("decision_draft", title="Fictional excluded Decision"),
            props(
                "paper",
                wiki_id="WPAPER-OTHER",
                title="Fictional other exact scope",
                document_maturity="in_review",
                research_direct_subject_refs=["IF-MEM-CORTEX"],
            ),
            props(
                "topic",
                wiki_id="TOPIC-UNSUPPORTED",
                title="Fictional unlinked topic",
                document_maturity="in_review",
                tags=["retrieval"],
            ),
            props(
                "synthesis",
                wiki_id="SYN-UNRELATED",
                title="Fictional unrelated synthesis",
                document_maturity="in_review",
                finding_refs=["WFIND-UNRELATED"],
            ),
        ],
        atlas.entities.keys(),
    )
