"""Bounded #125 synthetic acceptance; no live vault, Zotero or literature access."""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path, PurePosixPath

import pytest
import yaml
from rq_reader_fixtures import fictional_catalog, fictional_properties, fictional_records
from test_research_wiki_views import setup  # noqa: F401

from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.private_reference_index import build_index, make_snapshot
from fh_agent.research_atlas.research_presentation import presentation_fingerprint
from fh_agent.research_atlas.rq_presentation import RQReader, rq_metadata
from fh_agent.research_atlas.source_presentation import SourceReader
from fh_agent.research_atlas.source_resolution import (
    SourceCatalog,
    SourceResolver,
    source_fingerprint,
)
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.wiki_schema import validate_wiki_records

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


@pytest.fixture(scope="module")
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


@pytest.fixture
def cached_lifecycle_setup(monkeypatch):
    """Reuse deterministic setup, keeping every projector and filesystem check live.

    This fictional lifecycle never edits Registry inputs. Content keys still miss
    on any changed byte; parsed mutable values are copied for each caller. The
    first call uses the real parser/tree builder, not a fabricated projection.
    """
    from fh_agent.research_atlas import private_projection as technical

    parse = technical.read_yaml
    registry_load = technical.load_registry
    build = technical.projection_tree
    registries = {}
    trees = {}

    cached_parse = lru_cache(maxsize=None)(parse)

    def read_yaml(text):
        return deepcopy(cached_parse(text))

    def registry(root):
        key = tuple(
            (root / "registry" / name).read_bytes()
            for name in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
        )
        if key not in registries:
            registries[key] = registry_load(root)
        return registries[key]  # frozen Atlas, mapping proxy and frozen entity models

    def tree(atlas, commit, registry_digests):
        # All Atlas instances above derive from exactly these Registry bytes.
        key = (commit, tuple(sorted(registry_digests.items())))
        if key not in trees:
            trees[key] = build(atlas, commit, registry_digests)
        return dict(trees[key])  # payload bytes are immutable

    monkeypatch.setattr(technical, "read_yaml", read_yaml)
    monkeypatch.setattr(views, "read_yaml", read_yaml)
    monkeypatch.setattr(technical, "load_registry", registry)
    monkeypatch.setattr(views, "load_registry", registry)
    monkeypatch.setattr(technical, "projection_tree", tree)


def reader(atlas, records, catalog=None):
    return RQReader(atlas, records, SourceReader(SourceResolver(catalog or fictional_catalog())))


def props(records):
    return [r.model_dump(mode="json", exclude_unset=True) for r in records]


def render(atlas, records, catalog=None):
    locators = {r.wiki_id: PurePosixPath("authored") / (r.title + ".md") for r in records}
    locators[records[0].wiki_id] = (
        views.OWNED_ROOT / views.rq_page_paths(records)[records[0].wiki_id]
    )
    return reader(atlas, records, catalog).render(
        records[0],
        COMMIT,
        locators,
        lambda ref: "[" + atlas.entities[ref].name + "](../identity-pages/" + ref + ".md)",
        presentation_fingerprint(records),
    )


@pytest.mark.parametrize(
    "gap",
    [
        "narrowing_required",
        "candidate_gap",
        "covered_by_prior_art",
        "insufficient_evidence",
        "unassessed",
    ],
)
def test_authored_scientific_states_reader_order_and_no_authorization(atlas, gap):
    records = fictional_records(atlas, gap)
    assert reader(atlas, records).conclusion_ok(records[0])
    page = render(atlas, records)
    normal = views.reader_export(page).decode()
    expected = [
        "Research Question",
        "Why this matters",
        "Most relevant literature",
        "Nearest work / closest prior art",
        "What the literature currently establishes",
        "Research conclusion",
        "Next work",
        "Zotero",
        "Sources & audit",
    ]
    positions = [normal.index("## " + heading) for heading in expected]
    assert positions == sorted(positions)
    c = records[0].presentation_analysis.conclusion
    assert normal.count(c.next_scientific_work) == 1
    assert c.authored_conclusion in normal and gap.replace("_", " ") in normal
    assert "Source-reported finding — Adverse evidence" in normal
    assert "Project inference" in normal and "Project-authored synthesis" in normal
    assert "Author-reported limitation" in normal
    assert "Checked version 1" in normal and "Navigation version 2" not in normal
    assert "Open Zotero" in normal and "Open RQ literature corpus" in normal
    assert "WPAPER-" not in normal and "srcf-" not in normal and "reviewed_inputs" not in normal
    assert "At a glance" not in normal and "Literature Coverage" not in normal
    assert "Program disposition" not in normal and records[0].decision_state == "none"
    assert "pursue" not in normal and "Claim accepted" not in normal
    assert rq_metadata(page.decode(), views.rq_page_paths(records)[records[0].wiki_id])
    audit = (
        page.decode()
        .split("> [!aga-audit]- Full audit\n", 1)[1]
        .split("\n\n## Return Navigation", 1)[0]
    )
    assert all(line.startswith(">") for line in audit.splitlines())


