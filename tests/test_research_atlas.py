import ast
import copy
import itertools
import shutil
import sys
from pathlib import Path
from typing import get_args

import pytest
import yaml

from fh_agent.research_atlas.render import render_overview
from fh_agent.research_atlas.schema import PREFIXES, RelationName, Relationship
from fh_agent.research_atlas.validator import (
    RELATION_PAIRS,
    AtlasSourceSchema,
    load_registry,
    validate_registry,
    validated_source_schema_version,
)

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
PACKAGE = ROOT / "src/fh_agent/research_atlas"
EXPECTED_FUNCTION_PARTICIPANTS = {
    "FUNC-ACQUIRE": {
        "ENV-GAME-INSTANCE",
        "CMP-SCREEN-CAPTURE",
        "CMP-VISIBLE-STATE-BRIDGE",
    },
    "FUNC-OBSERVE": {
        "CMP-NO-SPOILER-FIREWALL",
        "CMP-PERCEPTION",
        "DAT-OBSERVATION",
        "CMP-TEMPORAL-STATE",
    },
    "FUNC-RETAIN-RETRIEVE": {
        "CMP-EVIDENCE-LEDGER",
        "CMP-MEMORY",
        "CMP-MEM-RETRIEVAL",
    },
    "FUNC-REASON": {"CMP-CORTEX"},
    "FUNC-EXECUTIVE-CONTROL": {
        "CMP-MANAGER",
        "CMP-MANAGER-GROUNDING",
        "CMP-MANAGER-SCHED-COMP",
        "CON-SKILL-CONTRACT",
    },
    "FUNC-ACT": {
        "CMP-BODY",
        "CMP-BOUNDED-REFLEX",
        "CMP-SAFETY-FILTER",
        "CMP-INPUT-EXECUTOR",
    },
    "FUNC-VERIFY": {
        "DAT-VISIBLE-OUTCOME",
        "CMP-INDEPENDENT-VERIFIER",
        "CON-VERIFIER-RESULT",
    },
    "FUNC-BETWEEN-RUNS": {
        "CMP-REPLAY-BUFFER",
        "CMP-SKILL-TRAINER",
        "DAT-CANDIDATE-BODY-VERSION",
        "CMP-BODY-CERTIFICATION",
    },
}
EXPECTED_COMPONENT_PARENTS = {
    "CMP-BODY": "SYS-AGA",
    "CMP-BODY-CERTIFICATION": "SYS-AGA",
    "CMP-BOUNDED-REFLEX": "CMP-BODY",
    "CMP-CORTEX": "SYS-AGA",
    "CMP-EVIDENCE-LEDGER": "SYS-AGA",
    "CMP-INDEPENDENT-VERIFIER": "SYS-AGA",
    "CMP-INPUT-EXECUTOR": "SYS-AGA",
    "CMP-MANAGER": "SYS-AGA",
    "CMP-MANAGER-GROUNDING": "CMP-MANAGER",
    "CMP-MANAGER-SCHED-COMP": "CMP-MANAGER",
    "CMP-MEM-EPISODIC": "CMP-MEMORY",
    "CMP-MEM-FACTS": "CMP-MEMORY",
    "CMP-MEM-HYPOTHESES": "CMP-MEMORY",
    "CMP-MEM-RETRIEVAL": "SYS-AGA",
    "CMP-MEM-STRATEGY": "CMP-MEMORY",
    "CMP-MEM-TOPOLOGY": "CMP-MEMORY",
    "CMP-MEMORY": "SYS-AGA",
    "CMP-NO-SPOILER-FIREWALL": "SYS-AGA",
    "CMP-OBSERVATION-BUILDER": "CMP-PERCEPTION",
    "CMP-PERCEPTION": "SYS-AGA",
    "CMP-PERCEPTION-UI-STATE": "CMP-PERCEPTION",
    "CMP-REPLAY-BUFFER": "SYS-AGA",
    "CMP-SAFETY-FILTER": "SYS-AGA",
    "CMP-SCREEN-CAPTURE": "SYS-AGA",
    "CMP-SKILL-COMPETENCE": "CMP-MEMORY",
    "CMP-SKILL-TRAINER": "SYS-AGA",
    "CMP-TEMPORAL-STATE": "SYS-AGA",
    "CMP-VISIBLE-STATE-BRIDGE": "SYS-AGA",
}


@pytest.fixture(scope="module")
def registry_templates():
    return [
        yaml.safe_load((ATLAS / "registry" / name).read_text())
        for name in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
    ]


@pytest.fixture
def payloads(registry_templates):
    return copy.deepcopy(registry_templates)


