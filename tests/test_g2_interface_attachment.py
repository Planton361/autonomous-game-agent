"""Completed #120 pilot and #121 rollout; all private Research is synthetic."""

import copy
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError
from test_research_wiki_schema import props

from fh_agent.research_atlas import private_reference_index as index
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.schema import Interface
from fh_agent.research_atlas.validator import Atlas, load_registry
from fh_agent.research_atlas.wiki_schema import validate_wiki_records

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
        "Gap-assessment status" in direct
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
    assert model.related_attachments == () and model.direct_attachments == ()
    page = views.render_identity_page(COMMIT, without, model).decode()
    assert "No matching Research through an accepted one-hop technical relation" in page
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
        assert model.direct_attachments == () and model.descendant_attachments == ()
        assert all(
            item.attachment.target_identifier == TARGET and item.relation is not None
            for item in model.related_attachments
        )
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
    entities[TARGET] = entities[
        "DOM-EVIDENCE-MEMORY"
    ]  # Resolver uses actual type, never IF prefix.
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


def test_rollout_enables_other_actual_interfaces(atlas):
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
    assert len(index.technical_navigation_rows(result)) == 1
    assert len(index.technical_attachment_rows(result)) == 1
    assert index.interface_attachment_rows(result) == ()


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


def test_g2_manifest_is_finite_and_reuses_preferred_ownership(atlas):
    import yaml

    reference = build(atlas)
    current = tree(atlas, reference)
    empty = tree(atlas, build(atlas, []), [])
    assert current.keys() == empty.keys()
    manifest = yaml.safe_load(current[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.13"
    assert manifest["reference_index_schema_version"] == "1.2"
    assert manifest["private_input_fingerprint"] == reference.private_input_fingerprint
    owned = {entry["path"]: entry for entry in manifest["owned_files"]}
    assert set(owned) == {str(p) for p in current if p != views.MANIFEST}
    assert all(
        entry["sha256"] == index.digest(current[PurePosixPath(path)])
        for path, entry in owned.items()
    )
    assert all(
        entry["ownership"] == views.STRICT_OWNERSHIP
        for path, entry in owned.items()
        if not path.endswith(".base")
    )


# #121: same synthetic private declarations, all six accepted actual Registry types.
ROLLOUT_TARGETS = {
    "System": "SYS-AGA",
    "Component": "CMP-OBSERVATION-BUILDER",
    "Interface": TARGET,
    "Contract": "CON-CORTEX-CONTEXT",
    "DataArtifact": "DAT-RETRIEVAL-SNAPSHOT",
    "MeasurementPoint": "MEAS-RETRIEVAL-DELIVERY-001",
}


def rollout_records():
    """Reusable positive G6 input; write only to a disposable physical-path vault."""
    targets = list(ROLLOUT_TARGETS.values())
    return [r | {role: targets for role in index.ROLES} for r in records()]


@pytest.fixture(scope="module")
def rollout(atlas):
    authored = rollout_records()
    reference = build(atlas, authored)
    return reference, tree(atlas, reference, authored)


@pytest.mark.parametrize("kind", ["paper", "reading_note", "finding"])
@pytest.mark.parametrize("target_type,target", ROLLOUT_TARGETS.items())
def test_rollout_all_types_records_roles_exact_projection(
    atlas, rollout, kind, target_type, target
):
    reference, outputs = rollout
    rows = [
        r
        for r in index.technical_attachment_rows(reference)
        if r.target_identifier == target and r.source_doc_type == kind
    ]
    assert len(rows) == 5
    assert {r.originating_role for r in rows} == set(index.ROLES)
    model = views.identity_page_model(atlas, reference, target)
    assert len(model.direct_attachments) == 15  # Multiple records/roles at one exact subject.
    page = outputs[views.identity_page_paths(atlas)[target]].decode()
    direct = page.split("### Directly attached Research", 1)[1].split(
        "### Research attached below", 1
    )[0]
    for row in rows:
        assert row.resolved_target_type == target_type
        assert row.source_record_version == 1
        assert row.via[-1].declared_target_identifier == target
        assert row.via[-1].role == row.originating_role == row.originating_property
        assert row.via[-1].declaring_wiki_id == row.source_wiki_id
        for literal in (row.row_id, row.source_wiki_id, row.originating_role, target, target_type):
            assert literal in direct
        assert "E9:forward" in direct and "resolved-public" in direct
    assert len(index.technical_attachment_rows(reference)) == 90
    assert len({r.source_wiki_id for r in index.technical_attachment_rows(reference)}) == 3
    assert all(len(r.via) <= 4 for r in reference.rows)
    assert all(
        r.via[-1].edge_id == "E9"
        for r in reference.rows
        if r.navigation_view in {"technical", "component"}
    )


@pytest.mark.parametrize("target", list(ROLLOUT_TARGETS.values()))
def test_rollout_actual_wrong_type_and_unresolved_prefix_fail_closed(atlas, target):
    entities = dict(atlas.entities)
    entities[target] = entities["DOM-EVIDENCE-MEMORY"]
    wrong = replace(atlas, entities=entities)
    rejected = build(wrong, [props("paper", research_direct_subject_refs=[target])])
    assert index.technical_attachment_rows(rejected) == ()
    assert all(not r.path_eligible for r in rejected.rows)
    assert (
        next(r for r in rejected.rows if r.target_identifier == target).resolved_target_type
        == "Domain"
    )
    entities.pop(target)
    missing = build(
        replace(atlas, entities=entities), [props("paper", research_direct_subject_refs=[target])]
    )
    assert index.technical_attachment_rows(missing) == ()
    assert next(r for r in missing.rows if r.target_identifier == target).diagnostic_codes == (
        "unresolved-reference",
    )


def synthetic_hierarchy(atlas, width=1, depth=6):
    """In-memory only; no Registry identities or hierarchy are authored into the repository."""
    from fh_agent.research_atlas.schema import Relationship

    entities = dict(atlas.entities)
    edges = list(atlas.relationships)
    trails = []
    for branch in range(width):
        trail = ["SYS-AGA"]
        for level in range(depth):
            identity = f"CMP-SYNTHETIC-{branch}-{level}"
            entities[identity] = entities["CMP-MEMORY"].model_copy(
                update={"id": identity, "name": identity}
            )
            edges.append(Relationship(source=identity, relation="part_of", target=trail[-1]))
            trail.append(identity)
        trails.append(tuple(trail))
    return replace(atlas, entities=entities, relationships=tuple(edges)), tuple(trails)


def test_six_level_component_scope_system_direct_and_no_parent_inheritance(atlas):
    hierarchy, trails = synthetic_hierarchy(atlas)
    trail = trails[0]
    authored = [
        props(
            "paper",
            research_direct_subject_refs=["SYS-AGA"],
            research_method_or_baseline_refs=[trail[-1]],
        ),
        props("finding", research_adjacent_context_refs=[trail[-1]]),
    ]
    reference = build(hierarchy, authored)
    root = views.identity_page_model(hierarchy, reference, "SYS-AGA")
    assert len(root.direct_attachments) == 1
    assert len(root.descendant_attachments) == 2
    assert root.direct_attachments[0].target_identifier == "SYS-AGA"
    assert all(item.part_of_path == trail for item in root.descendant_attachments)
    page = views.render_identity_page(COMMIT, hierarchy, root).decode()
    assert "### Directly attached Research" in page
    assert "### Research attached below this scope" in page
    assert " → ".join(f"`{identity}`" for identity in trail) in page
    assert "this page does not inherit" in page
    for level, identity in enumerate(trail[1:-1], 1):
        model = views.identity_page_model(hierarchy, reference, identity)
        assert model.direct_attachments == ()
        assert all(item.part_of_path == trail[level:] for item in model.descendant_attachments)
        assert index.component_navigation_rows(reference, identity) == ()
        assert all(
            item.attachment.target_identifier == trail[-1] for item in model.descendant_attachments
        )
    leaf = views.identity_page_model(hierarchy, reference, trail[-1])
    assert len(leaf.direct_attachments) == 2 and leaf.descendant_attachments == ()
    # Membership alone cannot create any E9 on a scope/parent or change the child's owner/role.
    assert {r.target_identifier for r in index.technical_attachment_rows(reference)} == {
        "SYS-AGA",
        trail[-1],
    }
    without = replace(
        hierarchy,
        relationships=tuple(
            e
            for e in hierarchy.relationships
            if not (e.relation == "part_of" and e.source == trail[-1])
        ),
    )
    assert views.identity_page_model(without, reference, "SYS-AGA").descendant_attachments == ()
    assert build(without, authored) == reference


def test_rollout_related_uses_only_existing_typed_lanes_no_measured_at(atlas):
    from fh_agent.research_atlas.schema import Relationship

    authored = [props("paper", research_direct_subject_refs=list(ROLLOUT_TARGETS.values()))]
    # Adversarial explicit adjacency to a supported target via an unaccepted lane.
    edges = (
        *atlas.relationships,
        Relationship(
            source="CMP-MEM-RETRIEVAL", relation="controls", target="DAT-RETRIEVAL-SNAPSHOT"
        ),
    )
    extended = replace(atlas, relationships=edges)
    reference = build(extended, authored)
    model = views.identity_page_model(extended, reference, "CMP-MEM-RETRIEVAL")
    assert model.direct_attachments == ()
    assert any(item.attachment.target_identifier == TARGET for item in model.related_attachments)
    for item in model.related_attachments:
        row, edge = item.attachment, item.relation
        assert row.target_identifier in {edge.source, edge.target}
        assert edge.relation in views._COMPONENT_LANE_RELATIONS[row.resolved_target_type]
        assert edge.relation not in {"measured_at", "controls", "part_of"}
    page = views.render_identity_page(COMMIT, extended, model).decode()
    related = page.split("### Related technical-scope Research", 1)[1].split("## Gap Analysis", 1)[
        0
    ]
    assert "Independent technical relation:" in related and "does not inherit" in related
    assert "MEAS-RETRIEVAL-DELIVERY-001" not in related
    assert "### Directly attached Research" not in page
    no_relations = replace(
        extended,
        relationships=tuple(
            e for e in edges if e not in tuple(item.relation for item in model.related_attachments)
        ),
    )
    assert (
        views.identity_page_model(no_relations, reference, model.subject.id).related_attachments
        == ()
    )
    assert build(no_relations, authored) == reference
    # No second hop: a Component related to a Component is not a lane to its Research.
    assert views.identity_page_model(extended, reference, "CMP-MEMORY").related_attachments == ()


def test_measurement_relevance_boundary_is_local_and_explicit(atlas, rollout):
    reference, outputs = rollout
    target = ROLLOUT_TARGETS["MeasurementPoint"]
    page = outputs[views.identity_page_paths(atlas)[target]].decode()
    for phrase in (
        "instrument validity",
        "measurement execution",
        "observed effect",
        "experimental result",
        "scientific evidence",
        "accepted Claim",
        "measured_at relations do not propagate",
    ):
        assert phrase in page
    for model in views.identity_page_models(atlas, reference):
        assert all(
            item.attachment.target_identifier != target for item in model.related_attachments
        )
        assert all(
            item.attachment.target_identifier != target for item in model.descendant_attachments
        )


def test_no_synthesis_rq_domain_function_assembly_or_opaque_relevance(atlas, rollout):
    from fh_agent.research_atlas.wiki_schema import ResearchQuestion

    authored = rollout_records() + [
        props("synthesis", research_direct_subject_refs=list(ROLLOUT_TARGETS.values())),
        props("research_question", research_direct_subject_refs=list(ROLLOUT_TARGETS.values())),
    ]
    reference = build(atlas, authored)
    assert not any(
        r.source_doc_type in {"synthesis", "research_question"}
        for r in index.technical_attachment_rows(reference)
    )
    assert "technical_subject_refs" not in ResearchQuestion.model_fields
    for model in views.identity_page_models(atlas, reference):
        if model.subject.type == "Function":
            assert not (
                model.direct_attachments
                or model.related_attachments
                or model.descendant_attachments
            )
    outputs = tree(atlas, reference, authored)
    legacy = (
        outputs[views.OBSERVE_SCOPE_RELATIVE_PATH].decode()
        if views.OBSERVE_SCOPE_RELATIVE_PATH in outputs
        else outputs[views.OBSERVE_SCOPE_MARKDOWN].decode()
    )
    assert "WPAPER-FIXTURE" not in legacy
    opaque = props(
        "paper",
        wiki_id="WPAPER-SIMILAR",
        title="Memory to Cortex",
        atlas_refs=list(ROLLOUT_TARGETS.values()),
        wiki_refs=["WFIND-FIXTURE"],
        related_version_refs=["WPAPER-FIXTURE"],
    )
    extended = build(atlas, authored + [opaque])
    assert not any(
        r.source_wiki_id == "WPAPER-SIMILAR" for r in index.technical_attachment_rows(extended)
    )
    assert not any(
        r.navigation_start.identifier == "WPAPER-SIMILAR"
        for r in index.technical_navigation_rows(extended)
    )


def test_large_synthetic_hierarchy_is_bounded_deterministic_and_terminal(atlas):
    from fh_agent.research_atlas.schema import Relationship

    hierarchy, trails = synthetic_hierarchy(atlas, width=24, depth=6)
    hierarchy = replace(
        hierarchy,
        relationships=(
            *hierarchy.relationships,
            *(
                edge
                for trail in trails
                for edge in (
                    Relationship(source=trail[1], relation="supplies", target=TARGET),
                    Relationship(
                        source=trail[1], relation="controls", target="DAT-RETRIEVAL-SNAPSHOT"
                    ),
                )
            ),
        ),
    )
    authored = [
        props(
            "paper", wiki_id=f"WPAPER-SYNTHETIC-{number}", research_direct_subject_refs=[trail[-1]]
        )
        for number, trail in enumerate(trails)
    ]
    authored += [
        props("paper", wiki_id="WPAPER-LARGE-INTERFACE", research_adjacent_context_refs=[TARGET]),
        props(
            "paper",
            wiki_id="WPAPER-LARGE-DATA",
            research_direct_subject_refs=["DAT-RETRIEVAL-SNAPSHOT"],
        ),
    ]
    reference = build(hierarchy, authored)
    root = views.identity_page_model(hierarchy, reference, "SYS-AGA")
    assert len(root.descendant_attachments) == 24
    assert {item.part_of_path for item in root.descendant_attachments} == set(trails)
    assert root.direct_attachments == root.related_attachments == ()
    assert len(index.technical_attachment_rows(reference)) == 26
    assert all(
        r.via[-1].edge_id == "E9" and len(r.via) == 1 for r in reference.rows if r.originating_role
    )
    assert len(reference.rows) == 78  # 26 E9, 26 finite K0 paths, 26 source audits.
    reversed_atlas = replace(
        hierarchy,
        entities=dict(reversed(tuple(hierarchy.entities.items()))),
        relationships=tuple(reversed(hierarchy.relationships)),
    )
    assert build(reversed_atlas, list(reversed(authored))) == reference
    reversed_model = views.identity_page_model(reversed_atlas, reference, "SYS-AGA")
    assert reversed_model == root
    assert views.render_identity_page(
        COMMIT, reversed_atlas, reversed_model
    ) == views.render_identity_page(COMMIT, hierarchy, root)
    for branch, trail in enumerate(trails):
        model = views.identity_page_model(hierarchy, reference, trail[1])
        assert len(model.descendant_attachments) == 1
        assert (
            model.descendant_attachments[0].attachment.source_wiki_id
            == f"WPAPER-SYNTHETIC-{branch}"
        )
        assert len(model.related_attachments) == 1
        assert model.related_attachments[0].attachment.target_identifier == TARGET
        assert model.related_attachments[0].relation.relation == "supplies"
        assert (
            model.related_attachments[0].attachment.originating_role
            == "research_adjacent_context_refs"
        )


def test_rollout_order_and_fingerprint_inputs_remain_literal(atlas, rollout):
    reference, outputs = rollout
    authored = rollout_records()
    reversed_atlas = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    for record in authored:
        for role in index.ROLES:
            record[role] = list(reversed(record[role]))
    assert build(reversed_atlas, list(reversed(authored))) == reference
    assert tree(reversed_atlas, reference, list(reversed(rollout_records()))) == outputs
    changed = copy.deepcopy(authored)
    changed[0]["research_direct_subject_refs"] = ["SYS-AGA"]
    assert build(atlas, changed).private_input_fingerprint != reference.private_input_fingerprint
    changed = copy.deepcopy(authored)
    changed[0]["title"] = "Different synthetic title"
    assert build(atlas, changed) == reference
    # Actual type changes generated rows independently of the unchanged authored fingerprint.
    entities = dict(atlas.entities)
    entities["DAT-RETRIEVAL-SNAPSHOT"] = entities["DOM-EVIDENCE-MEMORY"]
    wrong = build(replace(atlas, entities=entities), authored)
    assert wrong.private_input_fingerprint == reference.private_input_fingerprint
    assert wrong.rows != reference.rows


@pytest.mark.parametrize(
    "fixture,expected_rows_digest,expected_fingerprint",
    [
        (
            "pilot",
            "0bd0f5bf615f4a4c93f7e51c752b08cda40a9989482572cc3686c84254ff61fc",
            "b7c863dfd703141b6577f2cbe91e0f5bc86568bdcf2f4ceca406198502666e9a",
        ),
        (
            "nc_nq_np",
            "20d8d216186bb5068e1c5100490d3c4fe5aa82c201823a5f17c6ecbf8cf5c44b",
            "38314020024e8c3baeb317c9a89cdba9ee154d22e64e0a38cadfd204e4c8b314",
        ),
    ],
)
def test_exact_base_pilot_and_original_navigation_rows_are_unchanged(
    atlas, fixture, expected_rows_digest, expected_fingerprint
):
    from test_research_wiki_reference_index import sample_records

    # Frozen by executing identical inputs on main@9dd79727 in an isolated source archive.
    reference = build(atlas, records() if fixture == "pilot" else sample_records())
    assert (
        index.digest(index.canonical([r.model_dump(mode="json") for r in reference.rows]))
        == expected_rows_digest
    )
    assert reference.private_input_fingerprint == expected_fingerprint


def test_three_bands_on_one_component_keep_distinct_exact_owners_targets(atlas):
    from fh_agent.research_atlas.schema import Relationship

    hierarchy, (trail,) = synthetic_hierarchy(atlas)
    parent = trail[1]
    hierarchy = replace(
        hierarchy,
        relationships=(
            *hierarchy.relationships,
            Relationship(source=parent, relation="supplies", target=TARGET),
        ),
    )
    authored = [
        props("paper", research_direct_subject_refs=[parent]),
        props("finding", research_method_or_baseline_refs=[trail[-1]]),
        props("reading_note", research_adjacent_context_refs=[TARGET]),
    ]
    reference = build(hierarchy, authored)
    model = views.identity_page_model(hierarchy, reference, parent)
    assert (
        len(model.direct_attachments)
        == len(model.descendant_attachments)
        == len(model.related_attachments)
        == 1
    )
    assert model.direct_attachments[0].source_wiki_id == "WPAPER-FIXTURE"
    assert model.descendant_attachments[0].attachment.source_wiki_id == "WFIND-FIXTURE"
    assert model.descendant_attachments[0].part_of_path == trail[1:]
    assert model.related_attachments[0].attachment.source_wiki_id == "READ-FIXTURE"
    page = views.render_identity_page(COMMIT, hierarchy, model).decode()
    direct, below = page.split("### Directly attached Research", 1)[1].split(
        "### Research attached below this scope", 1
    )
    below, related = below.split("### Related technical-scope Research", 1)
    for band, owner, target, role in (
        (direct, "WPAPER-FIXTURE", parent, "research_direct_subject_refs"),
        (below, "WFIND-FIXTURE", trail[-1], "research_method_or_baseline_refs"),
        (related, "READ-FIXTURE", TARGET, "research_adjacent_context_refs"),
    ):
        assert f"Exact authored role: `{role}`" in band
        assert f"· `{target}` · type" in band
        assert f"`{owner}` · type" in band
    assert "does not inherit" in below and "does not inherit" in related
    assert model.direct_attachments[0].target_identifier == parent


def test_part_of_discovery_preserves_multiple_paths_and_rejects_cycles(atlas):
    from fh_agent.research_atlas.schema import Relationship

    hierarchy, (trail,) = synthetic_hierarchy(atlas)
    hierarchy = replace(
        hierarchy,
        relationships=(
            *hierarchy.relationships,
            Relationship(source=trail[-1], relation="part_of", target=trail[1]),
        ),
    )
    paths = views.component_descendant_paths(hierarchy, "SYS-AGA")
    assert trail in paths and ("SYS-AGA", trail[1], trail[-1]) in paths
    cyclic = replace(
        hierarchy,
        relationships=(
            *hierarchy.relationships,
            Relationship(source=trail[1], relation="part_of", target=trail[-1]),
        ),
    )
    with pytest.raises(views.ProjectionError, match="Cyclic technical part_of"):
        views.component_descendant_paths(cyclic, "SYS-AGA")


def test_progressive_disclosure_three_records_fifteen_exact_role_audits(atlas):
    reference = build(atlas)
    model = views.identity_page_model(atlas, reference, TARGET)
    paths = views.identity_page_paths(atlas)
    locators = {
        r["wiki_id"]: PurePosixPath("synthetic") / (r["wiki_id"] + ".md") for r in records()
    }
    rendered = views._render_attachment_rows(
        atlas, model, model.direct_attachments, locators, paths
    )
    page = "\n".join(rendered)
    summary = page.split("> [!info]-", 1)[0]
    assert len([line for line in summary.splitlines() if line.startswith("- ")]) == 3
    assert "Declaring private record / exact role owner:" not in summary
    assert page.count("> [!info]- Audit / provenance") == 3
    assert page.count("> - Declaring private record / exact role owner:") == 15
    assert page.count(">   - Direct attachment audit row:") == 15
    for owner in ("WPAPER-FIXTURE", "READ-FIXTURE", "WFIND-FIXTURE"):
        assert summary.count(f"`{owner}`") == 1
    role_lines = [line for line in summary.splitlines() if "Authored Research roles:" in line]
    assert len(role_lines) == 3
    assert all(all(f"`{role}`" in line for role in index.ROLES) for line in role_lines)
    assert summary.count(f"`{TARGET}`") == 3 and "type `Interface`" in summary
    assert "revision `v1`" in summary
    # Removing only native quote prefixes recovers every original audit block verbatim.
    unquoted = "\n".join(line[2:] if line.startswith("> ") else "" for line in rendered)
    for row in model.direct_attachments:
        audit = views._render_attachment_audit(atlas, model, (row,), locators, paths)
        assert "\n".join(audit).strip() in unquoted
        assert row.row_id in page and row.originating_role in page
    for path in model.technical_paths:
        assert path.recipe in page and path.row_id in page
    assert "E9:forward" in page and "N-T/K0/" in page and "N-T/K3/" in page
    assert "Prerequisite (not traversed)" in page and "property `" in page
    assert "synthetic/" in page and str(paths[TARGET].with_suffix("")) in page
    # No CSS, optional plugin, JavaScript or custom HTML carries any attachment content.
    assert not any(token in page for token in ("<details", "<script", "<div", "style=", "```"))
    reordered = replace(model, technical_paths=tuple(reversed(model.technical_paths)))
    assert (
        views._render_attachment_rows(
            atlas, reordered, tuple(reversed(model.direct_attachments)), locators, paths
        )
        == rendered
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"source_wiki_id": "WPAPER-OTHER"},
        {"source_record_version": 2},
        {"source_doc_type": "reading_note"},
        {"target_identifier": "SYS-AGA", "resolved_target_type": "System"},
        {"resolved_target_type": "Contract"},
    ],
)
def test_summary_grouping_never_merges_exact_id_revision_target_or_type(atlas, changes):
    reference = build(atlas)
    model = views.identity_page_model(atlas, reference, TARGET)
    row = next(row for row in model.direct_attachments if row.source_doc_type == "paper")
    distinct = row.model_copy(update=changes)
    rendered = "\n".join(
        views._render_attachment_rows(
            atlas, model, (row, distinct), {}, views.identity_page_paths(atlas)
        )
    )
    summary = rendered.split("> [!info]-", 1)[0]
    assert len([line for line in summary.splitlines() if line.startswith("- ")]) == 2
    assert rendered.count("> [!info]-") == 2
    assert rendered.count("Direct attachment audit row:") == 2
    for value in changes.values():
        assert str(value) in summary


