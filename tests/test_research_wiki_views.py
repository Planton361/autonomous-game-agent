"""Direct views only, using synthetic Git checkouts/vaults; never real private data."""

import copy
import hashlib
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
import yaml
from pydantic import ValidationError
from test_research_wiki_projection import commit, filesystem_state, git, snapshot, write_note

from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.assembly_scopes import PRIVATE_OBSERVE_SCOPE_PATH
from fh_agent.research_atlas.schema import Relationship
from fh_agent.research_atlas.validator import (
    Atlas,
    load_registry,
    validated_source_schema_version,
)
from fh_agent.research_atlas.wiki_schema import Process, validate_wiki_records
from fh_agent.research_atlas.workspace import parse_frontmatter, render_base, workspace_tree

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
SOURCE = ROOT / views.DIRECT_SOURCE
SEEDS = ATLAS / "Process Seeds"
MATRIX = ATLAS / "Wiki Views/Direct View Capability Matrix.md"
ROLES = (
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
)
DIRECT_VIEWS = {
    "Processes": "process",
    "Topics / Methods": "topic",
    "Paper identities": "paper",
    "Reading Notes by reading depth": "reading_note",
    "Reading Notes by document maturity": "reading_note",
    "Findings by review state": "finding",
    "Findings by claim origin": "finding",
    "Research Questions by stage / decision state": "research_question",
    "Experiment Leads by stage / decision state": "experiment_lead",
    "Search Records inventory": "search_record",
    "Decisions by state / scope": "decision_draft",
    "Syntheses by document maturity": "synthesis",
}
PROCESS_WARNINGS = {
    "PROC-OBSERVATION-CORTEX-CONTEXT-001": (
        "Target/partial paths are not automatically implemented."
    ),
    "PROC-CORTEX-MANAGER-CONTRACT-001": "Cortex never owns primitive control.",
    "PROC-CONTRACT-EXECUTION-REPLAN-001": "Process order is not a technical hierarchy.",
    "PROC-VISIBLE-OUTCOME-VERIFY-001": "Screenshot change is not success.",
    "PROC-EXPERIENCE-REUSE-001": "Wiki contents do not enter Agent Memory.",
    "PROC-BETWEEN-RUN-LEARNING-001": (
        "The between-run target path is not a claim of current implementation."
    ),
    "PROC-SCIENTIFIC-EVALUATION-001": "Research workflow is not a Runtime Component Chain.",
}
REQUIRED_CAPABILITIES = {
    "Literature by Component — with role": "direct-partial",
    "Literature by Process": "direct-partial",
    "Literature by RQ": "direct-partial",
    "Methods/Baselines": "direct-partial",
    "Environment/Outcome": "requires-structured-contract/review",
    "Findings by Conditions": "requires-structured-contract/review",
    "Contradictions/Heterogeneity": "requires-structured-contract/review",
    "Open Questions": "direct-ready",
    "Candidate History": "requires-derived-index",
    "Search Coverage": "direct-partial",
    "Source Verification Queue": "direct-ready",
    "Decision Lineage": "requires-derived-index",
    "Evidence Profiles": "requires-structured-contract/review",
    "Atlas Mapping Incomplete": "direct-ready",
    "Synthesis comparison view": "requires-structured-contract/review",
}
ENVELOPE = dict(
    wiki_schema_version="0.1",
    epistemic_schema_version="0.1",
    wiki_id="PROC-SYNTHETIC-001",
    doc_type="process",
    title="Synthetic view fixture",
    record_version=1,
    document_maturity="draft",
    privacy="private",
    export_policy="deny",
    atlas_refs=["CMP-CORTEX"],
)


@pytest.fixture
def setup(tmp_path):
    repo = tmp_path / "public"
    repo.mkdir()
    shutil.copytree(ATLAS / "registry", repo / "docs/research-atlas/registry")
    for relative in (views.PUBLIC_SOURCE, views.DIRECT_SOURCE, views.CATALOG_PATH):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    code = repo / "src/fh_agent/research_atlas/source.py"
    code.parent.mkdir(parents=True)
    code.write_text("# synthetic tracked source\n")
    asset = repo / technical.HERO_SOURCE
    asset.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / technical.HERO_SOURCE, asset)
    git(repo, "init", "--quiet")
    sha = commit(repo)
    vault = tmp_path / "private"
    vault.mkdir()
    (vault / ".research-wiki-private").write_text(
        'research_wiki_private_version: "1.0"\nproject: ' + views.REPOSITORY + "\n"
    )
    write_note(vault / "authored/process.md", ENVELOPE)
    (vault / "authored/attachment.bin").write_bytes(bytes(range(256)))
    (vault / "ordinary.md").write_text("SYNTHETIC-PRIVATE-VIEWS-SECRET\n")
    technical.project(repo, vault, sha)
    return repo, vault, sha


def remove_g4_payloads(vault, manifest):
    """Historical manifest fixtures cannot contain later G4 generated files."""
    for relative in views.SOURCE_PAYLOADS:
        (vault / views.OWNED_ROOT / relative).unlink(missing_ok=True)
    manifest["owned_files"] = [
        item
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]) not in views.SOURCE_PAYLOADS
    ]


def derived(vault):
    return vault / views.OWNED_ROOT


def outside_owned(vault):
    return {
        str(p.relative_to(vault)): technical.digest(p.read_bytes())
        for p in vault.rglob("*")
        if p.is_file() and not p.is_relative_to(derived(vault))
    }


def tree_digest(tree):
    digest = hashlib.sha256()
    for path, payload in sorted(tree.items(), key=lambda item: str(item[0])):
        digest.update(str(path).encode())
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return digest.hexdigest()


def change_manifest(vault, edit):
    path = derived(vault) / views.MANIFEST
    data = yaml.safe_load(path.read_text())
    edit(data)
    path.write_text(technical.yaml_text(data))


def install_legacy_workbench_paths(vault):
    root = derived(vault)
    manifest_path = root / views.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_text())
    pairs = (
        (views.MEMORY_WORKBENCH, views.LEGACY_MEMORY_WORKBENCH),
        (views.VERIFIER_WORKBENCH, views.LEGACY_VERIFIER_WORKBENCH),
    )
    atlas = load_registry(ATLAS)
    for current, legacy in pairs:
        identity = next(
            identity
            for identity, hub in views.COMPONENT_HUB_PATHS.items()
            if hub.overview == current
        )
        metadata = views._identity_page_generated_metadata((root / current).read_text(), current)
        data = views.render_component_hub_view(
            metadata["source_commit"],
            atlas,
            views._component_hub_model(atlas, identity),
            "overview",
            views.make_snapshot([], atlas),
            False,
        )
        (root / current).unlink()
        (root / legacy).write_bytes(data)
        item = next(item for item in manifest["owned_files"] if item["path"] == str(current))
        item["path"] = str(legacy)
        item["sha256"] = technical.digest(data)
    manifest["owned_files"].sort(key=lambda item: item["path"])
    manifest_path.write_text(technical.yaml_text(manifest))


def manifest_owned_item(relative, data):
    path = PurePosixPath(relative)
    item = {
        "path": str(path),
        "sha256": technical.digest(data),
        "ownership": (
            views.OBSIDIAN_BASE_OWNERSHIP if path.suffix == ".base" else views.STRICT_OWNERSHIP
        ),
    }
    if path.suffix == ".base":
        item["semantic_sha256"] = views._base_semantic_digest(data)
    return item


def remove_w07_landscape_for_legacy_manifest(vault, manifest):
    for item in list(manifest["owned_files"]):
        if item["path"] == str(views.RESEARCH_LANDSCAPE):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)


def remove_observe_scope_for_legacy_manifest(vault, manifest):
    for item in list(manifest["owned_files"]):
        if item["path"] == str(views.OBSERVE_SCOPE):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)


def remove_identity_pages_for_legacy_manifest(vault, manifest):
    for item in list(manifest["owned_files"]):
        if PurePosixPath(item["path"]).parent == PurePosixPath("identity-pages"):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)


def install_v29_stable_id_identity_paths(vault, atlas):
    """Model the already-applied v2.9 owner marker and generic ID paths."""
    root = derived(vault)
    manifest_path = root / views.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_text())
    old_paths = {}
    for identity, current in views.identity_page_paths(atlas).items():
        if identity in views.COMPONENT_HUB_PATHS:
            continue
        previous = (
            current
            if identity in views.IDENTITY_PAGE_PATHS
            else PurePosixPath("identity-pages") / f"{identity}.md"
        )
        rendered = (root / current).read_text()
        visible, _, _ = rendered.partition(views.IDENTITY_PAGE_METADATA_MARKER)
        metadata = views._identity_page_generated_metadata(rendered, current)
        metadata.pop("identity_page_path")
        metadata["identity_page_schema_version"] = "1.0"
        prior_bytes = (
            visible + views.IDENTITY_PAGE_METADATA_MARKER + technical.yaml_text(metadata) + "-->\n"
        ).encode()
        if previous != current:
            (root / current).unlink()
        (root / previous).write_bytes(prior_bytes)
        item = next(item for item in manifest["owned_files"] if item["path"] == str(current))
        item["path"] = str(previous)
        item["sha256"] = technical.digest(prior_bytes)
        old_paths[identity] = previous
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.9"
    manifest["reference_index_schema_version"] = "1.0"
    manifest["owned_files"].sort(key=lambda item: item["path"])
    manifest_path.write_text(technical.yaml_text(manifest))
    return old_paths


def downgrade_manifest_to_v26(vault):
    path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(path.read_text())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.6"
    manifest["reference_index_schema_version"] = "1.0"
    remove_observe_scope_for_legacy_manifest(vault, manifest)
    remove_identity_pages_for_legacy_manifest(vault, manifest)
    path.write_text(technical.yaml_text(manifest))


def downgrade_manifest_to_v2(vault):
    path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(path.read_text())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.0"
    manifest["reference_index_schema_version"] = "1.0"
    remove_w07_landscape_for_legacy_manifest(vault, manifest)
    remove_observe_scope_for_legacy_manifest(vault, manifest)
    remove_identity_pages_for_legacy_manifest(vault, manifest)
    # Reconstruct the old finite output set before testing a v2.0 migration.
    for item in list(manifest["owned_files"]):
        if (
            item["path"] == str(views.HIERARCHY)
            or item["path"].startswith("hierarchy/")
            or PurePosixPath(item["path"]) in views.K3_HUB_CHILD_PAYLOADS
            or PurePosixPath(item["path"]) in views.TECHNICAL_DETAIL_PAYLOADS
        ):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)
    for item in manifest["owned_files"]:
        item.pop("ownership")
        item.pop("semantic_sha256", None)
    path.write_text(technical.yaml_text(manifest))


def downgrade_manifest_to_v22(vault):
    path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(path.read_text())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.2"
    manifest["reference_index_schema_version"] = "1.0"
    remove_w07_landscape_for_legacy_manifest(vault, manifest)
    remove_observe_scope_for_legacy_manifest(vault, manifest)
    remove_identity_pages_for_legacy_manifest(vault, manifest)
    for item in list(manifest["owned_files"]):
        if (
            PurePosixPath(item["path"]) in views.K3_HUB_CHILD_PAYLOADS
            or PurePosixPath(item["path"]) in views.TECHNICAL_DETAIL_PAYLOADS
        ):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)
    path.write_text(technical.yaml_text(manifest))


def install_pre_w02_v21(vault):
    path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(path.read_text())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.1"
    manifest["reference_index_schema_version"] = "1.0"
    remove_w07_landscape_for_legacy_manifest(vault, manifest)
    remove_observe_scope_for_legacy_manifest(vault, manifest)
    remove_identity_pages_for_legacy_manifest(vault, manifest)
    for item in list(manifest["owned_files"]):
        if (
            item["path"] == str(views.HIERARCHY)
            or item["path"].startswith("hierarchy/")
            or PurePosixPath(item["path"]) in views.K3_HUB_CHILD_PAYLOADS
            or PurePosixPath(item["path"]) in views.TECHNICAL_DETAIL_PAYLOADS
        ):
            (derived(vault) / item["path"]).unlink()
            manifest["owned_files"].remove(item)
    path.write_text(technical.yaml_text(manifest))


def normalize_owned_bases_as_obsidian(vault):
    """Reproduce actual Obsidian save: comments/formatting change and note IDs shorten."""
    for relative in views.OBSIDIAN_MANAGED_BASES:
        path = derived(vault) / relative
        base = yaml.safe_load(path.read_bytes())
        for view in base["views"]:
            if "order" in view:
                view["order"] = [
                    item.removeprefix("note.") if isinstance(item, str) else item
                    for item in view["order"]
                ]
            if "groupBy" in view:
                view["groupBy"]["property"] = view["groupBy"]["property"].removeprefix("note.")
            for item in view.get("sort", []):
                item["property"] = item["property"].removeprefix("note.")
        path.write_text(yaml.safe_dump(base, allow_unicode=True, sort_keys=True))