def edge(payloads, relation, source="CMP-CORTEX", target="CMP-MANAGER", **kwargs):
    payloads[1]["relationships"].append(
        dict(relation=relation, source=source, target=target, **kwargs)
    )


def minimal_registry(payloads, node_ids, relationships=()):
    templates = {node["id"]: node for node in payloads[0]["nodes"]}
    nodes = []
    for node_id in node_ids:
        node = copy.deepcopy(templates[node_id])
        node.update(atlas_level=None, overview_visibility=None, overview_order=None)
        nodes.append(node)
    return [
        {"atlas_schema_version": "0.3", "nodes": nodes},
        {"atlas_schema_version": "0.3", "relationships": list(relationships)},
        {"atlas_schema_version": "0.3", "evidence": []},
    ]


def test_valid_pilot_registry_loads():
    atlas = load_registry(ATLAS)
    assert atlas.source_atlas_schema == "0.3"
    expected = {
        "CMP-MEM-RETRIEVAL": ("partial", "unverified"),
        "CMP-CORTEX": ("implemented", "integration-tested"),
        "CMP-MANAGER": ("implemented", "integration-tested"),
    }
    for node_id, (implementation, verification) in expected.items():
        node = atlas.entities[node_id]
        assert node.technical.architecture_authority == "canonical-target"
        assert node.technical.implementation_status == implementation
        assert node.technical.verification_status == verification
    assert atlas.entities["DAT-RETRIEVAL-SNAPSHOT"].technical.implementation_status == "target-only"
    assert atlas.entities["CON-SKILL-CONTRACT"].type == "Contract"
    assert not any(n.type in {"Paper", "Finding"} for n in atlas.entities.values())


def test_schema_03_functions_and_legacy_02_migration_are_explicit(payloads):
    assert get_args(AtlasSourceSchema) == ("0.2", "0.3")
    atlas = validate_registry(*payloads)
    assert validated_source_schema_version(*payloads) == "0.3"
    assert atlas.source_atlas_schema == "0.3"

    legacy = copy.deepcopy(payloads)
    function_ids = {node["id"] for node in legacy[0]["nodes"] if node["type"] == "Function"}
    legacy[0]["nodes"] = [node for node in legacy[0]["nodes"] if node["id"] not in function_ids]
    legacy[1]["relationships"] = [
        relation
        for relation in legacy[1]["relationships"]
        if relation["source"] not in function_ids and relation["target"] not in function_ids
    ]
    for item in legacy:
        item["atlas_schema_version"] = "0.2"
    assert validate_registry(*legacy).source_atlas_schema == "0.2"

    # Schema 0.2 remains readable for legacy contents but cannot claim the 0.3 vocabulary.
    for item in payloads:
        item["atlas_schema_version"] = "0.2"
    with pytest.raises(ValueError, match="schema 0.2 does not support Function semantics"):
        validate_registry(*payloads)


def test_mixed_registry_source_schema_versions_fail_closed(payloads):
    payloads[1]["atlas_schema_version"] = "0.2"
    with pytest.raises(ValueError, match="must agree on atlas_schema_version"):
        validated_source_schema_version(*payloads)
    with pytest.raises(ValueError, match="must agree on atlas_schema_version"):
        validate_registry(*payloads)


@pytest.mark.parametrize("version", ["0.4", "0.5", "0.2 ", None])
def test_unsupported_registry_source_schema_version_fails_closed(payloads, version):
    for payload in payloads:
        payload["atlas_schema_version"] = version
    with pytest.raises(ValueError, match="Unsupported Atlas source schema version"):
        validated_source_schema_version(*payloads)


@pytest.mark.parametrize("payload", [None, {"nodes": []}, {"atlas_schema_version": ["0.2"]}])
def test_malformed_registry_source_envelope_fails_closed(payloads, payload):
    payloads[1] = payload
    with pytest.raises(ValueError):
        validated_source_schema_version(*payloads)


