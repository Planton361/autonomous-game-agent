"""W03 public-safe visual surfaces; no private vault or game access."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from fh_agent.research_atlas import private_projection
from fh_agent.research_atlas.anatomy import (
    ANATOMY_RECORD_IDS,
    ANATOMY_REGIONS,
    BETWEEN_RUN_RELATION_KEYS,
    DOMAIN_LINKED_IDS,
    DOMAIN_MEMBER_IDS,
    DOMAIN_RELATION_KEYS,
    FLOW_KEYS,
)
from fh_agent.research_atlas.private_views import MEMORY_WORKBENCH
from fh_agent.research_atlas.private_views import OWNED_ROOT as DERIVED_ROOT
from fh_agent.research_atlas.validator import Atlas, load_registry
from fh_agent.research_atlas.workspace import (
    ANATOMY_PATH,
    DOMAIN_SLICE_PATH,
    HOME_PATH,
    MAP_PATH,
    note_link,
    parse_frontmatter,
    validate_links,
    validate_workspace_tree,
    workspace_tree,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def atlas():
    return load_registry(REPOSITORY_ROOT / "docs/research-atlas")


def scene(markdown):
    match = re.search(r"\n## Drawing\n[^`]*```json\n([\s\S]*?)```\n", markdown)
    assert match
    return json.loads(match.group(1))


def rewrite_scene(markdown, value):
    prefix, remainder = markdown.split("```json\n", 1)
    _, suffix = remainder.split("\n```", 1)
    return (
        prefix
        + "```json\n"
        + json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```"
        + suffix
    )


def record_elements(value):
    return {
        element["customData"]["atlas_id"]: element
        for element in value["elements"]
        if "atlas_id" in element.get("customData", {})
    }


def technical_edges(value):
    return {
        tuple(
            element["customData"]["atlas_relation"][key] for key in ("source", "relation", "target")
        )
        for element in value["elements"]
        if "atlas_relation" in element.get("customData", {})
    }


def inside(inner, outer):
    return (
        outer["x"] <= inner["x"]
        and outer["y"] <= inner["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def test_w03_assets_are_finite_generated_and_navigable(atlas):
    tree = workspace_tree(atlas)
    assert {MAP_PATH, ANATOMY_PATH, DOMAIN_SLICE_PATH} <= tree.keys()
    assert parse_frontmatter(tree[ANATOMY_PATH])["atlas_workspace_generated"] is True
    assert parse_frontmatter(tree[DOMAIN_SLICE_PATH])["atlas_workspace_generated"] is True
    assert parse_frontmatter(tree[ANATOMY_PATH])["atlas_visual_surface"] == "agent-anatomy"
    assert parse_frontmatter(tree[DOMAIN_SLICE_PATH])["atlas_visual_surface"] == "domain-slice"

    home = tree[HOME_PATH]
    assert home.index("Agent Anatomy") < home.index("System Anatomy")
    assert "Primary visual entry" in home and "Markdown Home" in home
    assert "comparison and rollback" in home
    assert "Technical Hierarchy" in tree[DOMAIN_SLICE_PATH]
    assert "Memory Retrieval Component Hub" in tree[DOMAIN_SLICE_PATH]
    validate_links(tree)


def test_agent_anatomy_regions_keep_runtime_boundaries_clear(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[ANATOMY_PATH])
    elements = value["elements"]
    records = record_elements(value)
    assert set(records) == {
        "SYS-AGA",
        "CMP-VISIBLE-STATE-BRIDGE",
        "CMP-SKILL-TRAINER",
        "DAT-CANDIDATE-BODY-VERSION",
        "CMP-BODY-CERTIFICATION",
    }
    regions = {
        element["customData"]["functional_region"]: element
        for element in elements
        if "functional_region" in element.get("customData", {})
    }
    assert set(regions) == {key for key, *_ in ANATOMY_REGIONS}

    boundaries = {
        element["customData"]["presentation_boundary"]: element
        for element in elements
        if "presentation_boundary" in element.get("customData", {})
    }
    assert set(boundaries) == {"in-run", "between-runs"}
    for identity in ("CMP-SKILL-TRAINER", "DAT-CANDIDATE-BODY-VERSION", "CMP-BODY-CERTIFICATION"):
        assert inside(records[identity], boundaries["between-runs"])
        assert not inside(records[identity], boundaries["in-run"])
    assert "frozen Body version, including Life Episode restarts" in tree[ANATOMY_PATH]
    assert "Cortex proposes · Manager contracts" in tree[ANATOMY_PATH]
    assert "Body/Reflex (active contract)" in tree[ANATOMY_PATH]
    assert "SafetyFilter → InputExecutor" in tree[ANATOMY_PATH]
    assert "Independent Verifier" in tree[ANATOMY_PATH]
    assert "outside cortex decision authority" in tree[ANATOMY_PATH].lower()
    assert "Outcome before replay" in tree[ANATOMY_PATH]

    bridge = records["CMP-VISIBLE-STATE-BRIDGE"]
    assert inside(bridge, regions["observation"])
    assert "CMP-NO-SPOILER-FIREWALL" in regions["observation"]["customData"]["atlas_landmarks"]
    assert bridge["strokeStyle"] == "dashed"
    assert bridge["customData"]["path_style"] == "optional"
    assert not any(
        relation[0] in {"CMP-VISIBLE-STATE-BRIDGE", "CMP-NO-SPOILER-FIREWALL"}
        or relation[2] in {"CMP-VISIBLE-STATE-BRIDGE", "CMP-NO-SPOILER-FIREWALL"}
        for relation in technical_edges(value)
    )
    flow_arrows = [
        element for element in elements if "presentation_flow" in element.get("customData", {})
    ]
    assert len(flow_arrows) == len(FLOW_KEYS)
    assert all(element["strokeStyle"] == "dashed" for element in flow_arrows)
    assert all("atlas_relation" not in element.get("customData", {}) for element in flow_arrows)
    assert all(
        element.get("link")
        for element in elements
        if set(element.get("customData", {})) & {"atlas_id", "functional_region", "navigation"}
    )

    verifier = regions["verification"]
    cortex = regions["cognition"]
    assert (
        verifier["x"] > cortex["x"] + cortex["width"]
        or cortex["x"] > verifier["x"] + verifier["width"]
    )
    assert not any(
        edge[0] == "CMP-CORTEX" and edge[2] == "CMP-INDEPENDENT-VERIFIER"
        for edge in technical_edges(value)
    )
    assert technical_edges(value) == set(BETWEEN_RUN_RELATION_KEYS)


def test_z2_exploded_home_is_one_system_with_distinct_assemblies(atlas):
    value = scene(workspace_tree(atlas)[ANATOMY_PATH])
    elements = value["elements"]
    regions = [
        element for element in elements if "functional_region" in element.get("customData", {})
    ]
    assert len(regions) == len(ANATOMY_REGIONS) == 7
    assert {element["type"] for element in regions} == {"ellipse", "rectangle"}
    assert {element["customData"]["functional_region"] for element in regions} == {
        key for key, *_ in ANATOMY_REGIONS
    }
    assert all(element["customData"]["presentation_only"] is True for element in regions)
    assert {
        element["customData"]["presentation_structure"]
        for element in elements
        if "presentation_structure" in element.get("customData", {})
    } >= {"shared-chassis", "shared-backplane", "independent-verifier-pod"}
    assert all(
        element["customData"]["atlas_landmarks"] == list(identities)
        for element in regions
        for key, _, _, identities in ANATOMY_REGIONS
        if element["customData"]["functional_region"] == key
    )
    assert all(
        element["customData"]["landmark_links"]
        == {identity: note_link(atlas.entities[identity]) for identity in identities}
        for element in regions
        for key, _, _, identities in ANATOMY_REGIONS
        if element["customData"]["functional_region"] == key
    )
    assert {identity for _, _, _, identities in ANATOMY_REGIONS for identity in identities} <= (
        ANATOMY_RECORD_IDS
    )
    parts = {
        key: {
            element["customData"]["figurative_part"]
            for element in elements
            if element.get("customData", {}).get("presentation_assembly") == key
        }
        for key, *_ in ANATOMY_REGIONS
    }
    assert all(len(value) >= 7 for value in parts.values())
    assert {"optic-glass", "antenna", "intake-mouth"} <= parts["environment"]
    assert {"visor", "scan-sweep", "inspection-lamp"} <= parts["observation"]
    assert {"ledger", "memory-cells", "retrieval-drawer"} <= parts["evidence-memory"]
    assert {"left-lobe", "right-lobe", "thought-core"} <= parts["cognition"]
    assert {"gate-lock", "left-relay", "right-relay"} <= parts["executive"]
    assert {"chest-guard", "left-upper-arm", "right-upper-arm"} <= parts["action-safety"]
    assert {"inspection-lens", "verdict-check", "replay-reel"} <= parts["verification"]
    assert any(
        element.get("customData", {}).get("presentation_structure") == "between-run-workshop"
        for element in elements
    )
    assert len([element for element in elements if element.get("link")]) <= 14
    assert all(" · CMP-" not in element.get("text", "") for element in elements)
    assert any(
        element.get("customData", {}).get("outside_decision_authority") is True
        for element in elements
    )
    assert "BETWEEN MISSION RUNS ONLY" in scene_text(elements)
    assert "optional visible-state bridge" in scene_text(elements).lower()
    assert "Dashed arrows: orientation only" in scene_text(elements)


def scene_text(elements):
    return "\n".join(element.get("text", "") for element in elements)


def test_domain_slice_separates_presentation_membership_from_technical_edges(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[DOMAIN_SLICE_PATH])
    elements = value["elements"]
    domain_groups = [
        element for element in elements if "presentation_domain" in element.get("customData", {})
    ]
    assert len(domain_groups) == 1
    assert domain_groups[0]["customData"]["presentation_domain"] == "DOM-EVIDENCE-MEMORY"
    assert "presentation grouping only" in tree[DOMAIN_SLICE_PATH]

    records = record_elements(value)
    assert set(records) == {"SYS-AGA", *DOMAIN_MEMBER_IDS}
    links = {element.get("link") for element in elements if element.get("link")}
    for identity in DOMAIN_LINKED_IDS:
        assert note_link(atlas.entities[identity]) in links

    edges = technical_edges(value)
    assert edges == set(DOMAIN_RELATION_KEYS)
    assert ("CMP-MEMORY", "part_of", "SYS-AGA") in edges
    assert ("CMP-MEM-RETRIEVAL", "part_of", "SYS-AGA") in edges
    assert not any(
        source == "CMP-MEMORY"
        and target == "CMP-MEM-RETRIEVAL"
        or source == "CMP-MEM-RETRIEVAL"
        and target == "CMP-MEMORY"
        for source, relation, target in edges
        if relation == "part_of"
    )
    assert not any(
        element.get("customData", {}).get("atlas_relation", {}).get("relation")
        == "presented_in_domain"
        for element in elements
    )
    assert {atlas.entities[identity].type for identity in DOMAIN_LINKED_IDS} >= {
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
    }
    assert all(
        element.get("link")
        for element in elements
        if set(element.get("customData", {})) & {"atlas_id", "navigation", "presentation_domain"}
    )


def test_z2_scoped_memory_action_reaches_existing_component_hub(atlas):
    public = scene(workspace_tree(atlas)[DOMAIN_SLICE_PATH])
    public_action = next(
        element
        for element in public["elements"]
        if element.get("customData", {}).get("navigation") == "memory-retrieval-overview"
    )
    assert (
        public_action["link"].split("|", 1)[0]
        == note_link(atlas.entities["CMP-MEM-RETRIEVAL"]).split("|", 1)[0]
    )
    digests = {name: "a" * 64 for name in private_projection.REGISTRY_FILES}
    private_tree = private_projection.projection_tree(atlas, "b" * 40, digests)
    projected = scene(private_tree[private_projection.DOMAIN_SLICE].decode())
    private_action = next(
        element
        for element in projected["elements"]
        if element.get("customData", {}).get("navigation") == "memory-retrieval-overview"
    )
    assert private_action["link"] == (
        f"[[{(DERIVED_ROOT / MEMORY_WORKBENCH).with_suffix('')}|Memory Retrieval → Overview]]"
    )
    assert private_projection.MEMORY_HUB_TARGET == (DERIVED_ROOT / MEMORY_WORKBENCH)
    assert technical_edges(projected) == set(DOMAIN_RELATION_KEYS)


def test_w03_generation_is_byte_deterministic_and_registry_order_independent(atlas):
    first = workspace_tree(atlas)
    second = workspace_tree(atlas)
    assert first == second
    shuffled = Atlas(
        dict(reversed(list(atlas.entities.items()))), tuple(reversed(atlas.relationships))
    )
    assert first == workspace_tree(shuffled)
    for path in (ANATOMY_PATH, DOMAIN_SLICE_PATH):
        value = scene(first[path])
        ids = [element["id"] for element in value["elements"]]
        assert all(re.fullmatch(r"[a-f0-9]{8}", identity) for identity in ids)
        assert len(ids) == len(set(ids))
        assert all(
            element["updated"] == 0 and element["versionNonce"] == 1
            for element in value["elements"]
        )
        assert (
            hashlib.sha256(first[path].encode()).digest()
            == hashlib.sha256(second[path].encode()).digest()
        )


def test_generated_visual_validation_rejects_unsupported_domain_edge_targets(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[DOMAIN_SLICE_PATH])
    relation_element = next(
        element
        for element in value["elements"]
        if "atlas_relation" in element.get("customData", {})
    )
    relation_element["customData"]["atlas_relation"]["target"] = "DOM-EVIDENCE-MEMORY"
    tree[DOMAIN_SLICE_PATH] = rewrite_scene(tree[DOMAIN_SLICE_PATH], value)
    with pytest.raises(ValueError, match="unsupported Registry relation"):
        validate_workspace_tree(atlas, tree)


def test_z2_home_rejects_fabricated_registry_edge(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[ANATOMY_PATH])
    relation = next(
        element
        for element in value["elements"]
        if "atlas_relation" in element.get("customData", {})
    )
    relation["customData"]["atlas_relation"]["target"] = "CMP-CORTEX"
    tree[ANATOMY_PATH] = rewrite_scene(tree[ANATOMY_PATH], value)
    with pytest.raises(ValueError, match="unsupported Registry relation"):
        validate_workspace_tree(atlas, tree)


def test_z2_home_rejects_duplicate_presentation_assembly(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[ANATOMY_PATH])
    region = next(
        element
        for element in value["elements"]
        if element.get("customData", {}).get("functional_region") == "cognition"
    )
    duplicate = dict(region, id="abcdef12")
    value["elements"].append(duplicate)
    tree[ANATOMY_PATH] = rewrite_scene(tree[ANATOMY_PATH], value)
    with pytest.raises(ValueError, match="functional-region coverage mismatch"):
        validate_workspace_tree(atlas, tree)
