"""Registry-to-vault regression checks; no Obsidian or agent execution is claimed."""

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

import pytest
import yaml

from fh_agent.research_atlas.schema import PREFIXES
from fh_agent.research_atlas.validator import load_registry, validate_registry
from fh_agent.research_atlas.workspace import (
    BASE_PATH,
    BETWEEN_RUNS,
    FOLDERS,
    HOME_PATH,
    MAP_PATH,
    note_link,
    note_path_for,
    parse_frontmatter,
    record_properties,
    validate_links,
    validate_workspace,
    workspace_tree,
    write_workspace,
)

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
BASELINE = "7b4ec2e1497dec50c94b921b61dab42245bf5c90"
REQUIRED_TYPES = {
    "DAT-OBSERVATION": "DataArtifact",
    "CON-CORTEX-CONTEXT": "Contract",
    "CON-PLANNER-OUTPUT": "Contract",
    "CON-SKILL-CONTRACT": "Contract",
    "CON-PRIMITIVE-ACTION": "Contract",
    "DAT-ACTION-RESULT": "DataArtifact",
    "DAT-VISIBLE-OUTCOME": "DataArtifact",
    "CON-MEMORY-UPDATE-REQUEST": "Contract",
    "CON-POST-MORTEM-OUTPUT": "Contract",
    "CMP-REPLAY-BUFFER": "Component",
    "DAT-REPLAY-TRANSITION": "DataArtifact",
}
REQUIRED_SPINE = set(
    """
SYS-AGA ENV-GAME-INSTANCE CMP-SCREEN-CAPTURE DAT-SCREEN-FRAME CMP-VISIBLE-STATE-BRIDGE
CMP-NO-SPOILER-FIREWALL CMP-PERCEPTION DAT-OBSERVATION CMP-TEMPORAL-STATE
CMP-EVIDENCE-LEDGER CMP-MEMORY CMP-MEM-RETRIEVAL IF-MEM-CORTEX DAT-RETRIEVAL-SNAPSHOT
CMP-MEM-EPISODIC CMP-MEM-FACTS CMP-MEM-HYPOTHESES CMP-MEM-TOPOLOGY CMP-MEM-STRATEGY
CMP-SKILL-COMPETENCE CMP-CORTEX CON-CORTEX-CONTEXT CON-PLANNER-OUTPUT IF-CORTEX-MANAGER
CMP-MANAGER CMP-MANAGER-GROUNDING CMP-MANAGER-SCHED-COMP CON-SKILL-CONTRACT CMP-BODY
CMP-BOUNDED-REFLEX CON-PRIMITIVE-ACTION CMP-SAFETY-FILTER CMP-INPUT-EXECUTOR DAT-ACTION-RESULT
DAT-VISIBLE-OUTCOME CMP-INDEPENDENT-VERIFIER CON-VERIFIER-RESULT CON-MEMORY-UPDATE-REQUEST
CON-POST-MORTEM-OUTPUT CMP-REPLAY-BUFFER DAT-REPLAY-TRANSITION CMP-SKILL-TRAINER
DAT-CANDIDATE-BODY-VERSION CMP-BODY-CERTIFICATION
""".split()
)
REQUIRED_VIEWS = {
    "Components by implementation status",
    "Target-only",
    "Partial",
    "Implemented",
    "Verification status",
    "Research Mapping Status",
    "Research Direction Status",
    "Research Questions by Component",
    "Research Questions by Interface",
    "Measurement Points",
    "Open Leads",
    "Decisions / History",
    "Findings with declared contradiction links",
    "Atlas Mapping Incomplete",
}


@pytest.fixture
def atlas():
    return load_registry(ATLAS)


@pytest.fixture
def payloads():
    return [
        yaml.safe_load((ATLAS / "registry" / f).read_text())
        for f in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
    ]


def find_node(payloads, id):
    return next(n for n in payloads[0]["nodes"] if n["id"] == id)