def test_duplicate_registry_source_schema_key_fails_closed(tmp_path):
    registry = tmp_path / "registry"
    registry.mkdir()
    for filename in ("nodes.yaml", "relationships.yaml", "evidence.yaml"):
        source = ATLAS / "registry" / filename
        shutil.copyfile(source, registry / filename)
    nodes_path = registry / "nodes.yaml"
    original = nodes_path.read_text(encoding="utf-8").splitlines()
    nodes_path.write_text(
        'atlas_schema_version: "0.2"\natlas_schema_version: "0.3"\n'
        + "\n".join(original[1:])
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate YAML key: atlas_schema_version"):
        load_registry(tmp_path)


@pytest.mark.parametrize("index", [0, 1, 2])
def test_schema_version_rejected(payloads, index):
    payloads[index]["atlas_schema_version"] = "0.1"
    with pytest.raises(ValueError):
        validate_registry(*payloads)


def test_function_memberships_and_component_hierarchy_are_exact(payloads):
    atlas = validate_registry(*payloads)
    functions = {node.id for node in atlas.entities.values() if node.type == "Function"}
    assert functions == set(EXPECTED_FUNCTION_PARTICIPANTS)

    memberships = [
        edge for edge in atlas.relationships if edge.relation == "contributes_to_function"
    ]
    actual_participants = {
        function_id: {edge.source for edge in memberships if edge.target == function_id}
        for function_id in functions
    }
    assert actual_participants == EXPECTED_FUNCTION_PARTICIPANTS
    assert len(memberships) == 26
    assert all(
        edge.functional_role is None and edge.functional_order is None for edge in memberships
    )
    assert all(
        ("EVID-FUNCTION-SEMANTICS-137", function_id)
        in {
            (edge.source, edge.target)
            for edge in atlas.relationships
            if edge.relation == "supports"
        }
        for function_id in functions
    )

    component_ids = {node.id for node in atlas.entities.values() if node.type == "Component"}
    assert component_ids == set(EXPECTED_COMPONENT_PARENTS)
    component_parents = {
        (edge.source, edge.target)
        for edge in atlas.relationships
        if edge.relation == "part_of" and atlas.entities[edge.source].type == "Component"
    }
    assert component_parents == set(EXPECTED_COMPONENT_PARENTS.items())
    assert len(component_parents) == 28
    assert sum(parent == "SYS-AGA" for _, parent in component_parents) == 17
    assert sum(parent in component_ids for _, parent in component_parents) == 11
    child_counts = {
        component: sum(parent == component for _, parent in component_parents)
        for component in component_ids
    }
    assert sum(count > 0 for count in child_counts.values()) == 4
    assert sum(count == 0 for count in child_counts.values()) == 24
    assert all(
        atlas.entities[edge.source].type != "Function"
        and atlas.entities[edge.target].type != "Function"
        for edge in atlas.relationships
        if edge.relation == "part_of"
    )


def test_function_prefix_is_closed(payloads):
    registry = minimal_registry(payloads, ["CMP-CORTEX", "FUNC-OBSERVE"])
    registry[0]["nodes"].append(
        dict(
            id="CMP-FUNCTION-WRONG",
            type="Function",
            name="Wrong prefix",
            description="Synthetic only",
        )
    )
    with pytest.raises(ValueError, match="ID prefix/type mismatch"):
        validate_registry(*registry)


def test_function_membership_can_overlap(payloads):
    registry = minimal_registry(
        payloads,
        ["CMP-CORTEX", "FUNC-REASON", "FUNC-OBSERVE"],
        [
            {
                "relation": "contributes_to_function",
                "source": "CMP-CORTEX",
                "target": "FUNC-REASON",
            },
            {
                "relation": "contributes_to_function",
                "source": "CMP-CORTEX",
                "target": "FUNC-OBSERVE",
            },
        ],
    )
    atlas = validate_registry(*registry)
    functions = {
        relation.target
        for relation in atlas.relationships
        if relation.relation == "contributes_to_function" and relation.source == "CMP-CORTEX"
    }
    assert functions == {"FUNC-REASON", "FUNC-OBSERVE"}


@pytest.mark.parametrize("source", ["DOM-COGNITION", "FUNC-REASON"])
def test_function_membership_rejects_unsupported_source_types(payloads, source):
    registry = minimal_registry(
        payloads,
        [source, "FUNC-OBSERVE"],
        [{"relation": "contributes_to_function", "source": source, "target": "FUNC-OBSERVE"}],
    )
    with pytest.raises(ValueError, match="Illegal contributes_to_function type pairing"):
        validate_registry(*registry)


def test_function_membership_target_must_be_function(payloads):
    registry = minimal_registry(
        payloads,
        ["CMP-CORTEX", "CMP-MANAGER"],
        [{"relation": "contributes_to_function", "source": "CMP-CORTEX", "target": "CMP-MANAGER"}],
    )
    with pytest.raises(ValueError, match="Illegal contributes_to_function type pairing"):
        validate_registry(*registry)


def test_duplicate_function_membership_fails(payloads):
    membership = {
        "relation": "contributes_to_function",
        "source": "CMP-CORTEX",
        "target": "FUNC-REASON",
    }
    registry = minimal_registry(
        payloads,
        ["CMP-CORTEX", "FUNC-REASON"],
        [membership, membership.copy()],
    )
    with pytest.raises(ValueError, match="Duplicate relationship"):
        validate_registry(*registry)


@pytest.mark.parametrize(
    "source,target", [("FUNC-OBSERVE", "CMP-PERCEPTION"), ("CMP-PERCEPTION", "FUNC-OBSERVE")]
)
def test_function_cannot_be_source_or_target_of_part_of(payloads, source, target):
    registry = minimal_registry(
        payloads,
        [source, target],
        [{"relation": "part_of", "source": source, "target": target}],
    )
    with pytest.raises(ValueError, match="Illegal part_of type pairing"):
        validate_registry(*registry)


@pytest.mark.parametrize(
    "relation,field,value",
    [
        ("consumes", "functional_role", "observer"),
        ("supplies", "functional_order", 1),
        ("part_of", "functional_role", None),
    ],
)
def test_function_metadata_is_rejected_on_unrelated_relations(relation, field, value):
    membership = {
        "relation": relation,
        "source": "CMP-CORTEX",
        "target": "CMP-MANAGER",
        field: value,
    }
    with pytest.raises(ValueError, match="functional metadata is only valid"):
        Relationship.model_validate(membership)


def test_function_order_is_optional_and_explicit_when_present(payloads):
    registry = minimal_registry(
        payloads,
        ["CMP-CORTEX", "CMP-MANAGER", "FUNC-OBSERVE"],
        [
            {
                "relation": "contributes_to_function",
                "source": "CMP-CORTEX",
                "target": "FUNC-OBSERVE",
                "functional_role": "short-horizon stabilizer",
            },
            {
                "relation": "contributes_to_function",
                "source": "CMP-MANAGER",
                "target": "FUNC-OBSERVE",
                "functional_order": 3,
            },
        ],
    )
    atlas = validate_registry(*registry)
    membership = next(
        item
        for item in atlas.relationships
        if item.relation == "contributes_to_function"
        and item.source == "CMP-CORTEX"
        and item.target == "FUNC-OBSERVE"
    )
    assert membership.functional_role == "short-horizon stabilizer"
    assert membership.functional_order is None
    participant = next(
        item
        for item in atlas.relationships
        if item.relation == "contributes_to_function"
        and item.source == "CMP-MANAGER"
        and item.target == "FUNC-OBSERVE"
    )
    assert participant.functional_order == 3


def test_duplicate_explicit_function_order_fails_within_one_function(payloads):
    registry = minimal_registry(
        payloads,
        ["CMP-CORTEX", "CMP-MANAGER", "FUNC-OBSERVE"],
        [
            {
                "relation": "contributes_to_function",
                "source": "CMP-CORTEX",
                "target": "FUNC-OBSERVE",
                "functional_order": 1,
            },
            {
                "relation": "contributes_to_function",
                "source": "CMP-MANAGER",
                "target": "FUNC-OBSERVE",
                "functional_order": 1,
            },
        ],
    )
    with pytest.raises(ValueError, match="Duplicate functional_order"):
        validate_registry(*registry)


@pytest.mark.parametrize("order", [0, -1, "1", True])
def test_function_order_requires_a_positive_strict_integer(order):
    with pytest.raises(ValueError):
        Relationship.model_validate(
            {
                "relation": "contributes_to_function",
                "source": "CMP-CORTEX",
                "target": "FUNC-OBSERVE",
                "functional_order": order,
            }
        )


@pytest.mark.parametrize("index,key", [(0, "nodes"), (2, "evidence")])
def test_duplicate_id_rejected(payloads, index, key):
    payloads[index][key].append(copy.deepcopy(payloads[index][key][0]))
    with pytest.raises(ValueError, match="Duplicate ID"):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "field,value", [("id", "CMP-WRONG"), ("domain_id", "DOM-COGNITION"), ("type", "AnyNode")]
)
def test_closed_node_schema(payloads, field, value):
    payloads[0]["nodes"][0][field] = value
    with pytest.raises(ValueError):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "relation,source,target",
    [
        ("controls", "CMP-CORTEX", "CMP-MISSING"),
        ("executes", "CMP-CORTEX", "CMP-MANAGER"),
        ("part_of", "DOM-COGNITION", "CMP-CORTEX"),
        ("part_of", "CMP-CORTEX", "DOM-COGNITION"),
        ("presented_in_domain", "CMP-CORTEX", "CMP-MANAGER"),
        ("contains", "SYS-AGA", "CMP-CORTEX"),
        ("related_to", "CMP-CORTEX", "CMP-MANAGER"),
    ],
)
def test_invalid_relationship_rejected(payloads, relation, source, target):
    edge(payloads, relation, source, target)
    with pytest.raises(ValueError):
        validate_registry(*payloads)