@pytest.fixture
def obsidian_normalized_bases(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    normalize_owned_bases_as_obsidian(vault)
    return repo, vault, sha, tree


def assert_no_mutation(setup, action, match=None):
    repo, vault, _ = setup
    before = filesystem_state(vault), snapshot(repo)
    with pytest.raises(technical.ProjectionError, match=match):
        action()
    assert (filesystem_state(vault), snapshot(repo)) == before


def test_complete_determinism_authored_and_technical_invariance(setup):
    repo, vault, sha = setup
    before = outside_owned(vault)
    public_before = snapshot(repo)
    tree = views.project(repo, vault, sha)
    assert set(tree) == {
        views.TECHNICAL_BASE,
        views.DIRECT_BASE,
        views.INDEX,
        views.MANIFEST,
        views.REFERENCE_INDEX,
        views.NAVIGATION,
        views.HIERARCHY,
    } | set(views.SOURCE_PAYLOADS) | set(views.K3_PAYLOADS) | set(views.W10_PAYLOADS) | set(
        views.OBSERVE_SCOPE_PAYLOADS
    ) | set(views.TECHNICAL_DETAIL_PAYLOADS) | set(
        views.identity_page_paths(load_registry(repo / "docs/research-atlas")).values()
    ) | set(views.hierarchy_tree(sha, load_registry(repo / "docs/research-atlas")))
    assert views.OWNED_ROOT == PurePosixPath("_generated/derived")
    assert outside_owned(vault) == before
    first = snapshot(derived(vault))
    assert views.project(repo, vault, sha) == tree
    assert snapshot(derived(vault)) == first
    assert views.project(repo, vault, sha, check=True) == tree
    assert outside_owned(vault) == before and snapshot(repo) == public_before
    assert all(str(vault).encode() not in data for data in tree.values())
    assert all(b"SYNTHETIC-PRIVATE-VIEWS-SECRET" not in data for data in tree.values())
    assert not any("timestamp" in data.decode().lower() for data in tree.values())


def test_manifest_exact_commit_schema_digests_and_sources(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    manifest = yaml.safe_load(tree[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.14"
    assert manifest["reference_index_schema_version"] == "1.2"
    assert (
        manifest["private_input_fingerprint"]
        == yaml.safe_load(tree[views.REFERENCE_INDEX])["private_input_fingerprint"]
    )
    assert manifest["generated_by"] == views.OWNER == "research-wiki-derived"
    assert manifest["source_repository"] == "Planton361/autonomous-game-agent"
    assert manifest["source_commit"] == sha == git(repo, "rev-parse", "HEAD")
    assert manifest["source_atlas_schema"] == "0.3"
    assert manifest["source_sha256"] == {
        "public_atlas_base": technical.digest((repo / views.PUBLIC_SOURCE).read_bytes()),
        "research_wiki_direct_base": technical.digest((repo / views.DIRECT_SOURCE).read_bytes()),
    }
    assert manifest["owned_files"] == [
        manifest_owned_item(p, data) for p, data in sorted(tree.items()) if p != views.MANIFEST
    ]
    public_base = yaml.safe_load((repo / views.PUBLIC_SOURCE).read_bytes())
    private_base = yaml.safe_load(tree[views.TECHNICAL_BASE])
    assert private_base.pop("filters") == {
        "and": ['file.inFolder("_generated/technical-atlas")', public_base.pop("filters")]
    }
    assert private_base == public_base
    assert tree[views.DIRECT_BASE] == views.BASE_OWNER.encode() + SOURCE.read_bytes()
    text = tree[views.INDEX].decode()
    for p in (views.DIRECT_BASE, views.TECHNICAL_BASE):
        assert f"[[{views.OWNED_ROOT / p}|" in text
    assert sha in text and "Process%20Seeds" in text and "Capability%20Matrix.md" in text


def test_current_03_private_views_report_source_schema_truthfully():
    atlas = load_registry(ATLAS)
    commit = "a" * 40
    snapshot = views.make_snapshot([], atlas)
    reference = views.build_index(atlas, snapshot, commit)
    tree = views.reference_views_tree(
        commit,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        {},
        snapshot,
        False,
    )
    manifest = yaml.safe_load(tree[views.MANIFEST])
    index_payload = yaml.safe_load(tree[views.REFERENCE_INDEX])

    assert manifest["source_atlas_schema"] == "0.3"
    assert index_payload["source_atlas_schema"] == "0.3"
    assert tree_digest(tree) == "bc343814e7e9c56cd2404092d3bab8df85197e254131a71b502107a3bf80f4e4"


def test_current_03_source_schema_propagates_through_private_views():
    payloads = [
        yaml.safe_load((ATLAS / "registry" / name).read_text(encoding="utf-8"))
        for name in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
    ]
    source_schema = validated_source_schema_version(*payloads)
    atlas = load_registry(ATLAS)
    assert atlas.source_atlas_schema == source_schema == "0.3"
    commit = "a" * 40
    snapshot = views.make_snapshot([], atlas)
    reference = views.build_index(atlas, snapshot, commit)
    tree = views.reference_views_tree(
        commit,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        {},
        snapshot,
        False,
    )
    manifest = yaml.safe_load(tree[views.MANIFEST])
    index_payload = yaml.safe_load(tree[views.REFERENCE_INDEX])

    assert manifest["source_atlas_schema"] == "0.3"
    assert index_payload["source_atlas_schema"] == "0.3"
    assert views.ManifestV214.model_validate(manifest).source_atlas_schema == "0.3"
    assert views.ReferenceIndex.model_validate(reference.model_dump()).source_atlas_schema == "0.3"
    manifest["source_atlas_schema"] = "0.4"
    with pytest.raises(ValidationError):
        views.ManifestV214.model_validate(manifest)


def test_observe_scope_migrates_from_v26_with_zero_write_check(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored_before = outside_owned(vault)
    downgrade_manifest_to_v26(vault)
    before = filesystem_state(vault)

    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before

    migrated = views.project(repo, vault, sha)
    manifest = yaml.safe_load(migrated[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.14"
    assert str(views.OBSERVE_SCOPE) in {item["path"] for item in manifest["owned_files"]}
    assert outside_owned(vault) == authored_before
    after = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == migrated
    assert filesystem_state(vault) == after


def test_identity_pages_migrate_from_v27_and_check_without_writes(setup):
    repo, vault, sha = setup
    current = views.project(repo, vault, sha)
    authored_before = outside_owned(vault)
    manifest_path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_bytes())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.7"
    manifest["reference_index_schema_version"] = "1.0"
    manifest["owned_files"] = [
        item
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]).parent != PurePosixPath("identity-pages")
    ]
    for path in current:
        if path.parent != PurePosixPath("identity-pages"):
            continue
        (derived(vault) / path).unlink()
    manifest_path.write_bytes(technical.yaml_text(manifest).encode())
    before_check = filesystem_state(vault)

    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before_check

    migrated = views.project(repo, vault, sha)
    migrated_manifest = yaml.safe_load(migrated[views.MANIFEST])
    assert migrated_manifest["view_schema_version"] == "2.14"
    assert views.IDENTITY_PAGE_PAYLOADS <= {
        PurePosixPath(item["path"]) for item in migrated_manifest["owned_files"]
    }
    assert all(path in current and path in migrated for path in views.IDENTITY_PAGE_PAYLOADS)
    assert outside_owned(vault) == authored_before
    after = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == migrated
    assert filesystem_state(vault) == after


def test_rm1_v28_pilot_paths_migrate_to_v29_without_adopting_new_paths(setup):
    repo, vault, sha = setup
    current = views.project(repo, vault, sha)
    authored = outside_owned(vault)
    manifest_path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_bytes())
    added_paths = {
        PurePosixPath(item["path"])
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]).parent == PurePosixPath("identity-pages")
        and PurePosixPath(item["path"]) not in views.IDENTITY_PAGE_PAYLOADS
    }
    assert len(added_paths) == 52
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.8"
    manifest["reference_index_schema_version"] = "1.0"
    manifest["owned_files"] = [
        item for item in manifest["owned_files"] if PurePosixPath(item["path"]) not in added_paths
    ]
    for path in added_paths:
        (derived(vault) / path).unlink()
    manifest_path.write_text(technical.yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    migrated = views.project(repo, vault, sha)
    assert migrated == current
    assert all((derived(vault) / path).is_file() for path in added_paths)
    assert outside_owned(vault) == authored


def test_identity_page_hidden_metadata_owns_exact_v28_paths_and_check_is_zero_write(setup):
    repo, vault, sha = setup
    generated = views.project(repo, vault, sha)
    manifest = views.read_yaml((derived(vault) / views.MANIFEST).read_text())
    owned = {
        PurePosixPath(item["path"])
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]) in views.IDENTITY_PAGE_PAYLOADS
    }

    assert manifest["view_schema_version"] == "2.14"
    assert owned == views.IDENTITY_PAGE_PAYLOADS
    for path in views.IDENTITY_PAGE_PAYLOADS:
        rendered = (derived(vault) / path).read_text()
        assert (
            views._identity_page_generated_metadata(rendered, path)["generated_by"] == views.OWNER
        )

    before_check = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == generated
    assert filesystem_state(vault) == before_check


@pytest.mark.parametrize(
    "fault",
    ("missing", "malformed", "wrong_owner", "wrong_subject", "wrong_type", "wrong_path"),
)
def test_identity_page_hidden_metadata_fails_closed(setup, fault):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    path = views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    target = derived(vault) / path
    original = target.read_text()
    visible, _, _ = original.partition(views.IDENTITY_PAGE_METADATA_MARKER)

    if fault == "missing":
        changed = visible
    elif fault == "malformed":
        changed = visible + views.IDENTITY_PAGE_METADATA_MARKER + "generated_by: [\n-->\n"
    else:
        metadata = views._identity_page_generated_metadata(original, path)
        if fault == "wrong_owner":
            metadata["generated_by"] = "another-generator"
        elif fault == "wrong_subject":
            metadata["identity_page_subject_id"] = "CMP-OBSERVATION-BUILDER"
        elif fault == "wrong_type":
            metadata["identity_page_registry_type"] = "DataArtifact"
        elif fault == "wrong_path":
            metadata["identity_page_path"] = "identity-pages/Other.md"
        changed = (
            visible + views.IDENTITY_PAGE_METADATA_MARKER + technical.yaml_text(metadata) + "-->\n"
        )

    target.write_text(changed)
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="lost its owner marker"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before


