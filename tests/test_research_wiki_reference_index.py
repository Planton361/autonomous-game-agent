"""A01–A20/A27: synthetic declared links, not literature or scientific judgments."""

import copy
import json
from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError
from test_research_wiki_schema import LEGACY, props

from fh_agent.research_atlas import private_reference_index as index
from fh_agent.research_atlas.schema import Paper
from fh_agent.research_atlas.validator import Atlas, load_registry

COMMIT = "a" * 40


@pytest.fixture(scope="module")
def atlas():
    original = load_registry(Path(__file__).resolve().parents[1] / "docs/research-atlas")
    return Atlas(
        dict(original.entities)
        | {
            "PAPER-FIXTURE": Paper(
                id="PAPER-FIXTURE", type="Paper", name="Fixture", description="Synthetic"
            )
        },
        original.relationships,
    )


def sample_records():
    return [
        props(
            "paper",
            reading_note_refs=["READ-FIXTURE"],
            research_method_or_baseline_refs=["CMP-CORTEX"],
        ),
        props(
            "reading_note",
            finding_refs=["WFIND-FIXTURE"],
            rq_refs=["WRQ-FIXTURE"],
            research_direct_subject_refs=["CMP-CORTEX"],
        ),
        props(
            "finding",
            source_refs=["WPAPER-FIXTURE"],
            reading_note_refs=["READ-FIXTURE"],
            rq_refs=["WRQ-FIXTURE"],
            research_adjacent_context_refs=["CMP-CORTEX"],
        ),
        props("research_question", finding_refs=["WFIND-FIXTURE"]),
        props("process", rq_refs=["WRQ-FIXTURE"]),
    ]


def build(atlas, records):
    return index.build_index(atlas, index.make_snapshot(records, atlas), COMMIT)


def audit(result, source=None, prop=None):
    return [
        r
        for r in result.rows
        if r.row_kind == "declared-reference"
        and (source is None or r.source_wiki_id == source)
        and (prop is None or r.originating_property == prop)
    ]


def navigation(result):
    return [r for r in result.rows if r.row_kind == "navigation-path"]


def signature(row):
    return tuple((v.edge_id, v.traversal_direction) for v in row.via)


def test_a01_exact_resolution_and_closed_schema(atlas):
    result = build(
        atlas,
        [
            props(
                "reading_note",
                paper_refs=["PAPER-FIXTURE"],
                rq_refs=["WRQ-FIXTURE", "RQ-PROGRAM-AB-001", "WRQ-MISSING"],
            ),
            props("research_question"),
        ],
    )
    rows = {r.target_identifier: r for r in audit(result)}
    assert rows["PAPER-FIXTURE"].resolved_target_type == "Paper"
    assert rows["PAPER-FIXTURE"].target_resolution_status == "resolved-public"
    assert rows["PAPER-FIXTURE"].target_record_version is None
    assert rows["WRQ-FIXTURE"].target_resolution_status == "resolved-private"
    assert rows["WRQ-FIXTURE"].target_profile == "ra2"
    assert rows["WRQ-FIXTURE"].target_record_version == 1
    assert rows["WRQ-MISSING"].target_resolution_status == "unresolved-external-or-missing"
    assert rows["WRQ-MISSING"].resolved_target_type is None
    assert rows["WRQ-MISSING"].expected_target_types == (
        "private:research_question",
        "public:ResearchQuestion",
    )
    assert index.ReferenceIndex.model_validate_json(result.model_dump_json()) == result
    for model in (result, result.rows[0], result.rows[0].via[0], result.rows[0].via[0].traverse_to):
        with pytest.raises(ValidationError):
            type(model).model_validate_json(
                json.dumps(model.model_dump(mode="json") | {"extra": 1})
            )
    for row in result.rows:
        assert row.row_id == index.digest(
            index.canonical(row.model_dump(mode="json", exclude={"row_id"}))
        )