@pytest.mark.parametrize("self_cycle", [False, True])
def test_technical_part_of_cycle_rejected(payloads, self_cycle):
    edge(payloads, "part_of")
    edge(payloads, "part_of", "CMP-MANAGER", "CMP-MANAGER" if self_cycle else "CMP-CORTEX")
    with pytest.raises(ValueError, match="cycle"):
        validate_registry(*payloads)


def test_domain_move_and_work_graph_do_not_change_ancestry(payloads):
    before = validate_registry(*payloads)
    for relation in payloads[1]["relationships"]:
        if relation["relation"] == "presented_in_domain":
            relation["target"] = "DOM-ENV-ACQUISITION"
    edge(payloads, "proposes_to", "CMP-MANAGER", "CMP-CORTEX")
    after = validate_registry(*payloads)
    assert after.ancestors("CMP-CORTEX") == before.ancestors("CMP-CORTEX") == {"SYS-AGA"}
    assert after.ancestors("DOM-ENV-ACQUISITION") == frozenset()
    assert render_overview(after) != render_overview(before)


def test_rename_keeps_stable_id(payloads):
    payloads[0]["nodes"][0]["name"] = "Renamed system"
    assert validate_registry(*payloads).entities["SYS-AGA"].name == "Renamed system"


def test_superseded_old_node_remains_addressable(payloads):
    edge(payloads, "supersedes")
    atlas = validate_registry(*payloads)
    assert atlas.entities["CMP-CORTEX"].id == "CMP-CORTEX"
    assert atlas.entities["CMP-MANAGER"].id == "CMP-MANAGER"


