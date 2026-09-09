"""Synthetic private vaults only; no real research corpus or agent execution."""

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

import pytest
import yaml

from fh_agent.research_atlas import private_projection as projection
from fh_agent.research_atlas.validator import load_registry, validate_registry
from fh_agent.research_atlas.wiki_schema import WIKI_PREFIXES, validate_wiki_records
from fh_agent.research_atlas.workspace import MAP_PATH, parse_frontmatter, workspace_tree

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
SECRET = "SYNTHETIC-PRIVATE-SECRET-RA1"
ENVELOPE = dict(
    wiki_schema_version="0.1",
    wiki_id="PROC-EXAMPLE-001",
    doc_type="process",
    privacy="private",
    export_policy="deny",
    atlas_refs=["CMP-CORTEX", "EVID-48-CORTEX"],
)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo):
    git(repo, "add", "--all")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        "Synthetic fixture",
    )
    return git(repo, "rev-parse", "HEAD")


def write_note(path, props=ENVELOPE):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(props) + "---\n" + SECRET + "\n", encoding="utf-8")


def snapshot(root, *, authored=False):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file() and not (authored and p.is_relative_to(root / projection.OWNED_ROOT))
    }


def filesystem_state(root):
    # Includes directory creation, inode replacement, and mtimes, not just file bytes.
    return {
        str(p.relative_to(root)): (
            p.stat().st_ino,
            p.stat().st_mtime_ns,
            p.is_dir(),
            p.read_bytes() if p.is_file() else None,
        )
        for p in [root, *root.rglob("*")]
    }


@pytest.fixture
def setup(tmp_path):
    repo = tmp_path / "public"
    repo.mkdir()
    shutil.copytree(ATLAS / "registry", repo / "docs/research-atlas/registry")
    package = repo / "src/fh_agent/research_atlas"
    package.mkdir(parents=True)
    (package / "fixture.py").write_text("# Synthetic clean source\n")
    git(repo, "init", "--quiet")
    head = commit(repo)
    vault = tmp_path / "private"
    vault.mkdir()
    (vault / ".research-wiki-private").write_text(
        yaml.safe_dump(dict(research_wiki_private_version="1.0", project=projection.REPOSITORY))
    )
    write_note(vault / "Research/process.md")
    (vault / "ordinary.md").write_bytes(b"ordinary\r\nuntouched\x00\n")
    (vault / "Research/attachment.bin").write_bytes(bytes(range(256)))
    (vault / "_generated/other-tool").mkdir(parents=True)
    (vault / "_generated/other-tool/output.txt").write_text(SECRET)
    return repo, vault, head


def generate(setup, *, check=False):
    return projection.project(*setup, check=check)


def test_authored_tree_invariance_determinism_and_provenance(setup):
    repo, vault, head = setup
    before = snapshot(vault, authored=True)
    first = generate(setup)
    assert snapshot(vault, authored=True) == before
    complete = snapshot(vault)
    assert generate(setup) == first
    assert snapshot(vault) == complete
    assert snapshot(vault, authored=True) == before
    state = filesystem_state(vault)
    generate(setup, check=True)
    assert filesystem_state(vault) == state
    assert snapshot(vault, authored=True) == before
    manifest = yaml.safe_load(first[projection.MANIFEST])
    atlas = load_registry(repo / "docs/research-atlas")
    assert manifest["source_commit"] == head and len(head) == 40
    assert manifest["source_repository"] == projection.REPOSITORY
    assert manifest["source_atlas_schema"] == "0.2"
    assert manifest["record_count"] == sum(n.type != "Evidence" for n in atlas.entities.values())
    assert manifest["evidence_count"] == sum(n.type == "Evidence" for n in atlas.entities.values())
    assert manifest["source_registry_sha256"] == {
        name: hashlib.sha256((repo / projection.SOURCE_PATHS[0] / name).read_bytes()).hexdigest()
        for name in projection.REGISTRY_FILES
    }
    assert [item["path"] for item in manifest["owned_files"]] == sorted(
        item["path"] for item in manifest["owned_files"]
    )
    assert {item["path"] for item in manifest["owned_files"]} == {
        str(p) for p in first if p != projection.MANIFEST
    }
    for item in manifest["owned_files"]:
        assert item["sha256"] == hashlib.sha256(first[PurePosixPath(item["path"])]).hexdigest()
    index = yaml.safe_load(first[projection.INDEX])
    assert index["source_commit"] == head
    assert list(index["entries"]) == sorted(atlas.entities)
    assert index["entries"]["CMP-CORTEX"] == dict(
        atlas_type="Component", display_name="Cortex", path="records/CMP-CORTEX.md"
    )
    for identity, node in atlas.entities.items():
        props = parse_frontmatter(first[projection.private_path(node)].decode())
        assert props["generated_by"] == projection.OWNER
        assert props["source_commit"] == head and props["source_schema"] == "0.2"
        assert props["source_repository"] == projection.REPOSITORY
        source = json.dumps(
            node.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
        ).encode()
        assert props["source_record_digest"] == hashlib.sha256(source).hexdigest()
        assert props["atlas_id"] == identity and props["atlas_name"] == node.name
    assert all(
        str(vault).encode() not in content and SECRET.encode() not in content
        for content in first.values()
    )
    assert not {p.name for p in first} & set(projection.REGISTRY_FILES)