def test_descendant_paths_and_related_relations_once_per_exact_group(atlas, rollout):
    from fh_agent.research_atlas.schema import Relationship

    reference, outputs = rollout
    paths = views.identity_page_paths(atlas)
    system = outputs[paths["SYS-AGA"]].decode()
    below = system.split("### Research attached below this scope", 1)[1].split(
        "## Gap Analysis", 1
    )[0]
    assert below.count("Exact part_of technical path") == 1
    assert below.count("#### Observation Builder") == 1
    assert "`SYS-AGA` → `CMP-PERCEPTION` → `CMP-OBSERVATION-BUILDER`" in below
    assert below.count("Authored Research roles:") == 3
    assert below.count("Direct attachment audit row:") == 15
    assert "this page does not inherit the descendant's role or attachment" in below
    assert "N-C/K0/E9:forward" in below
    # Distinct paths to the same target must both remain in the human view.
    extra_path = replace(
        atlas,
        relationships=(
            *atlas.relationships,
            Relationship(source="CMP-OBSERVATION-BUILDER", relation="part_of", target="SYS-AGA"),
        ),
    )
    model = views.identity_page_model(extra_path, reference, "SYS-AGA")
    rendered = "\n".join(views._render_technical_research(extra_path, model, {}, paths))
    assert rendered.count("Exact part_of technical path") == 2
    assert rendered.count("Direct attachment audit row:") == 45  # 15 direct + 2 × 15 below.
    # Distinct independent relations to one target each retain their own records/audits.
    extra_relation = replace(
        atlas,
        relationships=(
            *atlas.relationships,
            Relationship(source="CMP-MEM-RETRIEVAL", relation="consumes", target=TARGET),
        ),
    )
    related_reference = build(extra_relation)
    model = views.identity_page_model(extra_relation, related_reference, "CMP-MEM-RETRIEVAL")
    rendered = "\n".join(views._render_technical_research(extra_relation, model, {}, paths))
    assert rendered.count("Independent technical relation:") == 2
    assert rendered.count("#### Memory to Cortex") == 2
    assert rendered.count("Authored Research roles:") == 6
    assert rendered.count("Direct attachment audit row:") == 30
    assert "does not inherit the role or attachment" in rendered
    reordered = replace(
        model,
        related_attachments=tuple(reversed(model.related_attachments)),
        technical_paths=tuple(reversed(model.technical_paths)),
    )
    assert (
        "\n".join(views._render_technical_research(extra_relation, reordered, {}, paths))
        == rendered
    )
    reordered = replace(model, related_attachments=())
    assert "No matching Research through an accepted one-hop technical relation" in "\n".join(
        views._render_technical_research(extra_relation, reordered, {}, paths)
    )
    descendant_model = views.identity_page_model(extra_path, reference, "SYS-AGA")
    assert views._render_technical_research(
        extra_path, descendant_model, {}, paths
    ) == views._render_technical_research(
        extra_path,
        replace(
            descendant_model,
            descendant_attachments=tuple(reversed(descendant_model.descendant_attachments)),
            technical_paths=tuple(reversed(descendant_model.technical_paths)),
        ),
        {},
        paths,
    )