def test_identity_page_edits_and_unowned_paths_are_not_adopted(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    root = derived(vault)
    path = views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    target = root / path
    original = target.read_bytes()
    edited = original.replace(b"derived navigation page", b"manual navigation page", 1)
    assert edited != original
    target.write_bytes(edited)
    before_edited = filesystem_state(vault)

    with pytest.raises(technical.ProjectionError, match="Identity Page was edited"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before_edited

    target.write_bytes(original)
    unowned = root / "identity-pages/Unregistered.md"
    unowned.write_text("Unowned synthetic page\n")
    before_unowned = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Unknown/unowned derived files"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before_unowned


def test_v29_stable_id_paths_migrate_to_human_first_without_authored_writes(setup):
    repo, vault, sha = setup
    expected = views.project(repo, vault, sha)
    atlas = load_registry(repo / "docs/research-atlas")
    old_paths = install_v29_stable_id_identity_paths(vault, atlas)
    authored = outside_owned(vault)
    before_check = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before_check

    migrated = views.project(repo, vault, sha)
    assert migrated == expected
    assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.14"
    assert old_paths["CMP-MEMORY"] == PurePosixPath("identity-pages/CMP-MEMORY.md")
    assert not (derived(vault) / old_paths["CMP-MEMORY"]).exists()
    memory = PurePosixPath("identity-pages/Memory.md")
    assert memory in migrated
    assert (
        views._identity_page_generated_metadata(migrated[memory].decode(), memory)[
            "identity_page_subject_id"
        ]
        == "CMP-MEMORY"
    )
    assert (
        views._derived_link(memory, "Memory")
        in migrated[views.identity_page_paths(atlas)["CMP-MEM-EPISODIC"]].decode()
    )
    assert (
        "_generated/derived/identity-pages/CMP-MEMORY|"
        not in migrated[views.identity_page_paths(atlas)["CMP-MEM-EPISODIC"]].decode()
    )
    assert outside_owned(vault) == authored
    after = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == migrated
    assert filesystem_state(vault) == after


def test_v29_identity_migration_fails_closed_without_writes(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    atlas = load_registry(repo / "docs/research-atlas")
    old_paths = install_v29_stable_id_identity_paths(vault, atlas)
    target = derived(vault) / old_paths["CMP-MEMORY"]
    intact = target.read_bytes()
    target.write_bytes(intact + b"Authored edit\n")
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Identity Page was edited|owner marker"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before
    target.write_bytes(intact)

    destination = derived(vault) / "identity-pages/Memory.md"
    destination.write_text("Authored destination\n")
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Unknown/unowned derived files"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("kind", ["Component", "Function"])
def test_rm1_synthetic_add_rename_remove_preserves_authored_bytes_and_zero_write(setup, kind):
    repo, vault, sha = setup
    baseline = views.project(repo, vault, sha)

    def authored_bytes():
        return {
            str(path.relative_to(vault)): path.read_bytes()
            for path in vault.rglob("*")
            if path.is_file() and not path.is_relative_to(vault / "_generated")
        }

    authored = authored_bytes()
    nodes_path = repo / "docs/research-atlas/registry/nodes.yaml"
    edges_path = repo / "docs/research-atlas/registry/relationships.yaml"
    original_nodes, original_edges = nodes_path.read_bytes(), edges_path.read_bytes()
    nodes = yaml.safe_load(original_nodes)
    edges = yaml.safe_load(original_edges)
    template_id = "CMP-PERCEPTION" if kind == "Component" else "FUNC-OBSERVE"
    template = next(node for node in nodes["nodes"] if node["id"] == template_id)
    synthetic_id = "CMP-SYN-ADDED" if kind == "Component" else "FUNC-SYN-ADDED"
    synthetic = {**template, "id": synthetic_id, "name": "Synthetic addition"}
    synthetic.update(
        description="Synthetic direct Component responsibility.",
        atlas_level=None,
        overview_visibility=None,
        overview_order=None,
    )
    nodes["nodes"].append(synthetic)
    edges["relationships"].append(
        {"relation": "part_of", "source": synthetic_id, "target": "CMP-PERCEPTION"}
        if kind == "Component"
        else {
            "relation": "contributes_to_function",
            "source": "CMP-PERCEPTION",
            "target": synthetic_id,
        }
    )
    nodes_path.write_text(technical.yaml_text(nodes))
    edges_path.write_text(technical.yaml_text(edges))
    added_sha = commit(repo)
    technical.project(repo, vault, added_sha)
    before_check = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, added_sha, check=True)
    assert filesystem_state(vault) == before_check
    added = views.project(repo, vault, added_sha)
    path = PurePosixPath("identity-pages/Synthetic addition.md")
    assert path in added and path not in baseline
    owned = {item["path"] for item in yaml.safe_load(added[views.MANIFEST])["owned_files"]}
    assert str(path) in owned
    assert "identity-pages/CMP-MEM-RETRIEVAL.md" not in owned
    assert "identity-pages/CMP-INDEPENDENT-VERIFIER.md" not in owned
    assert "Synthetic addition" in added[path].decode()
    assert views.project(repo, vault, added_sha, check=True) == added
    assert authored_bytes() == authored

    synthetic["name"] = "Renamed synthetic Component"
    nodes_path.write_text(technical.yaml_text(nodes))
    renamed_sha = commit(repo)
    technical.project(repo, vault, renamed_sha)
    prior_page = derived(vault) / path
    original_prior = prior_page.read_bytes()
    prior_page.write_bytes(original_prior + b"Edited old generated page\n")
    before_rejected_rename = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Identity Page was edited|owner marker"):
        views.project(repo, vault, renamed_sha)
    assert filesystem_state(vault) == before_rejected_rename
    prior_page.write_bytes(original_prior)
    renamed_path = PurePosixPath("identity-pages/Renamed synthetic Component.md")
    occupied = derived(vault) / renamed_path
    occupied.write_text("Authored destination\n")
    before_occupied = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Unknown/unowned derived files"):
        views.project(repo, vault, renamed_sha)
    assert filesystem_state(vault) == before_occupied
    occupied.unlink()
    renamed = views.project(repo, vault, renamed_sha)
    assert path not in renamed and not (derived(vault) / path).exists()
    assert renamed_path in renamed
    pilot = views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    label = "Open component" if kind == "Component" else "Renamed synthetic Component"
    assert views._derived_link(renamed_path, label) in renamed[pilot].decode()
    assert views._derived_link(path, "Synthetic addition") not in renamed[pilot].decode()
    assert "Renamed synthetic Component" in renamed[renamed_path].decode()
    assert "Synthetic addition" not in renamed[renamed_path].decode()
    assert authored_bytes() == authored

    nodes_path.write_bytes(original_nodes)
    edges_path.write_bytes(original_edges)
    removed_sha = commit(repo)
    technical.project(repo, vault, removed_sha)
    edited_page = derived(vault) / renamed_path
    edited_page.write_bytes(renamed[renamed_path] + b"Manual edit must survive\n")
    before_rejected_remove = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="owner marker|Identity Page was edited"):
        views.project(repo, vault, removed_sha)
    assert filesystem_state(vault) == before_rejected_remove
    edited_page.write_bytes(renamed[renamed_path])
    removed = views.project(repo, vault, removed_sha)
    assert renamed_path not in removed and not edited_page.exists()
    assert authored_bytes() == authored
    before_final_check = filesystem_state(vault)
    assert views.project(repo, vault, removed_sha, check=True) == removed
    assert filesystem_state(vault) == before_final_check


def test_observe_scope_uses_finite_private_ownership_and_existing_w05_destinations(setup):
    repo, vault, sha = setup
    atlas = load_registry(repo / "docs/research-atlas")
    tree = views.project(repo, vault, sha)
    scope = tree[views.OBSERVE_SCOPE].decode()
    properties, body = technical.markdown_parts(scope)
    generated_metadata = views._observe_scope_generated_metadata(scope)

    assert views.OBSERVE_SCOPE == PurePosixPath("assembly-scopes/Observe.md")
    assert PRIVATE_OBSERVE_SCOPE_PATH == views.OWNED_ROOT / views.OBSERVE_SCOPE
    assert properties == {}
    assert generated_metadata["generated_by"] == views.OWNER
    assert generated_metadata["source_repository"] == views.REPOSITORY
    assert generated_metadata["source_commit"] == sha
    assert generated_metadata["source_registry_revision"].startswith("sha256:")
    assert generated_metadata["observe_scope_view_schema_version"] == "1.0"
    assert views.OBSERVE_SCOPE_METADATA_MARKER in scope
    assert "**OBSERVE — Observation Integrity / State**" in body
    assert "**Navigation location:** Agent Anatomy / Observe" in body
    assert "## Authority, revision and limitations" in body

    first_view = body.split("## Exact Registry relations\n", 1)[0]
    assert len(first_view.splitlines()) <= 30
    assert (
        first_view.index("← Agent Anatomy")
        < first_view.index("**OBSERVE — Observation Integrity / State**")
        < first_view.index("Visible observation boundary")
    )
    assert (
        first_view.index("Visible observation boundary")
        < first_view.index("Presentation context")
        < first_view.index("## Observe landmarks")
    )
    assert first_view.count("**Action:**") == 4

    expected_actions = {
        "CMP-VISIBLE-STATE-BRIDGE": "Open Visible-State Bridge",
        "CMP-NO-SPOILER-FIREWALL": "Open No-Spoiler Firewall",
        "CMP-PERCEPTION": "Open Perception",
        "DAT-OBSERVATION": "Open Observation",
    }
    for identity, label in expected_actions.items():
        path = views.identity_page_paths(atlas).get(identity)
        action_link = (
            views._derived_link(path, label)
            if path is not None
            else technical.private_link(technical.private_path(atlas.entities[identity]), label)
        )
        assert action_link in body
    card_section = body.split("## Observe landmarks\n", 1)[1].split(
        "## Exact Registry relations\n", 1
    )[0]
    assert card_section.count("**Action:**") == 4
    assert (
        card_section.index("### No-Spoiler Firewall")
        < card_section.index("> **Visible-State Bridge — OPTIONAL**")
        < card_section.index("### Perception")
        < card_section.index("### Observation")
    )
    assert "Type: `DataArtifact`" in card_section
    assert "CMP-TEMPORAL-STATE" not in card_section

    for identity in ("CMP-OBSERVATION-BUILDER", "CMP-PERCEPTION-UI-STATE"):
        child = atlas.entities[identity]
        parent = atlas.entities["CMP-PERCEPTION"]
        child_link = views._derived_link(
            views.IDENTITY_PAGE_PATHS[identity], f"{child.name} · {identity}"
        )
        parent_link = views._derived_link(
            views.IDENTITY_PAGE_PATHS[parent.id], f"{parent.name} · {parent.id}"
        )
        assert (f"| {child_link} | `part_of` | {parent_link} |") in body

    detail_markdown, detail_canvas = views.technical_detail_paths("DAT-OBSERVATION")
    assert views._derived_link(detail_markdown, "Observation · W05 Technical Detail") in body
    assert views._canvas_link(detail_canvas, "Observation · W05 native Canvas") in body
    assert detail_markdown in tree and detail_canvas in tree
    assert "No directly related endpoint of this type" in body
    assert "The Registry declares no Bridge → Firewall → Perception pipeline edge." in body

    manifest = yaml.safe_load(tree[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.14"
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert views.OBSERVE_SCOPE in owned
    assert views.IDENTITY_PAGE_PAYLOADS <= owned
    assert set(views.COMPONENT_HUB_PATHS) == {
        "CMP-MEM-RETRIEVAL",
        "CMP-INDEPENDENT-VERIFIER",
    }
    for hub_paths in views.COMPONENT_HUB_PATHS.values():
        assert {hub_paths.overview, hub_paths.technical, hub_paths.research} <= tree.keys()

    digests = {
        name: technical.digest((repo / technical.SOURCE_PATHS[0] / name).read_bytes())
        for name in technical.REGISTRY_FILES
    }
    anatomy = technical.projection_tree(atlas, sha, digests)[technical.ANATOMY].decode()
    function_path = views.OWNED_ROOT / views.identity_page_paths(atlas)["FUNC-OBSERVE"].with_suffix(
        ""
    )
    assert f"[[{function_path}|Observe · Functional Context]]" in anatomy
    assert str(PRIVATE_OBSERVE_SCOPE_PATH.with_suffix("")) not in anatomy
    expected_back_link = (
        "[← Agent Anatomy](../../technical-atlas/system-map/Agent%20Anatomy.excalidraw.md)"
    )
    assert expected_back_link in body
    target = unquote(expected_back_link.partition("](")[2].partition(")")[0])
    resolved_target = PurePosixPath(
        posixpath.normpath(
            str((views.OWNED_ROOT / views.OBSERVE_SCOPE).parent / PurePosixPath(target))
        )
    )
    assert resolved_target == technical.OWNED_ROOT / technical.ANATOMY
    assert str(vault).encode() not in scope.encode()
    assert b"SYNTHETIC-PRIVATE-VIEWS-SECRET" not in scope.encode()

    before = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == tree
    assert filesystem_state(vault) == before


def test_observe_research_rows_end_only_at_selected_component_subjects(setup):
    from test_research_wiki_schema import props

    repo, vault, sha = setup
    paper_id = "WPAPER-OBSERVE-SCOPE"
    write_note(
        vault / "authored/paper-observe.md",
        props(
            "paper",
            wiki_id=paper_id,
            title="Synthetic Observe path fixture",
            source_refs=["synthetic-source-v1"],
            research_direct_subject_refs=[
                "CMP-CORTEX",
                "CMP-PERCEPTION",
                "DAT-OBSERVATION",
            ],
        ),
    )
    tree = views.project(repo, vault, sha)
    scope = tree[views.OBSERVE_SCOPE].decode()
    research = scope.split("### Eligible declared literature navigation\n", 1)[1].split(
        "## Authority, revision and limitations\n", 1
    )[0]
    assert "Perception · `CMP-PERCEPTION` · path 1" in research
    assert "WPAPER-OBSERVE-SCOPE" in research
    assert "`N-C/K0/E9:forward`" in research
    assert "Cortex · `CMP-CORTEX` · path" not in research
    assert "Exact terminal subject" in research
    assert "DAT-OBSERVATION` · path" not in research


def test_different_vault_locations_produce_identical_complete_output(setup):
    repo, vault, sha = setup
    other = vault.with_name("second-synthetic-vault")
    shutil.copytree(vault, other)
    assert views.project(repo, vault, sha) == views.project(repo, other, sha)
    assert snapshot(derived(vault)) == snapshot(derived(other))


def test_k3_payloads_use_stable_ids_and_exact_typed_relationships(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    home = tree[views.K3_HOME].decode()
    memory = tree[views.MEMORY_HUB_TECHNICAL].decode()
    verifier = tree[views.VERIFIER_HUB_TECHNICAL].decode()

    assert "# Research Knowledge Home" in home
    assert "CMP-MEM-RETRIEVAL" in home and "CMP-INDEPENDENT-VERIFIER" in home
    assert "_generated/derived/workbenches/Memory Retrieval — CMP-MEM-RETRIEVAL" in home
    assert "_generated/derived/workbenches/Independent Verifier — CMP-INDEPENDENT-VERIFIER" in home
    assert "_generated/technical-atlas/records/CMP-MEM-RETRIEVAL" in memory
    assert "_generated/technical-atlas/records/CMP-INDEPENDENT-VERIFIER" in verifier
    assert "`part_of` →" in memory and "`supplies` →" in memory
    assert "`measured_at` →" in memory and "`presented_in_domain` →" in memory
    assert "`consumes` →" in verifier and "`observes` →" in verifier
    assert "`supplies` →" in verifier and "`part_of` →" in verifier
    assert "Presentation grouping (not technical `part_of`)" in memory
    assert "Presentation grouping (not technical `part_of`)" in verifier
    assert "DOM-COGNITION" not in memory
    assert "RQ-PROGRAM-AB-001" not in memory
    assert "CortexContext · CON-CORTEX-CONTEXT" in memory
    assert "IF-MEM-CORTEX" in memory
    assert "DAT-RETRIEVAL-SNAPSHOT" in memory


def test_w02_hierarchy_direction_domain_separation_and_link_targets(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    entry = tree[views.HIERARCHY].decode()
    memory = tree[views._hierarchy_path("CMP-MEMORY")].decode()
    retrieval = tree[views._hierarchy_path("CMP-MEM-RETRIEVAL")].decode()
    verifier = tree[views._hierarchy_path("CMP-INDEPENDENT-VERIFIER")].decode()
    assert "# Technical Hierarchy" in entry
    assert (
        views._identity_page_human_link(
            load_registry(repo / "docs/research-atlas"), "CMP-MEM-RETRIEVAL"
        )
        in entry
    )
    assert (
        views._identity_page_human_link(
            load_registry(repo / "docs/research-atlas"), "CMP-INDEPENDENT-VERIFIER"
        )
        in entry
    )
    assert "## Technical children" in memory
    assert "Open Overview" in retrieval
    assert "Memory Retrieval · CMP-MEM-RETRIEVAL" not in memory
    assert "## Technical parents" in retrieval
    assert "Autonomous Game Agent Experiment System · SYS-AGA" in retrieval
    assert "Memory · CMP-MEMORY" not in retrieval
    retrieval_props, _ = technical.markdown_parts(retrieval)
    assert retrieval_props["up"] == ["[[_generated/derived/hierarchy/SYS-AGA]]"]
    assert retrieval_props["presentation_domains"] == ["DOM-EVIDENCE-MEMORY"]
    assert "Verification & Learning · DOM-VERIFY-LEARN" in verifier
    assert "Open Overview" in verifier
    assert "## Presentation Domains (not technical ancestry)" in verifier
    assert "## Without a `part_of` path to a System" in entry
    assert (
        "No `part_of` path to a System is declared"
        in tree[views._hierarchy_path("IF-MEM-CORTEX")].decode()
    )
    for path, data in tree.items():
        if path != views.HIERARCHY and path.parent != views.HIERARCHY_DIR:
            continue
        for link in re.findall(r"\[\[([^\]]+)\]\]", data.decode()):
            target = link.partition("|")[0]
            assert (vault / f"{target}.md").is_file(), (path, target)


def test_w02_multiple_parents_cycles_self_parent_and_shuffled_order():
    atlas = load_registry(ATLAS)
    extra = Relationship(relation="part_of", source="CMP-BOUNDED-REFLEX", target="CMP-MANAGER")
    multi = Atlas(atlas.entities, (*atlas.relationships, extra))
    first = views.hierarchy_tree("a" * 40, multi)
    reflex = first[views._hierarchy_path("CMP-BOUNDED-REFLEX")].decode()
    assert "Body · CMP-BODY" in reflex and "Manager · CMP-MANAGER" in reflex
    assert reflex.count("→ [[_generated/derived/hierarchy/CMP-BOUNDED-REFLEX") == 2
    reflex_props, _ = technical.markdown_parts(reflex)
    assert reflex_props["technical_parents"] == ["CMP-BODY", "CMP-MANAGER"]
    assert reflex_props["up"] == [
        "[[_generated/derived/hierarchy/CMP-BODY]]",
        "[[_generated/derived/hierarchy/CMP-MANAGER]]",
    ]
    shuffled = Atlas(
        dict(reversed(list(atlas.entities.items()))), tuple(reversed(multi.relationships))
    )
    assert first == views.hierarchy_tree("a" * 40, shuffled)
    with pytest.raises(technical.ProjectionError, match="cycle"):
        views.hierarchy_tree(
            "a" * 40,
            Atlas(
                atlas.entities,
                (
                    *atlas.relationships,
                    Relationship(
                        relation="part_of", source="CMP-BODY", target="CMP-BOUNDED-REFLEX"
                    ),
                ),
            ),
        )
    with pytest.raises(technical.ProjectionError, match="Self-parent"):
        views.hierarchy_tree(
            "a" * 40,
            Atlas(
                atlas.entities,
                (
                    *atlas.relationships,
                    Relationship(relation="part_of", source="CMP-BODY", target="CMP-BODY"),
                ),
            ),
        )
    with pytest.raises(technical.ProjectionError, match="Missing hierarchy relationship endpoint"):
        views.hierarchy_tree(
            "a" * 40,
            Atlas(
                atlas.entities,
                (
                    *atlas.relationships,
                    Relationship(relation="part_of", source="CMP-MISSING", target="SYS-AGA"),
                ),
            ),
        )
    with pytest.raises(technical.ProjectionError, match="Duplicate part_of"):
        views.hierarchy_tree(
            "a" * 40,
            Atlas(atlas.entities, (*atlas.relationships, extra, extra)),
        )


def test_w02_v21_migration_check_is_zero_write_and_authored_bytes_survive(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    install_pre_w02_v21(vault)
    before = filesystem_state(vault)
    authored = outside_owned(vault)
    with pytest.raises(technical.ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    tree = views.project(repo, vault, sha)
    assert yaml.safe_load(tree[views.MANIFEST])["view_schema_version"] == "2.14"
    assert views.project(repo, vault, sha, check=True) == tree
    assert outside_owned(vault) == authored


def test_w04_hub_views_share_a_human_first_plain_markdown_contract(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    home = tree[views.K3_HOME].decode()
    home_props, _ = technical.markdown_parts(tree[views.K3_HOME].decode())
    assert home_props["k3_view_schema_version"] == views.K3_VIEW_SCHEMA_VERSION == "1.6"
    assert "Preferred Component identities" in home
    assert "complete Identity Page with same-page Technical and Research" in home

    expected = (
        (
            "CMP-MEM-RETRIEVAL",
            "Memory Retrieval",
            views.COMPONENT_HUB_PATHS["CMP-MEM-RETRIEVAL"],
        ),
        (
            "CMP-INDEPENDENT-VERIFIER",
            "Independent Verifier",
            views.COMPONENT_HUB_PATHS["CMP-INDEPENDENT-VERIFIER"],
        ),
    )
    for identity, title, paths in expected:
        payloads = (
            ("overview", paths.overview),
            ("technical", paths.technical),
            ("research", paths.research),
        )
        assert f"{title} · {identity}" in home
        for view, path in payloads:
            if view == "overview":
                body = tree[path].decode()
                metadata = views._identity_page_generated_metadata(body, path)
                assert metadata["identity_page_subject_id"] == identity
                assert metadata["identity_page_registry_type"] == "Component"
                assert body.startswith(f"# {title}\n")
                assert "## Technical" in body and "## Research" in body
                assert "## Return Navigation" in body
            else:
                properties, body = technical.markdown_parts(tree[path].decode())
                assert properties["k3_view_schema_version"] == views.K3_VIEW_SCHEMA_VERSION
                assert properties["k3_surface"] == f"component-hub-{view}"
                assert properties["k3_subject"] == identity
                assert body.startswith(f"# {title}\n\n*Component Hub · {view.title()}*")
                assert "**Views:**" in body
            assert f"`{identity}`" in body
            assert "Technical Hierarchy" in body
            if view != "overview":
                assert "Agent Anatomy" in body
            assert "Research Knowledge Home" in body
        overview = tree[paths.overview].decode()
        assert "### Responsibility / why it exists" in overview
        assert "### Research Questions" in overview
        assert "Technical auxiliary view" in overview and "Research auxiliary view" in overview
        assert "No direct subcomponents are registered." in overview
        assert f"Stable ID: `{identity}` · Type: `Component`" in overview
        status = load_registry(repo / "docs/research-atlas").entities[identity].technical
        assert status.implementation_status.replace("-", " ") in overview
        assert status.verification_status.replace("-", " ") in overview
        return_navigation = overview.split("## Return Navigation", 1)[1]
        assert "Autonomous Game Agent" in return_navigation
        assert "Memory.md" not in return_navigation


def test_w01_k3_navigation_links_resolve_in_generated_fixture(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)

    for path in views.K3_PAYLOADS:
        links = re.findall(r"\[\[([^\]]+)\]\]", tree[path].decode())
        assert links
        for link in links:
            target = link.replace(r"\|", "|").partition("|")[0]
            if target.startswith("#"):
                assert target[1:] in tree[path].decode(), (path, target)
                continue
            relative = PurePosixPath(target)
            if relative.suffix == ".excalidraw":
                generated = PurePosixPath(f"{relative}.md")
            elif relative.suffix in {".canvas", ".base"}:
                generated = relative
            elif not relative.suffix:
                generated = relative.with_suffix(".md")
            else:
                generated = relative
            if relative.is_relative_to(views.OWNED_ROOT):
                assert generated.relative_to(views.OWNED_ROOT) in tree, (path, target)
            else:
                assert relative.is_relative_to(technical.OWNED_ROOT), (path, target)
            expected = vault / generated
            assert expected.is_file(), (path, target)


def test_w03_home_and_domain_slice_navigation_resolves_in_complete_fixture(setup):
    repo, vault, sha = setup
    technical_tree = technical.project(repo, vault, sha, check=True)
    derived_tree = views.project(repo, vault, sha)
    technical_manifest = yaml.safe_load(technical_tree[technical.MANIFEST])
    assert technical_manifest["projection_schema_version"] == "1.1"
    assert technical.ANATOMY in technical_tree and technical.DOMAIN_SLICE in technical_tree
    assert technical.MAP in technical_tree
    assert {item["kind"] for item in technical_manifest["owned_files"]} >= {
        "system_map",
        "agent_anatomy",
        "domain_slice",
    }

    home = derived_tree[views.K3_HOME].decode()
    assert home.index("Agent Anatomy") < home.index("System Anatomy")
    assert "representative Domain slice" in home
    assert "Technical Hierarchy" in home
    assert "Memory Retrieval · CMP-MEM-RETRIEVAL" in home
    assert "Markdown fallback" in home and "comparison and rollback" in home
    assert (
        f"[[{(views.OWNED_ROOT / views.MEMORY_WORKBENCH).with_suffix('')}|"
        "Memory Retrieval → Overview]]"
    ) in technical_tree[technical.DOMAIN_SLICE].decode()

    targets = {
        str(technical.OWNED_ROOT / candidate)
        for path in technical_tree
        for candidate in (path, path.with_suffix(""))
    } | {
        str(views.OWNED_ROOT / candidate)
        for path in derived_tree
        for candidate in (path, path.with_suffix(""))
    }
    for path, data in (*technical_tree.items(), *derived_tree.items()):
        for raw in re.findall(r"\[\[([^\]]+)\]\]", data.decode()):
            target = raw.replace(r"\|", "|").partition("|")[0].partition("#")[0]
            if not target:
                anchor = raw.replace(r"\|", "|").partition("|")[0].removeprefix("#")
                assert f"## {anchor}" in data.decode(), (path, anchor)
                continue
            assert target in targets, (path, target)
            assert (vault / target).is_file() or (vault / f"{target}.md").is_file(), (
                path,
                target,
            )


def test_w01_status_axes_preserve_registry_states_without_promotion(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    memory = tree[views.MEMORY_HUB_TECHNICAL].decode()
    verifier = tree[views.VERIFIER_HUB_TECHNICAL].decode()

    for text in (memory, verifier):
        assert "## Status axes — kept separate" in text
        assert "not one overall badge, score or maturity claim" in text
        assert "| Target architecture / basis | `canonical-target` |" in text
        assert "| Technical verification | `unverified` |" in text
        assert "| Measurement validity | Not established by this view |" in text
        assert "| Scientific evidence | No private scientific evidence is shown" in text
        assert "| Accepted scientific claim | None created or implied by this view |" in text
    assert "| Implementation declaration | `partial` |" in memory
    assert "| Implementation declaration | `implemented` |" in verifier
    assert "`target-only`" in memory
    assert "Actual memory/evidence delivered to Cortex · MEAS-RETRIEVAL-DELIVERY-001" in memory
    assert "No directly related MeasurementPoint is selected for this Component" in verifier

    measurement_row = next(
        line for line in memory.splitlines() if line.startswith("| Measurement presence |")
    )
    cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", measurement_row.strip("|"))]
    assert len(cells) == 3
    assert cells[0] == "Measurement presence"
    assert "[[" in cells[1] and r"\|Actual memory/evidence delivered" in cells[1]
    assert cells[2] == "A MeasurementPoint does not establish measurement validity."
    assert views._markdown_table_cell("[[one|One]]; [[two|Two]]") == (r"[[one\|One]]; [[two\|Two]]")
    assert "|Research Knowledge Home]]" in memory


def test_w04_component_hub_lanes_use_exact_direct_registry_types(setup):
    repo, vault, sha = setup
    atlas = load_registry(repo / "docs/research-atlas")
    memory_hub = views._component_hub_model(atlas, "CMP-MEM-RETRIEVAL")
    verifier_hub = views._component_hub_model(atlas, "CMP-INDEPENDENT-VERIFIER")
    assert memory_hub.interface_ids == ("IF-MEM-CORTEX",)
    assert memory_hub.contract_ids == ("CON-CORTEX-CONTEXT",)
    assert memory_hub.data_artifact_ids == ("DAT-RETRIEVAL-SNAPSHOT",)
    assert memory_hub.measurement_point_ids == ("MEAS-RETRIEVAL-DELIVERY-001",)
    assert verifier_hub.interface_ids == ()
    assert verifier_hub.contract_ids == ("CON-VERIFIER-RESULT",)
    assert verifier_hub.data_artifact_ids == ("DAT-OBSERVATION", "DAT-VISIBLE-OUTCOME")
    assert verifier_hub.measurement_point_ids == ()

    tree = views.project(repo, vault, sha)
    verifier = tree[views.VERIFIER_HUB_TECHNICAL].decode()
    lane = verifier.split("## Interface lane\n\n", 1)[1].split("\n## ", 1)[0]
    assert "Explicitly empty" in lane
    assert "No corresponding `IF-*` Registry record exists" in lane
    assert "No other relation type is rendered as an Interface" in lane
    assert "IF-MEM-CORTEX" not in verifier


def test_w04_non_interface_relation_cannot_populate_interface_lane(setup):
    repo, vault, sha = setup
    atlas = load_registry(repo / "docs/research-atlas")
    false_interface = Relationship(
        relation="supports",
        source="CMP-INDEPENDENT-VERIFIER",
        target="IF-MEM-CORTEX",
    )
    atlas_with_non_interface_edge = Atlas(
        atlas.entities,
        (*atlas.relationships, false_interface),
    )
    hub = views._component_hub_model(atlas_with_non_interface_edge, "CMP-INDEPENDENT-VERIFIER")
    assert hub.interface_ids == ()
    verifier = views.render_component_hub_view(
        sha,
        atlas_with_non_interface_edge,
        hub,
        "technical",
        views.make_snapshot([], atlas_with_non_interface_edge),
        False,
    ).decode()
    assert "IF-MEM-CORTEX" not in verifier
    assert "Explicitly empty" in verifier


def test_w04_v22_manifest_migrates_with_finite_hub_ownership(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored_before = outside_owned(vault)
    downgrade_manifest_to_v22(vault)
    before_check = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before_check

    migrated = views.project(repo, vault, sha)
    manifest = yaml.safe_load(migrated[views.MANIFEST])
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert manifest["view_schema_version"] == "2.14"
    assert views.K3_PAYLOADS <= owned
    assert outside_owned(vault) == authored_before
    assert views.project(repo, vault, sha, check=True) == migrated


def test_w07_landscape_manifest_migrates_v24_with_finite_ownership(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    landscape = derived(vault) / views.RESEARCH_LANDSCAPE
    landscape.unlink()

    def downgrade(manifest):
        manifest.pop("presentation_fingerprint_version", None)
        manifest.pop("presentation_input_fingerprint", None)
        manifest.pop("source_resolution_fingerprint_version", None)
        manifest.pop("source_resolution_input_fingerprint", None)
        remove_g4_payloads(vault, manifest)
        manifest["view_schema_version"] = "2.4"
        manifest["reference_index_schema_version"] = "1.0"
        remove_identity_pages_for_legacy_manifest(vault, manifest)
        manifest["owned_files"] = [
            item
            for item in manifest["owned_files"]
            if item["path"] not in {str(views.RESEARCH_LANDSCAPE), str(views.OBSERVE_SCOPE)}
        ]
        (derived(vault) / views.OBSERVE_SCOPE).unlink()

    change_manifest(vault, downgrade)
    authored_before = outside_owned(vault)
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    migrated = views.project(repo, vault, sha)
    manifest = views.read_yaml(migrated[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.14"
    assert str(views.RESEARCH_LANDSCAPE) in {item["path"] for item in manifest["owned_files"]}
    assert outside_owned(vault) == authored_before
    assert views.project(repo, vault, sha, check=True) == migrated


def test_w10_manifest_migration_is_zero_write_and_fails_closed_for_unowned_paths(setup):
    from test_research_wiki_schema import props

    repo, vault, sha = setup
    paper_id = "WPAPER-W10-MIGRATION"
    write_note(
        vault / "authored/paper.md",
        props("paper", wiki_id=paper_id, source_refs=["zsrc-synthetic-migration"]),
    )
    write_note(
        vault / "authored/reading-note.md",
        props("reading_note", wiki_id="READ-W10-MIGRATION", paper_refs=[paper_id]),
    )
    authored_before = outside_owned(vault)
    current = views.project(repo, vault, sha)
    old_tree = {
        path: data
        for path, data in current.items()
        if path != views.LITERATURE_INSPECTION and path.parent != PurePosixPath("identity-pages")
    }
    for path in views.SOURCE_PAYLOADS:
        old_tree.pop(path)
    old_tree.pop(views.OBSERVE_SCOPE)

    landscape_section = (
        "## Literature Inspection\n\n"
        f"- {views._derived_link(views.LITERATURE_INSPECTION, 'Open Literature Inspection')}\n"
        "Inspect existing accepted Paper and ReadingNote structured fields and open their "
        "authored records.\n\n"
    )
    landscape = old_tree[views.RESEARCH_LANDSCAPE].decode()
    assert landscape_section in landscape
    old_tree[views.RESEARCH_LANDSCAPE] = landscape.replace(landscape_section, "", 1).encode()
    index_route = f"- {views._derived_link(views.LITERATURE_INSPECTION, 'Literature Inspection')}\n"
    direct_index = old_tree[views.INDEX].decode()
    assert index_route in direct_index
    old_tree[views.INDEX] = direct_index.replace(index_route, "", 1).encode()

    manifest = views.read_yaml(old_tree[views.MANIFEST].decode())
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = "2.5"
    manifest["reference_index_schema_version"] = "1.0"
    manifest["owned_files"] = [
        item
        for item in manifest["owned_files"]
        if item["path"]
        not in {
            str(views.LITERATURE_INSPECTION),
            str(views.OBSERVE_SCOPE),
            *(str(path) for path in current if path.parent == PurePosixPath("identity-pages")),
        }
    ]
    for item in manifest["owned_files"]:
        path = PurePosixPath(item["path"])
        item["sha256"] = technical.digest(old_tree[path])
        if path.suffix == ".base":
            item["semantic_sha256"] = views._base_semantic_digest(old_tree[path])
    old_tree[views.MANIFEST] = technical.yaml_text(manifest).encode()

    root = derived(vault)
    target = root / views.LITERATURE_INSPECTION
    target.unlink()
    (root / views.OBSERVE_SCOPE).unlink()
    for path in current:
        if path.parent != PurePosixPath("identity-pages"):
            continue
        (root / path).unlink()
    for relative, data in old_tree.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    before_check = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before_check

    target.write_text("Unowned synthetic content\n")
    before_block = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="Unknown/unowned derived files"):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == before_block
    target.unlink()

    migrated = views.project(repo, vault, sha)
    migrated_manifest = views.read_yaml(migrated[views.MANIFEST].decode())
    assert migrated_manifest["view_schema_version"] == "2.14"
    assert str(views.LITERATURE_INSPECTION) in {
        item["path"] for item in migrated_manifest["owned_files"]
    }
    assert b"WPAPER-W10-MIGRATION" in migrated[views.LITERATURE_INSPECTION]
    assert b"READ-W10-MIGRATION" in migrated[views.LITERATURE_INSPECTION]
    assert b"SYNTHETIC-PRIVATE-SECRET-RA1" not in migrated[views.LITERATURE_INSPECTION]
    assert outside_owned(vault) == authored_before
    after_migration = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == migrated
    assert filesystem_state(vault) == after_migration


def test_w04_hub_rendering_is_registry_order_independent():
    atlas = load_registry(ATLAS)
    shuffled = Atlas(
        dict(reversed(list(atlas.entities.items()))),
        tuple(reversed(atlas.relationships)),
    )

    def render(atlas):
        snapshot = views.make_snapshot([], atlas)
        reference = views.build_index(atlas, snapshot, "a" * 40)
        output = {}
        for subject_id, paths in views.COMPONENT_HUB_PATHS.items():
            hub = views._component_hub_model(atlas, subject_id)
            research_model = views._component_research_model(atlas, reference, subject_id)
            for view, path in (
                ("overview", paths.overview),
                ("technical", paths.technical),
                ("research", paths.research),
            ):
                output[path] = views.render_component_hub_view(
                    "a" * 40,
                    atlas,
                    hub,
                    view,
                    snapshot,
                    False,
                    research_model if view == "research" else None,
                    {},
                )
        return output

    assert render(atlas) == render(shuffled)


def test_w01_workbench_rename_migrates_only_owned_legacy_paths(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored_before = outside_owned(vault)
    install_legacy_workbench_paths(vault)
    before_check = filesystem_state(vault)

    with pytest.raises(technical.ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before_check

    migrated = views.project(repo, vault, sha)
    manifest = yaml.safe_load(migrated[views.MANIFEST])
    owned = {item["path"] for item in manifest["owned_files"]}
    assert {str(path) for path in views.K3_PAYLOADS} <= owned
    assert not ({str(path) for path in views.LEGACY_K3_PAYLOADS} & owned)
    for current in (views.MEMORY_WORKBENCH, views.VERIFIER_WORKBENCH):
        assert (derived(vault) / current).is_file()
    for legacy in views.LEGACY_K3_PAYLOADS:
        assert not (derived(vault) / legacy).exists()
    assert outside_owned(vault) == authored_before
    assert views.project(repo, vault, sha, check=True) == migrated


def test_obsidian_normalized_v2_bases_allow_legacy_workbench_migration(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored_before = outside_owned(vault)
    install_legacy_workbench_paths(vault)
    downgrade_manifest_to_v2(vault)
    normalize_owned_bases_as_obsidian(vault)

    migrated = views.project(repo, vault, sha)
    manifest = yaml.safe_load(migrated[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.14"
    for base in views.OBSIDIAN_MANAGED_BASES:
        assert (derived(vault) / base).read_bytes() == migrated[base]
    for current in (views.MEMORY_WORKBENCH, views.VERIFIER_WORKBENCH):
        assert (derived(vault) / current).is_file()
    for legacy in views.LEGACY_K3_PAYLOADS:
        assert not (derived(vault) / legacy).exists()
    assert outside_owned(vault) == authored_before
    assert views.project(repo, vault, sha, check=True) == migrated


@pytest.mark.parametrize("fault", ["edited", "owner", "unknown"])
def test_w01_legacy_workbench_cleanup_fails_closed(setup, fault):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    install_legacy_workbench_paths(vault)
    legacy = derived(vault) / views.LEGACY_MEMORY_WORKBENCH
    if fault == "edited":
        legacy.write_text(legacy.read_text() + "Authored edit must survive\n")
        match = "Obsolete"
    elif fault == "owner":
        legacy.write_text(legacy.read_text().replace(views.OWNER, "other-owner"))
        match = "owner marker"
    else:
        (derived(vault) / "unknown.md").write_text("Unknown content must survive\n")
        match = "Unknown/unowned"

    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), match)
    assert legacy.is_file()


def test_k3_verifier_interface_lane_is_explicitly_empty(setup):
    repo, vault, sha = setup
    verifier = views.project(repo, vault, sha)[views.VERIFIER_HUB_TECHNICAL].decode()

    interface_start = verifier.index("## Interface lane")
    contract_start = verifier.index("## Contract lane")
    interface = verifier[interface_start:contract_start]
    assert "Explicitly empty" in interface
    assert "No corresponding `IF-*` Registry record exists" in interface
    assert "No Interface is invented" in interface
    assert "IF-MEM-CORTEX" not in verifier


def test_k3_empty_private_and_source_state_is_non_scientific(setup):
    repo, vault, sha = setup
    (vault / "authored/process.md").unlink()
    tree = views.project(repo, vault, sha)
    for path in (views.MEMORY_HUB_RESEARCH, views.VERIFIER_HUB_RESEARCH):
        text = tree[path].decode()
        assert (
            "No matching declared Component literature paths are present in this snapshot." in text
        )
        assert "Authored private research record count: `0`." in text
        assert "No authored private research records are present in this snapshot." in text
        assert "No populated source/Zotero projection is available in this snapshot." in text
        assert "Only current Registry `related_to_research_question` edges" in text
        assert "not a scientific finding" in text
        assert "No accepted scientific claim is created or implied by this Hub view." in text
        assert "Historical technical Evidence appears only in the Technical view" in text
        assert "No private evidence body is shown by this navigation view." in text
        assert "zsrc-" not in text and "zsv-" not in text
        assert "Open Declared Literature Navigation" in text
        assert "IF-MEM-CORTEX" not in text
        assert "CON-CORTEX-CONTEXT" not in text
        assert "DAT-RETRIEVAL-SNAPSHOT" not in text
        assert "MEAS-RETRIEVAL-DELIVERY-001" not in text


def test_k3_private_input_does_not_change_public_bytes_or_k3_output(setup):
    repo, vault, sha = setup
    first = views.project(repo, vault, sha)
    public_before = snapshot(repo)
    (vault / "ordinary.md").write_text("PRIVATE-K3-BODY-SECRET\n")
    second = views.project(repo, vault, sha)
    assert first == second
    assert snapshot(repo) == public_before
    assert all(b"PRIVATE-K3-BODY-SECRET" not in data for data in second.values())


def test_k3_manifest_ownership_and_check_are_deterministic(setup):
    repo, vault, sha = setup
    tree = views.project(repo, vault, sha)
    manifest = yaml.safe_load(tree[views.MANIFEST])
    owned = {item["path"] for item in manifest["owned_files"]}
    assert {str(path) for path in views.K3_PAYLOADS} <= owned
    workbench_owned = {
        PurePosixPath(path) for path in owned if PurePosixPath(path).is_relative_to("workbenches")
    }
    assert (
        workbench_owned
        == (views.K3_PRE_W07_PAYLOADS - {views.K3_HOME}) | views.TECHNICAL_DETAIL_PAYLOADS
    )
    assert manifest["generated_by"] == views.OWNER
    before = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == tree
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("invalid", [b"[]", b"{}", b"views: []", b"bad: [", b"\xff"])
@pytest.mark.parametrize("source", ["public", "direct"])
def test_invalid_base_source_fails_with_validation_error(invalid, source):
    public = (ROOT / views.PUBLIC_SOURCE).read_bytes()
    direct = SOURCE.read_bytes()
    with pytest.raises(technical.ProjectionError):
        views.views_tree(
            "a" * 40,
            invalid if source == "public" else public,
            invalid if source == "direct" else direct,
            load_registry(ATLAS).source_atlas_schema,
        )


@pytest.mark.parametrize("mode", ["same", "inside", "contains"])
def test_nested_topologies_fail(setup, mode):
    repo, vault, sha = setup
    target = repo if mode == "same" else repo / "private" if mode == "inside" else repo.parent
    assert_no_mutation(setup, lambda: views.project(repo, target, sha), "non-nested")


@pytest.mark.parametrize("marker", [None, "{}", "project: wrong\n", "not: [valid", "[]"])
def test_missing_or_bad_marker_fail(setup, marker):
    repo, vault, sha = setup
    path = vault / ".research-wiki-private"
    if marker is None:
        path.unlink()
    else:
        path.write_text(marker)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))


@pytest.mark.parametrize("fault", ["missing", "drift", "bad_ra2"])
def test_exact_ra1_projection_required_without_repairs(setup, fault):
    repo, vault, sha = setup
    if fault == "missing":
        (vault / technical.OWNED_ROOT / technical.MANIFEST).unlink()
    elif fault == "drift":
        path = vault / technical.OWNED_ROOT / "records/CMP-CORTEX.md"
        path.write_text(path.read_text() + "drift")
    else:
        write_note(vault / "authored/process.md", ENVELOPE | {"confidence": 0.9})
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))
    assert not derived(vault).exists()


@pytest.mark.parametrize("boundary", ["vault", "generated", "derived", "descendant"])
def test_symlink_boundary_or_descendant_rejected(setup, boundary):
    repo, vault, sha = setup
    if boundary == "vault":
        alias = vault.with_name("alias")
        alias.symlink_to(vault, target_is_directory=True)
        target = alias
    else:
        target = vault
        if boundary == "generated":
            # RA-1 was already generated; move the directory then symlink it.
            path = vault / "_generated"
            moved = vault.with_name("generated-outside")
            path.rename(moved)
            path.symlink_to(moved, target_is_directory=True)
        elif boundary == "derived":
            derived(vault).symlink_to(vault / "authored", target_is_directory=True)
        else:
            derived(vault).mkdir()
            (derived(vault) / "escape").symlink_to(vault / "authored", target_is_directory=True)
    assert_no_mutation(setup, lambda: views.project(repo, target, sha), "Symlink")


@pytest.mark.parametrize(
    "unknown",
    [
        "unknown.md",
        "bases/Technical Atlas Views.base",
        "indexes/Research Landscape.md",
    ],
)
def test_unknown_content_is_never_overwritten_or_deleted(setup, unknown):
    repo, vault, sha = setup
    path = derived(vault) / unknown
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Unowned content must survive")
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Unknown/unowned")


def test_unknown_file_blocks_otherwise_valid_obsolete_cleanup(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    data = views.BASE_OWNER.encode() + b"views: []\n"
    relative = "bases/obsolete.base"
    (derived(vault) / relative).write_bytes(data)
    change_manifest(vault, lambda m: m["owned_files"].append(manifest_owned_item(relative, data)))
    (derived(vault) / "unknown.md").write_text("Preserve this unowned note")
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Unknown/unowned")
    assert (derived(vault) / relative).read_bytes() == data


@pytest.mark.parametrize("name", ["corrupt.md", "corrupt.MD"])
def test_invalid_derived_markdown_encoding_is_expected_failure(setup, name):
    repo, vault, sha = setup
    derived(vault).mkdir()
    (derived(vault) / name).write_bytes(bytes([255]))
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "UTF-8")


@pytest.mark.parametrize("absolute", [False, True])
def test_manifest_cannot_claim_existing_authored_file_for_cleanup(setup, absolute):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored = vault / "authored/process.md"
    relative = str(authored) if absolute else "../../authored/process.md"
    change_manifest(
        vault,
        lambda m: m["owned_files"].append(manifest_owned_item(relative, authored.read_bytes())),
    )
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Unsafe")


@pytest.mark.parametrize(
    "path",
    [
        "../authored/process.md",
        "/tmp/escape.md",
        "C:/escape.md",
        "indexes/../../escape.md",
        "bases//old.base",
        "bases/./old.base",
        "bases/../old.base",
        "bases\\old.base",
        "manifest/direct-views.yaml",
        "indexes/old.yaml",
        "records/old.md",
        "workbenches/not-owned.md",
        "",
    ],
)
def test_prior_manifest_paths_fail_closed(setup, path):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    change_manifest(
        vault,
        lambda m: m["owned_files"].append(
            {
                "path": path,
                "sha256": "0" * 64,
                "ownership": views.STRICT_OWNERSHIP,
            }
        ),
    )
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))


@pytest.mark.parametrize(
    "fault", ["owner", "schema", "sha", "duplicate", "source_digests", "extra"]
)
def test_invalid_manifest_rejected_before_writes(setup, fault):
    repo, vault, sha = setup
    views.project(repo, vault, sha)

    def edit(m):
        if fault == "owner":
            m["generated_by"] = "other"
        elif fault == "schema":
            m["view_schema_version"] = "3.0"
        elif fault == "sha":
            m["owned_files"][0]["sha256"] = "invalid"
        elif fault == "duplicate":
            m["owned_files"].append(m["owned_files"][0].copy())
        elif fault == "source_digests":
            m["source_sha256"]["private_source"] = "0" * 64
        else:
            m["unknown"] = True

    change_manifest(vault, edit)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))


@pytest.mark.parametrize("fault", ["base_as_strict", "strict_as_base", "missing_semantic"])
def test_v21_ownership_classification_fails_closed(setup, fault):
    repo, vault, sha = setup
    views.project(repo, vault, sha)

    def edit(manifest):
        base = next(
            item for item in manifest["owned_files"] if item["path"] == str(views.DIRECT_BASE)
        )
        strict = next(item for item in manifest["owned_files"] if item["path"] == str(views.INDEX))
        if fault == "base_as_strict":
            base["ownership"] = views.STRICT_OWNERSHIP
        elif fault == "strict_as_base":
            strict["ownership"] = views.OBSIDIAN_BASE_OWNERSHIP
            strict["semantic_sha256"] = strict["sha256"]
        else:
            base.pop("semantic_sha256")

    change_manifest(vault, edit)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "ownership")


@pytest.mark.parametrize("suffix", [".base", ".md"])
@pytest.mark.parametrize("edited", [False, True])
def test_cleanup_only_intact_manifest_owned_navigation(setup, suffix, edited):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    before = outside_owned(vault)
    relative = "bases/obsolete.base" if suffix == ".base" else str(views.LEGACY_MEMORY_WORKBENCH)
    data = (
        views.BASE_OWNER + "views: []\n"
        if suffix == ".base"
        else "---\ngenerated_by: research-wiki-derived\n---\nNavigation only\n"
    ).encode()
    path = derived(vault) / relative
    path.write_bytes(data)
    change_manifest(vault, lambda m: m["owned_files"].append(manifest_owned_item(relative, data)))
    if edited:
        if suffix == ".base":
            path.write_text(views.BASE_OWNER + "views:\n- type: table\n  name: Edited\n")
            match = "semantically"
        else:
            path.write_bytes(data + b"Authored edits")
            match = "Obsolete"
        assert_no_mutation(setup, lambda: views.project(repo, vault, sha), match)
    else:
        views.project(repo, vault, sha)
        assert not path.exists()
        assert outside_owned(vault) == before


@pytest.mark.parametrize(
    "relative",
    [
        views.INDEX,
        views.REFERENCE_INDEX,
        views.NAVIGATION,
        views.K3_HOME,
        views.MEMORY_WORKBENCH,
        views.VERIFIER_WORKBENCH,
    ],
)
def test_owner_marker_required_even_for_current_output(setup, relative):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    path = derived(vault) / relative
    path.write_text(path.read_text().replace(views.OWNER, "unowned"))
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "owner marker")


def test_obsidian_normalized_bases_are_semantically_owned_and_check_is_zero_write(
    obsidian_normalized_bases, monkeypatch
):
    repo, vault, sha, tree = obsidian_normalized_bases
    manifest = yaml.safe_load(tree[views.MANIFEST])
    owned = {item["path"]: item for item in manifest["owned_files"]}
    for relative in views.OBSIDIAN_MANAGED_BASES:
        data = (derived(vault) / relative).read_bytes()
        assert not data.startswith(views.BASE_OWNER.encode())
        assert data != tree[relative]
        assert technical.digest(data) != owned[str(relative)]["sha256"]
        assert views._base_semantic_digest(data) == owned[str(relative)]["semantic_sha256"]
    before = filesystem_state(vault), snapshot(repo)
    monkeypatch.setattr(views, "atomic_write", deny_write)
    monkeypatch.setattr(technical, "atomic_write", deny_write)
    monkeypatch.setattr(Path, "mkdir", deny_write)
    monkeypatch.setattr(Path, "unlink", deny_write)
    monkeypatch.setattr(Path, "write_bytes", deny_write)
    monkeypatch.setattr(Path, "write_text", deny_write)
    monkeypatch.setattr(technical.os, "replace", deny_write)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", deny_write)
    assert views.project(repo, vault, sha, check=True) == tree
    assert (filesystem_state(vault), snapshot(repo)) == before


@pytest.mark.parametrize("relative", sorted(views.OBSIDIAN_MANAGED_BASES))
@pytest.mark.parametrize("change", ["name", "column_order", "filter"])
def test_meaningful_base_changes_still_fail_closed(setup, relative, change):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    normalize_owned_bases_as_obsidian(vault)
    path = derived(vault) / relative
    base = yaml.safe_load(path.read_bytes())
    if change == "name":
        base["views"][0]["name"] += " — operator edit"
    elif change == "column_order":
        base["views"][0]["order"][-2:] = reversed(base["views"][0]["order"][-2:])
    else:
        base["filters"]["and"].append('file.name == "operator edit"')
    path.write_text(yaml.safe_dump(base, allow_unicode=True, sort_keys=True))
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "semantically")


@pytest.mark.parametrize(
    "path", ["bases", "indexes/Direct Views Index.md", "manifest/direct-views.yaml"]
)
def test_occupied_targets_rejected_before_partial_write(setup, path):
    repo, vault, sha = setup
    target = derived(vault) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if path == "bases":
        target.write_text("unowned")
    else:
        target.mkdir()
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))


def deny_write(*args, **kwargs):
    pytest.fail("Check attempted a write")


@pytest.mark.parametrize("state", ["exact", "missing", "drift"])
def test_check_is_zero_write_even_on_failure(setup, monkeypatch, state):
    repo, vault, sha = setup
    if state != "missing":
        views.project(repo, vault, sha)
    if state == "drift":
        path = derived(vault) / views.INDEX
        path.write_bytes(path.read_bytes() + b"# drift\n")
    before = filesystem_state(vault), snapshot(repo)
    monkeypatch.setattr(views, "atomic_write", deny_write)
    monkeypatch.setattr(technical, "atomic_write", deny_write)
    monkeypatch.setattr(Path, "mkdir", deny_write)
    monkeypatch.setattr(Path, "unlink", deny_write)
    monkeypatch.setattr(Path, "write_bytes", deny_write)
    monkeypatch.setattr(Path, "write_text", deny_write)
    monkeypatch.setattr(technical.os, "replace", deny_write)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", deny_write)
    if state == "exact":
        views.project(repo, vault, sha, check=True)
    else:
        with pytest.raises(technical.ProjectionError, match="drift"):
            views.project(repo, vault, sha, check=True)
    assert (filesystem_state(vault), snapshot(repo)) == before


def test_atomic_payloads_and_manifest_last(setup, monkeypatch):
    repo, vault, sha = setup
    writes = []
    replaces = []
    original = views.atomic_write
    replace = technical.os.replace

    def record(root, relative, data):
        writes.append(relative)
        return original(root, relative, data)

    def replace_same_directory(source, target):
        assert Path(source).parent == Path(target).parent
        assert Path(target).is_relative_to(derived(vault))
        replaces.append(Path(target).relative_to(derived(vault)))
        return replace(source, target)

    monkeypatch.setattr(views, "atomic_write", record)
    monkeypatch.setattr(technical.os, "replace", replace_same_directory)
    views.project(repo, vault, sha)
    assert writes[-1] == replaces[-1] == views.MANIFEST
    manifest = yaml.safe_load((derived(vault) / views.MANIFEST).read_text())
    assert len(writes) == len(replaces) == len(manifest["owned_files"]) + 1
    assert not list(derived(vault).rglob(".projection-*"))


@pytest.mark.parametrize(
    "source",
    [
        str(views.PUBLIC_SOURCE),
        str(views.DIRECT_SOURCE),
        "docs/research-atlas/Wiki Views/extra.md",
        "docs/research-atlas/Process Seeds/extra.md",
        "src/fh_agent/research_atlas/source.py",
    ],
)
@pytest.mark.parametrize("staged", [False, True])
def test_relevant_source_dirt_rejected(setup, source, staged):
    repo, vault, sha = setup
    path = repo / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((path.read_text() if path.exists() else "") + "\n# synthetic dirty source\n")
    if staged:
        git(repo, "add", "--", source)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "dirty")


def test_unrelated_dirt_accepted_unchanged(setup):
    repo, vault, sha = setup
    (repo / "unrelated.txt").write_text("Unrelated staged user work")
    git(repo, "add", "unrelated.txt")
    (repo / "untracked.txt").write_text("Unrelated untracked work")
    before = snapshot(repo), git(repo, "status", "--porcelain")
    views.project(repo, vault, sha)
    views.project(repo, vault, sha, check=True)
    assert (snapshot(repo), git(repo, "status", "--porcelain")) == before


def test_ref_must_match_head_and_repo_must_be_root(setup):
    repo, vault, sha = setup
    commit(repo)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "HEAD")
    assert_no_mutation(setup, lambda: views.project(repo / "docs", vault, "HEAD"), "worktree root")