@pytest.mark.parametrize("decision", [None, "CMP-CORTEX", "DEC-MISSING", "DEC-ATLAS-PILOT-001"])
def test_decomposition_without_valid_decision_rejected(payloads, decision):
    edge(payloads, "decomposed_into", decision_id=decision)
    with pytest.raises(ValueError, match="Decision"):
        validate_registry(*payloads)


def test_decomposition_with_decision_accepted_and_history_preserved(payloads):
    architecture_approval(payloads)
    edge(payloads, "decomposed_into", decision_id="DEC-ARCH-DECOMP-TEST")
    atlas = validate_registry(*payloads)
    assert "CMP-CORTEX" in atlas.entities and "CMP-MANAGER" in atlas.entities
    assert atlas.ancestors("CMP-MANAGER") == {"SYS-AGA"}


def test_research_suggestion_does_not_mutate_hierarchy_or_status(payloads):
    before = validate_registry(*payloads)
    payloads[0]["nodes"].append(
        dict(id="LEAD-TEST", type="ExperimentLead", name="Test lead", description="Test only")
    )
    edge(payloads, "research_suggests_decomposition", "LEAD-TEST", "CMP-CORTEX")
    after = validate_registry(*payloads)
    assert after.ancestors("CMP-CORTEX") == before.ancestors("CMP-CORTEX")
    assert after.entities["CMP-CORTEX"] == before.entities["CMP-CORTEX"]
    edge(payloads, "decomposed_into", decision_id="LEAD-TEST")
    with pytest.raises(ValueError, match="Decision"):
        validate_registry(*payloads)


@pytest.mark.parametrize("field", ["repository", "ref", "path", "symbol", "checked_date"])
def test_github_evidence_requires_locator(payloads, field):
    item = next(
        e for e in payloads[2]["evidence"] if e["provenance_kind"] == "github_implementation"
    )
    del item[field]
    with pytest.raises(ValueError):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "kind",
    [
        "canonical_project_source",
        "primary_literature",
        "scientific_project_artifact",
        "chat_historical_context",
        "synthesis_inference",
        "project_decision",
    ],
)
def test_document_evidence_rejects_bare_link(payloads, kind):
    item = payloads[2]["evidence"][0]
    item.update(provenance_kind=kind, document="https://example.org/paper")
    del item["section"]
    with pytest.raises(ValueError, match="locator"):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "implementation,mapping",
    itertools.product(
        ["target-only", "implemented"],
        ["unmapped", "leads-collected", "primary-partially-checked", "focused-review-complete"],
    ),
)
def test_status_axes_are_independent(payloads, implementation, mapping):
    item = payloads[0]["nodes"][0]
    item["technical"]["implementation_status"] = implementation
    item["research_mapping"] = mapping
    result = validate_registry(*payloads).entities[item["id"]]
    assert result.technical.verification_status == "unverified"
    assert result.technical.implementation_status == implementation
    assert result.research_mapping == mapping
    assert result.research_direction is None