@pytest.mark.parametrize(
    "kind,field,target,actual",
    [
        ("reading_note", "paper_refs", "CMP-CORTEX", "Component"),
        ("finding", "rq_refs", "WPAPER-FIXTURE", "paper"),
        ("paper", "reading_note_refs", "TOPIC-FIXTURE", "topic"),
    ],
)
def test_a02_wrong_type_is_retained_not_cast(atlas, kind, field, target, actual):
    records = [props("topic"), props("paper"), props(kind, **{field: [target]})]
    if kind == "paper":
        records.pop(1)
    before = copy.deepcopy(records)
    result = build(atlas, records)
    row = audit(result, records[-1]["wiki_id"], field)[0]
    assert row.type_check == "mismatch" and row.resolved_target_type == actual
    assert row.target_resolution_status != "unresolved-external-or-missing"
    assert not row.path_eligible and row.diagnostic_codes == ("wrong-target-type",)
    assert navigation(result) == [] and records == before


@pytest.mark.parametrize(
    "ref",
    [
        "CMP-MISSING",
        "WPAPER-MISSING",
        "WRQ-MISSING",
        "wpaper-fixture",
        "Fixture Title",
        "alias",
        "[[WPAPER-FIXTURE]]",
        "WPAPER-FIXTURE#v1",
        "WPAPER-FIXTURE@1",
        "https://example.invalid/source",
        "doi:10.0000/synthetic",
        "urn:example:source",
    ],
)
def test_a03_no_name_prefix_alias_or_normalization(atlas, ref):
    result = build(
        atlas,
        [
            props("paper", title="Fixture Title", aliases=["alias"], tags=[ref]),
            props("finding", source_refs=[ref]),
        ],
    )
    row = audit(result, "WFIND-FIXTURE", "source_refs")[0]
    assert row.resolved_target_type is None and row.target_profile is None
    assert row.type_check == "unresolved" and not row.path_eligible


def test_a04_shared_external_sources_are_not_identity_joins(atlas):
    reading = props("reading_note", source_refs=["doi:example"], rq_refs=["WRQ-FIXTURE"])
    del reading["paper_refs"]
    result = build(
        atlas,
        [
            props("paper", source_refs=["doi:example"], doi="doi:example"),
            props("paper", wiki_id="WPAPER-OTHER", source_refs=["doi:example"]),
            reading,
            props("research_question"),
        ],
    )
    assert navigation(result) == []
    assert len([r for r in audit(result) if r.target_identifier == "doi:example"]) == 3


def test_a05_legacy_and_duplicate_collision_failures(atlas):
    legacy = LEGACY | {"wiki_id": "READ-LEGACY", "doc_type": "reading_note", "secret": "opaque"}
    result = build(atlas, [legacy, props("paper", reading_note_refs=["READ-LEGACY"])])
    row = audit(result, "WPAPER-FIXTURE", "reading_note_refs")[0]
    assert row.target_resolution_status == "resolved-private"
    assert row.target_profile == "legacy" and row.target_record_version is None
    assert not row.path_eligible and row.type_check == "match"
    assert navigation(result) == []
    with pytest.raises(index.ProjectionError, match="Invalid private"):
        build(atlas, [LEGACY, props()])
    collision = Atlas(
        dict(atlas.entities) | {"WPAPER-FIXTURE": atlas.entities["PAPER-FIXTURE"]}, ()
    )
    with pytest.raises(index.ProjectionError):
        build(collision, [props("paper")])
    snapshot = index.make_snapshot([props()], atlas)
    with pytest.raises(index.ProjectionError, match="Duplicate"):
        index.Resolver(atlas, index.Snapshot(records=snapshot.records * 2))


def test_a06_roles_remain_distinct_and_uninherited(atlas):
    records = [props("paper"), props("reading_note", **{r: ["CMP-CORTEX"] for r in index.ROLES})]
    result = build(atlas, records)
    rows = navigation(result)
    assert len(rows) == 5
    assert {r.originating_role for r in rows} == set(index.ROLES)
    assert all(
        r.source_wiki_id == "READ-FIXTURE" and r.navigation_start.identifier == "WPAPER-FIXTURE"
        for r in rows
    )
    assert all(r.originating_property == r.via[-1].property == r.originating_role for r in rows)
    assert records[0].get("research_direct_subject_refs") is None


