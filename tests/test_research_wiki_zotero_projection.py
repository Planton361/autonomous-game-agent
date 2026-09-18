"""A01–A45: fixture-only source projection; no personal library, vault, PDF or app."""

import ast
import copy
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

import pytest
import yaml
from test_research_wiki_projection import commit, filesystem_state, git, write_note
from test_research_wiki_schema import props

from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_reference_index as references
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import zotero_projection as z
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.wiki_schema import validate_wiki_records
from fh_agent.research_atlas.workspace import workspace_tree

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / z.SOURCE_PATHS[1]


def fixture_data():
    """Exactly three synthetic families; attachment bytes only exist in this builder."""
    items = []
    for number in (1, 2, 3):
        items.append(
            {
                "zotero_item_key": f"Z{number}ITEM01",
                "persistent_ids": [
                    {"kind": "doi", "value": f"10.5555/synthetic.z{number}"},
                    {"kind": "arxiv", "value": f"synthetic-z{number}"},
                ],
                "source_version": "synthetic-preprint-v1" if number == 3 else "synthetic-v1",
                "primary_attachment": {
                    "zotero_attachment_key": f"Z{number}ATT001",
                    "sha256": hashlib.sha256(f"SYNTHETIC-PDF-Z{number}-V1".encode()).hexdigest(),
                },
                "predecessor": None,
                "metadata": {
                    "item_type": "journalArticle",
                    "title": f"Synthetic Z{number} Paper",
                    "creators": ["Fixture Author", "Second Fixture Author"],
                    "publication_year": 2026,
                    "container_title": "Synthetic Venue",
                    "citation_key": f"FixtureZ{number}",
                    "url": f"https://example.invalid/z{number}",
                },
                "annotations": [
                    {
                        "annotation_key": f"Z{number}ANN01",
                        "text": "Synthetic annotation one",
                        "locator": {
                            "page": "2",
                            "section": "Methods",
                            "attachment_relative": {"kind": "pdf-page", "value": "2"},
                        },
                    },
                    {
                        "annotation_key": f"Z{number}ANN02",
                        "text": "Synthetic annotation two",
                        "locator": {"section": "Synthetic Appendix"},
                    },
                ],
            }
        )
    return {
        "fixture_schema_version": "1.0",
        "export_revision": "synthetic-export-r1",
        "library_context": "fixture-library-alpha",
        "items": items,
    }


def parsed(data=None):
    return z.parse_fixture(json.dumps(data if data is not None else fixture_data()).encode())


def records(data=None):
    fixture = parsed(data)
    return [z.record_for(fixture, item) for item in fixture.items]


def mutate_version(data, mode="all"):
    item = data["items"][2]
    item["predecessor"] = {
        "source_version": item["source_version"],
        "zotero_attachment_key": item["primary_attachment"]["zotero_attachment_key"],
        "attachment_digest": item["primary_attachment"]["sha256"],
    }
    if mode in {"version", "all"}:
        item["source_version"] = "synthetic-preprint-v2"
    if mode in {"key", "all"}:
        item["primary_attachment"]["zotero_attachment_key"] = "Z3ATT002"
    if mode in {"digest", "all"}:
        item["primary_attachment"]["sha256"] = hashlib.sha256(b"SYNTHETIC-PDF-Z3-V2").hexdigest()
    data["export_revision"] = "synthetic-export-r3"
    return data


def bytes_tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def outside(vault):
    return {p: b for p, b in bytes_tree(vault).items() if not p.startswith(str(z.OWNED_ROOT) + "/")}


@pytest.fixture
def setup(tmp_path):
    repo, vault = tmp_path / "repo", tmp_path / "vault"
    repo.mkdir()
    vault.mkdir()
    shutil.copytree(ROOT / "docs/research-atlas/registry", repo / "docs/research-atlas/registry")
    package = repo / "src/fh_agent/research_atlas"
    shutil.copytree(
        ROOT / "src/fh_agent/research_atlas", package, ignore=shutil.ignore_patterns("__pycache__")
    )
    (repo / "src/fh_agent/__init__.py").write_text("# Synthetic CLI package\n")
    (package / "fixture.py").write_text("# Synthetic committed generator input\n")
    for relative in (views.PUBLIC_SOURCE, views.DIRECT_SOURCE, PurePosixPath(z.SOURCE_PATHS[1])):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    git(repo, "init", "--quiet")
    sha = commit(repo)
    (vault / ".research-wiki-private").write_text(
        'research_wiki_private_version: "1.0"\nproject: Planton361/autonomous-game-agent\n'
    )
    source = records()[2]
    reading = props(
        "reading_note",
        source_refs=[source.source_id],
        version_read=source.source_version_id,
        reading_depth="methods_checked",
        checked_sections=["methods"],
        read_date="2026-09-10",
    )
    del reading["paper_refs"]
    write_note(vault / "authored/reading.md", reading)
    write_note(vault / "authored/finding.md", props("finding"))
    write_note(vault / "authored/decision.md", props("decision_draft"))
    (vault / "ordinary.md").write_text("SYNTHETIC-PRIVATE-ORDINARY\n")
    (vault / "attachment.bin").write_bytes(b"SYNTHETIC-NOT-AN-INPUT")
    technical.project(repo, vault, sha)
    views.project(repo, vault, sha)
    export = tmp_path / "synthetic-export.json"
    export.write_text(json.dumps(fixture_data()))
    (tmp_path / "zotero.sqlite").write_bytes(b"SYNTHETIC-DB-SENTINEL")
    return repo, vault, sha, export


