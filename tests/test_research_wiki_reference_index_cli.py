"""A14/A15/A17/A19/A24/A28: real module CLI, synthetic committed sources and private vault."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from test_research_wiki_projection import commit, filesystem_state, git, write_note
from test_research_wiki_reference_index import sample_records

from fh_agent.research_atlas import private_views as views

ROOT = Path(__file__).resolve().parents[1]


def test_committed_cli_lifecycle_without_real_vault(tmp_path):
    repo = tmp_path / "synthetic-repo"
    vault = tmp_path / "synthetic-private"
    repo.mkdir()
    vault.mkdir()
    shutil.copytree(ROOT / "docs/research-atlas/registry", repo / "docs/research-atlas/registry")
    shutil.copytree(
        ROOT / "src/fh_agent/research_atlas",
        repo / "src/fh_agent/research_atlas",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (repo / "src/fh_agent/__init__.py").write_text('"""Synthetic fixture package."""\n')
    for relative in (views.PUBLIC_SOURCE, views.DIRECT_SOURCE):
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    git(repo, "init", "--quiet")
    sha = commit(repo)
    assert git(repo, "rev-parse", "HEAD") == sha
    (vault / ".research-wiki-private").write_text(
        'research_wiki_private_version: "1.0"\nproject: Planton361/autonomous-game-agent\n'
    )
    for record in sample_records():
        write_note(vault / "authored" / (record["wiki_id"] + ".md"), record)
    environment = os.environ | {"PYTHONPATH": str(repo / "src"), "PYTHONDONTWRITEBYTECODE": "1"}

    def cli(module, *extra):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fh_agent.research_atlas." + module,
                "--repo-root",
                str(repo),
                "--vault-root",
                str(vault),
                "--source-ref",
                sha,
                *extra,
            ],
            env=environment,
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert "SYNTHETIC-PRIVATE" not in result.stdout + result.stderr
        assert str(vault) not in result.stdout + result.stderr
        return result

    assert cli("private_projection").returncode == 0
    technical_before = filesystem_state(vault / "_generated/technical-atlas")
    public_before = filesystem_state(repo)
    assert cli("private_views").returncode == 0
    before_check = filesystem_state(vault)
    assert cli("private_views", "--check").returncode == 0
    assert filesystem_state(vault) == before_check
    root = vault / views.OWNED_ROOT
    assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == {
        str(views.MANIFEST),
        str(views.INDEX),
        str(views.DIRECT_BASE),
        str(views.TECHNICAL_BASE),
        str(views.NAVIGATION),
        str(views.REFERENCE_INDEX),
    }
    old_yaml = (root / views.REFERENCE_INDEX).read_bytes()
    payload = yaml.safe_load(old_yaml)
    assert payload["source_commit"] == sha
    assert len(payload["rows"]) == 45
    assert sum(r["row_kind"] == "declared-reference" for r in payload["rows"]) == 13
    assert sum(r["row_kind"] == "navigation-path" for r in payload["rows"]) == 32
    note = vault / "authored/READ-FIXTURE.md"
    note.write_text(note.read_text().replace("WRQ-FIXTURE", "WRQ-MISSING"))
    before_check = filesystem_state(vault)
    assert cli("private_views", "--check").returncode == 2
    assert filesystem_state(vault) == before_check
    assert cli("private_views").returncode == 0
    assert cli("private_views", "--check").returncode == 0
    assert (root / views.REFERENCE_INDEX).read_bytes() != old_yaml
    before_body = (root / views.REFERENCE_INDEX).read_bytes()
    note.write_text(note.read_text() + "\nSYNTHETIC-PRIVATE-BODY-ONLY\n")
    before_check = filesystem_state(vault)
    assert cli("private_views", "--check").returncode == 0
    assert filesystem_state(vault) == before_check
    assert (root / views.REFERENCE_INDEX).read_bytes() == before_body
    assert filesystem_state(repo) == public_before
    assert filesystem_state(vault / "_generated/technical-atlas") == technical_before