def test_sparse_attachment_native_card_and_truthful_empty_state(atlas):
    paths = views.identity_page_paths(atlas)
    reference = build(atlas, [props("paper", research_direct_subject_refs=[TARGET])])
    model = views.identity_page_model(atlas, reference, TARGET)
    rendered = "\n".join(views._render_technical_research(atlas, model, {}, paths))
    assert rendered.count("Authored Research roles:") == 1
    assert rendered.count("> [!info]- Audit / provenance") == 1
    assert "| ---" not in rendered
    assert "Exact technical target:" in rendered and TARGET in rendered
    empty = views.identity_page_model(atlas, build(atlas, []), TARGET)
    rendered = "\n".join(views._render_technical_research(atlas, empty, {}, paths))
    assert "No matching exact direct Research attachments in this snapshot." in rendered
    assert "Authored Research roles:" not in rendered and "[!info]" not in rendered


# #122 G3 / human reader: entirely fictional, opt-in, never real literature.
def reader_records():
    target = "CMP-PERCEPTION"
    result = []
    for suffix, title, subject, origin in (
        ("A", "Synthetic — Hierarchical Visual State Representations", target, "authors_result"),
        (
            "B",
            "Synthetic — Evidence-linked Observation Assembly",
            "CMP-OBSERVATION-BUILDER",
            "authors_result",
        ),
        ("C", "Synthetic — Limits of Sparse Visual Signals", target, "our_inference"),
    ):
        paper_id, finding_id, reading_id = (
            p + "-READER-" + suffix for p in ("WPAPER", "WFIND", "READ")
        )
        contexts = [
            dict(
                role=index.ROLES[0],
                target_ref=subject,
                why_relevant="Fictional example: relevant to visible observation assembly.",
                finding_ref=finding_id,
                reading_note_ref=reading_id,
            )
        ]
        targets = [subject]
        if suffix == "A":
            # One Paper, two separately authored contexts, including original W09 proof target.
            targets.append("CMP-MEM-RETRIEVAL")
            contexts.append(
                dict(
                    role=index.ROLES[0],
                    target_ref=targets[-1],
                    why_relevant="Fictional example: inspect evidence retrieval separately.",
                    finding_ref=finding_id,
                    reading_note_ref=reading_id,
                )
            )
        result += [
            props(
                "paper",
                wiki_id=paper_id,
                title=title,
                epistemic_schema_version="0.2",
                document_maturity="domain_accepted",
                authors=["Fictional Doe et al."],
                publication_year=2025,
                research_direct_subject_refs=targets,
                presentation_contexts=contexts,
                source_refs=["fictional-source-" + suffix],
                url="https://example.invalid/fictional-" + suffix,
            ),
            props(
                "reading_note",
                wiki_id=reading_id,
                title="Synthetic reading record " + suffix,
                paper_refs=[paper_id],
                version_read="Fictional version 1",
                read_date="2026-09-01",
                reading_depth="methods_checked",
                checked_sections=["methods"],
                document_maturity="draft",
            ),
            props(
                "finding",
                wiki_id=finding_id,
                title="Synthetic attributed finding " + suffix,
                epistemic_schema_version="0.2",
                document_maturity="domain_accepted",
                review_state="domain_accepted",
                claim_origin=origin,
                source_refs=[paper_id],
                reading_note_refs=[reading_id],
                presentation_statement=(
                    "Fictional example: evidence-linked signals can be assembled."
                ),
                presentation_limitation=(
                    "Fictional limitation: no real experiment or literature result."
                ),
            ),
        ]
    result += [
        props(
            "synthesis",
            wiki_id="SYN-READER",
            title="Synthetic independent synthesis",
            epistemic_schema_version="0.2",
            document_maturity="domain_accepted",
            finding_refs=["WFIND-READER-A"],
            presentation_summary=(
                "Fictional independently authored synthesis; no consensus inferred."
            ),
            presentation_limitation="Synthetic only; no accepted project claim.",
        )
    ]
    return result


