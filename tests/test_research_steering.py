"""Fictional #126 proof; no production Research or private Vault access."""

from copy import deepcopy
from pathlib import Path, PurePosixPath

import pytest
import yaml
from projection_test_cache import cached_full_projections  # noqa: F401
from rq_reader_fixtures import fictional_catalog, fictional_records
from test_research_wiki_views import filesystem_state, outside_owned, setup  # noqa: F401
from test_rq_reader import cached_lifecycle_setup  # noqa: F401

from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.private_projection import ProjectionError, yaml_text
from fh_agent.research_atlas.research_presentation import presentation_fingerprint
from fh_agent.research_atlas.research_steering import (
    GAP_STATES,
    ROOT,
    STEERING_BASE,
    UNAVAILABLE,
    base_cell,
    base_output,
    inventories,
    markdown_tables,
    paper_membership,
)
from fh_agent.research_atlas.rq_presentation import RQReader
from fh_agent.research_atlas.source_presentation import SourceReader
from fh_agent.research_atlas.source_resolution import SourceResolver
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.wiki_schema import validate_wiki_records


@pytest.fixture(scope="module")
def atlas():
    return load_registry(Path(__file__).resolve().parents[1] / "docs/research-atlas")


def projection(atlas, records, catalog=None):
    reader = RQReader(atlas, records, SourceReader(SourceResolver(catalog or fictional_catalog())))
    locators = {r.wiki_id: PurePosixPath("Research") / (r.title + ".md") for r in records}
    locators.update({ref: ROOT / path for ref, path in views.rq_page_paths(records).items()})
    return reader, inventories(reader, locators, views.identity_page_paths(atlas))


def component(values, name):
    return next(row.cells for row in values[1].rows if row.cells[0][0].label == name)


@pytest.fixture(scope="module")
def reused(atlas):
    records = fictional_records(atlas)
    original = records[0]
    # Current navigation/analysis with no conclusion needs no invented assessment.
    a = original.presentation_analysis.model_copy(update={"conclusion": None})
    rq = original.model_copy(update={"presentation_analysis": a})
    second = rq.model_copy(
        update={
            "wiki_id": "WRQ-SECOND",
            "title": "Second fictional question",
            "presentation_question": "Does the same fictional Paper inform another question?",
            "research_direct_subject_refs": ["CMP-OBSERVATION-BUILDER"],
        }
    )
    third = rq.model_copy(
        update={
            "wiki_id": "WRQ-THIRD",
            "title": "Third fictional question",
            "presentation_question": "Does the fictional Paper inform memory retrieval?",
            "research_direct_subject_refs": ["CMP-MEM-RETRIEVAL"],
        }
    )
    data = [
        r.model_dump(mode="json", exclude_unset=True) for r in (rq, second, third, *records[1:])
    ]
    for question in data[:3]:
        question["presentation_analysis"]["subject_contexts"] = [
            context
            for context in question["presentation_analysis"]["subject_contexts"]
            if context["target_ref"] in question["research_direct_subject_refs"]
        ]
    paper = data[3]
    for question in data[1:3]:
        paper["research_direct_subject_refs"].append(question["wiki_id"])
        context = deepcopy(paper["presentation_contexts"][0])
        context["target_ref"] = question["wiki_id"]
        paper["presentation_contexts"].append(context)
    return validate_wiki_records(data, atlas.entities.keys())


def test_reuse_exact_sets_and_no_inheritance(atlas, reused):
    reader, values = projection(atlas, reused)
    assert [row.cells[2] for row in values[0].rows] == [1, 1, 1]
    assert all(paper_membership(reader, rq) == {"WPAPER-CEDAR"} for rq in reused[:3])
    assert component(values, "Observation Builder")[1:] == (2, 1, f"2 {UNAVAILABLE}")
    assert component(values, "Temporal State")[1:] == (1, 1, f"1 {UNAVAILABLE}")
    assert component(values, "Memory Retrieval")[1:] == (1, 1, f"1 {UNAVAILABLE}")
    # Retrieval's parent and neighboring children do not inherit its RQ/Paper.
    for name in ("Memory", "Episodic Memory", "Cortex"):
        assert component(values, name)[1:] == (0, 0, "No directly mapped current RQs")
    assert len(values[2].rows) == 1
    paper = values[2].rows[0].cells
    assert paper[2] == 3
    assert {link.label for link in paper[1]} == {
        "Observation Builder",
        "Temporal State",
        "Memory Retrieval",
    }
    assert len(values[0].rows[0].cells[1]) == 2  # explicitly multi-subject, not flattened


