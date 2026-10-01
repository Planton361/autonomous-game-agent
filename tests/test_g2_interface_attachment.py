"""Bounded #120 G2 proof; every private Research record here is synthetic."""

import copy
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
import yaml
from pydantic import ValidationError
from test_research_wiki_projection import SECRET, filesystem_state, git, write_note
from test_research_wiki_schema import props
from test_research_wiki_views import setup as setup

from fh_agent.research_atlas import private_reference_index as index
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.schema import Interface
from fh_agent.research_atlas.validator import Atlas, load_registry
from fh_agent.research_atlas.wiki_schema import validate_wiki_records
from fh_agent.research_atlas.workspace import workspace_tree
from fh_agent.research_atlas.workspace_harness import check as check_workspace

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
TARGET = index.PILOT_INTERFACE


@pytest.fixture(scope="module")
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


def records():
    # All five roles remain authored literally, without asserting any source was read.
    roles = {role: [TARGET] for role in index.ROLES}
    return [
        props("paper", reading_note_refs=["READ-FIXTURE"], **roles),
        props("reading_note", finding_refs=["WFIND-FIXTURE"], **roles),
        props(
            "finding", source_refs=["WPAPER-FIXTURE"], reading_note_refs=["READ-FIXTURE"], **roles
        ),
    ]


def build(atlas, authored=None):
    return index.build_index(
        atlas, index.make_snapshot(records() if authored is None else authored, atlas), COMMIT
    )


def tree(atlas, reference, authored=None, locators=None):
    authored = records() if authored is None else authored
    return views.reference_views_tree(
        COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators
        if locators is not None
        else {r["wiki_id"]: PurePosixPath("synthetic") / (r["wiki_id"] + ".md") for r in authored},
        index.make_snapshot(authored, atlas),
        False,
        validate_wiki_records(authored, atlas.entities.keys()),
    )


@pytest.mark.parametrize(
    "kind,owner",
    [("paper", "WPAPER-FIXTURE"), ("reading_note", "READ-FIXTURE"), ("finding", "WFIND-FIXTURE")],
)
def test_synthetic_direct_attachment_all_literal_roles(atlas, kind, owner):
    result = build(atlas)
    attachments = [
        row for row in index.interface_attachment_rows(result) if row.source_wiki_id == owner
    ]
    assert len(attachments) == 5
    assert {row.originating_role for row in attachments} == set(index.ROLES)
    for row in attachments:
        assert row.source_doc_type == kind
        assert row.source_record_version == 1
        assert row.target_identifier == TARGET and row.resolved_target_type == "Interface"
        assert row.row_kind == "declared-reference" and row.path_kind == "direct"
        assert row.via[0].declaring_wiki_id == owner
        assert row.via[0].role == row.originating_role == row.originating_property
        assert row.via[0].declared_target_identifier == TARGET
        assert row.via[0].declared_target_type == "Interface"
        assert row.via[0].edge_id == "E9"
    paths = index.technical_navigation_rows(result)
    assert {p.recipe.split("/")[1] for p in paths} == {"K0", "K1", "K2", "K3"}
    assert {p.source_wiki_id for p in paths} == {"WPAPER-FIXTURE", "READ-FIXTURE", "WFIND-FIXTURE"}
    assert all(p.via[-1].edge_id == "E9" and len(p.via) <= 3 for p in paths)
    assert index.component_navigation_rows(result, "CMP-MEM-RETRIEVAL") == ()
    assert index.ReferenceIndex.model_validate_json(result.model_dump_json()) == result