@pytest.mark.parametrize("paper_id", ["WPAPER-FIXTURE", "PAPER-FIXTURE"])
@pytest.mark.parametrize("source_field", ["paper_refs", "source_refs"])
def test_a07_inverse_e1_e6_public_and_private(atlas, paper_id, source_field):
    reading = props("reading_note", rq_refs=["RQ-PROGRAM-AB-001"])
    del reading["paper_refs"]
    reading[source_field] = [paper_id]
    result = build(atlas, [props("paper"), reading])
    rows = navigation(result)
    assert len(rows) == 1
    assert signature(rows[0]) == (("E1", "inverse"), ("E6", "forward"))
    assert rows[0].via[0].property == source_field
    assert all(v.declaring_wiki_id == "READ-FIXTURE" for v in rows[0].via)


@pytest.mark.parametrize("source", ["WPAPER-FIXTURE", "WPAPER-OTHER", "doi:unknown"])
def test_a08_e2_requires_exact_confirmation(atlas, source):
    reading = props("reading_note", source_refs=[source], rq_refs=["WRQ-FIXTURE"])
    del reading["paper_refs"]
    result = build(
        atlas,
        [
            props("paper", reading_note_refs=["READ-FIXTURE"]),
            reading,
            props("paper", wiki_id="WPAPER-OTHER"),
            props("research_question"),
        ],
    )
    audit_row = audit(result, "WPAPER-FIXTURE", "reading_note_refs")[0]
    e2_rows = [r for r in navigation(result) if r.via[0].edge_id == "E2"]
    if source == "WPAPER-FIXTURE":
        assert audit_row.path_eligible and len(e2_rows) == 1
        premise = e2_rows[0].prerequisite_refs[0]
        assert premise.declaring_wiki_id == "READ-FIXTURE"
        assert premise.property == "source_refs"
        assert premise.declared_target_identifier == source
        assert premise.traversal_direction == "forward"
    else:
        assert not audit_row.path_eligible and not e2_rows
        assert audit_row.diagnostic_codes == ("reading-source-not-matched",)


def test_a09_a10_all_provenances_and_inverse_process_owner(atlas):
    result = build(atlas, sample_records())
    nav = navigation(result)
    assert {v.edge_id for r in nav for v in r.via} == {f"E{i}" for i in range(1, 10)}
    paths = {signature(r) for r in nav}
    for first in (("E1", "inverse"), ("E2", "forward")):
        for middle in (("E4", "forward"), ("E5", "inverse")):
            for rq in (("E6", "forward"), ("E7", "inverse")):
                assert (first, middle, rq, ("E8", "inverse")) in paths
    assert (("E3", "inverse"), ("E6", "forward")) in paths
    rows = [r for r in nav if r.navigation_view == "process"]
    assert len(rows) == 12
    for row in rows:
        assert row.source_wiki_id == row.target_identifier == "PROC-FIXTURE"
        assert row.originating_property == "rq_refs" and row.originating_role is None
        assert row.via[-1].declared_target_identifier == "WRQ-FIXTURE"
        assert row.via[-1].declaring_wiki_id == "PROC-FIXTURE"
        assert row.via[-1].traverse_from.identifier == "WRQ-FIXTURE"
    assert len({r.row_id for r in result.rows}) == len(result.rows)


@pytest.mark.parametrize(
    "target,view", [("CMP-CORTEX", "component"), ("PROC-FIXTURE", "process"), ("WRQ-FIXTURE", "rq")]
)
def test_a11_terminal_roles_and_k0(atlas, target, view):
    result = build(
        atlas,
        [
            props("paper", research_method_or_baseline_refs=[target]),
            props("process", rq_refs=["WRQ-FIXTURE"]),
            props("research_question"),
        ],
    )
    rows = navigation(result)
    assert len(rows) == 1 and rows[0].navigation_view == view
    assert rows[0].path_kind == "direct"
    assert rows[0].source_wiki_id == "WPAPER-FIXTURE"
    assert rows[0].originating_role == "research_method_or_baseline_refs"
    assert signature(rows[0]) == (("E9", "forward"),)