@pytest.mark.parametrize("gap", GAP_STATES)
def test_all_stored_states_distribution_and_count_neutrality(atlas, gap):
    records = fictional_records(atlas, gap)
    reader, values = projection(atlas, records)
    assert reader.conclusion_ok(records[0])
    assert values[0].rows[0].cells[3] == gap.replace("_", " ")
    assert component(values, "Observation Builder")[3] == "1 " + gap.replace("_", " ")
    c = records[0].presentation_analysis.conclusion
    assert records[0].decision_state == "none"
    assert c.next_scientific_work not in "\n".join(markdown_tables(values))
    before = deepcopy(records)
    # An unrelated Paper increases global record count, never gap/authorization.
    extra = records[1].model_copy(update={"wiki_id": "WPAPER-UNUSED", "title": "Unused fiction"})
    _, changed = projection(atlas, (*records, extra))
    assert changed[0] == values[0] and changed[1] == values[1]
    assert len(changed[2].rows) == 2 and changed[2].rows[1].cells[2] == 0
    assert records == before


@pytest.mark.parametrize("fault", ["none", "stale", "historical", "draft", "legacy"])
def test_sparse_and_noncurrent_states(atlas, fault):
    records = fictional_records(atlas)
    rq = records[0]
    if fault == "none":
        rq = rq.model_copy(
            update={
                "presentation_analysis": rq.presentation_analysis.model_copy(
                    update={"conclusion": None}
                ),
            }
        )
    elif fault == "stale":
        rq = rq.model_copy(update={"record_version": 2})
    elif fault in {"historical", "draft"}:
        rq = rq.model_copy(
            update={"document_maturity": "archived" if fault == "historical" else "draft"}
        )
    else:
        rq = rq.model_copy(
            update={"epistemic_schema_version": "0.2", "presentation_analysis": None}
        )
    _, values = projection(atlas, (rq, *records[1:]))
    if fault in {"historical", "draft"}:
        assert not values[0].rows
        assert component(values, "Observation Builder")[1] == 0
        assert values[2].rows[0].cells[2] == 0
    else:
        assert values[0].rows[0].cells[3] == UNAVAILABLE
        if fault == "legacy":
            assert values[0].rows[0].cells[1] == "No exact technical subject bound"
            assert values[0].rows[0].cells[2] == 0


def test_no_domain_function_adjacency_generic_attachment_or_search_leakage(atlas, reused):
    rq = reused[0].model_copy(
        update={
            "research_direct_subject_refs": ["DOM-EVIDENCE-MEMORY", "FUNC-OBSERVE"],
            "atlas_refs": ["CMP-CORTEX"],
            "research_adjacent_context_refs": ["CMP-MEMORY"],
        }
    )
    reader, values = projection(atlas, (rq, *reused[3:]))
    assert reader.subjects(rq) == []
    assert all(row.cells[1:3] == (0, 0) for row in values[1].rows)
    assert values[2].rows[0].cells[1] == "No Component mapped through current RQ use"
    # A generic attached Paper and Search results cannot enter curated membership.
    no_rows = rq.presentation_analysis.model_copy(
        update={
            "literature_rows": [],
            "nearest_work_rows": [],
            "establishes": [],
        }
    )
    assert not paper_membership(reader, rq.model_copy(update={"presentation_analysis": no_rows}))