@pytest.mark.parametrize(
    "mutation",
    [
        "paper-type",
        "paper-dangling",
        "finding-type",
        "finding-paper",
        "reading-type",
        "reading-paper",
        "reading-version",
        "reading-abstract",
        "finding-review",
        "finding-historical",
        "synthesis-rq",
        "stale-version",
        "stale-rq",
        "review-extra",
        "review-missing",
        "review-type",
        "search-target",
        "nearest-evidence",
        "location-note",
    ],
)
def test_wrong_dangling_historical_and_stale_inputs_fail_closed(atlas, mutation):
    data = props(fictional_records(atlas))
    a = data[0]["presentation_analysis"]
    if mutation == "paper-type":
        a["literature_rows"][0]["paper_ref"] = "READ-CEDAR"
    elif mutation == "paper-dangling":
        a["literature_rows"][0]["paper_ref"] = "WPAPER-MISSING"
    elif mutation == "finding-type":
        data[1]["presentation_contexts"][0]["finding_ref"] = "READ-CEDAR"
    elif mutation == "finding-paper":
        data[3]["source_refs"] = ["WPAPER-MISSING"]
    elif mutation == "reading-type":
        data[1]["presentation_contexts"][0]["reading_note_ref"] = "WFIND-CEDAR"
    elif mutation == "reading-paper":
        data[2]["paper_refs"] = ["WPAPER-MISSING"]
    elif mutation == "reading-version":
        data[2]["version_read"] = "srcv-missing"
    elif mutation == "reading-abstract":
        data[2].update(reading_depth="abstract_checked", checked_sections=["abstract"])
    elif mutation == "finding-review":
        data[3]["review_state"] = "draft"
    elif mutation == "finding-historical":
        data[3]["document_maturity"] = "archived"
    elif mutation == "synthesis-rq":
        data[5]["rq_refs"] = []
    elif mutation == "stale-version":
        data[2]["record_version"] = 2
    elif mutation == "stale-rq":
        data[0]["record_version"] = 2
    elif mutation == "review-extra":
        a["conclusion"]["reviewed_inputs"].append(dict(ref="JOURNAL-OBSERVER", record_version=1))
    elif mutation == "review-missing":
        a["conclusion"]["reviewed_inputs"].pop()
    elif mutation == "review-type":
        data[0]["review_refs"] = ["WPAPER-CEDAR"]
    elif mutation == "search-target":
        search = dict(
            data[6],
            wiki_id="SEARCH-OTHER",
            doc_type="search_record",
            title="Other search",
            target_refs=["CMP-OBSERVATION-BUILDER"],
            search_date="2026-10-01",
        )
        for key in ("entry_date", "resulting_object_refs"):
            search.pop(key)
        data.append(search)
        data[0]["search_refs"] = ["SEARCH-OTHER"]
        a["conclusion"]["reviewed_inputs"].append(dict(ref="SEARCH-OTHER", record_version=1))
    elif mutation == "nearest-evidence":
        a["nearest_work_rows"][0]["evidence_refs"] = ["WFIND-INFERENCE"]
    elif mutation == "location-note":
        data[3]["presentation_source_locations"][0]["reading_note_ref"] = "READ-MISSING"
    records = validate_wiki_records(data, atlas.entities.keys())
    current = reader(atlas, records)
    assert not current.conclusion_ok(records[0])
    normal = views.reader_export(render(atlas, records)).decode()
    assert a["conclusion"]["authored_conclusion"] not in normal
    assert "Current research conclusion unavailable" in normal
    assert "No current authored next work" in normal
    assert not any("replacement" in r.title for r in records)