def test_direct_and_related_preferred_pages_and_native_links(atlas):
    result = build(atlas)
    locators = {
        r["wiki_id"]: PurePosixPath("synthetic notes") / (r["wiki_id"] + ".md") for r in records()
    }
    outputs = tree(atlas, result, locators=locators)
    paths = views.identity_page_paths(atlas)
    direct = outputs[paths[TARGET]].decode()
    related = outputs[paths["CMP-MEM-RETRIEVAL"]].decode()
    assert "### Directly attached Research" in direct
    assert "### Related technical-scope Research" in related
    assert "### Directly attached Research" not in related
    assert "Related technical-scope Research" not in direct
    assert "Memory Retrieval does not inherit the role or attachment" in related
    assert "`CMP-MEM-RETRIEVAL` — `supplies`" in related
    for page in (direct, related):
        assert "type `Interface`" in page and "Original technical target:" in page
        assert "N-T/K0/E9:forward" in page
        assert "N-T/K3/" in page and "Prerequisite (not traversed)" in page
        for row in index.interface_attachment_rows(result):
            assert row.source_wiki_id in page and row.row_id in page
            assert row.originating_role in page
        assert "synthetic%20notes/" in page
        assert "_generated/derived/" + str(paths[TARGET].with_suffix("")) in page
        assert "No parent, part_of ancestry, Function membership, Domain, legacy Assembly" in page
    assert "_generated/derived/" + str(paths["CMP-MEM-RETRIEVAL"].with_suffix("")) in direct
    assert paths["CMP-MEM-RETRIEVAL"] == views.MEMORY_WORKBENCH
    assert len([p for p in outputs if p == paths[TARGET]]) == 1
    # All attachment facts/navigation are native Markdown; CSS/Mermaid supplies none.
    assert "Exact authored role:" in direct and "Direct attachment audit row:" in direct
    assert (
        "Gap Analysis" in direct
        and "Not assessed / no authorized gap assessment attached." in direct
    )


def test_related_requires_exact_independent_one_hop_supplies(atlas):
    result = build(atlas)
    without = replace(
        atlas,
        relationships=tuple(
            e
            for e in atlas.relationships
            if (e.source, e.relation, e.target) != ("CMP-MEM-RETRIEVAL", "supplies", TARGET)
        ),
    )
    model = views.identity_page_model(without, result, "CMP-MEM-RETRIEVAL")
    assert model.related_scope_relation is None and model.interface_attachments == ()
    page = views.render_identity_page(COMMIT, without, model).decode()
    assert "No accepted one-hop technical relation" in page
    assert "WPAPER-FIXTURE" not in page
    assert index.render_index(build(without)) == index.render_index(result)
    # Technical edges never alter the private fingerprint or create a Research edge.
    assert build(without).private_input_fingerprint == result.private_input_fingerprint


def test_no_parent_function_domain_assembly_folder_backlink_or_graph_inheritance(atlas):
    authored = records() + [props("research_question", research_direct_subject_refs=[TARGET])]
    for r in authored:
        r["atlas_refs"] = ["CMP-MEMORY"]
        r["wiki_refs"] = ["CMP-MEM-RETRIEVAL", "FUNC-RETAIN-RETRIEVE", "DOM-EVIDENCE-MEMORY"]
    result = build(atlas, authored)
    assert not any(
        r.navigation_view == "technical" and r.source_doc_type == "research_question"
        for r in result.rows
    )
    assert all(r.target_identifier == TARGET for r in index.technical_navigation_rows(result))
    for identity in views.identity_page_paths(atlas):
        if identity in {TARGET, "CMP-MEM-RETRIEVAL"}:
            continue
        model = views.identity_page_model(atlas, result, identity)
        assert model.interface_attachments == () and model.technical_paths == ()
        assert model.related_scope_relation is None
    assert all(
        index.component_navigation_rows(result, identity) == ()
        for identity in ("CMP-MEMORY", "SYS-AGA", "CMP-MEM-RETRIEVAL")
    )
    assert all(
        r.via[-1].declared_target_identifier == TARGET
        for r in index.interface_attachment_rows(result)
    )


@pytest.mark.parametrize(
    "target",
    [
        "DOM-EVIDENCE-MEMORY",
        "FUNC-RETAIN-RETRIEVE",
        "ENV-GAME-INSTANCE",
        "IF-CORTEX-MANAGER",
        "IF-MISSING",
    ],
)
def test_unaccepted_or_unresolved_targets_remain_diagnostic(atlas, target):
    result = build(atlas, [props("paper", research_direct_subject_refs=[target])])
    row = next(r for r in result.rows if r.originating_role)
    assert not row.path_eligible and row.diagnostic_codes
    assert index.technical_navigation_rows(result) == ()
    assert index.interface_attachment_rows(result) == ()
    if target == "IF-MISSING":
        assert row.diagnostic_codes == ("unresolved-reference",)


def test_exact_interface_wrong_actual_type_fails_closed(atlas):
    entities = dict(atlas.entities)
    entities[TARGET] = entities["CMP-CORTEX"]  # Resolver uses actual type, never IF prefix.
    wrong = replace(atlas, entities=entities)
    result = build(wrong)
    assert index.interface_attachment_rows(result) == ()
    assert index.technical_navigation_rows(result) == ()
    assert all(not r.path_eligible for r in result.rows if r.originating_role)