def test_exact_statement_sources_only_and_missing_papers(atlas):
    records = fictional_records(atlas)
    rq = records[0]
    a = rq.presentation_analysis.model_copy(update={"literature_rows": [], "nearest_work_rows": []})
    selected = rq.model_copy(update={"presentation_analysis": a})
    reader, _ = projection(atlas, (selected, *records[1:]))
    assert paper_membership(reader, selected) == {"WPAPER-CEDAR"}
    # SourceFamily references alone do not become Paper identities.
    finding = records[3].model_copy(update={"source_refs": ["srcf-cedar"]})
    no_exact = a.model_copy(update={"establishes": [a.establishes[0]]})
    selected = selected.model_copy(update={"presentation_analysis": no_exact})
    reader, _ = projection(atlas, (selected, records[1], records[2], finding, *records[4:]))
    assert not paper_membership(reader, selected)
    reader, values = projection(atlas, tuple(r for r in records if r.wiki_id != "WPAPER-CEDAR"))
    assert not paper_membership(reader, records[0])
    assert not values[2].rows


def test_read_and_source_version_states_stay_distinct(atlas):
    records = fictional_records(atlas)
    note = records[2].model_copy(update={"version_read": "srcv-missing"})
    _, values = projection(atlas, (records[0], records[1], note, *records[3:]))
    paper = values[2].rows[0].cells
    assert "results checked" in paper[3]
    assert "version read unresolved" in paper[4]
    assert "Source family resolved" in paper[4]
    assert paper[5][0].destination == "zotero://select/library/items/CEDAR001"
    _, no_note = projection(atlas, tuple(r for r in records if r.wiki_id != note.wiki_id))
    assert no_note[2].rows[0].cells[3] == "No mapped ReadingNote"
    assert "Source version resolved" in no_note[2].rows[0].cells[4]


def test_ambiguous_zotero_is_unavailable(atlas):
    records = fictional_records(atlas)
    catalog = fictional_catalog()
    second = catalog.bindings[0].model_copy(
        update={"value": "zotero://select/library/items/CEDAR002"}
    )
    catalog = catalog.model_copy(update={"bindings": [*catalog.bindings, second]})
    _, values = projection(atlas, records, catalog)
    assert values[2].rows[0].cells[5] == "Unavailable / ambiguous"


def test_exact_routes_base_markdown_parity_determinism_and_fallback(atlas, reused):
    _, values = projection(atlas, reused)
    text = "\n".join(markdown_tables(values))
    base = base_output(values, views.BASE_OWNER)
    data = yaml.safe_load(base)
    assert [view["name"] for view in data["views"]] == [v.name for v in values]
    for index, inventory in enumerate(values):
        view = data["views"][index]
        assert len(view["filters"]["or"]) == len(inventory.rows)
        for column, label in enumerate(inventory.columns):
            key = f"inventory_{index}_{column}"
            assert data["properties"]["formula." + key]["displayName"] == label
            for row in inventory.rows:
                assert base_cell(row.cells[column]) in data["formulas"][key]
        for row in inventory.rows:
            assert f'file.path == "{row.path}"' in view["filters"]["or"]
    assert "../research-questions/" in text and "../identity-pages/" in text
    assert "../../../Research/Cedar" in text and "zotero://select/library/items/CEDAR001" in text
    assert "WRQ-" not in text and "WPAPER-" not in text and "WFIND-" not in text
    assert "/Users/" not in text and "reviewed_inputs" not in text
    _, shuffled = projection(atlas, tuple(reversed(reused)))
    assert shuffled == values
    assert markdown_tables(shuffled) == markdown_tables(values)
    assert base_output(shuffled, views.BASE_OWNER) == base
    # Core tables survive deleting every rich-view link.
    fallback = "\n".join(line for line in text.splitlines() if ".base#" not in line)
    assert sum(line.startswith("| ---") for line in fallback.splitlines()) == 3
    assert "../research-questions/" in fallback