def project(setup, data=None, *, check=False):
    if data is not None:
        setup[3].write_text(json.dumps(data))
    return z.project(*setup, check=check)


def args(setup):
    repo, vault, sha, export = setup
    return [
        "--repo-root",
        str(repo),
        "--vault-root",
        str(vault),
        "--source-ref",
        sha,
        "--fixture-export",
        str(export),
    ]


def no_mutation(setup, action, match=None):
    before = filesystem_state(setup[0]), filesystem_state(setup[1])
    with pytest.raises(z.ProjectionError, match=match):
        action()
    assert (filesystem_state(setup[0]), filesystem_state(setup[1])) == before


def modify_manifest(setup, edit):
    path = setup[1] / z.OWNED_ROOT / z.MANIFEST
    manifest = yaml.safe_load(path.read_bytes())
    edit(manifest)
    path.write_text(z.yaml_text(manifest))


def source_payloads(tree):
    return {p: b for p, b in tree.items() if p.parts[0] == "sources"}


@pytest.mark.parametrize(
    "case",
    [
        "schema",
        "missing",
        "extra",
        "nested-extra",
        "wrong-type",
        "duplicate-item",
        "duplicate-attachment",
        "duplicate-annotation",
        "bool-year",
    ],
)
def test_a01_strict_fixture_before_writes(setup, case):
    data = fixture_data()
    if case == "schema":
        data["fixture_schema_version"] = "2.0"
    elif case == "missing":
        del data["items"][0]["source_version"]
    elif case == "extra":
        data["opaque"] = {}
    elif case == "nested-extra":
        data["items"][0]["metadata"]["opaque"] = {}
    elif case == "wrong-type":
        data["items"][0]["zotero_item_key"] = 1
    elif case == "duplicate-item":
        data["items"].append(copy.deepcopy(data["items"][0]))
    elif case == "duplicate-attachment":
        data["items"][1]["primary_attachment"] = data["items"][0]["primary_attachment"]
    elif case == "duplicate-annotation":
        data["items"][0]["annotations"] *= 2
    else:
        data["items"][0]["metadata"]["publication_year"] = True
    setup[3].write_text(json.dumps(data))
    no_mutation(setup, lambda: project(setup))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"items": [], "items": []}',
        b'{"x": NaN}',
        b'{"x": Infinity}',
        b'{"x": -Infinity}',
        b'{"x": 1e999}',
        b"[]",
        b"{}",
        b"\xff",
    ],
)
def test_a01_json_parser_rejects_invalid(raw):
    with pytest.raises(z.ProjectionError):
        z.parse_fixture(raw)


def test_a01_all_nested_models_closed_and_strict():
    fixture = parsed()
    models = [
        fixture,
        fixture.items[0],
        fixture.items[0].metadata,
        fixture.items[0].primary_attachment,
        fixture.items[0].persistent_ids[0],
        fixture.items[0].annotations[0],
        fixture.items[0].annotations[0].locator,
        fixture.items[0].annotations[0].locator.attachment_relative,
    ]
    for model in models:
        with pytest.raises(z.ProjectionError):
            z.validate(type(model), model.model_dump() | {"opaque": 1})
    data = fixture_data()
    del data["items"][0]["primary_attachment"]["sha256"]
    assert parsed(data).items[0].primary_attachment.sha256 is None


