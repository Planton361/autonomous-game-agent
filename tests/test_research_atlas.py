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
from fh_agent.research_atlas.schema import PREFIXES, RelationName
from fh_agent.research_atlas.validator import (
    RELATION_PAIRS,
    load_registry,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
PACKAGE = ROOT / "src/fh_agent/research_atlas"


@pytest.fixture
def payloads():
    return [
        yaml.safe_load((ATLAS / "registry" / name).read_text())
        for name in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
    ]


def edge(payloads, relation, source="CMP-CORTEX", target="CMP-MANAGER", **kwargs):
    payloads[1]["relationships"].append(
        dict(relation=relation, source=source, target=target, **kwargs)
    )


def test_valid_pilot_registry_loads():
    atlas = load_registry(ATLAS)
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


@pytest.mark.parametrize("index", [0, 1, 2])
def test_schema_version_rejected(payloads, index):
    payloads[index]["atlas_schema_version"] = "0.1"
    with pytest.raises(ValueError):
        validate_registry(*payloads)


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
    assert len(PREFIXES) == 15
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
                        "schema",
                        "validator",
                        "render",
                        "workspace",
                        "wiki_schema",
                        "private_projection",
                        "private_views",
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
