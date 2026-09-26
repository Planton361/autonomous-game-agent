"""W03 public-safe visual surfaces; no private vault or game access."""

import base64
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
    HERO_ASSET_PATH,
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
    assert {MAP_PATH, ANATOMY_PATH, DOMAIN_SLICE_PATH, HERO_ASSET_PATH} <= tree.keys()
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
        "DAT-OBSERVATION",
        "CON-PLANNER-OUTPUT",
        "CON-SKILL-CONTRACT",
        "DAT-VISIBLE-OUTCOME",
        "CON-MEMORY-UPDATE-REQUEST",
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
    assert all(region["customData"]["presentation_only"] is True for region in regions.values())
    assert all(
        region["customData"]["atlas_landmarks"] == list(identities)
        for key, _, _, identities in ANATOMY_REGIONS
        for region in [regions[key]]
    )
    boundaries = {
        element["customData"]["presentation_boundary"]: element
        for element in elements
        if "presentation_boundary" in element.get("customData", {})
    }
    assert set(boundaries) == {"in-run", "between-runs"}
    for identity in ("CMP-SKILL-TRAINER", "DAT-CANDIDATE-BODY-VERSION", "CMP-BODY-CERTIFICATION"):
        assert inside(records[identity], boundaries["between-runs"])
        assert not inside(records[identity], boundaries["in-run"])
    assert "frozen Body version through Life Episode restarts" in tree[ANATOMY_PATH]
    assert "Cortex proposes" in tree[ANATOMY_PATH]
    assert "Manager grounds contracts" in tree[ANATOMY_PATH]
    assert "Body acts within contract" in tree[ANATOMY_PATH]
    assert "Outside Cortex decision authority" in tree[ANATOMY_PATH]
    assert "Optional bridge · no-spoiler perception" in tree[ANATOMY_PATH]
    assert records["CMP-VISIBLE-STATE-BRIDGE"]["strokeStyle"] == "dashed"
    assert records["CMP-VISIBLE-STATE-BRIDGE"]["customData"]["path_style"] == "optional"
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
    assert regions["verification"]["customData"]["outside_decision_authority"] is True
    assert not any(
        edge[0] == "CMP-CORTEX" and edge[2] == "CMP-INDEPENDENT-VERIFIER"
        for edge in technical_edges(value)
    )
    assert technical_edges(value) == set(BETWEEN_RUN_RELATION_KEYS)


def test_z2_illustrated_home_is_one_system_with_distinct_visual_grammar(atlas):
    tree = workspace_tree(atlas)
    value = scene(tree[ANATOMY_PATH])
    elements = value["elements"]
    images = [element for element in elements if element["type"] == "image"]
    assert len(images) == 1
    image = images[0]
    assert image["customData"]["presentation_structure"] == "shared-agent-silhouette"
    assert image["customData"]["illustration_source"] == str(HERO_ASSET_PATH)
    asset_bytes = tree[HERO_ASSET_PATH].encode()
    file_id = hashlib.sha256(asset_bytes).hexdigest()[:32]
    assert image["fileId"] == file_id
    assert len(value["files"]) == 1
    assert value["files"][file_id]["dataURL"] == (
        "data:image/svg+xml;base64," + base64.b64encode(asset_bytes).decode()
    )
    assert f"{file_id}: [[{HERO_ASSET_PATH}]]" in tree[ANATOMY_PATH]
    assert "<script" not in tree[HERO_ASSET_PATH]
    assert "href=" not in tree[HERO_ASSET_PATH]
    assert "url(" not in tree[HERO_ASSET_PATH]
    assert "file:" not in tree[HERO_ASSET_PATH]
    assert len([element for element in elements if element["type"] in {"ellipse", "diamond"}]) == 0
    assert {identity for _, _, _, identities in ANATOMY_REGIONS for identity in identities} <= (
        ANATOMY_RECORD_IDS
    )
    tokens = {
        element["customData"]["atlas_id"]: element["customData"]
        for element in elements
        if element.get("customData", {}).get("visual_grammar") in {"contract-token", "data-card"}
    }
    assert tokens["CON-PLANNER-OUTPUT"]["visual_grammar"] == "contract-token"
    assert tokens["CON-SKILL-CONTRACT"]["visual_grammar"] == "contract-token"
    assert tokens["DAT-OBSERVATION"]["visual_grammar"] == "data-card"
    assert tokens["DAT-VISIBLE-OUTCOME"]["visual_grammar"] == "data-card"
    assert tokens["DAT-CANDIDATE-BODY-VERSION"]["visual_grammar"] == "data-card"
    assert tokens["CON-MEMORY-UPDATE-REQUEST"]["proposal_only"] is True
    assert "BETWEEN MISSION RUNS" in scene_text(elements)
    assert "Dashed cues: orientation / optional path" in scene_text(elements)


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
    public_home = scene(workspace_tree(atlas)[ANATOMY_PATH])
    memory_region = next(
        element
        for element in public_home["elements"]
        if element.get("customData", {}).get("functional_region") == "evidence-memory"
    )
    assert memory_region["link"].startswith(f"[[{DOMAIN_SLICE_PATH.with_suffix('')}|")
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


def test_z2_verifier_home_action_reaches_existing_component_hub(atlas):
    public = scene(workspace_tree(atlas)[ANATOMY_PATH])
    public_verifier = next(
        element
        for element in public["elements"]
        if element.get("customData", {}).get("functional_region") == "verification"
    )
    assert (
        public_verifier["link"].split("|", 1)[0]
        == note_link(atlas.entities["CMP-INDEPENDENT-VERIFIER"]).split("|", 1)[0]
    )
    assert public_verifier["link"].endswith("|Independent Verifier → Overview]]")
    digests = {name: "a" * 64 for name in private_projection.REGISTRY_FILES}
    projected_tree = private_projection.projection_tree(atlas, "b" * 40, digests)
    private = scene(projected_tree[private_projection.ANATOMY].decode())
    private_verifier = next(
        element
        for element in private["elements"]
        if element.get("customData", {}).get("functional_region") == "verification"
    )
    assert private_verifier["link"] == (
        f"[[{private_projection.VERIFIER_HUB_TARGET.with_suffix('')}|"
        "Independent Verifier → Overview]]"
    )
    assert (
        projected_tree[private_projection.HERO_ASSET]
        == workspace_tree(atlas)[HERO_ASSET_PATH].encode()
    )
    assert (
        f"[[{private_projection.OWNED_ROOT / private_projection.HERO_ASSET}]]"
        in projected_tree[private_projection.ANATOMY].decode()
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