def test_exact_multi_subject_binding_and_sparse_component_cards(atlas):
    records = fictional_records(atlas)
    current = reader(atlas, records)
    assert set(current.subjects(records[0])) == {"CMP-OBSERVATION-BUILDER", "CMP-TEMPORAL-STATE"}
    snapshot = make_snapshot(props(records), atlas)
    reference = build_index(atlas, snapshot, COMMIT)
    locators = {r.wiki_id: PurePosixPath("authored") / (r.title + ".md") for r in records}
    tree = views.reference_views_tree(
        COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        records,
        source_catalog=fictional_catalog(),
    )
    assert (
        sum(path.parent == views.rq_page_paths(records)[records[0].wiki_id].parent for path in tree)
        == 1
    )
    for target in ("CMP-OBSERVATION-BUILDER", "CMP-TEMPORAL-STATE"):
        page = tree[views.identity_page_paths(atlas)[target]]
        normal = views.reader_export(page).decode()
        research = normal.split("## Research\n", 1)[1].split("## Sources & verification", 1)[0]
        assert "Open Research Question" in research and "narrowing required" in research
        assert "Cedar" not in research and "WFIND-" not in research
        assert "Prior work covers" not in research and "nearest_work_rows" not in research
        assert "## Research conclusion" not in research
    parent = views.reader_export(tree[views.identity_page_paths(atlas)["CMP-PERCEPTION"]]).decode()
    assert records[0].presentation_question not in parent
    assert locators[records[0].wiki_id].parent == PurePosixPath("authored")
    manifest = yaml.safe_load(tree[views.MANIFEST])
    assert (
        manifest["view_schema_version"] == "2.15"
        and manifest["presentation_fingerprint_version"] == "1.1"
    )


@pytest.mark.parametrize("version", ["0.1", "0.2", "0.3"])
def test_unbound_and_old_rq_roles_do_not_acquire_binding(atlas, version):
    data = fictional_properties()
    rq = data[0]
    rq.pop("presentation_analysis")
    if version == "0.1":
        rq.pop("presentation_question")
    rq["epistemic_schema_version"] = version
    if version == "0.3":
        rq["research_direct_subject_refs"] = []
    rq["atlas_refs"] = ["CMP-OBSERVATION-BUILDER"]
    rq["research_method_or_baseline_refs"] = ["CMP-OBSERVATION-BUILDER"]
    records = validate_wiki_records([rq], atlas.entities.keys())
    assert reader(atlas, records).subjects(records[0]) == []
    normal = views.reader_export(render(atlas, records)).decode()
    assert "No exact technical subject bound" in normal
    assert (
        "No literature explicitly curated" in normal
        and "No nearest work explicitly compared" in normal
    )
    assert "Unassessed — no authored research conclusion" in normal


@pytest.mark.parametrize(
    "target", ["FUNC-OBSERVE", "DOM-COGNITION", "ENV-GAME-INSTANCE", "WRQ-OBSERVER", "CMP-MISSING"]
)
def test_actual_target_types_without_prefix_inference(atlas, target):
    data = fictional_properties()
    data[0].pop("presentation_analysis")
    data[0]["research_direct_subject_refs"] = [target]
    records = validate_wiki_records(data, atlas.entities.keys())
    assert reader(atlas, records).subjects(records[0]) == []


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "unknown-nested",
        "bool-version",
        "blank",
        "duplicate-paper",
        "duplicate-set",
        "bad-ref",
        "unsafe-zotero",
        "candidate-rationale",
        "bad-date",
        "source-location-empty",
        "old-analysis",
        "old-location",
    ],
)
def test_closed_strict_opt_in_schema(atlas, mutation):
    data = fictional_properties("candidate_gap")
    a = data[0]["presentation_analysis"]
    if mutation == "unknown":
        a["metadata"] = {}
    elif mutation == "unknown-nested":
        a["nearest_work_rows"][0]["score"] = 0.8
    elif mutation == "bool-version":
        a["conclusion"]["question_version"] = True
    elif mutation == "blank":
        a["subject_contexts"][0]["why_matters"] = "  "
    elif mutation == "duplicate-paper":
        a["literature_rows"] *= 2
    elif mutation == "duplicate-set":
        a["conclusion"]["evidence_refs"] *= 2
    elif mutation == "bad-ref":
        a["nearest_work_rows"][0]["paper_ref"] = "../WPAPER-CEDAR"
    elif mutation == "unsafe-zotero":
        a["zotero_corpus"]["ref"] = "javascript:alert(1)"
    elif mutation == "candidate-rationale":
        a["conclusion"].pop("project_fit")
    elif mutation == "bad-date":
        a["conclusion"]["as_of"] = 1
    elif mutation == "source-location-empty":
        data[3]["presentation_source_locations"] = [dict(reading_note_ref="READ-CEDAR")]
    elif mutation == "old-analysis":
        data[0]["epistemic_schema_version"] = "0.2"
    elif mutation == "old-location":
        data[3]["epistemic_schema_version"] = "0.2"
    with pytest.raises(ValueError):
        validate_wiki_records(data, atlas.entities.keys())