def reader_tree(atlas, authored=None):
    authored = reader_records() if authored is None else authored
    locators = {r["wiki_id"]: PurePosixPath("authored") / (r["title"] + ".md") for r in authored}
    return tree(atlas, build(atlas, authored), authored, locators)


def test_human_reader_order_titles_role_labels_and_complete_audit(atlas):
    from fh_agent.research_atlas.research_presentation import ROLE_LABELS
    from fh_agent.research_atlas.technical_reader import PROTOTYPES

    authored = reader_records()
    outputs = reader_tree(atlas, authored)
    path = views.identity_page_paths(atlas)["CMP-PERCEPTION"]
    page = outputs[path]
    normal = views.reader_export(page).decode()
    headings = [
        "What this is",
        "Responsibility / why it exists",
        "How it works",
        "Inputs / outputs / important connections",
        "Subcomponents / go deeper",
        "Current implementation state",
        "Important limitations",
        "Research Questions",
        "Relevant Research / Literature",
        "Gap-assessment status",
        "Sources & verification",
    ]
    positions = [
        normal.index("### " + h if h != "Sources & verification" else "## " + h) for h in headings
    ]
    assert positions == sorted(positions)
    assert page.decode().index("# Perception") < page.decode().index("CMP-PERCEPTION")
    assert "Engineering provenance" not in normal
    assert "EVID-" not in normal and "WPAPER-" not in normal and "WFIND-" not in normal
    assert all(role not in normal for role in index.ROLES)
    assert ROLE_LABELS[index.ROLES[0]] in normal
    assert "Synthetic — Hierarchical Visual State Representations" in normal
    for value in (
        PROTOTYPES["CMP-PERCEPTION"].implementation,
        PROTOTYPES["CMP-PERCEPTION"].limitations,
    ):
        assert normal.count(value) == 1
    assert "one durable identity" not in normal
    assert "No explicit Research Question is currently attached to this subject." in normal
    assert "Fictional Doe et al. (2025)" in normal
    audit = page.decode().split("> [!aga-audit]- Full audit", 1)[1]
    for value in ("CMP-PERCEPTION", "EVID-48-BUILDER", "E9:forward", "N-C/K0", COMMIT):
        assert value in audit
    for row in index.technical_attachment_rows(build(atlas, authored)):
        if row.target_identifier != "CMP-PERCEPTION":
            continue
        assert row.row_id in audit and row.originating_role in audit
    assert len(normal) < len(page) and "```yaml" not in normal
    assert reader_tree(atlas, list(reversed(authored))) == outputs