@pytest.mark.parametrize("fault", ["missing", "symlink", "untracked"])
def test_source_must_be_committed_regular_file(setup, fault):
    repo, vault, _ = setup
    path = repo / views.DIRECT_SOURCE
    data = path.read_bytes()
    path.unlink()
    if fault == "symlink":
        other = repo / "elsewhere.base"
        other.write_bytes(data)
        path.symlink_to(other)
    sha = commit(repo)
    if fault == "untracked":
        path.write_bytes(data)
    technical.project(repo, vault, sha)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha))


def test_cli_exit_contract_and_unexpected_faults(setup, capsys, monkeypatch):
    repo, vault, sha = setup
    args = ["--repo-root", str(repo), "--vault-root", str(vault), "--source-ref", sha]
    assert views.main(args) == 0
    assert views.main(args + ["--check"]) == 0
    path = derived(vault) / views.INDEX
    path.write_text(path.read_text() + "\nDrift")
    before = filesystem_state(vault)
    assert views.main(args + ["--check"]) == 2
    assert "drift" in capsys.readouterr().err
    assert filesystem_state(vault) == before
    result = subprocess.run(
        [sys.executable, "-B", "-m", "fh_agent.research_atlas.private_views", *args, "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and "Traceback" not in result.stderr
    assert filesystem_state(vault) == before

    def unexpected(*args, **kwargs):
        raise RuntimeError("Synthetic unexpected fault")

    monkeypatch.setattr(views, "project", unexpected)
    with pytest.raises(RuntimeError, match="unexpected"):
        views.main(args)


def test_public_base_label_only_and_registry_regressions():
    base = yaml.safe_load(render_base())
    public = (ROOT / views.PUBLIC_SOURCE).read_text()
    assert public == render_base()
    assert "Unmapped research areas" not in public
    mapping = next(v for v in base["views"] if v["name"] == "Atlas Mapping Incomplete")
    assert mapping["filters"] == {
        "and": ['note.atlas_type == "Component"', 'note.research_mapping == "unmapped"']
    }
    assert not any(
        word in public.lower() for word in ("exhaustion", "novelty", "gap", "saturation")
    )
    before = snapshot(ATLAS / "registry")
    atlas = load_registry(ATLAS)
    ancestors = {identity: atlas.ancestors(identity) for identity in atlas.entities}
    old = copy.deepcopy(dict(atlas.entities))
    for seed in SEEDS.glob("*.md"):
        properties = yaml.safe_load(re.search(r"```yaml\n(.*?)\n```", seed.read_text(), re.S)[1])
        validate_wiki_records([properties], atlas.entities)
    rendered = workspace_tree(atlas)
    assert all("SYNTHETIC-PRIVATE-VIEWS-SECRET" not in text for text in rendered.values())
    assert atlas.entities == old
    assert {identity: atlas.ancestors(identity) for identity in atlas.entities} == ancestors
    assert snapshot(ATLAS / "registry") == before
    assert all(
        yaml.safe_load(p.read_text())["atlas_schema_version"] == "0.3"
        for p in (ATLAS / "registry").glob("*.yaml")
    )


def flat_matches(expression, props, path="authored/note.md"):
    # Deliberately only the emitted subset, not eval or a substitute Obsidian engine.
    if expression == 'file.ext == "md"':
        return path.endswith(".md")
    if expression == '!file.inFolder("_generated")':
        return not path.startswith("_generated/")
    match = re.fullmatch(r"!note\.(\w+)\.isEmpty\(\)", expression)
    if match:
        return bool(props.get(match[1]))
    match = re.fullmatch(r'note\.(\w+) == "([^"]+)"', expression)
    assert match, expression
    return props.get(match[1]) == match[2]


def test_direct_base_structure_flat_properties_and_view_set():
    from test_research_wiki_schema import props as valid_profile

    base = yaml.safe_load(SOURCE.read_text())
    assert set(base) == {"filters", "views"}
    names = [v["name"] for v in base["views"]]
    assert len(names) == len(set(names)) == 17
    assert set(names) == set(DIRECT_VIEWS) | {role + " present" for role in ROLES}
    for view in base["views"]:
        assert view["type"] == "table"
        assert set(view) <= {"type", "name", "filters", "groupBy", "order", "sort"}
        kind = DIRECT_VIEWS.get(view["name"], "process")
        props = valid_profile(kind)
        record = validate_wiki_records([props], load_registry(ATLAS).entities)[0]
        text = yaml.safe_dump(view)
        assert set(re.findall(r"note\.([a-z_]+)", text)) <= set(type(record).model_fields)
        if view["name"] in DIRECT_VIEWS:
            assert view["filters"] == {"and": [f'note.doc_type == "{kind}"']}
        else:
            role = view["name"].removesuffix(" present")
            assert view["filters"] == {"and": [f"!note.{role}.isEmpty()"]}
            for other in ROLES:
                sample = ENVELOPE | {other: ["CMP-CORTEX"]}
                assert all(flat_matches(e, sample) for e in view["filters"]["and"]) == (
                    role == other
                )
    assert not any(
        term in SOURCE.read_text().lower()
        for term in (
            "confidence",
            "exhaustion",
            "saturation",
            "score",
            "formula",
            "summary",
            "backlinks",
        )
    )


def test_direct_dataset_isolation():
    base = yaml.safe_load(SOURCE.read_text())

    def accepts(props, path="authored/note.md"):
        return all(flat_matches(e, props, path) for e in base["filters"]["and"])

    assert accepts(ENVELOPE)
    for key in (
        "wiki_schema_version",
        "epistemic_schema_version",
        "wiki_id",
        "privacy",
        "export_policy",
    ):
        sample = ENVELOPE.copy()
        del sample[key]
        assert not accepts(sample)
    assert not accepts(ENVELOPE, "_generated/technical-atlas/records/example.md")
    assert not accepts(ENVELOPE, "_generated/derived/indexes/example.md")
    assert not accepts(ENVELOPE, "attachment.base")
    assert not accepts({})
    for source in [*SEEDS.glob("*.md"), *(ATLAS / "Wiki Templates").glob("*.md")]:
        assert not accepts(parse_frontmatter(source.read_text()), str(source))
    atlas = load_registry(ATLAS)
    for text in technical.projection_tree(
        atlas, "a" * 40, {name: "b" * 64 for name in technical.REGISTRY_FILES}
    ).values():
        assert not accepts(parse_frontmatter(text.decode()))
    for key, value in [
        ("privacy", "public"),
        ("export_policy", "allow"),
        ("wiki_id", ""),
        ("epistemic_schema_version", "0.2"),
    ]:
        assert not accepts(ENVELOPE | {key: value})


def test_process_seeds_exact_ids_refs_warnings_and_template_extension():
    assert {p.name for p in SEEDS.iterdir()} == {identity + ".md" for identity in PROCESS_WARNINGS}
    atlas = load_registry(ATLAS)
    for identity, warning in PROCESS_WARNINGS.items():
        text = (SEEDS / (identity + ".md")).read_text()
        assert text.startswith("# ") and not parse_frontmatter(text)
        blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.S)
        assert len(blocks) == 1
        props = yaml.safe_load(blocks[0])
        result = validate_wiki_records([props], atlas.entities)[0]
        assert isinstance(result, Process)
        assert result.wiki_id == identity and result.document_maturity == "draft"
        assert result.atlas_refs and set(result.atlas_refs) <= atlas.entities.keys()
        assert warning in text and "Process membership is not implementation evidence." in text
        assert "not run authorization" in text and "Public `part_of`" in text
        assert "not an active private record" in text
        assert "RA-2 Process template" in text and "B0/B2 requirements" in text
        for field in (
            "Responsible author/editor",
            "Creation date",
            "Revision date",
            "Origin including LLM/chat assistance",
            "Record revision",
            "Change reason",
            "Exact source/object versions",
            "Concrete source/object locators",
            "Review actor",
            "Review role",
            "Review date",
            "Review scope",
            "Review result",
        ):
            assert "| " + field + " |" in text
        for field in (
            "Review actor",
            "Review role",
            "Review date",
            "Review scope",
            "Review result",
        ):
            assert f"| {field} | not reviewed |" in text
        for heading in (
            "Purpose/scope and descriptive vs proposed character",
            "Trigger/preconditions",
            "Participants",
            "Inputs",
            "Steps/branches",
            "Outputs/closure",
            "Measurements/evidence",
            "Open research questions / uncertainty",
        ):
            assert "\n## " + heading + "\n" in text
        assert not re.search(r"(?:/home/|/Users/|/private/|[A-Z]:[\\/])", text)


def test_capability_matrix_exact_coverage_and_conservative_dispositions():
    text = MATRIX.read_text()
    rows = [line.strip("|").split("|") for line in text.splitlines() if line.startswith("| ")]
    data = [[cell.strip() for cell in row] for row in rows[2:]]
    assert len(data) == 15 and all(len(row) == 6 for row in data)
    assert {row[0]: row[1] for row in data} == REQUIRED_CAPABILITIES
    assert all(all(cell for cell in row) for row in data)
    by_name = {row[0]: row for row in data}
    assert "RA-6" in by_name["Evidence Profiles"][-1]
    assert "Body" in by_name["Findings by Conditions"][3]
    assert "contradicts_refs" in by_name["Contradictions/Heterogeneity"][4]
    assert "current status row" in by_name["Candidate History"][4]
    assert "inventory" in by_name["Search Coverage"][-1]
    assert "Paper → ReadingNote/Finding → RQ → Process → Component" in text
    assert "not authorization" in text and "not a research result" in text


@pytest.fixture
def reference_setup(setup):
    from test_research_wiki_reference_index import sample_records

    repo, vault, sha = setup
    for record in sample_records():
        write_note(vault / "authored" / (record["wiki_id"] + ".md"), record)
    return repo, vault, sha


def test_a14_a15_a16_structured_drift_body_and_locator(reference_setup):
    repo, vault, sha = reference_setup
    original = views.project(repo, vault, sha)
    path = vault / "authored/READ-FIXTURE.md"
    text = path.read_text()
    path.write_text(text + "\nPRIVATE-BODY-SECRET\n")
    assert views.project(repo, vault, sha, check=True) == original
    path.write_text(path.read_text().replace("title: Synthetic fixture", "title: PRIVATE-TITLE"))
    with pytest.raises(technical.ProjectionError, match="Direct-view drift"):
        views.project(repo, vault, sha, check=True)
    moved = path.with_name("renamed [reading]#.md")
    path.rename(moved)
    assert_no_mutation(
        reference_setup, lambda: views.project(repo, vault, sha, check=True), "drift"
    )
    relocated = views.project(repo, vault, sha)
    assert relocated[views.REFERENCE_INDEX] == original[views.REFERENCE_INDEX]
    assert relocated[views.NAVIGATION] != original[views.NAVIGATION]
    assert b"renamed%20%5Breading%5D%23.md" in relocated[views.NAVIGATION]
    assert b"PRIVATE-TITLE" in relocated[views.RESEARCH_LANDSCAPE]
    assert b"PRIVATE-BODY-SECRET" not in relocated[views.RESEARCH_LANDSCAPE]
    assert b"PRIVATE-TITLE" not in relocated[views.REFERENCE_INDEX]
    assert b"PRIVATE-TITLE" not in relocated[views.NAVIGATION]
    moved.write_text(moved.read_text().replace("WRQ-FIXTURE", "WRQ-MISSING"))
    assert_no_mutation(
        reference_setup, lambda: views.project(repo, vault, sha, check=True), "drift"
    )
    changed = views.project(repo, vault, sha)
    assert changed[views.REFERENCE_INDEX] != relocated[views.REFERENCE_INDEX]
    assert views.project(repo, vault, sha, check=True) == changed
    other = vault.with_name("relocated-vault")
    shutil.copytree(vault, other)
    assert views.project(repo, other, sha, check=True) == changed


def test_a17_a19_private_outputs_preserve_public_and_authored(reference_setup):
    from fh_agent.research_atlas.workspace import workspace_tree

    repo, vault, sha = reference_setup
    before = outside_owned(vault), filesystem_state(repo)
    atlas = load_registry(repo / "docs/research-atlas")
    public = workspace_tree(atlas)
    ancestry = {key: atlas.ancestors(key) for key in atlas.entities}
    output = views.project(repo, vault, sha)
    assert b"WPAPER-FIXTURE" in output[views.REFERENCE_INDEX]
    assert all(
        str(vault).encode() not in data and b"SYNTHETIC-PRIVATE" not in data
        for data in output.values()
    )
    assert (outside_owned(vault), filesystem_state(repo)) == before
    assert workspace_tree(atlas) == public
    assert {key: atlas.ancestors(key) for key in atlas.entities} == ancestry


def install_v1(repo, vault, sha):
    tree = views.views_tree(
        sha,
        (repo / views.PUBLIC_SOURCE).read_bytes(),
        (repo / views.DIRECT_SOURCE).read_bytes(),
        load_registry(repo / "docs/research-atlas").source_atlas_schema,
    )
    for path, data in tree.items():
        target = derived(vault) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return tree


def test_a21_v1_write_migration_and_zero_write_check(reference_setup):
    repo, vault, sha = reference_setup
    old = install_v1(repo, vault, sha)
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    migrated = views.project(repo, vault, sha)
    assert views.HIERARCHY in migrated
    assert migrated[views.DIRECT_BASE] == old[views.DIRECT_BASE]
    assert migrated[views.TECHNICAL_BASE] == old[views.TECHNICAL_BASE]
    assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.14"
    assert views.project(repo, vault, sha, check=True) == migrated


@pytest.mark.parametrize(
    "version,path",
    [
        ("1.0", str(views.REFERENCE_INDEX)),
        ("2.1", "indexes/other.yaml"),
        ("2.1", "indexes/nested/declared-reference-index.yaml"),
    ],
)
def test_a21_yaml_ownership_is_exact(setup, version, path):
    repo, vault, sha = setup
    if version == "1.0":
        install_v1(repo, vault, sha)
    else:
        views.project(repo, vault, sha)
    item = {"path": path, "sha256": "0" * 64}
    if version == "2.1":
        item["ownership"] = views.STRICT_OWNERSHIP
    change_manifest(vault, lambda m: m["owned_files"].append(item))
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "ownership")