def test_a02_library_and_item_identity_exact():
    expected = (
        "zsrc-"
        + hashlib.sha256(
            json.dumps(
                {"library_context": "fixture-library-alpha", "zotero_item_key": "Z1ITEM01"},
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()
    )
    assert records()[0].source_id == expected
    assert z.source_id("fixture-library-beta", "Z1ITEM01") != expected


@pytest.mark.parametrize("field", ["title", "citation_key", "persistent_ids"])
def test_a03_a04_a05_no_bibliographic_identity_merge(field):
    data = fixture_data()
    initial = records(data)
    for item in data["items"]:
        if field == "persistent_ids":
            item[field] = [
                {"kind": "doi", "value": "10.5555/synthetic.shared"},
                {"kind": "arxiv", "value": "synthetic-shared"},
            ]
        else:
            item["metadata"][field] = "Synthetic identical metadata"
    changed = records(data)
    assert len({r.source_id for r in changed}) == 3
    assert [(r.source_id, r.source_version_id) for r in changed] == [
        (r.source_id, r.source_version_id) for r in initial
    ]


def test_a06_a07_a18_a22_z1_and_boundary_invariance(setup):
    repo, vault, _, _ = setup
    before = outside(vault), bytes_tree(repo)
    technical_before = bytes_tree(vault / technical.OWNED_ROOT)
    derived_before = bytes_tree(vault / views.OWNED_ROOT)
    authored = (vault / "authored/reading.md").read_bytes()
    first = project(setup)
    assert set(first) == {z.MANIFEST, z.INDEX, z.HOME} | {
        z.source_path(r.source_id, r.source_version_id) for r in records()
    }
    assert len(first) == 6
    assert project(setup) == first == project(setup, check=True)
    assert (outside(vault), bytes_tree(repo)) == before
    assert bytes_tree(vault / technical.OWNED_ROOT) == technical_before
    assert bytes_tree(vault / views.OWNED_ROOT) == derived_before
    assert (vault / "authored/reading.md").read_bytes() == authored
    assert z.OWNED_ROOT == PurePosixPath("_generated/zotero")
    for path, raw in first.items():
        fields = (
            technical.markdown_parts(raw.decode())[0]
            if path.suffix == ".md"
            else yaml.safe_load(raw)
        )
        assert fields["generated_by"] == z.OWNER == "zotero-source-projection"
    assert z.WARNING in first[z.HOME].decode()
    assert not any("current.source" in str(p) for p in first)
    assert not any(
        p.is_symlink() or p.stat().st_nlink != 1
        for p in (vault / z.OWNED_ROOT).rglob("*")
        if p.is_file()
    )


def test_a08_order_normalization_and_creator_order(setup):
    first = project(setup)
    data = fixture_data()
    data["items"].reverse()
    for item in data["items"]:
        item["persistent_ids"].reverse()
        item["annotations"].reverse()
    setup[3].write_text(json.dumps(data, indent=3, sort_keys=True))
    assert project(setup, check=True) == first
    assert parsed(data).items[0].metadata.creators == data["items"][-1]["metadata"]["creators"]
    data["items"][0]["metadata"]["creators"].reverse()
    assert project(setup, data) != first


@pytest.mark.parametrize("change", ["metadata", "annotation"])
def test_a09_a10_z2_delta_isolation_even_with_new_export_revision(setup, change):
    vault = setup[1]
    before_outside = outside(vault)
    first = project(setup)
    data = fixture_data()
    data["export_revision"] = "synthetic-export-r2"
    if change == "metadata":
        data["items"][1]["metadata"]["title"] = "Synthetic corrected Z2 title"
    else:
        data["items"][1]["annotations"][0]["text"] = "Synthetic changed annotation"
    second = project(setup, data)
    path = z.source_path(records()[1].source_id, records()[1].source_version_id)
    assert {p for p in first if first[p] != second[p]} == {path, z.INDEX, z.HOME, z.MANIFEST}
    old, new = [technical.markdown_parts(tree[path].decode())[0] for tree in (first, second)]
    for key in ("source_id", "source_version_id", "attachment_identity"):
        assert old[key] == new[key]
    assert (old["annotation_set_digest"] == new["annotation_set_digest"]) is (change == "metadata")
    assert old["source_record_digest"] != new["source_record_digest"]
    assert outside(vault) == before_outside
    assert project(setup, check=True) == second


@pytest.mark.parametrize("mode", ["version", "key", "digest", "all"])
def test_a11_a15_z3_explicit_version_and_retention(setup, mode):
    before = outside(setup[1])
    first = project(setup)
    old = records()[2]
    data = mutate_version(fixture_data(), mode)
    new = records(data)[2]
    second = project(setup, data)
    assert old.source_id == new.source_id and old.source_version_id != new.source_version_id
    assert (old.attachment_identity != new.attachment_identity) is (mode in {"key", "all"})
    assert new.predecessor_source_version_id == old.source_version_id
    assert old.annotations[0].annotation_id != new.annotations[0].annotation_id
    old_path = z.source_path(old.source_id, old.source_version_id)
    new_path = z.source_path(new.source_id, new.source_version_id)
    assert second[old_path] == first[old_path]
    assert new_path in second and len(second) == 7
    index = yaml.safe_load(second[z.INDEX])
    family = next(f for f in index["sources"] if f["source_id"] == old.source_id)
    assert family["current_source_version_id"] == new.source_version_id
    assert {v["source_version_id"]: v["projection_presence"] for v in family["versions"]} == {
        old.source_version_id: "retained",
        new.source_version_id: "current",
    }
    assert outside(setup[1]) == before
    assert project(setup, check=True) == second
    for record in records()[:2]:
        path = z.source_path(record.source_id, record.source_version_id)
        assert first[path] == second[path]


@pytest.mark.parametrize(
    "fault", ["absent", "wrong-version", "wrong-key", "wrong-digest", "same-doi", "first-dangling"]
)
def test_a16_a17_no_implicit_predecessor(setup, fault):
    if fault != "first-dangling":
        project(setup)
    data = mutate_version(fixture_data())
    predecessor = data["items"][2]["predecessor"]
    if fault in {"absent", "same-doi"}:
        data["items"][2]["predecessor"] = None
    elif fault == "wrong-version":
        predecessor["source_version"] = "unknown"
    elif fault == "wrong-key":
        predecessor["zotero_attachment_key"] = "Z1ATT001"
    elif fault == "wrong-digest":
        predecessor["attachment_digest"] = "0" * 64
    setup[3].write_text(json.dumps(data))
    no_mutation(setup, lambda: project(setup), "predecessor")


def test_a19_a21_three_imports_keep_all_other_roots_exact(setup):
    before = outside(setup[1])
    for data in (fixture_data(), mutate_version(fixture_data()), mutate_version(fixture_data())):
        project(setup, data)
        assert outside(setup[1]) == before
        project(setup, check=True)
        assert outside(setup[1]) == before
    # RA-3B has not gained a Zotero identity resolver.
    atlas = load_registry(setup[0] / "docs/research-atlas")
    resolver = references.Resolver(atlas, references.make_snapshot([], atlas))
    assert (
        resolver.resolve(records()[2].source_id).resolution_status
        == "unresolved-external-or-missing"
    )


@pytest.mark.parametrize(
    "name", ["unknown.md", "sources/unowned.source.md", "indexes/unowned.yaml"]
)
def test_a23_owner_text_does_not_allow_adoption(setup, name):
    project(setup)
    path = setup[1] / z.OWNED_ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\ngenerated_by: zotero-source-projection\n---\nSynthetic unowned\n")
    no_mutation(setup, lambda: project(setup), "Unknown/unowned")


@pytest.mark.parametrize("kind", ["source", "yaml", "markdown"])
@pytest.mark.parametrize("fault", ["owner", "identity"])
def test_a24_lost_owner_or_identity(setup, kind, fault):
    tree = project(setup)
    relative = (
        next(iter(source_payloads(tree)))
        if kind == "source"
        else z.INDEX
        if kind == "yaml"
        else z.HOME
    )
    path = setup[1] / z.OWNED_ROOT / relative
    text = path.read_text()
    if fault == "owner" or kind != "source":
        text = text.replace(z.OWNER, "other-owner")
    else:
        text = text.replace(records()[0].source_id, "zsrc-" + "0" * 64)
    path.write_text(text)
    no_mutation(setup, lambda: project(setup))


@pytest.mark.parametrize(
    "path",
    [
        "../escape.md",
        "/escape.md",
        "C:/escape.md",
        "\\\\host\\share",
        "sources\\old",
        "sources//old",
        "sources/./old",
        "sources/../old",
        "x\x00y",
        "manifest/projection.yaml",
    ],
)
def test_a25_manifest_paths_never_escape(setup, path):
    project(setup)
    modify_manifest(setup, lambda m: m["owned_files"][0].update(path=path))
    no_mutation(setup, lambda: project(setup))


@pytest.mark.parametrize(
    "where",
    [
        "vault",
        "marker",
        "generated",
        "owned",
        "fixture",
        "fixture-parent",
        "output-parent",
        "descendant",
    ],
)
def test_a26_symlinks_rejected(setup, where, tmp_path):
    project(setup)
    repo, vault, sha, export = setup
    path = {
        "vault": vault,
        "marker": vault / ".research-wiki-private",
        "generated": vault / "_generated",
        "owned": vault / z.OWNED_ROOT,
        "fixture": export,
        "fixture-parent": tmp_path / "export-parent",
        "output-parent": vault / z.OWNED_ROOT / "sources",
        "descendant": vault / z.OWNED_ROOT / z.HOME,
    }[where]
    if where == "fixture-parent":
        path.mkdir()
        export.rename(path / "fixture.json")
        export = path / "fixture.json"
    moved = tmp_path / "preserved"
    path.rename(moved)
    path.symlink_to(moved, target_is_directory=moved.is_dir())
    no_mutation((repo, vault, sha, export), lambda: z.project(repo, vault, sha, export), "Symlink")


@pytest.mark.parametrize(
    "fault",
    [
        "schema",
        "owner",
        "repository",
        "duplicate-path",
        "duplicate-version",
        "duplicate-current",
        "kind",
        "digest",
        "extra",
        "inventory",
        "index-identity",
    ],
)
def test_a27_invalid_manifest_preflight(setup, fault):
    project(setup)

    def edit(m):
        if fault == "schema":
            m["projection_schema_version"] = "2.0"
        elif fault == "owner":
            m["generated_by"] = "other"
        elif fault == "repository":
            m["source_repository"] = "other/repo"
        elif fault == "duplicate-path":
            m["owned_files"].append(m["owned_files"][0])
        elif fault == "duplicate-version":
            m["retained_source_versions"].append(m["current_source_versions"][0])
        elif fault == "duplicate-current":
            m["current_source_versions"].append(m["current_source_versions"][0])
        elif fault == "kind":
            m["owned_files"][0]["kind"] = "source_version"
        elif fault == "digest":
            m["owned_files"][0]["sha256"] = "not-a-hash"
        elif fault == "extra":
            m["opaque"] = {}
        elif fault == "inventory":
            m["current_source_versions"].pop()
        else:
            m["owned_files"][0]["source_id"] = records()[0].source_id

    modify_manifest(setup, edit)
    no_mutation(setup, lambda: project(setup))


@pytest.mark.parametrize("edited", [False, True])
def test_a28_cleanup_only_valid_non_source_and_never_history(setup, edited):
    tree = project(setup)
    root = setup[1] / z.OWNED_ROOT
    prior = z.validate_prior(root)
    previous = {p: b for p, b in tree.items() if p != z.MANIFEST}
    # v1 expects both fixed indexes. Exercise future-topology cleanup without
    # accepting a third index path or weakening the current exact topology.
    expected = {p: b for p, b in tree.items() if p != z.HOME}
    if edited:
        previous[z.HOME] += b"Edited obsolete data"
        with pytest.raises(z.ProjectionError, match="obsolete"):
            z.cleanup_paths(prior, expected, previous)
    else:
        assert z.cleanup_paths(prior, expected, previous) == [z.HOME]
    expected.pop(next(iter(source_payloads(tree))))
    with pytest.raises(z.ProjectionError):
        z.cleanup_paths(prior, expected, previous)
    empty = fixture_data() | {"items": []}
    retained = project(setup, empty)
    assert source_payloads(retained) == source_payloads(tree)
    assert all(
        f["current_source_version_id"] is None for f in yaml.safe_load(retained[z.INDEX])["sources"]
    )


@pytest.mark.parametrize("fault", ["missing", "edited"])
def test_a29_retained_history_cannot_be_forgotten(setup, fault):
    first = project(setup)
    project(setup, mutate_version(fixture_data()))
    old = records()[2]
    path = setup[1] / z.OWNED_ROOT / z.source_path(old.source_id, old.source_version_id)
    if fault == "missing":
        path.unlink()
    else:
        path.write_bytes(
            first[z.source_path(old.source_id, old.source_version_id)] + b"Changed history"
        )
    no_mutation(
        setup, lambda: project(setup), "retained" if fault == "missing" else "digest changed"
    )


@pytest.mark.parametrize("tamper", ["body", "metadata", "predecessor"])
def test_prior_current_digest_blocks_read_and_provenance_reuse(setup, monkeypatch, capsys, tamper):
    tree = project(setup)
    data = fixture_data()
    if tamper == "predecessor":
        data = mutate_version(data)
        tree = project(setup, data)
    record = records(data)[2]
    root = setup[1] / z.OWNED_ROOT
    path = root / z.source_path(record.source_id, record.source_version_id)
    if tamper == "body":
        changed = path.read_bytes() + b"Synthetic changed body"
    else:
        if tamper == "predecessor":
            # Removing this fixture descriptor would otherwise preserve the
            # tampered embedded predecessor as if it were trusted provenance.
            record = record.model_copy(update={"predecessor_source_version_id": None})
            data["items"][2]["predecessor"] = None
            setup[3].write_text(json.dumps(data))
        else:
            record = record.model_copy(
                update={
                    "source_metadata": record.source_metadata.model_copy(
                        update={"title": "Synthetic tampered title"}
                    )
                }
            )
        # Even a consistent embedded record digest is not the trust boundary.
        changed = z.render_source(z.seal(record))
    path.write_bytes(changed)
    assert (root / z.MANIFEST).read_bytes() == tree[z.MANIFEST]
    read_record = z.read_record

    def guarded_read(raw, owned):
        assert raw != changed, "Digest-mismatched payload reached embedded record parsing"
        return read_record(raw, owned)

    monkeypatch.setattr(z, "read_record", guarded_read)
    for name in ("render_source", "cleanup_paths", "atomic_write"):
        monkeypatch.setattr(z, name, denied)
    for name in ("mkdir", "write_text", "write_bytes", "unlink"):
        monkeypatch.setattr(Path, name, denied)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", denied)
    monkeypatch.setattr(os, "replace", denied)
    no_mutation(setup, lambda: project(setup), "digest changed")
    before = filesystem_state(setup[0]), filesystem_state(setup[1])
    assert z.main(args(setup)) == 2
    assert capsys.readouterr().err == (
        "Zotero projection: Prior source payload digest changed; "
        "preserve or restore generated history\n"
    )
    assert (filesystem_state(setup[0]), filesystem_state(setup[1])) == before
    assert (root / z.MANIFEST).read_bytes() == tree[z.MANIFEST]
    assert path.read_bytes() == changed


def test_missing_current_can_be_reconstructed(setup):
    tree = project(setup)
    path = next(iter(source_payloads(tree)))
    (setup[1] / z.OWNED_ROOT / path).unlink()
    assert project(setup) == tree


def test_a30_a31_manifest_last_and_interrupted_new_version_recovery(setup, monkeypatch):
    root = setup[1] / z.OWNED_ROOT
    calls = []
    original = os.replace

    def spy(source, target):
        assert Path(source).parent == Path(target).parent
        assert Path(target).is_relative_to(root)
        calls.append(Path(target).relative_to(root))
        original(source, target)

    monkeypatch.setattr(os, "replace", spy)
    first = project(setup)
    assert calls[-1] == z.MANIFEST and len(calls) == 6
    assert not list(root.rglob(".projection-*"))
    data = mutate_version(fixture_data())
    setup[3].write_text(json.dumps(data))
    atomic = z.atomic_write

    def interrupt(root, relative, raw):
        if relative == z.MANIFEST:
            raise RuntimeError("Synthetic interruption")
        atomic(root, relative, raw)

    monkeypatch.setattr(z, "atomic_write", interrupt)
    with pytest.raises(RuntimeError, match="interruption"):
        project(setup)
    assert (root / z.MANIFEST).read_bytes() == first[z.MANIFEST]
    monkeypatch.setattr(z, "atomic_write", atomic)
    no_mutation(setup, lambda: project(setup), "Unknown/unowned")
    new = records(data)[2]
    unmanifested = root / z.source_path(new.source_id, new.source_version_id)
    preserved = setup[1].parent / "preserved-version.md"
    unmanifested.rename(preserved)
    final = project(setup)
    assert final == project(setup, check=True)
    assert preserved.read_bytes() == final[z.source_path(new.source_id, new.source_version_id)]


def denied(*args, **kwargs):
    pytest.fail("Unexpected write/network/app operation")


@pytest.mark.parametrize(
    "state", ["exact", "empty", "missing", "content", "manifest", "index", "version", "unowned"]
)
def test_a32_a33_check_is_zero_write(setup, monkeypatch, capsys, state):
    tree = project(setup) if state != "empty" else {}
    root = setup[1] / z.OWNED_ROOT
    if state == "missing":
        (root / z.HOME).unlink()
    elif state in {"content", "index"}:
        path = root / (next(iter(source_payloads(tree))) if state == "content" else z.HOME)
        path.write_bytes(path.read_bytes() + b"drift")
    elif state == "manifest":
        modify_manifest(setup, lambda m: m.update(fixture_export_revision="synthetic-drift"))
    elif state == "version":
        setup[3].write_text(json.dumps(mutate_version(fixture_data())))
    elif state == "unowned":
        (root / "unowned.md").write_text("Synthetic unowned")
    before = filesystem_state(setup[0]), filesystem_state(setup[1])
    for name in ("mkdir", "write_text", "write_bytes", "unlink"):
        monkeypatch.setattr(Path, name, denied)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", denied)
    monkeypatch.setattr(os, "replace", denied)
    monkeypatch.setattr(z, "atomic_write", denied)
    assert z.main(args(setup) + ["--check"]) == (0 if state == "exact" else 2)
    error = capsys.readouterr().err
    assert bool(error) is (state != "exact")
    assert str(setup[1]) not in error and str(setup[3]) not in error
    assert (filesystem_state(setup[0]), filesystem_state(setup[1])) == before


@pytest.mark.parametrize(
    "state", ["wrong-ref", "invalid-ref", "subdir", "staged", "unstaged", "untracked", "doc-dirt"]
)
def test_a34_git_gate(setup, state, capsys):
    repo, vault, sha, export = setup
    if state == "wrong-ref":
        commit(repo)
    elif state == "invalid-ref":
        sha = "missing-ref"
    elif state == "subdir":
        repo = repo / "src"
    else:
        relative = z.SOURCE_PATHS[1] if state == "doc-dirt" else z.SOURCE_PATHS[0] + "/fixture.py"
        if state == "untracked":
            relative = z.SOURCE_PATHS[0] + "/unknown.py"
        (repo / relative).write_text("# Synthetic dirt\n")
        if state == "staged":
            git(repo, "add", "--", relative)
    before = filesystem_state(vault)
    assert z.main(args((repo, vault, sha, export))) == 2
    assert capsys.readouterr().err and filesystem_state(vault) == before


def test_a34_unrelated_dirt_and_actual_module_cli(setup):
    repo, vault, sha, export = setup
    (repo / "unrelated").write_text("Synthetic unrelated staged work")
    git(repo, "add", "unrelated")
    (repo / "untracked").write_text("Synthetic unrelated untracked work")
    before = filesystem_state(repo)
    command = [
        sys.executable,
        "-B",
        "-m",
        "fh_agent.research_atlas.zotero_projection",
        *args(setup),
    ]
    environment = os.environ | {"PYTHONPATH": str(repo / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        command, env=environment, cwd=repo, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    state = filesystem_state(vault)
    result = subprocess.run(
        command + ["--check"],
        env=environment,
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert filesystem_state(vault) == state and filesystem_state(repo) == before
    assert "Traceback" not in result.stderr


def test_a35_no_private_path_serialization_and_vault_move(setup):
    tree = project(setup)
    for raw in tree.values():
        assert str(setup[1]).encode() not in raw and str(setup[3]).encode() not in raw
        assert b"zotero.sqlite" not in raw and b"storage/" not in raw
    other = setup[1].with_name("other-vault")
    shutil.copytree(setup[1], other)
    assert z.project(setup[0], other, setup[2], setup[3], check=True) == tree


FORBIDDEN_FIELDS = {
    "wiki_schema_version",
    "wiki_id",
    "epistemic_schema_version",
    "doc_type",
    "document_maturity",
    "reading_depth",
    "checked_sections",
    "read_date",
    "version_read",
    "review_state",
    "question_stage",
    "decision_state",
    "decision_record_state",
    "research_direction",
    "implementation_status",
    "verification_status",
    "finding_refs",
    "decision_refs",
    "accepted",
    "verified",
    "scientifically_valid",
}


def keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(keys(v) for v in value))
    return set()


def test_a36_a38_no_epistemic_record_or_promotion(setup):
    authored = outside(setup[1])
    for data in (fixture_data(), mutate_version(fixture_data())):
        tree = project(setup, data)
        for path, raw in tree.items():
            fields = (
                technical.markdown_parts(raw.decode())[0]
                if path.suffix == ".md"
                else yaml.safe_load(raw)
            )
            assert not keys(fields) & FORBIDDEN_FIELDS
            assert b"WFIND-" not in raw and b"WDEC-" not in raw and b"READ-" not in raw
            assert validate_wiki_records([fields], set()) == ()
    assert outside(setup[1]) == authored
    for cls in (
        z.SourceRecord,
        z.ProjectedAnnotation,
        z.AnnotationLocator,
        z.SourceIndex,
        z.Manifest,
    ):
        assert not set(cls.model_fields) & FORBIDDEN_FIELDS


def test_a39_a40_a42_read_and_execution_boundaries(setup, monkeypatch):
    project(setup)
    read = Path.read_bytes
    run = subprocess.run
    reads = []

    def read_spy(path):
        assert (
            path == setup[3]
            or path == setup[1] / ".research-wiki-private"
            or path.is_relative_to(setup[1] / z.OWNED_ROOT)
        )
        reads.append(path)
        return read(path)

    def git_only(command, **kwargs):
        assert command[:2] == ["git", "--no-optional-locks"]
        assert command[4] in {"rev-parse", "status"}
        return run(command, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", read_spy)
        patch.setattr(subprocess, "run", git_only)
        patch.setattr(socket, "create_connection", denied)
        patch.setattr(socket.socket, "connect", denied)
        patch.setattr(technical, "project", denied)
        patch.setattr(views, "project", denied)
        project(setup, check=True)
        project(setup)
    assert setup[3] in reads
    assert (setup[3].parent / "zotero.sqlite").read_bytes() == b"SYNTHETIC-DB-SENTINEL"
    tree = ast.parse((ROOT / "src/fh_agent/research_atlas/zotero_projection.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                assert node.module == "private_projection"
            else:
                imported.add(node.module.split(".")[0])
    assert not imported & {"sqlite3", "socket", "requests", "httpx", "urllib", "http", "subprocess"}
    assert imported <= sys.stdlib_module_names | {"pydantic"}


def test_a41_public_atlas_is_not_a_projection_sink(setup):
    atlas = load_registry(setup[0] / "docs/research-atlas")
    public = workspace_tree(atlas)
    registry = bytes_tree(setup[0] / "docs/research-atlas/registry")
    data = fixture_data()
    data["items"][0]["metadata"]["title"] = "SYNTHETIC-PRIVATE-ZOTERO-TITLE"
    project(setup, data)
    assert workspace_tree(load_registry(setup[0] / "docs/research-atlas")) == public
    assert bytes_tree(setup[0] / "docs/research-atlas/registry") == registry
    assert all("SYNTHETIC-PRIVATE-ZOTERO-TITLE" not in s for s in public.values())


@pytest.mark.parametrize("field", ["page", "section", "attachment_relative"])
@pytest.mark.parametrize(
    "literal",
    [
        "/synthetic/path",
        "C:/synthetic/path",
        "\\\\synthetic\\path",
        "file:synthetic",
        "../synthetic",
        "x\x00y",
    ],
)
def test_a43_unsafe_locator_rejected(field, literal):
    data = fixture_data()
    locator = data["items"][0]["annotations"][0]["locator"]
    locator[field] = (
        {"kind": "pdf-page", "value": literal} if field == "attachment_relative" else literal
    )
    with pytest.raises(z.ProjectionError):
        parsed(data)


def test_a43_locator_binding_and_markdown_escaping():
    data = fixture_data()
    data["items"][0]["annotations"][0]["text"] = (
        "Synthetic | [link](https://example.invalid) `<tag>`"
    )
    record = records(data)[0]
    for annotation in record.annotations:
        assert annotation.locator.source_version_id == record.source_version_id
        assert annotation.locator.attachment_identity == record.attachment_identity
        assert annotation.locator.annotation_key == annotation.annotation_key
    rendered = z.render_source(record).decode().split("\n---\n", 1)[1]
    assert "[link]" not in rendered and "<tag>" not in rendered
    assert "&#124;" in rendered
    data["items"][0]["annotations"][0]["locator"] = {}
    with pytest.raises(z.ProjectionError, match="human location"):
        parsed(data)


def test_a44_fixture_is_synthetic_and_has_no_attachment_input():
    data = fixture_data()
    assert len(data["items"]) == 3 and data["library_context"] == "fixture-library-alpha"
    for item in data["items"]:
        assert item["metadata"]["url"].startswith("https://example.invalid/")
        assert item["metadata"]["title"].startswith("Synthetic")
        assert all(a["text"].startswith("Synthetic") for a in item["annotations"])
        assert set(item["primary_attachment"]) == {"zotero_attachment_key", "sha256"}


def test_a45_operator_limits_and_review_gates():
    for path in (CONTRACT, ROOT / "docs/research-atlas/Private Research Wiki Projection.md"):
        text = path.read_text()
        for phrase in (
            "single writer",
            "per-file atomic",
            "manifest last",
            "unmanifested",
            "whole-tree transaction",
        ):
            assert phrase in text
    text = CONTRACT.read_text()
    assert "SCI" in text and "RA-4B" in text and "SKIP" in text and "RA-5" in text


def test_unexpected_fault_propagates(setup, monkeypatch):
    def fault(*args, **kwargs):
        raise RuntimeError("Synthetic unexpected failure")

    monkeypatch.setattr(z, "expected_tree", fault)
    with pytest.raises(RuntimeError, match="unexpected"):
        z.main(args(setup))


@pytest.mark.parametrize("kind", ["manifest", "source"])
def test_a24_a27_missing_owner_and_default_schema_fields_do_not_get_adopted(setup, kind):
    tree = project(setup)
    relative = z.MANIFEST if kind == "manifest" else next(iter(source_payloads(tree)))
    path = setup[1] / z.OWNED_ROOT / relative
    original = path.read_bytes()
    for field in ("generated_by", "fixture_schema_version", "import_schema_version"):
        raw = original.decode()
        props, body = (
            technical.markdown_parts(raw) if kind == "source" else (yaml.safe_load(raw), "")
        )
        del props[field]
        path.write_bytes(
            z.markdown(props, body) if kind == "source" else z.yaml_text(props).encode()
        )
        no_mutation(
            setup, lambda: project(setup), "lost" if kind == "manifest" else "digest changed"
        )
    path.write_bytes(original)
    assert project(setup, check=True) == tree


def test_a29_missing_current_cannot_erase_predecessor_or_reconstruct_different_bytes(setup):
    project(setup)
    data = mutate_version(fixture_data())
    tree = project(setup, data)
    new = records(data)[2]
    path = setup[1] / z.OWNED_ROOT / z.source_path(new.source_id, new.source_version_id)
    path.unlink()
    without_predecessor = copy.deepcopy(data)
    without_predecessor["items"][2]["predecessor"] = None
    setup[3].write_text(json.dumps(without_predecessor))
    no_mutation(setup, lambda: project(setup), "reconstructed exactly")
    assert project(setup, data) == tree


@pytest.mark.parametrize("where", ["repo", "vault", "fixture", "marker", "output"])
def test_required_inputs_and_targets_are_regular(setup, where):
    repo, vault, sha, export = setup
    if where == "repo":
        repo = export
    elif where == "vault":
        vault = export
    elif where == "fixture":
        export = vault
    elif where == "marker":
        path = vault / ".research-wiki-private"
        path.unlink()
        path.mkdir()
    else:
        (vault / z.OWNED_ROOT / z.INDEX).mkdir(parents=True)
    no_mutation(setup, lambda: z.project(repo, vault, sha, export))


@pytest.mark.parametrize("topology", ["same", "inside", "contains"])
def test_non_nested_topology(setup, topology):
    repo, vault, sha, export = setup
    if topology == "same":
        vault = repo
    elif topology == "inside":
        vault = repo / "nested-vault"
        vault.mkdir()
    else:
        vault = repo.parent
    no_mutation(setup, lambda: z.project(repo, vault, sha, export), "non-nested")