@pytest.mark.parametrize("kind", ["ResearchQuestion", "ExperimentLead"])
@pytest.mark.parametrize(
    "mapping,direction",
    itertools.product(
        ["unmapped", "leads-collected", "primary-partially-checked", "focused-review-complete"],
        ["open-lead", "needs-closure", "deprioritized", "killed", "active-candidate"],
    ),
)
def test_candidate_status_axes_do_not_change_technical_ancestry(payloads, kind, mapping, direction):
    before = validate_registry(*payloads)
    identity = PREFIXES[kind] + "-STATUS-FIXTURE"
    payloads[0]["nodes"].append(
        dict(
            id=identity,
            type=kind,
            name="Synthetic candidate",
            description="Fixture only",
            research_mapping=mapping,
            research_direction=direction,
        )
    )
    after = validate_registry(*payloads)
    assert after.entities[identity].research_mapping == mapping
    assert after.entities[identity].research_direction == direction
    assert after.relationships == before.relationships
    for node_id, node in before.entities.items():
        assert after.entities[node_id] == node
        assert after.ancestors(node_id) == before.ancestors(node_id)


@pytest.mark.parametrize("kind", sorted(set(PREFIXES) - {"ResearchQuestion", "ExperimentLead"}))
def test_non_candidate_direction_rejected(payloads, kind):
    items = payloads[2]["evidence"] if kind == "Evidence" else payloads[0]["nodes"]
    item = next((n for n in items if n["type"] == kind), None)
    if item is None:
        item = dict(id=PREFIXES[kind] + "-STATUS", type=kind, name=kind, description="Fixture")
        items.append(item)
    # Establish a valid control so rejection cannot hide a malformed fixture.
    validate_registry(*payloads)
    item["research_direction"] = "killed"
    with pytest.raises(ValueError, match="research_direction"):
        validate_registry(*payloads)


def test_deterministic_render_independent_of_registry_order(payloads):
    expected = render_overview(validate_registry(*payloads))
    for payload, key in zip(payloads, ["nodes", "relationships", "evidence"], strict=True):
        payload[key].reverse()
    assert render_overview(validate_registry(*payloads)) == expected


def test_committed_overview_equals_renderer():
    assert render_overview(load_registry(ATLAS)) == (ATLAS / "overview.md").read_text()


def test_duplicate_yaml_key_rejected(tmp_path):
    shutil.copytree(ATLAS, tmp_path / "atlas")
    path = tmp_path / "atlas/registry/nodes.yaml"
    path.write_text(path.read_text() + '\natlas_schema_version: "0.1"\n')
    with pytest.raises(ValueError, match="Duplicate YAML key"):
        load_registry(tmp_path / "atlas")


def test_duplicate_relationship_rejected(payloads):
    payloads[1]["relationships"].append(payloads[1]["relationships"][0].copy())
    with pytest.raises(ValueError, match="Duplicate relationship"):
        validate_registry(*payloads)


def test_all_node_types_and_relations_are_closed_and_supported(payloads):
    assert len(PREFIXES) == 16
    assert set(get_args(RelationName)) == set(RELATION_PAIRS)
    for kind, prefix in PREFIXES.items():
        if kind in {n["type"] for n in payloads[0]["nodes"]} or kind == "Evidence":
            continue
        item = dict(id=f"{prefix}-TEST", type=kind, name=kind, description="Schema test")
        if kind == "Environment":
            item["technical"] = payloads[0]["nodes"][0]["technical"].copy()
        payloads[0]["nodes"].append(item)
    assert {n.type for n in validate_registry(*payloads).entities.values()} == set(PREFIXES)


def test_package_imports_only_stdlib_pydantic_yaml_and_itself():
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    assert node.level == 1
                    assert node.module in {
                        "anatomy",
                        "assembly_scopes",
                        "schema",
                        "validator",
                        "render",
                        "workspace",
                        "wiki_schema",
                        "private_projection",
                        "private_views",
                        "private_reference_index",
                    }
                    continue
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                assert module.split(".")[0] in sys.stdlib_module_names | {"pydantic", "yaml"}
        assert not any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id in {"__import__", "eval", "exec"}
            for n in ast.walk(tree)
        )