def test_schema_spine_types_and_retained_status(atlas, payloads):
    assert all(p["atlas_schema_version"] == "0.2" for p in payloads)
    assert REQUIRED_SPINE <= atlas.entities.keys()
    for id, kind in REQUIRED_TYPES.items():
        assert atlas.entities[id].type == kind
    assert atlas.entities["SYS-AGA"].name == "Autonomous Game Agent Experiment System"
    assert atlas.entities["SYS-AGA"].technical.implementation_status == "target-only"
    assert atlas.entities["ENV-GAME-INSTANCE"].technical.implementation_status == "target-only"
    assert atlas.ancestors("ENV-GAME-INSTANCE") == frozenset()
    for id in BETWEEN_RUNS | {
        "CMP-BOUNDED-REFLEX",
        "DAT-VISIBLE-OUTCOME",
        "DAT-RETRIEVAL-SNAPSHOT",
    }:
        assert atlas.entities[id].technical.implementation_status == "target-only"
        assert atlas.entities[id].technical.verification_status == "unverified"
    assert "CMP-LLM" not in atlas.entities


@pytest.mark.parametrize("version", ["0.1", "1.0", "0.3"])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_incompatible_schema_rejected(payloads, index, version):
    payloads[index]["atlas_schema_version"] = version
    with pytest.raises(ValueError):
        validate_registry(*payloads)


def test_domain_multiplicity_is_a_view_not_taxonomy(payloads):
    before = validate_registry(*payloads)
    payloads[1]["relationships"].append(
        dict(relation="presented_in_domain", source="CMP-CORTEX", target="DOM-EVIDENCE-MEMORY")
    )
    after = validate_registry(*payloads)
    assert before.ancestors("CMP-CORTEX") == after.ancestors("CMP-CORTEX")
    assert before.entities["CMP-CORTEX"] == after.entities["CMP-CORTEX"]
    assert len(record_properties(after, after.entities["CMP-CORTEX"])["presented_in_domain"]) == 2


def test_main_l2_domain_is_required(payloads):
    payloads[1]["relationships"] = [
        e
        for e in payloads[1]["relationships"]
        if not (e["relation"] == "presented_in_domain" and e["source"] == "CMP-CORTEX")
    ]
    with pytest.raises(ValueError, match="at least one"):
        validate_registry(*payloads)


@pytest.mark.parametrize(
    "id,field,value",
    [
        ("CMP-CORTEX", "atlas_level", "L0"),
        ("CMP-CORTEX", "atlas_level", "L1"),
        ("DOM-COGNITION", "atlas_level", "L2"),
        ("CMP-CORTEX", "overview_order", 0),
        ("CMP-CORTEX", "overview_order", True),
        ("CMP-CORTEX", "overview_order", 1.5),
        ("CMP-MANAGER-SCHED-COMP", "atlas_level", "L2"),
        ("CMP-MANAGER-SCHED-COMP", "overview_visibility", "main"),
    ],
)
def test_presentation_depth_rejected(payloads, id, field, value):
    find_node(payloads, id)[field] = value
    with pytest.raises(ValueError):
        validate_registry(*payloads)


def test_l3_parent_and_authority(payloads, atlas):
    grounding = atlas.entities["CMP-MANAGER-GROUNDING"]
    assert grounding.technical.architecture_authority == "canonical-target"
    assert grounding.atlas_level == "L3"
    for n in atlas.entities.values():
        if n.type == "Component" and n.technical.architecture_authority == "implementation-derived":
            assert n.atlas_level == "L3" and n.overview_visibility == "expansion"
    for e in payloads[1]["relationships"]:
        if e["relation"] == "part_of" and e["source"] == "CMP-MANAGER-GROUNDING":
            e["target"] = "SYS-AGA"
    with pytest.raises(ValueError, match="L3 Component"):
        validate_registry(*payloads)


def test_current_head_claims_have_current_source_evidence(atlas):
    evidence = [
        n for n in atlas.entities.values() if n.type == "Evidence" and n.id.startswith("EVID-48-")
    ]
    assert evidence
    for n in evidence:
        if n.provenance_kind != "github_implementation":
            continue
        assert n.repository == "Planton361/autonomous-game-agent"
        assert n.ref == BASELINE
        assert n.checked_date.isoformat() == "2026-09-09"
        assert (ROOT / n.path).is_file() and (n.symbol or n.line)
    for n in atlas.entities.values():
        if n.type not in {
            "System",
            "Component",
            "Contract",
            "Interface",
            "DataArtifact",
            "Environment",
        }:
            continue
        if n.technical.implementation_status not in {"implemented", "partial"}:
            continue
        assert any(
            e.relation == "supports"
            and e.target == n.id
            and e.source.startswith("EVID-48-")
            and atlas.entities[e.source].provenance_kind == "github_implementation"
            for e in atlas.relationships
        ), n.id