def test_parent_reader_routes_down_without_descendant_paper_or_audit_wall(atlas):
    outputs = reader_tree(atlas)
    paths = views.identity_page_paths(atlas)
    normal = views.reader_export(outputs[paths["CMP-PERCEPTION"]]).decode()
    assert "Research available — open component" in normal
    assert str(paths["CMP-OBSERVATION-BUILDER"].with_suffix("")) + "|Open component]]" in normal
    assert "Synthetic — Evidence-linked Observation Assembly" not in normal
    assert "Fictional example: relevant" in normal  # only own direct context
    system = views.reader_export(outputs[paths["SYS-AGA"]]).decode()
    assert "Hierarchical Visual State Representations" not in system
    assert "Authored Research roles" not in system and "Direct attachment audit row" not in system
    assert "Research in subcomponents" in system and "Observation Builder" in system
    assert "No explicit Research Question is currently attached to this subject." in system
    # RQ not inferred from a private role, body, Domain, Function or scientific proximity.
    authored = reader_records() + [
        props(
            "research_question",
            title="Synthetic unbound question",
            research_direct_subject_refs=["CMP-PERCEPTION"],
        )
    ]
    question_page = views.reader_export(
        reader_tree(atlas, authored)[paths["CMP-PERCEPTION"]]
    ).decode()
    assert "Synthetic unbound question" not in question_page
    assert "No explicit Research Question is currently attached to this subject." in question_page


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "absent",
        "wrong-paper",
        "draft-review",
        "checked-review",
        "archived",
        "draft-owner",
    ],
)
def test_g3_explicit_selection_and_restrictive_eligibility(atlas, mutation):
    authored = reader_records()[:3]
    context = authored[0]["presentation_contexts"][0]
    if mutation == "missing":
        context["finding_ref"] = "WFIND-MISSING"
    elif mutation == "absent":
        context["finding_ref"] = None
    elif mutation == "wrong-paper":
        authored[2]["source_refs"] = ["WPAPER-OTHER"]
    elif mutation in {"draft-review", "checked-review"}:
        authored[2]["review_state"] = mutation.split("-")[0]
    elif mutation == "archived":
        authored[2]["document_maturity"] = "archived"
    elif mutation == "draft-owner":
        authored[0]["document_maturity"] = "draft"
    normal = views.reader_export(
        reader_tree(atlas, authored)[views.identity_page_paths(atlas)["CMP-PERCEPTION"]]
    ).decode()
    assert authored[2]["presentation_statement"] not in normal
    assert authored[2]["presentation_limitation"] not in normal
    if mutation == "absent":
        assert "No Finding explicitly selected" in normal
    elif mutation != "draft-owner":
        assert "no replacement selected" in normal