@pytest.mark.parametrize("target", [views.REFERENCE_INDEX, views.NAVIGATION])
def test_a22_new_targets_are_never_adopted(setup, target):
    repo, vault, sha = setup
    install_v1(repo, vault, sha)
    (derived(vault) / target).write_text("Unowned must survive")
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Unknown/unowned")


def test_a22_yaml_owner_version_is_required(setup):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    path = derived(vault) / views.REFERENCE_INDEX
    path.write_text(
        path.read_text().replace("index_schema_version: '1.2'", "index_schema_version: '2.0'")
    )
    assert "2.0" in path.read_text()
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "owner marker")


@pytest.mark.parametrize("state", ["v1", "unresolved", "unowned"])
def test_a24_extended_states_check_has_zero_writes(setup, monkeypatch, state):
    from test_research_wiki_schema import props

    repo, vault, sha = setup
    if state == "v1":
        install_v1(repo, vault, sha)
    else:
        write_note(vault / "authored/finding.md", props("finding", source_refs=["PAPER-MISSING"]))
        views.project(repo, vault, sha)
        if state == "unowned":
            (derived(vault) / "keep.md").write_text("Unowned")
    before = filesystem_state(vault), filesystem_state(repo)
    monkeypatch.setattr(views, "atomic_write", deny_write)
    monkeypatch.setattr(technical, "atomic_write", deny_write)
    monkeypatch.setattr(Path, "mkdir", deny_write)
    monkeypatch.setattr(Path, "write_bytes", deny_write)
    monkeypatch.setattr(Path, "write_text", deny_write)
    monkeypatch.setattr(Path, "unlink", deny_write)
    monkeypatch.setattr(technical.os, "replace", deny_write)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", deny_write)
    args = ["--repo-root", str(repo), "--vault-root", str(vault), "--source-ref", sha, "--check"]
    assert views.main(args) == (0 if state == "unresolved" else 2)
    assert (filesystem_state(vault), filesystem_state(repo)) == before