@pytest.mark.parametrize("topology", ["same", "vault-in-repo", "repo-in-vault"])
def test_nested_topology_rejected(setup, topology):
    repo, vault, head = setup
    if topology == "same":
        vault = repo
    elif topology == "vault-in-repo":
        vault = repo / "private"
        vault.mkdir()
    else:
        vault = repo.parent
    before = filesystem_state(repo.parent)
    with pytest.raises(projection.ProjectionError, match="non-nested"):
        projection.project(repo, vault, head)
    assert filesystem_state(repo.parent) == before


@pytest.mark.parametrize(
    "marker",
    [
        None,
        "garbage",
        "[]",
        "research_wiki_private_version: '0.1'\nproject: wrong\n",
        "research_wiki_private_version: '1.0'\nproject: wrong\n",
        "project: x\nproject: y\n",
    ],
)
def test_missing_invalid_marker(setup, marker):
    repo, vault, head = setup
    path = vault / ".research-wiki-private"
    if marker is None:
        path.unlink()
    else:
        path.write_text(marker)
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError):
        generate(setup)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("where", ["vault", "generated", "owned", "descendant", "marker"])
def test_symlink_boundary_and_descendants_fail_closed(setup, where, tmp_path):
    repo, vault, head = setup
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text(SECRET)
    owned = vault / projection.OWNED_ROOT
    if where == "vault":
        link = tmp_path / "vault-link"
        link.symlink_to(vault, target_is_directory=True)
        vault = link
    elif where == "generated":
        (vault / "_generated").rename(vault / "preserved-generated")
        (vault / "_generated").symlink_to(outside, target_is_directory=True)
    elif where == "owned":
        owned.symlink_to(outside, target_is_directory=True)
    elif where == "marker":
        (vault / ".research-wiki-private").rename(outside / "marker")
        (vault / ".research-wiki-private").symlink_to(outside / "marker")
    else:
        owned.mkdir()
        (owned / "escape").symlink_to(outside, target_is_directory=True)
    before = snapshot(outside)
    with pytest.raises(projection.ProjectionError, match="Symlink"):
        projection.project(repo, vault, head)
    assert snapshot(outside) == before


@pytest.mark.parametrize(
    "bad_path",
    [
        "../escape.md",
        "records/../../escape.md",
        "/tmp/escape.md",
        "records/../escape.md",
        "C:/escape.md",
        "records//CMP-CORTEX.md",
    ],
)
def test_malicious_manifest_never_escapes_cleanup(setup, bad_path):
    _, vault, _ = setup
    generate(setup)
    manifest_path = vault / projection.OWNED_ROOT / projection.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["owned_files"][0]["path"] = bad_path
    manifest_path.write_text(yaml.safe_dump(manifest))
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError, match="Unsafe"):
        generate(setup)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize(
    "location", ["unknown.md", "records/CMP-CORTEX.md", "unknown/deep/private.bin"]
)
def test_unowned_files_not_overwritten_or_deleted(setup, location):
    _, vault, _ = setup
    path = vault / projection.OWNED_ROOT / location
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SECRET)
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError, match="Unknown/unowned"):
        generate(setup)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize(
    "change", ["owner", "schema", "duplicate", "counts", "digests", "identity"]
)
def test_prior_manifest_validation(setup, change):
    _, vault, _ = setup
    generate(setup)
    path = vault / projection.OWNED_ROOT / projection.MANIFEST
    manifest = yaml.safe_load(path.read_text())
    if change == "owner":
        manifest["generated_by"] = "unowned"
    elif change == "schema":
        manifest["projection_schema_version"] = "2.0"
    elif change == "duplicate":
        manifest["owned_files"].append(manifest["owned_files"][0])
    elif change == "counts":
        manifest["record_count"] += 1
    elif change == "digests":
        manifest["source_registry_sha256"].pop("nodes.yaml")
    else:
        manifest["owned_files"][0]["atlas_id"] = "EVID-OTHER"
    path.write_text(yaml.safe_dump(manifest))
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError):
        generate(setup)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("edited", [False, True])