def test_g3_in_review_attribution_read_provenance_and_independent_synthesis(atlas):
    authored = reader_records()
    authored[2]["document_maturity"] = "in_review"
    authored[2]["review_state"] = "checked"
    outputs = reader_tree(atlas, authored)
    page = views.reader_export(outputs[views.identity_page_paths(atlas)["CMP-PERCEPTION"]]).decode()
    for label in (
        "Source-reported finding (in review)",
        "Author-reported limitation / applicability",
        "Project inference",
        "Project-authored limitation / applicability",
        "document draft",
        "Version read",
        "Fictional version 1",
        "Read date",
        "2026-09-01",
        "Checked sections",
    ):
        assert label in page
    assert "Fictional independently authored synthesis" not in page
    assert (
        "Fictional independently authored synthesis" in outputs[views.RESEARCH_LANDSCAPE].decode()
    )
    missing = [r for r in authored if r["wiki_id"] != "WFIND-READER-A"]
    assert (
        "Fictional independently authored synthesis"
        not in reader_tree(atlas, missing)[views.RESEARCH_LANDSCAPE].decode()
    )


def test_g3_context_is_terminal_owner_role_target_exact_and_v02_opt_in(atlas):
    for changes in ({"target_ref": "CMP-CORTEX"}, {"role": index.ROLES[1]}):
        authored = reader_records()
        authored[0]["presentation_contexts"][0].update(changes)
        with pytest.raises(views.ProjectionError, match="Invalid private identity"):
            build(atlas, authored)
    authored = reader_records()
    authored[0]["epistemic_schema_version"] = "0.1"
    with pytest.raises(views.ProjectionError, match="Invalid private identity"):
        build(atlas, authored)
    authored = reader_records()[:3]
    # Paper declares only its other context; ReadingNote declares Perception but has no context.
    authored[0]["research_direct_subject_refs"] = ["CMP-MEM-RETRIEVAL"]
    authored[0]["presentation_contexts"] = authored[0]["presentation_contexts"][1:]
    authored[1]["research_direct_subject_refs"] = ["CMP-PERCEPTION"]
    authored[1]["document_maturity"] = "domain_accepted"
    normal = views.reader_export(
        reader_tree(atlas, authored)[views.identity_page_paths(atlas)["CMP-PERCEPTION"]]
    ).decode()
    assert "Fictional example: inspect evidence retrieval separately." not in normal
    assert "No authored relevance context or selected Finding" in normal