@pytest.mark.parametrize(
    "mutation",
    [
        {"recipe": "N-T/K4/E9:forward"},
        {"recipe": "N-T/K0/E9:forward/E8:inverse"},
        {"recipe": "N-T/K1/E9:forward"},
        {"navigation_view": "component"},
        {"target_identifier": "CMP-MEM-RETRIEVAL"},
        {"resolved_target_type": "Component"},
        {"source_wiki_id": "READ-FIXTURE"},
        {"originating_role": "research_adjacent_context_refs"},
    ],
)
def test_invalid_finite_recipes_fail_before_projection(atlas, mutation):
    result = build(atlas)
    row = next(
        r
        for r in result.rows
        if r.recipe == "N-T/K0/E9:forward" and r.originating_role == "research_direct_subject_refs"
    )
    with pytest.raises(ValidationError, match="Invalid finite N-T"):
        index.Row.model_validate(row.model_dump() | mutation)
    forged = row.model_copy(update=mutation)
    bad = result.model_copy(update={"rows": (forged,)})
    with pytest.raises(ValidationError):
        tree(atlas, bad)


def test_e9_cannot_continue_even_if_terminal_has_other_declarations(atlas):
    result = build(
        atlas,
        records()
        + [
            props("research_question", finding_refs=["WFIND-FIXTURE"]),
            props("process", rq_refs=["WRQ-FIXTURE"]),
        ],
    )
    terminal = next(r for r in result.rows if r.recipe == "N-T/K0/E9:forward")
    path = index.NavigationPath(
        terminal.navigation_start, "K0", tuple(index.Hop(v) for v in terminal.via)
    )
    fake = terminal.via[-1].model_copy(
        update={
            "edge_id": "E8",
            "traverse_from": path.end,
            "traverse_to": terminal.navigation_start,
        }
    )
    assert path.extend(index.Hop(fake)) is None
    assert all(not any(v.edge_id == "E9" for v in row.via[:-1]) for row in result.rows)
    assert max(len(row.via) for row in result.rows) <= 4


def test_unanchored_reading_and_finding_still_display_exact_direct_declarations(atlas):
    authored = [
        props("reading_note", paper_refs=["WPAPER-MISSING"], research_direct_subject_refs=[TARGET]),
        props("finding", research_adjacent_context_refs=[TARGET]),
    ]
    result = build(atlas, authored)
    assert len(index.interface_attachment_rows(result)) == 2
    assert index.technical_navigation_rows(result) == ()
    direct = tree(atlas, result, authored)[views.identity_page_paths(atlas)[TARGET]].decode()
    assert "READ-FIXTURE" in direct and "WFIND-FIXTURE" in direct
    assert "No resolved Paper-anchored finite N-T path" in direct


def test_order_independent_bytes_and_private_fingerprint(atlas):
    authored = records()
    before = copy.deepcopy(authored)
    result = build(atlas, authored)
    reversed_atlas = Atlas(
        dict(reversed(tuple(atlas.entities.items()))),
        tuple(reversed(atlas.relationships)),
        atlas.source_atlas_schema,
    )
    reversed_records = list(reversed(authored))
    assert index.render_index(build(reversed_atlas, reversed_records)) == index.render_index(result)
    assert tree(reversed_atlas, build(reversed_atlas, reversed_records), reversed_records) == tree(
        atlas, result, authored
    )
    for role in index.ROLES:
        changed = copy.deepcopy(authored)
        changed[0][role] = []
        assert build(atlas, changed).private_input_fingerprint != result.private_input_fingerprint
    changed = copy.deepcopy(authored)
    changed[0]["record_version"] = 2
    assert build(atlas, changed).private_input_fingerprint != result.private_input_fingerprint
    changed[0] = authored[0] | {"title": "Different synthetic title", "aliases": ["different"]}
    assert build(atlas, changed) == result
    locators = {r["wiki_id"]: PurePosixPath("synthetic") / (r["wiki_id"] + ".md") for r in authored}
    locators["WPAPER-FIXTURE"] = PurePosixPath("folder/synthetic.md")
    assert tree(atlas, result, locators=locators) != tree(atlas, result)
    assert authored == before