def test_type_folder_mapping_and_safe_paths():
    assert set(FOLDERS) == set(PREFIXES)
    assert FOLDERS == {
        "System": "Home",
        "Domain": "Architecture/Domains",
        "Environment": "Architecture/Environments",
        "Component": "Components",
        "Interface": "Interfaces & Contracts",
        "Contract": "Interfaces & Contracts",
        "DataArtifact": "Data Artifacts",
        "Evidence": "Evidence",
        "ResearchQuestion": "Research Questions",
        "ResearchThread": "Research Threads",
        "Finding": "Findings",
        "Paper": "Literature",
        "Decision": "Decisions",
        "MeasurementPoint": "Measurements",
        "ExperimentLead": "Experiment Leads",
    }
    assert (
        str(note_path_for("CMP-CORTEX", "Component", "Cortex"))
        == "Components/CMP-CORTEX — Cortex.md"
    )
    path = note_path_for("CMP-CORTEX", "Component", "../name/# [bad]|a\\b\n")
    assert path.parent == PurePosixPath("Components")
    assert not any(c in path.name for c in "[]|#\\\n")
    with pytest.raises(ValueError):
        note_path_for("../../unsafe", "Component", "x")


def test_all_records_covered_and_properties_resolve(atlas):
    tree = workspace_tree(atlas)
    notes = {p: parse_frontmatter(s) for p, s in tree.items() if p.suffix == ".md"}
    records = {p: props for p, props in notes.items() if props.get("atlas_generated") is True}
    ids = [props["atlas_id"] for props in records.values()]
    assert len(ids) == len(set(ids)) == len(atlas.entities)
    assert set(ids) == set(atlas.entities)
    for path, props in records.items():
        n = atlas.entities[props["atlas_id"]]
        assert path.name.split(" — ")[0] == n.id
        assert props == record_properties(atlas, n)
        assert "atlas_level" in props
        assert props["registry_schema_version"] == "0.2"
        assert path == note_path_for(n.id, n.type, n.name)
    for kind in ("Evidence", "Environment"):
        assert any(p["atlas_type"] == kind for p in records.values())
    validate_links(tree)


def test_evidence_notes_show_locator_and_both_polarities(payloads):
    payloads[1]["relationships"].append(
        dict(relation="contradicts", source="EVID-48-OCR-LIMIT", target="CMP-PERCEPTION")
    )
    a = validate_registry(*payloads)
    e = a.entities["EVID-48-OCR-LIMIT"]
    content = workspace_tree(a)[note_path_for(e.id, e.type, e.name)]
    assert "## Evidence locator" in content
    assert e.checked_date.isoformat() in content and e.provenance_kind in content
    assert f"/blob/{BASELINE}/" in content and e.symbol in content
    assert "`supports`" in content and "`contradicts`" in content
    assert note_link(a.entities["CMP-PERCEPTION"]) in content


def test_committed_workspace_and_migration(atlas):
    validate_workspace(atlas, ATLAS)
    assert not list((ATLAS / "dossiers").glob("*.md"))
    for p, text in workspace_tree(atlas).items():
        assert "(dossiers/" not in text and "[[dossiers/" not in text
        assert "dossiers/" not in str(p)
    assert not (ATLAS / ".obsidian").exists()