@pytest.mark.parametrize(
    "owner,field,value",
    [
        (0, "title", "Synthetic changed title"),
        (0, "authors", ["Fictional Smith"]),
        (0, "publication_year", 2024),
        (0, "url", "https://example.invalid/changed"),
        (0, "doi", "fictional-doi"),
        (0, "source_refs", ["fictional-changed"]),
        (0, "document_maturity", "archived"),
        (0, "record_version", 2),
        (1, "reading_depth", "relevant_fulltext_checked"),
        (1, "checked_sections", ["methods", "limitations"]),
        (1, "version_read", "Fictional version 2"),
        (1, "read_date", "2026-09-02"),
        (1, "document_maturity", "in_review"),
        (2, "presentation_statement", "Fictional edited statement."),
        (2, "presentation_limitation", "Fictional edited limitation."),
        (2, "claim_origin", "our_inference"),
        (2, "review_state", "checked"),
        (9, "presentation_summary", "Fictional edited synthesis."),
        (9, "presentation_limitation", "Fictional edited synthesis limitation."),
        (9, "finding_refs", ["WFIND-READER-C"]),
    ],
)
def test_g3_consumed_structured_field_changes_separate_presentation_fingerprint(
    atlas, owner, field, value
):
    from fh_agent.research_atlas.research_presentation import presentation_fingerprint

    before = reader_records()
    after = copy.deepcopy(before)
    after[owner][field] = value

    def validated(authored):
        return validate_wiki_records(authored, atlas.entities.keys())

    assert presentation_fingerprint(validated(before)) != presentation_fingerprint(validated(after))
    if field not in index.PROPERTIES and field != "record_version":
        assert (
            build(atlas, before).private_input_fingerprint
            == build(atlas, after).private_input_fingerprint
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("why_relevant", "Fictional edited context."),
        ("finding_ref", "WFIND-READER-C"),
        ("reading_note_ref", None),
    ],
)
def test_g3_context_fields_and_body_independence(atlas, field, value):
    from fh_agent.research_atlas.research_presentation import presentation_fingerprint

    authored = reader_records()
    changed = copy.deepcopy(authored)
    changed[0]["presentation_contexts"][0][field] = value

    def validated(data):
        return validate_wiki_records(data, atlas.entities.keys())

    assert presentation_fingerprint(validated(changed)) != presentation_fingerprint(
        validated(authored)
    )
    assert (
        build(atlas, changed).private_input_fingerprint
        == build(atlas, authored).private_input_fingerprint
    )
    changed = copy.deepcopy(authored)
    for r in changed:
        r["aliases"] = ["Unconsumed synthetic alias"]
        r["tags"] = ["Unconsumed synthetic annotation"]
    assert presentation_fingerprint(validated(changed)) == presentation_fingerprint(
        validated(authored)
    )
    assert reader_tree(atlas, changed) == reader_tree(atlas, authored)