def test_a12_no_other_traversal_or_cross_product(atlas):
    records = sample_records()
    before = build(atlas, records)
    records[3]["research_direct_subject_refs"] = ["CMP-CORTEX"]
    records[4]["research_direct_subject_refs"] = ["CMP-CORTEX"]
    records[2].update(supports_refs=["WFIND-FIXTURE"], wiki_refs=["WFIND-FIXTURE"])
    records += [
        props("topic", paper_refs=["WPAPER-FIXTURE"], process_refs=["PROC-FIXTURE"]),
        props("dossier", paper_refs=["WPAPER-FIXTURE"], process_refs=["PROC-FIXTURE"]),
        props("research_thread", process_refs=["PROC-FIXTURE"], finding_refs=["WFIND-FIXTURE"]),
    ]
    after = build(atlas, records)
    assert navigation(after) == navigation(before)
    assert max(len(r.via) for r in navigation(after)) == 4
    assert all(
        r.source_wiki_id not in {"TOPIC-FIXTURE", "DOS-FIXTURE", "WTHREAD-FIXTURE"}
        for r in navigation(after)
    )
    assert all(
        len({r.via[0].traverse_from.identifier, *(v.traverse_to.identifier for v in r.via)})
        == len(r.via) + 1
        for r in navigation(after)
    )


def test_a13_fingerprint_and_row_order_are_deterministic(atlas):
    records = sample_records()
    records[1]["rq_refs"] += ["RQ-PROGRAM-AB-001"]
    before = build(atlas, records)
    for record in records:
        for field, values in record.items():
            if field in index.PROPERTIES and isinstance(values, list):
                values.reverse()
                values += values[:1]
    # ReadingNote's source cardinality is validated BEFORE deduplication.
    records[1]["paper_refs"] = ["WPAPER-FIXTURE"]
    after = build(atlas, [dict(reversed(list(r.items()))) for r in reversed(records)])
    assert after == before
    assert index.render_index(after) == index.render_index(before)
    assert [r.row_id for r in after.rows] == sorted(r.row_id for r in after.rows)
    records[1]["paper_refs"] *= 2
    with pytest.raises(index.ProjectionError):
        build(atlas, records)


def test_a14_a20_nonconsumed_properties_and_statuses(atlas):
    records = sample_records()
    before = build(atlas, records)
    for record in records:
        record.update(
            title="SYNTHETIC-PRIVATE-TITLE",
            aliases=["secret"],
            tags=["secret"],
            document_maturity="archived",
            supersedes_refs=["OLD"],
            review_refs=["REVIEW"],
        )
    records[2]["review_state"] = "domain_accepted"
    records[3].update(
        question_stage="candidate", decision_state="accepted", decision_refs=["WDEC-UNKNOWN"]
    )
    after = build(atlas, records)
    assert after == before
    raw = index.render_index(after)
    for forbidden in (
        b"SYNTHETIC",
        b"supports_refs",
        b"review_state",
        b"decision_state",
        b"supersedes_refs",
        b"question_stage",
    ):
        assert forbidden not in raw
    records[3]["question_stage"] = "idea"
    with pytest.raises(index.ProjectionError):
        build(atlas, records)


@pytest.mark.parametrize("change", ["ref", "revision", "identity", "type", "add", "remove"])
def test_a15_relevant_changes_change_fingerprint(atlas, change):
    records = sample_records()
    before = build(atlas, records)
    if change == "ref":
        records[1]["rq_refs"] = ["WRQ-MISSING"]
    elif change == "revision":
        records[2]["record_version"] += 1
    elif change == "identity":
        records[0]["wiki_id"] = "WPAPER-CHANGED"
    elif change == "type":
        records[-1] = props("topic")
    elif change == "add":
        records.append(props("topic"))
    else:
        records.pop()
    assert build(atlas, records).private_input_fingerprint != before.private_input_fingerprint