def test_only_obsolete_manifest_owned_files_deleted(setup, edited):
    _, vault, _ = setup
    generate(setup)
    root = vault / projection.OWNED_ROOT
    obsolete = root / "records/CMP-OBSOLETE.md"
    obsolete.write_text(
        "---\ngenerated_by: public-research-atlas\natlas_id: CMP-OBSOLETE\n---\n"
        "Synthetic obsolete view\n"
    )
    manifest_path = root / projection.MANIFEST
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["owned_files"].append(
        dict(
            path="records/CMP-OBSOLETE.md",
            kind="atlas_record",
            atlas_id="CMP-OBSOLETE",
            sha256=projection.digest(obsolete.read_bytes()),
        )
    )
    manifest["record_count"] += 1
    manifest_path.write_text(yaml.safe_dump(manifest))
    before = snapshot(vault, authored=True)
    if edited:
        obsolete.write_text(obsolete.read_text() + SECRET)
        state = filesystem_state(vault)
        with pytest.raises(projection.ProjectionError, match="edited"):
            generate(setup)
        assert filesystem_state(vault) == state
    else:
        generate(setup)
        assert not obsolete.exists()
        generate(setup, check=True)
    assert snapshot(vault, authored=True) == before


def test_lost_embedded_owner_cannot_be_overwritten(setup):
    _, vault, _ = setup
    generate(setup)
    path = vault / projection.OWNED_ROOT / "records/CMP-CORTEX.md"
    path.write_text(
        path.read_text().replace("generated_by: public-research-atlas", "generated_by: authored")
    )
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError, match="owner marker"):
        generate(setup)
    assert filesystem_state(vault) == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("wiki_id", "READ-EXAMPLE-001"),
        ("doc_type", "unknown"),
        ("atlas_refs", ["CMP-MISSING"]),
        ("atlas_refs", "CMP-CORTEX"),
        ("privacy", "public"),
        ("export_policy", "allow"),
        ("wiki_schema_version", "0.2"),
        ("atlas_id", "CMP-CORTEX"),
    ],
)
def test_private_envelope_failures(setup, field, value):
    _, vault, _ = setup
    props = copy.deepcopy(ENVELOPE)
    props[field] = value
    write_note(vault / "Research/process.md", props)
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError):
        generate(setup)
    assert filesystem_state(vault) == before


def test_duplicate_wiki_id_rejected(setup):
    _, vault, _ = setup
    write_note(vault / "duplicate.md")
    with pytest.raises(projection.ProjectionError):
        generate(setup)
    assert not (vault / projection.OWNED_ROOT).exists()


def test_all_closed_doc_types_and_unmodeled_notes():
    atlas = load_registry(ATLAS)
    assert WIKI_PREFIXES == dict(
        dossier="DOS",
        process="PROC",
        topic="TOPIC",
        reading_note="READ",
        synthesis="SYN",
        search_record="SEARCH",
        journal_entry="JOURNAL",
        paper="WPAPER",
        finding="WFIND",
        research_question="WRQ",
        experiment_lead="WLEAD",
        research_thread="WTHREAD",
        decision_draft="WDEC",
    )
    props = [
        dict(ENVELOPE, wiki_id=prefix + "-FIXTURE", doc_type=kind, opaque_future_property=SECRET)
        for kind, prefix in WIKI_PREFIXES.items()
    ]
    records = validate_wiki_records([{}, {"doc_type": "ordinary"}, *props], atlas.entities.keys())
    assert len(records) == 13
    assert all(record.atlas_refs == ENVELOPE["atlas_refs"] for record in records)


def test_private_references_and_secrets_do_not_change_public_atlas(setup):
    _, vault, _ = setup
    atlas = load_registry(ATLAS)
    ancestry = {id: atlas.ancestors(id) for id in atlas.entities}
    public = workspace_tree(atlas)
    generate(setup)
    validate_wiki_records(
        projection.authored_properties(vault, vault / projection.OWNED_ROOT), atlas.entities.keys()
    )
    assert {id: atlas.ancestors(id) for id in atlas.entities} == ancestry
    assert workspace_tree(atlas) == public
    assert all(SECRET not in text and str(vault) not in text for text in public.values())