@pytest.mark.parametrize(
    "drift",
    ["unknown", "duplicate", "filename", "properties", "link", "missing", "dossier", "base", "map"],
)
def test_workspace_rejects_drift(atlas, tmp_path, drift):
    write_workspace(atlas, tmp_path)
    node = atlas.entities["CMP-CORTEX"]
    path = tmp_path / note_path_for(node.id, node.type, node.name)
    if drift == "unknown":
        path.write_text(path.read_text().replace("atlas_id: CMP-CORTEX", "atlas_id: CMP-UNKNOWN"))
    elif drift == "duplicate":
        (tmp_path / "extra.md").write_text(path.read_text())
    elif drift == "filename":
        path.rename(path.with_name("CMP-OTHER — Cortex.md"))
    elif drift == "properties":
        path.write_text(
            path.read_text().replace(
                "implementation_status: implemented", "implementation_status: partial"
            )
        )
    elif drift == "link":
        path.write_text(path.read_text() + "\n[[Components/CMP-MISSING|missing]]\n")
    elif drift == "missing":
        path.unlink()
    elif drift == "dossier":
        (tmp_path / "dossiers").mkdir()
        (tmp_path / "dossiers/CMP-CORTEX.md").write_text("stale")
    elif drift == "base":
        (tmp_path / BASE_PATH).write_text("views: []\n")
    else:
        (tmp_path / MAP_PATH).write_text("broken map")
    with pytest.raises(ValueError):
        validate_workspace(atlas, tmp_path)


def test_regeneration_replaces_drift_preserves_authored_notes(atlas, tmp_path):
    write_workspace(atlas, tmp_path)
    n = atlas.entities["CMP-CORTEX"]
    path = tmp_path / note_path_for(n.id, n.type, n.name)
    path.write_text(
        path.read_text().replace(
            "implementation_status: implemented", "implementation_status: partial"
        )
    )
    proposal = tmp_path / "proposal.md"
    proposal.write_text("Authored proposal, not authoritative.\n")
    write_workspace(atlas, tmp_path)
    validate_workspace(atlas, tmp_path)
    assert proposal.read_text() == "Authored proposal, not authoritative.\n"


def test_only_exact_private_base_source_is_exempt_from_public_base_count(atlas, tmp_path):
    write_workspace(atlas, tmp_path)
    source = tmp_path / "Wiki Views/Research Wiki Direct Views.base"
    source.parent.mkdir()
    original = (ATLAS / "Wiki Views/Research Wiki Direct Views.base").read_bytes()
    source.write_bytes(original)
    validate_workspace(atlas, tmp_path)
    write_workspace(atlas, tmp_path)
    assert source.read_bytes() == original
    extra = source.with_name("unexpected.base")
    extra.write_text("views: []\n")
    with pytest.raises(ValueError, match="Exactly one central Base"):
        validate_workspace(atlas, tmp_path)


def test_rename_regenerates_all_links_without_changing_relations(payloads, tmp_path):
    before = validate_registry(*payloads)
    write_workspace(before, tmp_path)
    old = before.entities["CMP-CORTEX"]
    old_path = note_path_for(old.id, old.type, old.name)
    relationships = copy.deepcopy(payloads[1])
    find_node(payloads, old.id)["name"] = "Renamed Cognition"
    after = validate_registry(*payloads)
    assert after.entities[old.id].id == old.id
    assert after.relationships == before.relationships and payloads[1] == relationships
    write_workspace(after, tmp_path)
    new = after.entities[old.id]
    new_path = note_path_for(new.id, new.type, new.name)
    assert new_path != old_path and not (tmp_path / old_path).exists()
    assert (tmp_path / new_path).exists()
    tree = workspace_tree(after)
    assert all(str(old_path.with_suffix("")) not in text for text in tree.values())
    assert any(note_link(new) in text for path, text in tree.items() if path != new_path)
    validate_workspace(after, tmp_path)