def test_authored_row_order_is_preserved_by_existing_reader(atlas):
    records = fictional_records(atlas)
    rq = records[0]
    a = rq.presentation_analysis
    reordered = rq.model_copy(
        update={
            "presentation_analysis": a.model_copy(
                update={"establishes": list(reversed(a.establishes))}
            ),
        }
    )
    assert presentation_fingerprint((reordered, *records[1:])) != presentation_fingerprint(records)
    assert inventories(*_inventory_arguments(atlas, records)) == inventories(
        *_inventory_arguments(atlas, (reordered, *records[1:])),
    )
    assert reordered.presentation_analysis.establishes == list(reversed(a.establishes))


def _inventory_arguments(atlas, records):
    reader = RQReader(atlas, records, SourceReader(SourceResolver(fictional_catalog())))
    locators = {r.wiki_id: PurePosixPath("Research") / (r.title + ".md") for r in records}
    return reader, locators, views.identity_page_paths(atlas)


def test_privacy_unsafe_locator_fails_closed(atlas):
    reader = RQReader(atlas, fictional_records(atlas), SourceReader(SourceResolver(None)))
    with pytest.raises(ProjectionError, match="Unsafe private presentation locator"):
        inventories(
            reader,
            {"WPAPER-CEDAR": PurePosixPath("/private/secret.md")},
            views.identity_page_paths(atlas),
        )