def test_pilot_does_not_enable_other_interfaces(atlas):
    entities = dict(atlas.entities)
    entities["IF-SYNTHETIC"] = Interface(
        id="IF-SYNTHETIC",
        type="Interface",
        name="Synthetic unrelated",
        description="Synthetic only",
        technical=entities[TARGET].technical,
    )
    extended = replace(atlas, entities=entities)
    result = build(extended, [props("paper", research_direct_subject_refs=["IF-SYNTHETIC"])])
    assert index.technical_navigation_rows(result) == ()
    assert index.interface_attachment_rows(result) == ()


def test_synthetic_projection_migration_authored_bytes_zero_write_and_export_denial(setup):
    repo, vault, sha = setup
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    for r in records():
        write_note(vault / "authored" / (r["wiki_id"] + ".md"), r)
    before = filesystem_state(vault)
    outputs = views.project(repo, vault, sha)
    after = filesystem_state(vault)
    assert all(after[path][3] == value[3] for path, value in before.items() if value[3] is not None)
    assert check_workspace(repo, vault) is not None
    assert filesystem_state(vault) == after
    manifest = yaml.safe_load(outputs[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.11"
    assert manifest["reference_index_schema_version"] == "1.1"
    assert {entry["path"] for entry in manifest["owned_files"]} == {
        str(p) for p in outputs if p != views.MANIFEST
    }
    assert all(SECRET.encode() not in payload for payload in outputs.values())
    # Simulate intact v2.10/index-1.0 generated ownership, then migrate only derived output.
    manifest["view_schema_version"] = "2.10"
    manifest["reference_index_schema_version"] = "1.0"
    root = vault / views.OWNED_ROOT
    reference_path = root / views.REFERENCE_INDEX
    old_index = reference_path.read_bytes().replace(
        b"index_schema_version: '1.1'", b"index_schema_version: '1.0'"
    )
    reference_path.write_bytes(old_index)
    for entry in manifest["owned_files"]:
        if entry["path"] == str(views.REFERENCE_INDEX):
            entry["sha256"] = index.digest(old_index)
    (root / views.MANIFEST).write_text(yaml.safe_dump(manifest))
    legacy_state = filesystem_state(vault)
    with pytest.raises(views.ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == legacy_state
    migrated = views.project(repo, vault, sha)
    assert migrated == outputs
    assert check_workspace(repo, vault) is not None
    assert all(
        filesystem_state(vault)[path][3] == value[3]
        for path, value in before.items()
        if value[3] is not None
    )
    public = workspace_tree(load_registry(repo / "docs/research-atlas"))
    assert all(
        owner not in payload
        for owner in ("WPAPER-FIXTURE", "READ-FIXTURE", "WFIND-FIXTURE")
        for payload in public.values()
    )


def test_nt_prerequisite_and_type_provenance_cannot_be_forged(atlas):
    result = build(atlas)
    path = next(r for r in result.rows if r.recipe == "N-T/K1/E2:forward/E9:forward")
    for mutation in (
        {"prerequisite_refs": ()},
        {"path_kind": "direct"},
        {
            "via": (
                path.via[0].model_copy(update={"declared_target_type": "Component"}),
                *path.via[1:],
            )
        },
    ):
        with pytest.raises(ValidationError, match="Invalid finite N-T"):
            index.Row.model_validate(path.model_dump() | mutation)


def test_opaque_lists_do_not_create_transitive_research_closure(atlas):
    authored = [
        props(
            "paper",
            wiki_id="WPAPER-UNATTACHED",
            related_version_refs=["WPAPER-FIXTURE"],
            wiki_refs=["WPAPER-FIXTURE"],
        ),
        props("paper", research_direct_subject_refs=[TARGET]),
        props(
            "research_question",
            finding_refs=["WFIND-FIXTURE"],
            research_project_transfer_refs=[TARGET],
        ),
        props("finding", research_direct_subject_refs=[TARGET]),
    ]
    result = build(atlas, authored)
    assert not any(
        r.navigation_start.identifier == "WPAPER-UNATTACHED"
        for r in index.technical_navigation_rows(result)
    )
    assert not any(
        r.source_doc_type == "research_question" for r in index.interface_attachment_rows(result)
    )
    # The separate #137 private ResearchQuestion target contract remains absent and closed.
    with pytest.raises(index.ProjectionError, match="Invalid private identity or profile"):
        build(atlas, [props("research_question", technical_subject_refs=[TARGET])])