def test_github_locators_resolve_without_importing_runtime():
    for evidence in load_registry(ATLAS).entities.values():
        if evidence.type != "Evidence" or evidence.provenance_kind != "github_implementation":
            continue
        path = ROOT / evidence.path
        tree = ast.parse(path.read_text())
        body = tree.body
        for name in evidence.symbol.split("."):
            found = next(
                n
                for n in body
                if isinstance(n, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
                and n.name == name
            )
            body = found.body


@pytest.mark.parametrize("relation", get_args(RelationName))
def test_each_relation_has_an_executable_valid_pair(payloads, relation):
    # Synthetic entities exercise vocabulary not instantiated in the pilot.
    technical = payloads[0]["nodes"][0]["technical"].copy()
    for kind, prefix in PREFIXES.items():
        if kind == "Evidence":
            continue
        item = dict(id=f"{prefix}-PAIR", type=kind, name="Pair test", description="Test only")
        if kind in {
            "System",
            "Component",
            "Interface",
            "Contract",
            "DataArtifact",
            "MeasurementPoint",
            "Environment",
        }:
            item["technical"] = technical.copy()
        if kind == "Domain":
            item["grouping_semantics"] = "presentation / navigation grouping"
        if kind == "Decision":
            item["decision_scope"] = "tooling"
        if kind == "ResearchThread":
            item["ordered_refs"] = []
        payloads[0]["nodes"].append(item)
    sources, targets = RELATION_PAIRS[relation]
    if relation in {"supersedes", "decomposed_into", "part_of"}:
        source, target = "CMP-CORTEX", "CMP-PAIR"
    else:
        source_kind, target_kind = sorted(sources)[0], sorted(targets)[0]
        source = (
            "EVID-PROGRAM-001" if source_kind == "Evidence" else PREFIXES[source_kind] + "-PAIR"
        )
        target = (
            "EVID-PROGRAM-001" if target_kind == "Evidence" else PREFIXES[target_kind] + "-PAIR"
        )
    if relation == "decomposed_into":
        architecture_approval(payloads)
    kwargs = {"decision_id": "DEC-ARCH-DECOMP-TEST"} if relation == "decomposed_into" else {}
    edge(payloads, relation, source, target, **kwargs)
    validate_registry(*payloads)


def architecture_approval(payloads):
    payloads[0]["nodes"].append(
        dict(
            id="DEC-ARCH-DECOMP-TEST",
            type="Decision",
            name="Synthetic approval",
            description="Test-only architecture approval",
            decision_scope="architecture",
        )
    )
    payloads[2]["evidence"].append(
        dict(
            id="EVID-ARCH-DECOMP-TEST",
            type="Evidence",
            name="Synthetic approval evidence",
            description="Test-only decision record",
            provenance_kind="project_decision",
            document="test-fixture",
            version="1",
            section="Architecture approval",
            checked_date="2026-09-09",
        )
    )
    edge(payloads, "supports", "EVID-ARCH-DECOMP-TEST", "DEC-ARCH-DECOMP-TEST")


@pytest.mark.parametrize("missing", ["support", "project_provenance", "architecture_scope"])
def test_decomposition_approval_is_fail_closed(payloads, missing):
    architecture_approval(payloads)
    if missing == "support":
        payloads[1]["relationships"].pop()
    elif missing == "project_provenance":
        payloads[2]["evidence"][-1]["provenance_kind"] = "synthesis_inference"
    else:
        payloads[0]["nodes"][-1]["decision_scope"] = "research"
    edge(payloads, "decomposed_into", decision_id="DEC-ARCH-DECOMP-TEST")
    with pytest.raises(ValueError, match="Decision"):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "source",
    [
        "IF-MEM-CORTEX",
        "CON-CORTEX-CONTEXT",
        "DAT-RETRIEVAL-SNAPSHOT",
        "MEAS-CORTEX-PROPOSAL-001",
        "DOM-COGNITION",
        "SYS-AGA",
    ],
)
def test_non_component_part_of_source_rejected(payloads, source):
    edge(payloads, "part_of", source, "CMP-CORTEX")
    with pytest.raises(ValueError, match="Illegal part_of"):
        validate_registry(*payloads)


@pytest.mark.parametrize("target", ["CMP-MANAGER", "SYS-AGA"])
def test_component_part_of_component_or_system_accepted(payloads, target):
    payloads[1]["relationships"] = [
        e
        for e in payloads[1]["relationships"]
        if not (e["relation"] == "part_of" and e["source"] == "CMP-CORTEX")
    ]
    edge(payloads, "part_of", "CMP-CORTEX", target)
    assert target in validate_registry(*payloads).ancestors("CMP-CORTEX")


@pytest.mark.parametrize(
    "target",
    [
        "CMP-CORTEX",
        "IF-MEM-CORTEX",
        "CON-CORTEX-CONTEXT",
        "DAT-RETRIEVAL-SNAPSHOT",
    ],
)
def test_measured_at_direction(payloads, target):
    edge(payloads, "measured_at", "MEAS-VERIFIED-OUTCOME-001", target)
    validate_registry(*payloads)
    edge(payloads, "measured_at", target, "MEAS-VERIFIED-OUTCOME-001")
    with pytest.raises(ValueError, match="Illegal measured_at"):
        validate_registry(*payloads)