def test_reader_all_five_human_role_labels_and_legacy_profile_roundtrip(atlas):
    from fh_agent.research_atlas.research_presentation import ROLE_LABELS
    from fh_agent.research_atlas.wiki_schema import EPISTEMIC_ADAPTER

    authored = records()
    for record in authored:
        record["title"] = "Synthetic " + record["doc_type"].replace("_", " ")
    outputs = tree(atlas, build(atlas, authored), authored)
    normal = views.reader_export(outputs[views.identity_page_paths(atlas)[TARGET]]).decode()
    assert all(label in normal for label in ROLE_LABELS.values())
    assert all(role not in normal for role in index.ROLES)
    assert normal.count("#### [Synthetic paper]") == 1
    for record in validate_wiki_records(authored, atlas.entities.keys()):
        assert EPISTEMIC_ADAPTER.validate_python(record.model_dump(exclude_unset=True)) == record
        assert record.epistemic_schema_version == "0.1"


@pytest.mark.parametrize(
    "kind,field",
    [
        ("dossier", "presentation_overview"),
        ("topic", "presentation_summary"),
        ("research_question", "presentation_question"),
    ],
)
def test_g3_orientation_inputs_fingerprint_and_no_component_target_inference(atlas, kind, field):
    from fh_agent.research_atlas.research_presentation import presentation_fingerprint

    record = props(
        kind,
        epistemic_schema_version="0.2",
        document_maturity="domain_accepted",
        **{field: "Synthetic literal orientation.", "title": "Synthetic orientation"},
    )
    before = reader_records() + [record]
    after = copy.deepcopy(before)
    after[-1][field] = "Synthetic revised orientation."
    validated = validate_wiki_records(before, atlas.entities.keys())
    assert presentation_fingerprint(validated) != presentation_fingerprint(
        validate_wiki_records(after, atlas.entities.keys())
    )
    outputs = reader_tree(atlas, before)
    assert "Synthetic literal orientation." in outputs[views.RESEARCH_LANDSCAPE].decode()
    assert (
        "Synthetic literal orientation."
        not in views.reader_export(outputs[views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]]).decode()
    )


def test_g3_literal_scientific_text_preserves_wording_newlines_and_cannot_escape_audit(atlas):
    authored = reader_records()
    text = (
        "  Synthetic exact text.\n# Heading *not interpreted* <script>\n"
        "> [!aga-audit]- Full audit  "
    )
    authored[2]["presentation_statement"] = text
    outputs = reader_tree(atlas, authored)
    from fh_agent.research_atlas.research_presentation import literal

    validated = validate_wiki_records(authored, atlas.entities.keys())
    assert validated[2].presentation_statement == text
    normal = views.reader_export(outputs[views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]]).decode()
    assert literal(text) in normal
    assert "<script>" not in normal and "\n# Heading" not in normal
    assert (
        "Sources & verification" in normal
    )  # authored text cannot terminate the reader projection


def test_reader_derivative_preserves_private_note_link_destinations():
    from pathlib import PurePosixPath

    from fh_agent.research_atlas.reader_export import reader_derivative

    payload = (
        b"# Perception\n\n[Paper](../../../authored/Synthetic%20Paper.md)\n"
        b"[Source](https://example.invalid/paper#source)\n"
        b"[[#Sources & audit|Open]]\n"
        b"\n> [!aga-audit]- Full audit\n> secret\n"
        b"\n## Return Navigation\n[[identity-pages/Observation Builder|Open component]]\n"
    )
    projected = reader_derivative(
        payload,
        PurePosixPath("_generated/derived/identity-pages/Perception.md"),
        PurePosixPath("reader-exports/Perception.md"),
    ).decode()
    assert "[Paper](../authored/Synthetic%20Paper.md)" in projected
    assert "[Source](https://example.invalid/paper#source)" in projected
    assert "[[identity-pages/Observation Builder|Open component]]" in projected
    assert "[[_generated/derived/identity-pages/Perception#Sources & audit|Open]]" in projected
    assert "secret" not in projected