def test_a25_interrupted_first_generation_preserves_unowned_recovery(setup, monkeypatch):
    repo, vault, sha = setup
    original = views.atomic_write

    def interrupt(root, path, data):
        original(root, path, data)
        raise RuntimeError("Synthetic interruption")

    monkeypatch.setattr(views, "atomic_write", interrupt)
    with pytest.raises(RuntimeError, match="interruption"):
        views.project(repo, vault, sha)
    assert not (derived(vault) / views.MANIFEST).exists()
    monkeypatch.setattr(views, "atomic_write", original)
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Unknown/unowned")


def test_a26_scanner_parity_and_generated_exclusion(setup):
    from test_research_wiki_schema import LEGACY, props

    from fh_agent.research_atlas.private_reference_index import make_snapshot

    repo, vault, _ = setup
    atlas = load_registry(repo / "docs/research-atlas")
    write_note(vault / "authored/legacy.md", LEGACY)
    write_note(vault / "authored/ra2.md", props("paper"))
    (vault / "ordinary-frontmatter.md").write_text("---\nother: [broken\n---\nordinary")
    (vault / "template.md").write_text("# Example\n```yaml\nwiki_id: WPAPER-FAKE\n```\n")
    (vault / "authored/alias.md").symlink_to(vault / "authored/ra2.md")
    (vault / "alias-dir").symlink_to(vault / "authored", target_is_directory=True)
    snapshot, locators, landscape_records = views.authored_snapshot(vault, atlas)
    assert snapshot == make_snapshot(
        technical.authored_properties(vault, vault / technical.OWNED_ROOT), atlas
    )
    write_note(vault / "_generated/other-tool/fake.md", props("paper"))
    assert views.authored_snapshot(vault, atlas) == (snapshot, locators, landscape_records)
    assert set(locators) == {"PROC-SYNTHETIC-001", "PROC-FIXTURE", "WPAPER-FIXTURE"}