def test_studied_by_is_literature_coverage_only(payloads):
    payloads[0]["nodes"].append(
        dict(id="PAPER-TEST", type="Paper", name="Synthetic paper", description="Test fixture only")
    )
    edge(payloads, "studied_by", "THREAD-EXPERIENCE-TO-ACTION-001", "PAPER-TEST")
    edge(payloads, "studied_by", "CMP-CORTEX", "PAPER-TEST")
    validate_registry(*payloads)
    edge(payloads, "studied_by", "CMP-CORTEX", "THREAD-EXPERIENCE-TO-ACTION-001")
    with pytest.raises(ValueError, match="Illegal studied_by"):
        validate_registry(*payloads)


def test_thread_order_and_references_preserved_without_architecture_mutation(payloads):
    before = validate_registry(*payloads)
    thread = next(n for n in payloads[0]["nodes"] if n["type"] == "ResearchThread")
    assert thread["ordered_refs"] == [
        "CMP-MEM-RETRIEVAL",
        "MEAS-RETRIEVAL-DELIVERY-001",
        "IF-MEM-CORTEX",
        "CON-CORTEX-CONTEXT",
        "CMP-CORTEX",
        "MEAS-CORTEX-PROPOSAL-001",
        "CON-PLANNER-OUTPUT",
        "IF-CORTEX-MANAGER",
        "CMP-MANAGER",
        "MEAS-MANAGER-DISPOSITION-001",
        "CON-SKILL-CONTRACT",
        "MEAS-VERIFIED-OUTCOME-001",
    ]
    assert all(ref in before.entities for ref in thread["ordered_refs"])
    thread["ordered_refs"].reverse()
    after = validate_registry(*payloads)
    assert after.entities[thread["id"]].ordered_refs == tuple(thread["ordered_refs"])
    assert before.relationships == after.relationships
    for node_id, node in before.entities.items():
        assert before.ancestors(node_id) == after.ancestors(node_id)
        if node_id != thread["id"]:
            assert after.entities[node_id] == node


@pytest.mark.parametrize(
    "reference",
    [
        "CMP-MISSING",
        "DOM-COGNITION",
        "SYS-AGA",
        "RQ-PROGRAM-AB-001",
        "EVID-PROGRAM-001",
        "DEC-ATLAS-PILOT-001",
    ],
)
def test_invalid_thread_reference_rejected(payloads, reference):
    thread = next(n for n in payloads[0]["nodes"] if n["type"] == "ResearchThread")
    thread["ordered_refs"].append(reference)
    with pytest.raises(ValueError, match="ResearchThread reference"):
        validate_registry(*payloads)


@pytest.mark.parametrize("status", ["live-demonstrated", "measurement-validated"])
def test_specific_verification_statuses_accepted(payloads, status):
    payloads[0]["nodes"][0]["technical"]["verification_status"] = status
    result = validate_registry(*payloads).entities["SYS-AGA"]
    assert result.technical.verification_status == status
    assert result.research_mapping == "unmapped"
    assert result.research_direction is None


def test_generic_validated_rejected(payloads):
    payloads[0]["nodes"][0]["technical"]["verification_status"] = "validated"
    with pytest.raises(ValueError):
        validate_registry(*payloads)


@pytest.mark.parametrize("relation", ["decomposed_into", "research_suggests_decomposition"])
@pytest.mark.parametrize(
    "target",
    [
        "SYS-AGA",
        "IF-MEM-CORTEX",
        "CON-CORTEX-CONTEXT",
        "DAT-RETRIEVAL-SNAPSHOT",
        "MEAS-CORTEX-PROPOSAL-001",
    ],
)
def test_decomposition_targets_are_components_only(payloads, relation, target):
    architecture_approval(payloads)
    payloads[0]["nodes"].append(
        dict(id="LEAD-TEST", type="ExperimentLead", name="Synthetic lead", description="Test only")
    )
    source = "CMP-CORTEX" if relation == "decomposed_into" else "LEAD-TEST"
    kwargs = {"decision_id": "DEC-ARCH-DECOMP-TEST"} if relation == "decomposed_into" else {}
    edge(payloads, relation, source, target, **kwargs)
    with pytest.raises(ValueError, match="Illegal"):
        validate_registry(*payloads)


def test_pilot_contains_no_architecture_decomposition_or_literature_edges():
    atlas = load_registry(ATLAS)
    assert atlas.entities["DEC-ATLAS-PILOT-001"].decision_scope == "tooling"
    assert not any(e.relation in {"decomposed_into", "studied_by"} for e in atlas.relationships)