@pytest.mark.parametrize(
    "literal",
    [
        "/private/secret",
        "C:/secret",
        "C:\\secret",
        "C:secret",
        "\\\\host\\secret",
        "file:///secret",
        "FILE:secret",
        "../secret",
        "safe/../../secret",
        "safe\\..\\secret",
        "secret\x00x",
        "x\ny",
        "x\ty",
        "x\u202ey",
    ],
)
def test_a18_unsafe_literals_are_generic_preflight_errors(atlas, literal):
    with pytest.raises(index.ProjectionError) as caught:
        build(atlas, [props("finding", source_refs=[literal])])
    assert literal not in str(caught.value)


def test_a17_a18_markdown_injection_and_private_locator_encoding(atlas):
    malicious = "https://example.invalid/`[x](file:x)|<script>&"
    result = build(atlas, [props("finding", source_refs=[malicious])])
    text = index.render_navigation(
        result, atlas, {"WFIND-FIXTURE": PurePosixPath("Notes/a [b]#(c)|.md")}
    ).decode()
    assert malicious not in text and "<script>" not in text and "file:x" not in text
    assert "Notes/a%20%5Bb%5D%23%28c%29%7C.md" in text
    assert "&#124;" in text and "&#96;" in text and "&#91;" in text
    assert text.count(index.WARNING) == 3
    for locator in (PurePosixPath("/private/x.md"), PurePosixPath("../x.md")):
        with pytest.raises(index.ProjectionError, match="locator"):
            index.render_navigation(result, atlas, {"WFIND-FIXTURE": locator})


def test_a27_empty_and_unresolved_only_are_valid(atlas):
    for records in ([], [props("finding", source_refs=["WPAPER-MISSING"])], [LEGACY]):
        result = build(atlas, records)
        assert navigation(result) == []
        text = index.render_navigation(result, atlas, {}).decode()
        assert text.count("No matching declared paths in this snapshot.") == 3
        assert "Direct Reference Audit" in text
        assert index.render_index(result) == index.render_index(build(atlas, records))


def test_row_hash_collision_is_not_silently_deduplicated(atlas, monkeypatch):
    monkeypatch.setattr(index, "digest", lambda _: "0" * 64)
    with pytest.raises(index.ProjectionError, match="collision"):
        build(atlas, sample_records())


def test_a17_legacy_opaque_fields_and_all_rows_remain_private(atlas):
    legacy = LEGACY | {
        "wiki_id": "READ-LEGACY",
        "doc_type": "reading_note",
        "opaque": {"private": "/private/LEGACY-SECRET"},
        "title": "LEGACY-TITLE-SECRET",
        "paper_refs": ["LEGACY-REF-SECRET"],
    }
    records = [*sample_records(), legacy]
    result = build(atlas, records)
    output = index.render_index(result) + index.render_navigation(result, atlas, {})
    assert b"LEGACY-SECRET" not in output
    assert b"LEGACY-TITLE-SECRET" not in output
    assert b"LEGACY-REF-SECRET" not in output
    markdown = index.render_navigation(result, atlas, {}).decode()
    assert all(markdown.count(row.row_id) == 1 for row in result.rows)
    before = copy.deepcopy(records)
    build(atlas, records)
    assert records == before


def test_a20_decision_and_candidate_metadata_never_fabricate_history(atlas):
    records = [
        props("research_question"),
        props("experiment_lead"),
        props("decision_draft"),
        props("decision_draft", wiki_id="WDEC-SECOND", record_version=9),
    ]
    first = build(atlas, records)
    records[0].update(
        question_stage="candidate", decision_state="accepted", decision_refs=["WDEC-SECOND"]
    )
    records[2].update(overrules_refs=["WDEC-SECOND"], supersedes_refs=["WDEC-OLD"])
    records[3].update(overrules_refs=["WDEC-FIXTURE"], supersedes_refs=["WDEC-FIXTURE"])
    assert build(atlas, list(reversed(records))) == first
    text = index.render_navigation(first, atlas, {}).decode()
    assert "Candidate History" not in text and "Decision Lineage" not in text
    assert navigation(first) == []