def test_status_corpus_and_paper_count_do_not_mutate_science(atlas):
    records = fictional_records(atlas, "candidate_gap")
    before = props(records)
    catalog = fictional_catalog().model_dump(mode="json")
    catalog["versions"][0]["status"] = "retracted"
    changed_catalog = SourceCatalog.model_validate(catalog)
    normal = views.reader_export(render(atlas, records, changed_catalog)).decode()
    assert "candidate gap" in normal and "Retracted version" in normal
    assert props(records) == before
    assert presentation_fingerprint(records) == presentation_fingerprint(tuple(reversed(records)))
    assert source_fingerprint(fictional_catalog(), records) != source_fingerprint(
        changed_catalog, records
    )
    data = props(records)
    data[0]["presentation_analysis"]["zotero_corpus"]["ref"] = (
        "zotero://select/library/collections/OTHER001"
    )
    data.append(dict(data[1], wiki_id="WPAPER-UNSELECTED", title="Uncurated fictional Paper"))
    changed = validate_wiki_records(data, atlas.entities.keys())
    assert reader(atlas, changed).conclusion_ok(changed[0])
    page = views.reader_export(render(atlas, changed)).decode()
    assert "Uncurated fictional Paper" not in page
    assert "candidate gap" in page
    assert (
        props(changed)[0]["presentation_analysis"]["conclusion"]
        == before[0]["presentation_analysis"]["conclusion"]
    )


def test_fingerprint_ordered_rows_set_determinism_and_annotations(atlas):
    records = fictional_records(atlas)
    original = presentation_fingerprint(records)
    data = props(records)
    data[0]["research_direct_subject_refs"].reverse()
    data[0]["finding_refs"].reverse()
    data[0]["presentation_analysis"]["conclusion"]["reviewed_inputs"].reverse()
    data[0]["presentation_analysis"]["conclusion"]["evidence_refs"].reverse()
    for record in data:
        record["aliases"] = ["Unconsumed annotation"]
        record["tags"] = ["synthetic"]
    assert presentation_fingerprint(validate_wiki_records(data, atlas.entities.keys())) == original
    data[0]["presentation_analysis"]["establishes"].reverse()
    assert presentation_fingerprint(validate_wiki_records(data, atlas.entities.keys())) != original
    assert json.dumps(data)  # all frozen data is portable, no PDFs/body access


def test_zotero_item_binding_ambiguity_and_exact_family_only(atlas):
    records = fictional_records(atlas)
    data = fictional_catalog().model_dump(mode="json")
    data["bindings"].append(
        dict(
            scheme="opaque", value="zotero://select/library/items/OTHER001", target_ref="srcf-cedar"
        )
    )
    assert reader(atlas, records, SourceCatalog.model_validate(data)).zotero(records[1]) is None
    data["bindings"] = [
        dict(
            scheme="opaque",
            value="zotero://select/library/items/CEDAR001",
            target_ref="srcv-cedar1",
        )
    ]
    assert reader(atlas, records, SourceCatalog.model_validate(data)).zotero(records[1]) is None