def test_base_contract_isolated_and_views(atlas):
    tree = workspace_tree(atlas)
    base = yaml.safe_load(tree[BASE_PATH])
    assert base["filters"] == {"and": ["note.atlas_generated == true", "!note.atlas_id.isEmpty()"]}
    assert {v["name"] for v in base["views"]} == REQUIRED_VIEWS
    declared = next(
        v for v in base["views"] if v["name"] == "Findings with declared contradiction links"
    )
    assert declared["filters"] == {
        "and": [
            'note.atlas_type == "Finding"',
            "!note.contradicted_by.isEmpty() || !note.contradicts.isEmpty()",
        ]
    }
    assert all(v["type"] == "table" for v in base["views"])
    # Base references only generated properties, including lifecycle relation projections.
    properties = set().union(*(record_properties(atlas, n) for n in atlas.entities.values()))
    assert set(re.findall(r"note\.([a-z_]+)", tree[BASE_PATH])) <= properties
    for path in (HOME_PATH, MAP_PATH, PurePosixPath("overview.md")):
        assert parse_frontmatter(tree[path]).get("atlas_generated") is not True
    assert (
        parse_frontmatter("---\natlas_generated: false\natlas_id: proposal\n---\n")[
            "atlas_generated"
        ]
        is False
    )
    assert not parse_frontmatter("Unrelated prose")
    assert not any(
        term in tree[BASE_PATH].lower()
        for term in (
            "evidence needing review",
            "exhaustion",
            "gap_confidence",
            "saturation",
            "today()",
            "now()",
        )
    )
    assert "formulas" not in base


def scene_from(text):
    # Matches the public plugin's uncompressed Drawing section, not a generic JSON fence.
    match = re.search(r"\n## Drawing\n[^`]*```json\n([\s\S]*?)```\n", text)
    assert match
    return json.loads(match.group(1))


def test_excalidraw_container_nodes_and_links(atlas):
    tree = workspace_tree(atlas)
    text = tree[MAP_PATH]
    assert parse_frontmatter(text)["excalidraw-plugin"] == "parsed"
    assert "# Excalidraw Data\n\n## Text Elements\n" in text
    assert "## Element Links\n" in text and text.endswith("%%\n")
    scene = scene_from(text)
    assert scene["type"] == "excalidraw" and scene["version"] == 2
    assert scene["files"] == {}
    elements = scene["elements"]
    assert len({el["id"] for el in elements}) == len(elements)
    assert {el["type"] for el in elements} <= {"rectangle", "text", "arrow"}
    nodes = {
        el["customData"]["atlas_id"]: el
        for el in elements
        if "atlas_id" in el.get("customData", {})
    }
    assert EXPECTED_MAP_IDS == nodes.keys()
    for id, el in nodes.items():
        assert el["link"] == note_link(atlas.entities[id])
    for el in elements:
        if el["type"] == "text":
            assert f"{el['rawText']} ^{el['id']}" in text
        if el["link"]:
            assert f"{el['id']}: {el['link']}" in text
        if el["type"] == "arrow":
            assert el["customData"]["atlas_relation"] in [
                e.model_dump(exclude_none=True) for e in atlas.relationships
            ]
    assert "CMP-LLM" not in text
    validate_links(tree)