@pytest.mark.parametrize("display_name", ["Renamed Cognition", "Planner's Cortex"])
def test_display_rename_keeps_private_path_and_resolver_links(setup, display_name):
    repo, vault, _ = setup
    generate(setup)
    authored = snapshot(vault, authored=True)
    path = repo / projection.SOURCE_PATHS[0] / "nodes.yaml"
    payload = yaml.safe_load(path.read_text())
    next(n for n in payload["nodes"] if n["id"] == "CMP-CORTEX")["name"] = display_name
    path.write_text(yaml.safe_dump(payload))
    head = commit(repo)
    tree = projection.project(repo, vault, head)
    assert PurePosixPath("records/CMP-CORTEX.md") in tree
    assert display_name.encode() in tree[PurePosixPath("records/CMP-CORTEX.md")]
    assert snapshot(vault, authored=True) == authored
    index = yaml.safe_load(tree[projection.INDEX])
    assert index["entries"]["CMP-CORTEX"]["path"] == "records/CMP-CORTEX.md"
    targets = {str(projection.OWNED_ROOT / p.with_suffix("")) for p in tree if p.suffix == ".md"}
    for data in tree.values():
        for target in re.findall(r"\[\[([^|\]]+)\|", data.decode()):
            assert target in targets
            assert " — " not in target


def scene(text):
    return json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])


def test_private_map_preserves_public_semantics(setup):
    tree = generate(setup)
    atlas = load_registry(ATLAS)
    public = scene(workspace_tree(atlas)[MAP_PATH])
    private = scene(tree[projection.MAP].decode())
    for original, projected in zip(public["elements"], private["elements"], strict=True):
        if original["link"]:
            assert projected["link"].startswith("[[_generated/technical-atlas/records/")
        assert {k: v for k, v in original.items() if k != "link"} == {
            k: v for k, v in projected.items() if k != "link"
        }
    assert {k: v for k, v in public.items() if k != "elements"} == {
        k: v for k, v in private.items() if k != "elements"
    }


@pytest.mark.parametrize("drift", ["none", "missing", "content", "unknown", "empty"])
def test_check_is_zero_write_and_cli_exit_semantics(setup, drift, monkeypatch, capsys):
    repo, vault, head = setup
    if drift != "empty":
        generate(setup)
    root = vault / projection.OWNED_ROOT
    record = root / "records/CMP-CORTEX.md"
    if drift == "missing":
        record.unlink()
    elif drift == "content":
        record.write_text(record.read_text() + "\nSynthetic generated drift\n")
    elif drift == "unknown":
        (root / "unknown.md").write_text(SECRET)
    before_vault, before_repo = filesystem_state(vault), filesystem_state(repo)

    def forbidden(*args, **kwargs):
        pytest.fail("--check attempted a filesystem write")

    with monkeypatch.context() as patch:
        patch.setattr(projection, "atomic_write", forbidden)
        patch.setattr(tempfile, "NamedTemporaryFile", forbidden)
        patch.setattr(Path, "mkdir", forbidden)
        patch.setattr(Path, "write_bytes", forbidden)
        patch.setattr(Path, "write_text", forbidden)
        patch.setattr(Path, "unlink", forbidden)
        patch.setattr(os, "replace", forbidden)
        result = projection.main(
            ["--repo-root", str(repo), "--vault-root", str(vault), "--source-ref", head, "--check"]
        )
    assert result == (0 if drift == "none" else 2)
    assert bool(capsys.readouterr().err) is (drift != "none")
    assert filesystem_state(vault) == before_vault
    assert filesystem_state(repo) == before_repo


@pytest.mark.parametrize(
    "state",
    [
        "wrong-ref",
        "invalid-ref",
        "staged-registry",
        "unstaged-code",
        "untracked-code",
        "untracked-registry",
        "subdirectory",
    ],
)
def test_git_source_contract_fails_before_writes(setup, state):
    repo, vault, head = setup
    if state == "wrong-ref":
        commit(repo)
    elif state == "invalid-ref":
        head = "nonexistent-ref"
    elif state == "staged-registry":
        path = repo / projection.SOURCE_PATHS[0] / "nodes.yaml"
        path.write_text(path.read_text() + "\n")
        git(repo, "add", "--", str(path))
    elif state == "unstaged-code":
        (repo / projection.SOURCE_PATHS[1] / "fixture.py").write_text("# dirty\n")
    elif state.startswith("untracked"):
        (repo / projection.SOURCE_PATHS[state == "untracked-code"] / "untracked.txt").write_text(
            "dirty"
        )
    else:
        repo = repo / "docs"
    before = filesystem_state(vault)
    with pytest.raises(projection.ProjectionError):
        projection.project(repo, vault, head)
    assert filesystem_state(vault) == before