def test_owned_rq_migration_body_independence_and_zero_write(
    cached_lifecycle_setup,
    setup,  # noqa: F811
    tmp_path,
):
    from test_research_wiki_projection import (
        filesystem_state,
        git,
        write_note,
    )

    from fh_agent.research_atlas import private_projection as technical
    from fh_agent.research_atlas.source_resolution import CATALOG_INPUT
    from fh_agent.research_atlas.workspace_harness import apply, check

    repo, vault, _ = setup
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    apply(repo, vault, tmp_path / "restore")
    root = vault / views.OWNED_ROOT
    # An intact prior G4 manifest has only its own finite paths/fingerprint version.
    manifest = yaml.safe_load((root / views.MANIFEST).read_bytes())
    manifest["view_schema_version"] = "2.14"
    manifest["presentation_fingerprint_version"] = "1.0"
    (root / views.MANIFEST).write_text(technical.yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(ValueError, match="drift"):
        check(repo, vault)
    assert filesystem_state(vault) == before
    records = fictional_records(load_registry(repo / "docs/research-atlas"))
    (vault / CATALOG_INPUT).write_text(fictional_catalog().model_dump_json())
    for record in records:
        write_note(
            vault / "authored" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    authored_before = {p: p.read_bytes() for p in (vault / "authored").glob("*.md")}
    apply(repo, vault, tmp_path / "restore")
    assert all(p.read_bytes() == payload for p, payload in authored_before.items())
    before = filesystem_state(vault)
    check(repo, vault)
    assert filesystem_state(vault) == before
    page = root / views.rq_page_paths(records)[records[0].wiki_id]
    original = page.read_bytes()
    # Body-only changes are not scientific inputs and cannot change generated science.
    note = vault / "authored" / (records[0].wiki_id + ".md")
    note.write_text(note.read_text() + "\nBODY-ONLY: candidate gap and authorized pursuit!\n")
    check(repo, vault)
    assert page.read_bytes() == original and b"BODY-ONLY" not in original
    before = filesystem_state(vault)
    page.write_bytes(original + b"\nEdited generated science\n")
    edited = filesystem_state(vault)
    with pytest.raises(ValueError, match="RQ page was edited"):
        check(repo, vault)
    assert filesystem_state(vault) == edited
    page.write_bytes(original)
    unknown = root / "research-questions/WRQ-UNOWNED.md"
    unknown.write_bytes(original)
    edited = filesystem_state(vault)
    with pytest.raises(ValueError, match="Unknown/unowned"):
        check(repo, vault)
    assert filesystem_state(vault) == edited
    unknown.unlink()
    assert page.read_bytes() == original
    # Historical manifests cannot adopt even correctly named unmanifested RQ files.
    data = yaml.safe_load((root / views.MANIFEST).read_bytes())
    data["view_schema_version"] = "2.14"
    data["presentation_fingerprint_version"] = "1.0"
    (root / views.MANIFEST).write_text(technical.yaml_text(data))
    with pytest.raises(ValueError, match="Historical manifest cannot own RQ"):
        views.validate_prior(root)


def test_sparse_provisional_conclusion_and_no_automatic_successor(atlas):
    data = fictional_properties("insufficient_evidence")[:1]
    rq = data[0]
    rq.update(document_maturity="in_review", finding_refs=[], synthesis_refs=[], review_refs=[])
    a = rq["presentation_analysis"]
    a.update(literature_rows=[], nearest_work_rows=[], establishes=[])
    a["conclusion"].update(evidence_refs=[], reviewed_by=[], reviewed_inputs=[])
    records = validate_wiki_records(data, atlas.entities.keys())
    normal = views.reader_export(render(atlas, records)).decode()
    assert "No literature explicitly curated" in normal
    assert "No nearest work explicitly compared" in normal
    assert "insufficient evidence — provisional / in review" in normal
    rq["document_maturity"] = "archived"
    records = validate_wiki_records(data, atlas.entities.keys())
    assert not reader(atlas, records).conclusion_ok(records[0])
    assert "navigation only" in views.reader_export(render(atlas, records)).decode()
    # A replacement is a separate identity and cannot silently replace the selected revision.
    replacement = dict(
        rq,
        wiki_id="WRQ-REPLACEMENT",
        title="Replacement question",
        document_maturity="in_review",
        supersedes_refs=["WRQ-OBSERVER"],
    )
    records = validate_wiki_records([rq, replacement], atlas.entities.keys())
    assert not reader(atlas, records).conclusion_ok(records[0])
    assert records[0].wiki_id != records[1].wiki_id
    assert reader(atlas, records).subjects(records[0]) == reader(atlas, records).subjects(
        records[1]
    )


def test_literal_question_fallback_source_locations_and_program_decision_audit_only(atlas):
    from fh_agent.research_atlas.research_presentation import literal

    data = props(fictional_records(atlas, "candidate_gap"))
    data[0]["presentation_question"] = None
    data[0]["title"] = "  Exact human title\n# not inferred *question*  "
    data[0]["decision_refs"] = ["WDEC-PROPOSAL"]
    data.append(
        dict(
            wiki_schema_version="0.1",
            epistemic_schema_version="0.3",
            wiki_id="WDEC-PROPOSAL",
            doc_type="decision_draft",
            title="Separate proposal",
            record_version=1,
            document_maturity="draft",
            privacy="private",
            export_policy="deny",
            atlas_refs=[],
            decision_type="pursue",
            decision_scope="program",
            subject_refs=["WRQ-OBSERVER"],
            decision_record_state="draft",
            authority_refs=[],
        )
    )
    records = validate_wiki_records(data, atlas.entities.keys())
    page = render(atlas, records)
    normal = views.reader_export(page).decode()
    assert literal(records[0].title) in normal
    assert "pursue" not in normal and "WDEC-PROPOSAL" not in normal
    assert "pursue" in page.decode().split("> [!aga-audit]- Full audit")[1]
    assert data[3]["presentation_source_locations"][0]["page"] == "4"
    assert '"reading_note_ref": "READ-CEDAR"' in page.decode()
    assert records[-1].decision_record_state == "draft"


def test_committed_human_first_prototype_matches_fictional_reader(atlas):
    prototype = ROOT / "tests/fixtures/rq-reader/Reader.md"
    assert (
        prototype.read_bytes()
        == views.reader_export(render(atlas, fictional_records(atlas))).rstrip() + b"\n"
    )


def test_human_preferred_names_duplicate_titles_and_ordered_table_fingerprints(atlas):
    records = fictional_records(atlas)
    rq = records[0]
    assert views.rq_page_paths(records)[rq.wiki_id].name == rq.title + ".md"
    second = rq.model_copy(update={"wiki_id": "WRQ-SECOND"})
    paths = views.rq_page_paths((*records, second))
    assert paths[rq.wiki_id] != paths[second.wiki_id]
    assert "WRQ-OBSERVER" in paths[rq.wiki_id].name
    assert views.rq_page_paths(tuple(reversed((*records, second)))) == paths
    unsafe = rq.model_copy(update={"title": "../bad/[name]/CON"})
    assert ".." not in views.rq_page_paths((unsafe,))[rq.wiki_id].parts
    too_long = rq.model_copy(update={"title": "Q" * 300})
    with pytest.raises(ValueError, match="Unsafe"):
        views.rq_page_paths((too_long,))
    data = props(records)
    a = data[0]["presentation_analysis"]
    a["literature_rows"].append(dict(a["literature_rows"][0], paper_ref="WPAPER-OTHER"))
    a["nearest_work_rows"].append(dict(a["nearest_work_rows"][0], paper_ref="WPAPER-OTHER"))
    before = presentation_fingerprint(validate_wiki_records(data, atlas.entities.keys()))
    a["literature_rows"].reverse()
    after = presentation_fingerprint(validate_wiki_records(data, atlas.entities.keys()))
    assert before != after
    a["nearest_work_rows"].reverse()
    assert presentation_fingerprint(validate_wiki_records(data, atlas.entities.keys())) != after


def test_multiline_card_stays_native_and_audit_is_recoverable(atlas):
    data = props(fictional_records(atlas))
    data[0]["presentation_question"] = "Exact question\n# escaped continuation"
    data[0]["presentation_analysis"]["subject_contexts"][0]["why_matters"] = (
        "Authored reason\nwith an exact second line."
    )
    records = validate_wiki_records(data, atlas.entities.keys())
    current = reader(atlas, records)
    card = current.card(
        records[0], "CMP-OBSERVATION-BUILDER", lambda r: "[Open Research Question](question.md)"
    )
    assert all(line.startswith(">") or line == "" for line in "\n".join(card).splitlines())
    page = render(atlas, records).decode()
    audit = page.split("> ```json\n", 1)[1].split("\n> ```", 1)[0]
    values = json.loads("\n".join(line.removeprefix("> ") for line in audit.splitlines()))
    rq = next(r for r in values if r["wiki_id"] == "WRQ-OBSERVER")
    assert rq["presentation_question"] == data[0]["presentation_question"]
