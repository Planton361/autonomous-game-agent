"""Direct views only, using synthetic Git checkouts/vaults; never real private data."""

import copy
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

import pytest
import yaml
from test_research_wiki_projection import commit, filesystem_state, git, snapshot, write_note

from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas.validator import load_registry
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
    for relative in (views.PUBLIC_SOURCE, views.DIRECT_SOURCE):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    code = repo / "src/fh_agent/research_atlas/source.py"
    code.parent.mkdir(parents=True)
    code.write_text("# synthetic tracked source\n")
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


def derived(vault):
    return vault / views.OWNED_ROOT


def outside_owned(vault):
    return {
        str(p.relative_to(vault)): technical.digest(p.read_bytes())
        for p in vault.rglob("*")
        if p.is_file() and not p.is_relative_to(derived(vault))
    }


def change_manifest(vault, edit):
    path = derived(vault) / views.MANIFEST
    data = yaml.safe_load(path.read_text())
    edit(data)
    path.write_text(technical.yaml_text(data))


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
    }
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
    assert manifest["view_schema_version"] == "2.0"
    assert manifest["reference_index_schema_version"] == "1.0"
    assert (
        manifest["private_input_fingerprint"]
        == yaml.safe_load(tree[views.REFERENCE_INDEX])["private_input_fingerprint"]
    )
    assert manifest["generated_by"] == views.OWNER == "research-wiki-derived"
    assert manifest["source_repository"] == "Planton361/autonomous-game-agent"
    assert manifest["source_commit"] == sha == git(repo, "rev-parse", "HEAD")
    assert manifest["source_atlas_schema"] == "0.2"
    assert manifest["source_sha256"] == {
        "public_atlas_base": technical.digest((repo / views.PUBLIC_SOURCE).read_bytes()),
        "research_wiki_direct_base": technical.digest((repo / views.DIRECT_SOURCE).read_bytes()),
    }
    assert manifest["owned_files"] == [
        {"path": str(p), "sha256": technical.digest(data)}
        for p, data in sorted(tree.items())
        if p != views.MANIFEST
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


def test_different_vault_locations_produce_identical_complete_output(setup):
    repo, vault, sha = setup
    other = vault.with_name("second-synthetic-vault")
    shutil.copytree(vault, other)
    assert views.project(repo, vault, sha) == views.project(repo, other, sha)
    assert snapshot(derived(vault)) == snapshot(derived(other))


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


@pytest.mark.parametrize("unknown", ["unknown.md", "bases/Technical Atlas Views.base"])
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
    change_manifest(
        vault,
        lambda m: m["owned_files"].append({"path": relative, "sha256": technical.digest(data)}),
    )
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
        lambda m: m["owned_files"].append(
            {"path": relative, "sha256": technical.digest(authored.read_bytes())}
        ),
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
        "",
    ],
)
def test_prior_manifest_paths_fail_closed(setup, path):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    change_manifest(vault, lambda m: m["owned_files"].append({"path": path, "sha256": "0" * 64}))
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


@pytest.mark.parametrize("suffix", [".base", ".md"])
@pytest.mark.parametrize("edited", [False, True])
def test_cleanup_only_intact_manifest_owned_navigation(setup, suffix, edited):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    before = outside_owned(vault)
    relative = ("bases/obsolete" if suffix == ".base" else "indexes/obsolete") + suffix
    data = (
        views.BASE_OWNER + "views: []\n"
        if suffix == ".base"
        else "---\ngenerated_by: research-wiki-derived\n---\nNavigation only\n"
    ).encode()
    path = derived(vault) / relative
    path.write_bytes(data)
    change_manifest(
        vault,
        lambda m: m["owned_files"].append({"path": relative, "sha256": technical.digest(data)}),
    )
    if edited:
        path.write_bytes(data + b"Authored edits")
        assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "Obsolete")
    else:
        views.project(repo, vault, sha)
        assert not path.exists()
        assert outside_owned(vault) == before


@pytest.mark.parametrize(
    "relative",
    [
        views.TECHNICAL_BASE,
        views.DIRECT_BASE,
        views.INDEX,
        views.REFERENCE_INDEX,
        views.NAVIGATION,
    ],
)
def test_owner_marker_required_even_for_current_output(setup, relative):
    repo, vault, sha = setup
    views.project(repo, vault, sha)
    path = derived(vault) / relative
    path.write_text(path.read_text().replace(views.OWNER, "unowned"))
    assert_no_mutation(setup, lambda: views.project(repo, vault, sha), "owner marker")


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
        path = derived(vault) / views.DIRECT_BASE
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
    assert len(writes) == len(replaces) == 6
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
        yaml.safe_load(p.read_text())["atlas_schema_version"] == "0.2"
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
    assert views.project(repo, vault, sha, check=True) == original
    moved = path.with_name("renamed [reading]#.md")
    path.rename(moved)
    assert_no_mutation(
        reference_setup, lambda: views.project(repo, vault, sha, check=True), "drift"
    )
    relocated = views.project(repo, vault, sha)
    assert relocated[views.REFERENCE_INDEX] == original[views.REFERENCE_INDEX]
    assert relocated[views.NAVIGATION] != original[views.NAVIGATION]
    assert b"renamed%20%5Breading%5D%23.md" in relocated[views.NAVIGATION]
    assert all(
        b"PRIVATE-BODY-SECRET" not in data and b"PRIVATE-TITLE" not in data
        for data in relocated.values()
    )
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
        sha, (repo / views.PUBLIC_SOURCE).read_bytes(), (repo / views.DIRECT_SOURCE).read_bytes()
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
    assert len(migrated) == 6
    assert migrated[views.DIRECT_BASE] == old[views.DIRECT_BASE]
    assert migrated[views.TECHNICAL_BASE] == old[views.TECHNICAL_BASE]
    assert yaml.safe_load(migrated[views.MANIFEST])["view_schema_version"] == "2.0"
    assert views.project(repo, vault, sha, check=True) == migrated


@pytest.mark.parametrize(
    "version,path",
    [
        ("1.0", str(views.REFERENCE_INDEX)),
        ("2.0", "indexes/other.yaml"),
        ("2.0", "indexes/nested/declared-reference-index.yaml"),
    ],
)
def test_a21_yaml_ownership_is_exact(setup, version, path):
    repo, vault, sha = setup
    if version == "1.0":
        install_v1(repo, vault, sha)
    else:
        views.project(repo, vault, sha)
    change_manifest(vault, lambda m: m["owned_files"].append({"path": path, "sha256": "0" * 64}))
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
        path.read_text().replace("index_schema_version: '1.0'", "index_schema_version: '2.0'")
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
    snapshot, locators = views.authored_snapshot(vault, atlas)
    assert snapshot == make_snapshot(
        technical.authored_properties(vault, vault / technical.OWNED_ROOT), atlas
    )
    write_note(vault / "_generated/other-tool/fake.md", props("paper"))
    assert views.authored_snapshot(vault, atlas) == (snapshot, locators)
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