@pytest.mark.parametrize(
    "fault", ["duplicate", "bad-yaml", "bad-profile", "bad-encoding", "epistemic-only"]
)
def test_a26_scanner_failure_and_discovery(setup, fault):
    repo, vault, _ = setup
    atlas = load_registry(repo / "docs/research-atlas")
    path = vault / "authored/test.md"
    if fault == "epistemic-only":
        path.write_text('---\nepistemic_schema_version: "0.1"\n---\n')
        assert len(views.authored_snapshot(vault, atlas)[0].records) == 1
        return
    if fault == "duplicate":
        write_note(path, ENVELOPE)
    elif fault == "bad-yaml":
        path.write_text('---\n"wiki_id": [bad\n---\n')
    elif fault == "bad-profile":
        write_note(
            path, ENVELOPE | {"wiki_id": "PROC-NEW", "epistemic_schema_version": "unsupported"}
        )
    else:
        path.write_bytes(b"\xff")
    with pytest.raises(technical.ProjectionError):
        views.authored_snapshot(vault, atlas)


def test_a26_scanner_read_failure_never_returns_partial(setup, monkeypatch):
    repo, vault, _ = setup
    original = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == vault / "authored/process.md":
            raise PermissionError("SYNTHETIC-PRIVATE-PATH")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(technical.ProjectionError, match="Cannot read authored") as caught:
        views.authored_snapshot(vault, load_registry(repo / "docs/research-atlas"))
    assert "SYNTHETIC-PRIVATE" not in str(caught.value)


def test_a18_unsafe_reference_failure_precedes_any_write(setup, monkeypatch, capsys):
    from test_research_wiki_schema import props

    repo, vault, sha = setup
    write_note(vault / "authored/finding.md", props("finding", source_refs=["/private/SECRET"]))
    before = filesystem_state(vault), filesystem_state(repo)
    monkeypatch.setattr(views, "atomic_write", deny_write)
    assert (
        views.main(["--repo-root", str(repo), "--vault-root", str(vault), "--source-ref", sha]) == 2
    )
    assert "SECRET" not in capsys.readouterr().err
    assert (filesystem_state(vault), filesystem_state(repo)) == before


def test_a25_interrupted_owned_regeneration_is_detectable_and_recoverable(
    reference_setup, monkeypatch
):
    repo, vault, sha = reference_setup
    views.project(repo, vault, sha)
    old_manifest = (derived(vault) / views.MANIFEST).read_bytes()
    note = vault / "authored/READ-FIXTURE.md"
    note.write_text(note.read_text().replace("WRQ-FIXTURE", "WRQ-MISSING"))
    original = views.atomic_write

    def interrupt(root, relative, data):
        if relative == views.MANIFEST:
            raise RuntimeError("Synthetic pre-manifest interruption")
        return original(root, relative, data)

    monkeypatch.setattr(views, "atomic_write", interrupt)
    with pytest.raises(RuntimeError, match="interruption"):
        views.project(repo, vault, sha)
    assert (derived(vault) / views.MANIFEST).read_bytes() == old_manifest
    assert_no_mutation(
        reference_setup, lambda: views.project(repo, vault, sha, check=True), "drift"
    )
    monkeypatch.setattr(views, "atomic_write", original)
    repaired = views.project(repo, vault, sha)
    assert repaired[views.MANIFEST] != old_manifest
    assert views.project(repo, vault, sha, check=True) == repaired


