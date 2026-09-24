"""W03 public-safe visual surfaces; no private vault or game access."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from fh_agent.research_atlas.anatomy import (
    ANATOMY_RECORD_IDS,
    ANATOMY_REGIONS,
    BETWEEN_RUN_RELATION_KEYS,
    DOMAIN_LINKED_IDS,
    DOMAIN_MEMBER_IDS,
    DOMAIN_RELATION_KEYS,
    FLOW_KEYS,
)
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
    assert set(records) == ANATOMY_RECORD_IDS
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
    assert "Life Episode restart does not refresh weights" in tree[ANATOMY_PATH]
    assert "Cortex proposes goals and constraints" in tree[ANATOMY_PATH]
    assert "does not control" in tree[ANATOMY_PATH]
    assert "Manager validates proposals" in tree[ANATOMY_PATH]
    assert "active contract" in tree[ANATOMY_PATH]
    assert "Independent Verifier" in tree[ANATOMY_PATH]
    assert "outside cortex decision authority" in tree[ANATOMY_PATH].lower()
    assert "Verified outcome" in tree[ANATOMY_PATH]

    bridge = records["CMP-VISIBLE-STATE-BRIDGE"]
    firewall = records["CMP-NO-SPOILER-FIREWALL"]
    assert inside(bridge, regions["observation"])
    assert inside(firewall, regions["observation"])
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

    verifier = records["CMP-INDEPENDENT-VERIFIER"]
    cortex = records["CMP-CORTEX"]
    assert (
        verifier["x"] > cortex["x"] + cortex["width"]
        or cortex["x"] > verifier["x"] + verifier["width"]
    )
    assert not any(
        edge[0] == "CMP-CORTEX" and edge[2] == "CMP-INDEPENDENT-VERIFIER"
        for edge in technical_edges(value)
    )
    assert technical_edges(value) == set(BETWEEN_RUN_RELATION_KEYS)


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