def test_workspace_finite_ownership_migration_and_zero_write(setup, cached_lifecycle_setup):  # noqa: F811
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    authored = outside_owned(vault)
    manifest_path = vault / views.OWNED_ROOT / views.MANIFEST
    manifest = yaml.safe_load(tree[views.MANIFEST])
    owned = {item["path"]: item for item in manifest["owned_files"]}
    assert owned[str(STEERING_BASE)]["ownership"] == views.OBSIDIAN_BASE_OWNERSHIP
    normal = tree[views.RESEARCH_LANDSCAPE].decode().split("<details>", 1)[0]
    assert "# Research Steering" in normal
    assert sum(line.startswith("| ---") for line in normal.splitlines()) == 3
    assert "WRQ-" not in normal and "WPAPER-" not in normal
    # Intact old 2.15 payload migrates by adding exactly one finite Base.
    (vault / views.OWNED_ROOT / STEERING_BASE).unlink()
    manifest["owned_files"] = [
        item for item in manifest["owned_files"] if item["path"] != str(STEERING_BASE)
    ]
    manifest_path.write_text(yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    assert views.project(repo, vault, sha) == tree
    before = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == tree
    assert filesystem_state(vault) == before and outside_owned(vault) == authored
    # Semantic Base edits remain owned-operator conflicts, never silently overwritten.
    path = vault / views.OWNED_ROOT / STEERING_BASE
    data = yaml.safe_load(path.read_bytes())
    data["formulas"]["inventory_1_1"] = "999"
    path.write_text(yaml_text(data))
    before = filesystem_state(vault)
    with pytest.raises(ProjectionError, match="changed semantically"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before


def test_mixed_component_distribution_and_consumed_count_changes(atlas, reused):
    records = fictional_records(atlas, "unassessed")
    rq = records[0]
    c = rq.presentation_analysis.conclusion.model_copy(
        update={
            "reviewed_by": [],
            "reviewed_inputs": [],
            "evidence_refs": [],
        }
    )
    a = rq.presentation_analysis.model_copy(
        update={
            "conclusion": c,
            "nearest_work_rows": [],
            "establishes": [],
        }
    )
    rq = rq.model_copy(update={"document_maturity": "in_review", "presentation_analysis": a})
    reader, before = projection(atlas, (rq, *records[1:]))
    assert reader.conclusion_ok(rq)
    extra = records[1].model_copy(update={"wiki_id": "WPAPER-SECOND", "title": "Second fiction"})
    row = a.literature_rows[0].model_copy(
        update={
            "paper_ref": extra.wiki_id,
            "context_owner_ref": extra.wiki_id,
        }
    )
    changed = rq.model_copy(
        update={
            "presentation_analysis": a.model_copy(
                update={"literature_rows": [*a.literature_rows, row]}
            ),
        }
    )
    sparse = reused[1]
    reader, after = projection(atlas, (changed, sparse, *records[1:], extra))
    assert reader.conclusion_ok(changed)
    assert changed.presentation_analysis.conclusion == rq.presentation_analysis.conclusion
    assert changed.decision_state == rq.decision_state == "none"
    assert before[0].rows[0].cells[2:] == (1, "unassessed")
    changed_row = next(
        row for row in after[0].rows if row.cells[0][0].label == rq.presentation_question
    )
    assert changed_row.cells[2:] == (2, "unassessed")
    assert component(after, "Observation Builder")[1:] == (
        2,
        2,
        "1 unassessed · 1 Current conclusion unavailable",
    )
    assert len(after[2].rows) == 2


def test_full_synthetic_projection_has_one_preferred_identity_and_finite_base(atlas):
    records = fictional_records(atlas)
    props = [r.model_dump(mode="json", exclude_unset=True) for r in records]
    snapshot = views.make_snapshot(props, atlas)
    commit = "a" * 40
    locators = {r.wiki_id: PurePosixPath("Research") / (r.title + ".md") for r in records}
    repo = Path(__file__).resolve().parents[1]
    tree = views.reference_views_tree(
        commit,
        (repo / views.PUBLIC_SOURCE).read_bytes(),
        (repo / views.DIRECT_SOURCE).read_bytes(),
        views.build_index(atlas, snapshot, commit),
        atlas,
        locators,
        snapshot,
        False,
        records,
        source_catalog=fictional_catalog(),
    )
    normal = tree[views.RESEARCH_LANDSCAPE].decode().split("<details>", 1)[0]
    assert "narrowing required" in normal and "results checked" in normal
    assert "WRQ-" not in normal and "WPAPER-" not in normal and "WFIND-" not in normal
    assert sum(line.startswith("| ---") for line in normal.splitlines()) == 3
    rq_paths = views.rq_page_paths(records)
    assert sum(path.parent == views.RQ_ROOT for path in tree) == 1
    assert "../research-questions/" in normal and rq_paths[records[0].wiki_id] in tree
    assert not any("steering-rows" in str(path) for path in tree)
    base = yaml.safe_load(tree[STEERING_BASE])
    rq_filter = base["views"][0]["filters"]["or"]
    assert rq_filter == [f'file.path == "{ROOT / rq_paths[records[0].wiki_id]}"']
    manifest = yaml.safe_load(tree[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.15"
    assert manifest["presentation_fingerprint_version"] == "1.1"
    assert manifest["source_resolution_fingerprint_version"] == "1.0"


def test_search_result_records_never_become_analysis_membership(atlas):
    records = fictional_records(atlas)
    rq = records[0].model_copy(update={"search_refs": ["SEARCH-FICTION"]})
    extra = records[1].model_copy(
        update={"wiki_id": "WPAPER-SEARCH", "title": "Search-only fiction"}
    )
    search = dict(
        wiki_schema_version="0.1",
        epistemic_schema_version="0.3",
        wiki_id="SEARCH-FICTION",
        doc_type="search_record",
        title="Fictional search",
        record_version=1,
        document_maturity="in_review",
        privacy="private",
        export_policy="deny",
        atlas_refs=[],
        target_refs=[rq.wiki_id],
        result_refs=[extra.wiki_id],
        search_date="2026-10-01",
    )
    props = [r.model_dump(mode="json", exclude_unset=True) for r in (rq, *records[1:], extra)]
    validated = validate_wiki_records([*props, search], atlas.entities.keys())
    reader, values = projection(atlas, validated)
    assert paper_membership(reader, validated[0]) == {"WPAPER-CEDAR"}
    assert len(values[2].rows) == 2
    search_only = next(row.cells for row in values[2].rows if row.cells[0][0].label == extra.title)
    assert search_only[2] == 0
    assert search_only[1] == "No Component mapped through current RQ use"