def inside(inner, outer):
    return (
        outer["x"] <= inner["x"]
        and outer["y"] <= inner["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def test_map_semantic_boundaries(atlas):
    text = workspace_tree(atlas)[MAP_PATH]
    elements = scene_from(text)["elements"]
    nodes = {
        el["customData"]["atlas_id"]: el
        for el in elements
        if "atlas_id" in el.get("customData", {})
    }
    boundaries = [
        el for el in elements if el["type"] == "rectangle" and el["strokeStyle"] == "dashed"
    ]
    agent, between = boundaries[:2]
    assert not inside(nodes["ENV-GAME-INSTANCE"], agent)
    assert inside(nodes["CMP-BOUNDED-REFLEX"], nodes["CMP-BODY"])
    assert inside(nodes["CMP-MANAGER-GROUNDING"], nodes["CMP-MANAGER"])
    assert not inside(nodes["CMP-MEMORY"], nodes["CMP-CORTEX"])
    assert (
        nodes["CMP-INDEPENDENT-VERIFIER"]["x"]
        > nodes["CMP-CORTEX"]["x"] + nodes["CMP-CORTEX"]["width"]
    )
    assert "Outside Cortex decision path" in text and "Reflection after verification" in text
    assert "Between runs only" in text
    for id in BETWEEN_RUNS:
        assert inside(nodes[id], between) and not inside(nodes[id], agent)


def test_deterministic_tree_including_map_after_registry_reordering(payloads):
    before = workspace_tree(validate_registry(*payloads))
    for payload, key in zip(payloads, ("nodes", "relationships", "evidence"), strict=True):
        payload[key].reverse()
    after = workspace_tree(validate_registry(*payloads))
    assert before == after
    assert not any(str(p).startswith(("../", "/")) for p in after)


def test_missing_link_rejected(atlas):
    tree = workspace_tree(atlas)
    tree[HOME_PATH] += "\n[[Components/CMP-MISSING|missing]]"
    with pytest.raises(ValueError, match="Unresolved generated link"):
        validate_links(tree)


def test_historical_evidence_records_are_immutable(payloads):
    historical = [e for e in payloads[2]["evidence"] if not e["id"].startswith("EVID-48-")]
    assert len(historical) == 22
    assert (
        hashlib.sha256(json.dumps(historical, sort_keys=True).encode()).hexdigest()
        == "baf7205576fffbd87042c3b2eb7db6ccd0748659288911d7b8fb304ad7cd880e"
    )


def test_all_v01_stable_ids_preserved(atlas):
    old_ids = [
        "CMP-CORTEX",
        "CMP-MANAGER",
        "CMP-MEM-RETRIEVAL",
        "CON-CORTEX-CONTEXT",
        "CON-PLANNER-OUTPUT",
        "CON-SKILL-CONTRACT",
        "DAT-RETRIEVAL-SNAPSHOT",
        "DEC-ATLAS-PILOT-001",
        "DOM-ACTION-SAFETY",
        "DOM-COGNITION",
        "DOM-ENV-ACQUISITION",
        "DOM-EVIDENCE-MEMORY",
        "DOM-EXECUTIVE",
        "DOM-OBS-INTEGRITY-STATE",
        "DOM-VERIFY-LEARN",
        "EVID-ATLAS-APPROVAL-001",
        "EVID-CANON-CORTEX",
        "EVID-CANON-MANAGER",
        "EVID-CANON-MEM",
        "EVID-GH-CORTEX-CONTEXT",
        "EVID-GH-CORTEX-INTEGRATION",
        "EVID-GH-CORTEX-OUTPUT",
        "EVID-GH-CORTEX-PLAN",
        "EVID-GH-CORTEX-PROVIDER",
        "EVID-GH-CORTEX-TEST",
        "EVID-GH-MANAGER-GROUND",
        "EVID-GH-MANAGER-INTEGRATION",
        "EVID-GH-MANAGER-ORCHESTRATOR",
        "EVID-GH-MANAGER-SCHEDULING-TEST",
        "EVID-GH-MANAGER-SPEC",
        "EVID-GH-MANAGER-TASK",
        "EVID-GH-MANAGER-TEST",
        "EVID-GH-MEM-CONTEXT",
        "EVID-GH-MEM-DB",
        "EVID-GH-MEM-FACTS",
        "EVID-GH-MEM-TEST",
        "EVID-PROGRAM-001",
        "IF-CORTEX-MANAGER",
        "IF-MEM-CORTEX",
        "MEAS-CORTEX-PROPOSAL-001",
        "MEAS-MANAGER-DISPOSITION-001",
        "MEAS-RETRIEVAL-DELIVERY-001",
        "MEAS-VERIFIED-OUTCOME-001",
        "RQ-PROGRAM-AB-001",
        "SYS-AGA",
        "THREAD-EXPERIENCE-TO-ACTION-001",
    ]
    assert set(old_ids) <= atlas.entities.keys()


def test_workspace_covers_closed_types_and_future_overlays(payloads):
    for kind in ("Paper", "Finding", "ExperimentLead"):
        payloads[0]["nodes"].append(
            dict(
                id=PREFIXES[kind] + "-FIXTURE",
                type=kind,
                name=kind,
                description="Synthetic fixture only",
            )
        )
    payloads[1]["relationships"].extend(
        [
            dict(relation="contradicts", source="FIND-FIXTURE", target="FIND-FIXTURE"),
            dict(
                relation="related_to_research_question",
                source="IF-MEM-CORTEX",
                target="RQ-PROGRAM-AB-001",
            ),
        ]
    )
    a = validate_registry(*payloads)
    tree = workspace_tree(a)
    notes = [parse_frontmatter(text) for text in tree.values()]
    assert {n["atlas_type"] for n in notes if n.get("atlas_generated")} == set(PREFIXES)
    finding = a.entities["FIND-FIXTURE"]
    props = record_properties(a, finding)
    assert props["contradicted_by"] == [note_link(finding)]
    rq = a.entities["RQ-PROGRAM-AB-001"]
    assert record_properties(a, rq)["research_interfaces"] == [
        note_link(a.entities["IF-MEM-CORTEX"])
    ]
    validate_links(tree)


@pytest.mark.parametrize("drift", ["base_property", "base_filter", "map_node", "map_arrow"])
def test_generated_tree_contract_rejects_invalid_views(atlas, drift):
    from fh_agent.research_atlas.workspace import validate_workspace_tree

    tree = workspace_tree(atlas)
    if drift == "base_property":
        tree[BASE_PATH] = tree[BASE_PATH].replace(
            "note.implementation_status", "note.fabricated_status"
        )
    elif drift == "base_filter":
        tree[BASE_PATH] = tree[BASE_PATH].replace(
            "note.atlas_generated == true", "note.atlas_generated != true"
        )
    else:
        scene = scene_from(tree[MAP_PATH])
        if drift == "map_node":
            scene["elements"] = [
                e
                for e in scene["elements"]
                if e.get("customData", {}).get("atlas_id") != "CMP-CORTEX"
            ]
        else:
            arrow = next(e for e in scene["elements"] if e["type"] == "arrow")
            arrow["customData"]["atlas_relation"]["relation"] = "related_to"
        before, drawing = tree[MAP_PATH].split("```json\n", 1)
        _, after = drawing.split("\n```", 1)
        tree[MAP_PATH] = before + "```json\n" + json.dumps(scene) + "\n```" + after
    with pytest.raises(ValueError):
        validate_workspace_tree(atlas, tree)


EXPECTED_MAP_IDS = set(
    """
SYS-AGA ENV-GAME-INSTANCE CMP-SCREEN-CAPTURE CMP-VISIBLE-STATE-BRIDGE
CMP-NO-SPOILER-FIREWALL CMP-PERCEPTION DAT-OBSERVATION CMP-TEMPORAL-STATE
CMP-EVIDENCE-LEDGER CMP-MEMORY CMP-MEM-RETRIEVAL CMP-CORTEX CON-PLANNER-OUTPUT
CMP-MANAGER CMP-MANAGER-GROUNDING CON-SKILL-CONTRACT CMP-BODY CMP-BOUNDED-REFLEX
CMP-SAFETY-FILTER CMP-INPUT-EXECUTOR DAT-VISIBLE-OUTCOME CMP-INDEPENDENT-VERIFIER
CMP-REPLAY-BUFFER CMP-SKILL-TRAINER DAT-CANDIDATE-BODY-VERSION CMP-BODY-CERTIFICATION
""".split()
)


@pytest.mark.parametrize("id", ["CMP-CORTEX", "CON-PLANNER-OUTPUT", "DAT-OBSERVATION"])
def test_l2_expansion_with_known_box_stays_l2_and_off_map(payloads, id):
    from fh_agent.research_atlas.workspace import MAP_BOXES, map_record_ids

    assert id in MAP_BOXES
    find_node(payloads, id)["overview_visibility"] = "expansion"
    a = validate_registry(*payloads)
    assert a.entities[id].atlas_level == "L2"
    assert id not in map_record_ids(a)
    text = workspace_tree(a)[MAP_PATH]
    assert id not in {e.get("customData", {}).get("atlas_id") for e in scene_from(text)["elements"]}


def test_compact_map_excludes_measurements_and_expansion_only(atlas):
    from fh_agent.research_atlas.workspace import map_record_ids

    ids = map_record_ids(atlas)
    assert ids == EXPECTED_MAP_IDS
    for id in ids:
        node = atlas.entities[id]
        assert node.type != "MeasurementPoint"
        if id not in {"CMP-MANAGER-GROUNDING", "CMP-BOUNDED-REFLEX"}:
            assert node.overview_visibility == "main"


def test_all_technical_detail_has_domains(atlas):
    for n in atlas.entities.values():
        if n.atlas_level in {"L2", "L3"}:
            assert record_properties(atlas, n)["presented_in_domain"], n.id


@pytest.mark.parametrize(
    "id",
    [
        "CON-CORTEX-CONTEXT",
        "DAT-SCREEN-FRAME",
        "ENV-GAME-INSTANCE",
        "CMP-MEM-FACTS",
        "MEAS-VERIFIED-OUTCOME-001",
    ],
)
def test_detail_domain_required(payloads, id):
    payloads[1]["relationships"] = [
        e
        for e in payloads[1]["relationships"]
        if not (e["relation"] == "presented_in_domain" and e["source"] == id)
    ]
    with pytest.raises(ValueError, match="at least one"):
        validate_registry(*payloads)


def test_changing_detail_domain_preserves_all_ancestry(payloads):
    before = validate_registry(*payloads)
    for e in payloads[1]["relationships"]:
        if e["relation"] == "presented_in_domain" and e["source"] == "CMP-MEM-FACTS":
            e["target"] = "DOM-COGNITION"
    after = validate_registry(*payloads)
    assert {id: before.ancestors(id) for id in before.entities} == {
        id: after.ancestors(id) for id in after.entities
    }


def test_cortex_human_dossier_and_empty_overlay_sections(atlas):
    from fh_agent.research_atlas.workspace import render_record

    text = render_record(atlas, atlas.entities["CMP-CORTEX"])
    for heading in [
        "Classification",
        "Technical structure",
        "Presentation",
        "Inputs and outputs",
        "Interfaces and contracts",
        "Data artifacts",
        "Measurement points",
        "Evidence",
        "Research questions",
        "Research threads",
        "Papers",
        "Findings and contradictions",
        "Decisions",
        "Experiment leads",
        "History",
        "Review / proposals",
    ]:
        assert "## " + heading + "\n" in text
    for heading in ["Papers", "Findings and contradictions", "Experiment leads"]:
        assert "## " + heading + "\n\nNone mapped." in text
    body = text.split("## Evidence\n", 1)[1].split("\n## ", 1)[0]
    assert note_link(atlas.entities["EVID-CANON-CORTEX"]) in body


def base_fixture_matches(view, props):
    # Evaluate only the emitted comparison/empty/boolean subset, against synthetic Properties.
    expressions = []
    for expression in view["filters"]["and"]:
        expression = re.sub(
            r"!note\.(\w+)\.isEmpty\(\)", lambda m: str(bool(props.get(m[1]))), expression
        )
        expression = re.sub(
            r'note\.(\w+) == "([^"]+)"', lambda m: str(props.get(m[1]) == m[2]), expression
        )
        expression = expression.replace("||", "or").replace("&&", "and")
        assert re.fullmatch(r"[TrueFalsondr ()]+", expression)
        expressions.append(eval(expression, {"__builtins__": {}}))
    return all(expressions)


@pytest.mark.parametrize(
    "direction,actionable,historical",
    [
        ("open-lead", True, False),
        ("needs-closure", True, False),
        ("active-candidate", True, False),
        ("killed", False, True),
        ("deprioritized", False, True),
    ],
)
def test_base_lead_action_and_history_fixtures(payloads, direction, actionable, historical):
    from fh_agent.research_atlas.workspace import render_base

    payloads[0]["nodes"].append(
        dict(
            id="LEAD-REVIEW-FIXTURE",
            type="ExperimentLead",
            name="Review fixture",
            description="Synthetic only",
            research_direction=direction,
        )
    )
    a = validate_registry(*payloads)
    props = record_properties(a, a.entities["LEAD-REVIEW-FIXTURE"])
    views = {v["name"]: v for v in yaml.safe_load(render_base())["views"]}
    assert base_fixture_matches(views["Open Leads"], props) is actionable
    assert base_fixture_matches(views["Decisions / History"], props) is historical
    props["atlas_type"] = "Component"
    assert not base_fixture_matches(views["Open Leads"], props)
    assert not base_fixture_matches(views["Decisions / History"], props)