def test_unrelated_staged_and_untracked_dirt_accepted_and_unchanged(setup):
    repo, vault, head = setup
    (repo / "unrelated.txt").write_text("staged user bytes")
    git(repo, "add", "unrelated.txt")
    (repo / "another.txt").write_text("untracked user bytes")
    before = filesystem_state(repo)
    generate(setup)
    generate(setup, check=True)
    assert filesystem_state(repo) == before


def test_atomic_writes_manifest_last(setup, monkeypatch):
    calls = []
    original = os.replace

    def replace(source, target):
        assert Path(source).parent == Path(target).parent
        calls.append(Path(target))
        original(source, target)

    monkeypatch.setattr(os, "replace", replace)
    tree = generate(setup)
    assert len(calls) == len(tree)
    assert calls[-1] == setup[1] / projection.OWNED_ROOT / projection.MANIFEST
    assert not list(setup[1].rglob(".projection-*"))


def test_projection_order_independence():
    payloads = [
        yaml.safe_load((ATLAS / "registry" / name).read_text())
        for name in projection.REGISTRY_FILES
    ]
    atlas = validate_registry(*payloads)
    digests = {name: "0" * 64 for name in projection.REGISTRY_FILES}
    before = projection.projection_tree(atlas, "a" * 40, digests)
    for payload, key in zip(payloads, ("nodes", "relationships", "evidence"), strict=True):
        payload[key].reverse()
    assert projection.projection_tree(validate_registry(*payloads), "a" * 40, digests) == before


def test_module_cli_write_and_check(setup):
    repo, vault, head = setup
    command = [
        sys.executable,
        "-B",
        "-m",
        "fh_agent.research_atlas.private_projection",
        "--repo-root",
        str(repo),
        "--vault-root",
        str(vault),
        "--source-ref",
        head,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    before = filesystem_state(vault)
    result = subprocess.run([*command, "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert filesystem_state(vault) == before
    result = subprocess.run(
        [*command[:-1], "invalid-ref", "--check"], capture_output=True, text=True
    )
    assert result.returncode == 2 and "Traceback" not in result.stderr


def test_unexpected_fault_is_not_normalized(setup, monkeypatch):
    def unexpected(*args, **kwargs):
        raise RuntimeError("Synthetic unexpected failure")

    monkeypatch.setattr(projection, "project", unexpected)
    with pytest.raises(RuntimeError):
        projection.main(
            ["--repo-root", str(setup[0]), "--vault-root", str(setup[1]), "--source-ref", setup[2]]
        )


@pytest.mark.parametrize("style", ["quoted", "flow"])
def test_alternative_yaml_envelope_spelling_cannot_bypass_validation(setup, style):
    _, vault, _ = setup
    props = dict(ENVELOPE, privacy="public")
    header = yaml.safe_dump(props, default_flow_style=style == "flow")
    if style == "quoted":
        header = header.replace("wiki_id:", '"wiki_id":').replace(
            "wiki_schema_version:", '"wiki_schema_version":'
        )
    (vault / "Research/process.md").write_text("---\n" + header + "---\n")
    with pytest.raises(projection.ProjectionError):
        generate(setup)


@pytest.mark.parametrize("where", ["marker", "manifest", "record", "manifest-directory"])
def test_invalid_owned_content_has_expected_cli_failure(setup, where, capsys):
    repo, vault, head = setup
    generate(setup)
    path = {
        "marker": vault / ".research-wiki-private",
        "manifest": vault / projection.OWNED_ROOT / projection.MANIFEST,
        "manifest-directory": vault / projection.OWNED_ROOT / projection.MANIFEST,
        "record": vault / projection.OWNED_ROOT / "records/CMP-CORTEX.md",
    }[where]
    if where == "manifest-directory":
        path.unlink()
        path.mkdir()
    else:
        path.write_bytes(b"\xff\xfe")
    before = filesystem_state(vault)
    assert (
        projection.main(
            ["--repo-root", str(repo), "--vault-root", str(vault), "--source-ref", head, "--check"]
        )
        == 2
    )
    assert "Traceback" not in capsys.readouterr().err
    assert filesystem_state(vault) == before


@pytest.mark.parametrize("subtree", ["Research", "_generated/technical-atlas/records"])
def test_unreadable_subtree_cannot_silently_pass_validation(setup, monkeypatch, subtree):
    _, vault, _ = setup
    generate(setup)
    before = filesystem_state(vault)
    original = os.scandir

    def inaccessible(path):
        if Path(path) == vault / subtree:
            raise PermissionError("Synthetic denied directory")
        return original(path)

    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", inaccessible)
        with pytest.raises(projection.ProjectionError, match="Cannot inspect"):
            generate(setup)
    assert filesystem_state(vault) == before