@pytest.mark.parametrize("edited", [False, True])
def test_uip_legacy_hub_overviews_migrate_only_when_intact(setup, edited):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    authored = outside_owned(vault)
    atlas = load_registry(repo / "docs/research-atlas")
    snapshot = views.make_snapshot([], atlas)
    manifest_path = derived(vault) / views.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_bytes())
    for identity, paths in views.COMPONENT_HUB_PATHS.items():
        legacy = views.render_component_hub_view(
            sha,
            atlas,
            views._component_hub_model(atlas, identity),
            "overview",
            snapshot,
            False,
        )
        (derived(vault) / paths.overview).write_bytes(legacy)
        item = next(item for item in manifest["owned_files"] if item["path"] == str(paths.overview))
        item["sha256"] = technical.digest(legacy)
    manifest_path.write_text(technical.yaml_text(manifest))
    if edited:
        with (derived(vault) / views.MEMORY_WORKBENCH).open("ab") as stream:
            stream.write(b"\nAuthored edit must be preserved.\n")
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="edited" if edited else "drift"):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before
    if edited:
        with pytest.raises(technical.ProjectionError, match="edited"):
            views.project(repo, vault, sha)
        assert filesystem_state(vault) == before
    else:
        migrated = views.project(repo, vault, sha)
        assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.14"
        for identity, paths in views.COMPONENT_HUB_PATHS.items():
            page = migrated[paths.overview].decode()
            assert (
                views._identity_page_generated_metadata(page, paths.overview)[
                    "identity_page_subject_id"
                ]
                == identity
            )
            assert "## Technical" in page and "## Research" in page
        after = filesystem_state(vault)
        assert views.project(repo, vault, sha, check=True) == migrated
        assert filesystem_state(vault) == after
    assert outside_owned(vault) == authored


def test_engineering_catalog_migration_preserves_authored_bytes_and_zero_write(setup, monkeypatch):
    repo, vault, sha = setup
    before = outside_owned(vault)
    parse = views.parse_catalog
    monkeypatch.setattr(views, "parse_catalog", lambda _data, _atlas: ())
    old = views.project(repo, vault, sha)
    monkeypatch.setattr(views, "parse_catalog", parse)
    new = views.project(repo, vault, sha)
    perception = views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    assert old[perception] != new[perception]
    assert outside_owned(vault) == before
    state = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == new
    assert filesystem_state(vault) == state
    path = derived(vault) / perception
    path.write_bytes(path.read_bytes() + b"authored edit\n")
    state = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError):
        views.project(repo, vault, sha)
    assert filesystem_state(vault) == state


@pytest.mark.parametrize("state", ["missing", "dirty", "duplicate", "wrong-subject"])
def test_engineering_catalog_failure_is_zero_write(setup, state):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    path = repo / views.CATALOG_PATH
    if state == "missing":
        path.unlink()
    elif state == "dirty":
        path.write_bytes(path.read_bytes() + b"# uncommitted\n")
    else:
        data = yaml.safe_load(path.read_bytes())
        if state == "duplicate":
            data["bindings"].append(data["bindings"][0])
        else:
            data["bindings"][0]["subject_id"] = "CMP-CORTEX"
        path.write_text(yaml.safe_dump(data))
        sha = commit(repo)
        technical.project(repo, vault, sha)
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError):
        views.project(repo, vault, sha, check=True)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("old_view,old_index_version", [("2.10", "1.0"), ("2.11", "1.1")])
def test_g2_synthetic_projection_migration_authored_bytes_zero_write_and_export_denial(
    setup, old_view, old_index_version
):
    from test_g2_interface_attachment import rollout_records as g2_records
    from test_research_wiki_projection import SECRET

    from fh_agent.research_atlas.workspace_harness import check as check_workspace

    repo, vault, sha = setup
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    for r in g2_records():
        write_note(vault / "authored" / (r["wiki_id"] + ".md"), r)
    before = filesystem_state(vault)
    outputs = views.project(repo, vault, sha)
    after = filesystem_state(vault)
    assert all(after[path][3] == value[3] for path, value in before.items() if value[3] is not None)
    assert check_workspace(repo, vault) is not None
    assert filesystem_state(vault) == after
    manifest = yaml.safe_load(outputs[views.MANIFEST])
    assert manifest["view_schema_version"] == "2.14"
    assert manifest["reference_index_schema_version"] == "1.2"
    assert {entry["path"] for entry in manifest["owned_files"]} == {
        str(p) for p in outputs if p != views.MANIFEST
    }
    assert all(SECRET.encode() not in payload for payload in outputs.values())
    # Simulate historical generated ownership, including index and preferred-page markers.
    manifest.pop("presentation_fingerprint_version", None)
    manifest.pop("presentation_input_fingerprint", None)
    manifest.pop("source_resolution_fingerprint_version", None)
    manifest.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, manifest)
    manifest["view_schema_version"] = old_view
    manifest["reference_index_schema_version"] = old_index_version
    root = vault / views.OWNED_ROOT
    for entry in manifest["owned_files"]:
        path = root / entry["path"]
        payload = path.read_bytes()
        legacy = payload.replace(
            b"index_schema_version: '1.2'", f"index_schema_version: '{old_index_version}'".encode()
        ).replace(
            b"reference_index_schema_version: '1.2'",
            f"reference_index_schema_version: '{old_index_version}'".encode(),
        )
        if legacy != payload:
            path.write_bytes(legacy)
            entry["sha256"] = views.digest(legacy)
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


def test_human_reader_v212_migration_body_independence_private_export_and_zero_write(setup):
    from test_g2_interface_attachment import reader_records

    from fh_agent.research_atlas.reader_export import export_reader, reader_derivative
    from fh_agent.research_atlas.workspace_harness import WorkspaceError
    from fh_agent.research_atlas.workspace_harness import check as workspace_check

    repo, vault, sha = setup
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    for record in reader_records():
        write_note(vault / "authored" / (record["title"] + ".md"), record)
    authored_before = outside_owned(vault)
    outputs = views.project(repo, vault, sha)
    assert outside_owned(vault) == authored_before
    current = yaml.safe_load(outputs[views.MANIFEST])
    assert current["view_schema_version"] == "2.14"
    assert current["presentation_fingerprint_version"] == "1.0"
    historical = copy.deepcopy(current)
    historical["view_schema_version"] = "2.12"
    historical.pop("presentation_fingerprint_version")
    historical.pop("presentation_input_fingerprint")
    historical.pop("source_resolution_fingerprint_version", None)
    historical.pop("source_resolution_input_fingerprint", None)
    remove_g4_payloads(vault, historical)
    manifest_path = derived(vault) / views.MANIFEST
    manifest_path.write_text(yaml.safe_dump(historical))
    before = filesystem_state(vault)
    with pytest.raises(WorkspaceError, match="drift"):
        workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    assert views.project(repo, vault, sha) == outputs
    before = filesystem_state(vault)
    workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    assert outside_owned(vault) == authored_before
    note = vault / "authored" / (reader_records()[0]["title"] + ".md")
    note.write_text(
        note.read_text() + "\nBODY-ONLY-SECRET: never projected, no automatic question.\n"
    )
    before = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == outputs
    workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    assert all(b"BODY-ONLY-SECRET" not in payload for payload in outputs.values())
    page = views.OWNED_ROOT / views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    export_path = PurePosixPath("reader-exports/Perception.md")
    export_reader(repo, vault, page, export_path)
    assert (vault / export_path).read_bytes() == reader_derivative(
        outputs[views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]], page, export_path
    )
    assert (vault / page).read_bytes() == outputs[views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]]
    before = filesystem_state(vault)
    workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    for bad in (
        PurePosixPath("../public.md"),
        PurePosixPath("/outside.md"),
        PurePosixPath("authored/master.md"),
        export_path,
    ):
        with pytest.raises(technical.ProjectionError):
            export_reader(repo, vault, page, bad)
        assert filesystem_state(vault) == before
    public = workspace_tree(load_registry(repo / "docs/research-atlas"))
    assert all(
        record["wiki_id"] not in payload and record["title"] not in payload
        for record in reader_records()
        for payload in public.values()
    )


def test_g4_catalog_projection_historical_migration_zero_write_and_private_isolation(setup):
    import json

    from source_resolution_fixtures import FIXTURE, synthetic_records

    from fh_agent.research_atlas.source_resolution import CATALOG_INPUT, SOURCE_DETAIL, SOURCE_INDEX
    from fh_agent.research_atlas.workspace_harness import WorkspaceError
    from fh_agent.research_atlas.workspace_harness import check as workspace_check

    repo, vault, sha = setup
    git(repo, "remote", "add", "origin", "https://github.com/Planton361/autonomous-game-agent.git")
    # Real physical synthetic test root; no operator PRIVATE_VAULT lookup or synced-vault access.
    baseline = views.project(repo, vault, sha)
    manifest = yaml.safe_load(baseline[views.MANIFEST])
    remove_g4_payloads(vault, manifest)
    manifest.pop("source_resolution_fingerprint_version")
    manifest.pop("source_resolution_input_fingerprint")
    manifest["view_schema_version"] = "2.13"
    (derived(vault) / views.MANIFEST).write_text(technical.yaml_text(manifest))
    before = filesystem_state(vault)
    with pytest.raises(WorkspaceError, match="drift"):
        workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    empty = views.project(repo, vault, sha)
    assert b"Project source catalog unavailable" in empty[SOURCE_DETAIL]
    assert b"srcf-a7k2" not in b"".join(empty.values())
    (vault / CATALOG_INPUT).write_bytes(FIXTURE.read_bytes())
    for record in synthetic_records():
        write_note(
            vault / "authored" / (record.title + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    before_authored = outside_owned(vault)
    public_before = snapshot(repo)
    outputs = views.project(repo, vault, sha)
    assert outside_owned(vault) == before_authored and snapshot(repo) == public_before
    before = filesystem_state(vault)
    assert workspace_check(repo, vault) is not None
    assert filesystem_state(vault) == before
    source_index = yaml.safe_load(outputs[SOURCE_INDEX])
    current = yaml.safe_load(outputs[views.MANIFEST])
    assert current["view_schema_version"] == "2.14"
    assert (
        current["source_resolution_input_fingerprint"]
        == source_index["source_resolution_input_fingerprint"]
    )
    note = vault / "authored" / "Synthetic — Reading Preprint v1.md"
    note.write_text(
        note.read_text() + "\nBody-only fictional annotation; never a resolver input.\n"
    )
    before = filesystem_state(vault)
    assert views.project(repo, vault, sha, check=True) == outputs
    assert filesystem_state(vault) == before
    authored_read_bytes = note.read_bytes()
    # A changed explicit preference causes drift, but the exact older read provenance stays.
    catalog = json.loads((vault / CATALOG_INPUT).read_text())
    catalog["families"][0]["preferred_version_ref"] = "srcv-b8q3"
    (vault / CATALOG_INPUT).write_text(json.dumps(catalog))
    before = filesystem_state(vault)
    with pytest.raises(WorkspaceError, match="drift"):
        workspace_check(repo, vault)
    assert filesystem_state(vault) == before
    changed = views.project(repo, vault, sha)
    assert changed[SOURCE_INDEX] != outputs[SOURCE_INDEX]
    _, _, records = views.authored_snapshot(vault, load_registry(repo / "docs/research-atlas"))
    reading = next(r for r in records if r.wiki_id == "READ-SOURCE-PROOF")
    assert reading.version_read == "srcv-b8q3"
    assert note.read_bytes() == authored_read_bytes  # No authored source/version rewriting.
    public = workspace_tree(load_registry(repo / "docs/research-atlas"))
    assert all(
        "srcf-a7k2" not in payload
        and "srcv-b8q3" not in payload
        and "Hierarchical Visual State Representations" not in payload
        for payload in public.values()
    )
    assert snapshot(repo) == public_before


@pytest.mark.parametrize(
    "fault",
    [
        "edited-index",
        "edited-detail",
        "lost-owner",
        "unowned",
        "catalog",
        "symlink",
        "missing-history",
        "pruned-history",
    ],
)
def test_g4_source_preflight_failures_never_write_or_adopt(setup, fault):
    import json

    from source_resolution_fixtures import FIXTURE

    from fh_agent.research_atlas.source_resolution import CATALOG_INPUT, SOURCE_DETAIL, SOURCE_INDEX

    repo, vault, sha = setup
    (vault / CATALOG_INPUT).write_bytes(FIXTURE.read_bytes())
    tree = views.project(repo, vault, sha)
    target = derived(vault) / (
        SOURCE_INDEX if fault in {"edited-index", "missing-history"} else SOURCE_DETAIL
    )
    if fault in {"edited-index", "edited-detail"}:
        target.write_bytes(target.read_bytes() + b"\n# fictional human edit\n")
    elif fault == "lost-owner":
        target.write_text(target.read_text().replace(views.OWNER, "unknown-owner"))
    elif fault == "unowned":
        (derived(vault) / "indexes/unowned-source.md").write_text("authored bytes")
    elif fault == "catalog":
        (vault / CATALOG_INPUT).write_text('{"source_catalog_schema_version":"unknown"}')
    elif fault == "symlink":
        (vault / CATALOG_INPUT).unlink()
        (vault / CATALOG_INPUT).symlink_to(FIXTURE)
    elif fault == "missing-history":
        target.unlink()
        data = json.loads((vault / CATALOG_INPUT).read_text())
        data["families"][0]["title"] = "Changed fictional source"
        (vault / CATALOG_INPUT).write_text(json.dumps(data))
    else:
        data = json.loads((vault / CATALOG_INPUT).read_text())
        data["versions"] = data["versions"][:3]
        (vault / CATALOG_INPUT).write_text(json.dumps(data))
    before = filesystem_state(vault)
    for check in (True, False):
        with pytest.raises(views.ProjectionError):
            views.project(repo, vault, sha, check=check)
        assert filesystem_state(vault) == before
    assert tree[SOURCE_INDEX]  # Original finite source payload existed; never silently adopted.


def test_g4_alias_retarget_of_unchanged_read_is_zero_write_rejected(setup):
    import json

    from source_resolution_fixtures import FIXTURE, synthetic_records

    from fh_agent.research_atlas.source_resolution import CATALOG_INPUT

    repo, vault, sha = setup
    (vault / CATALOG_INPUT).write_bytes(FIXTURE.read_bytes())
    for record in synthetic_records():
        if record.doc_type == "reading_note":
            record = record.model_copy(update={"version_read": "arxiv:fictional-v1"})
        write_note(
            vault / "authored" / (record.wiki_id + ".md"),
            record.model_dump(mode="json", exclude_unset=True),
        )
    views.project(repo, vault, sha)
    data = json.loads((vault / CATALOG_INPUT).read_text())
    next(b for b in data["bindings"] if b["scheme"] == "arxiv")["target_ref"] = "srcv-c9r4"
    (vault / CATALOG_INPUT).write_text(json.dumps(data))
    before = filesystem_state(vault)
    for check in (True, False):
        with pytest.raises(
            views.ProjectionError, match="version-read binding cannot silently retarget"
        ):
            views.project(repo, vault, sha, check=check)
        assert filesystem_state(vault) == before
