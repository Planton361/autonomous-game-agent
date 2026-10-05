# ruff: noqa: F811
"""Synthetic intake filesystem lifecycle and ownership proofs; no actual vault."""

import json

import pytest
from rq_reader_fixtures import fictional_catalog
from test_research_intake import properties, write_records
from test_research_wiki_projection import filesystem_state
from test_workspace_harness import setup  # noqa: F401,F811

from fh_agent.research_atlas import private_projection as technical
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import research_intake as intake
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.validator import load_registry


def file_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("populated", [False, True])
def test_intake_validate_render_inspect_idempotent_zero_write_authored_protection(
    setup, populated, capsys
):
    repo, vault, _ = setup
    atlas = load_registry(repo / "docs/research-atlas")
    data = properties(atlas) if populated else []
    if populated:
        write_records(vault, data)
        (vault / ".research-source-catalog.json").write_text(fictional_catalog().model_dump_json())
    args = ["--repo-root", str(repo), "--vault-root", str(vault)]
    before = filesystem_state(vault)
    assert intake.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["scientific_acceptance"] is False
    assert filesystem_state(vault) == before
    workspace.apply(repo, vault)
    rendered = filesystem_state(vault)
    for path, content in before.items():
        if not content[2]:
            assert rendered[path] == content
    assert intake.main(args + ["--check-generated"]) == 0
    assert filesystem_state(vault) == rendered
    rendered_bytes = file_bytes(vault)
    workspace.apply(repo, vault)
    assert file_bytes(vault) == rendered_bytes
    refreshed = filesystem_state(vault)
    workspace.check(repo, vault)
    assert filesystem_state(vault) == refreshed
    if populated:
        page = next((vault / views.OWNED_ROOT / "research-questions").glob("*.md")).read_text()
        assert "Recovery under missing observations" in page
        assert "Checked version 1" in page and "srcv-cedar1" in page
        assert (vault / "intake/READ-CEDAR.md").read_bytes() == before["intake/READ-CEDAR.md"][3]
    else:
        assert not list((vault / views.OWNED_ROOT / "research-questions").glob("*.md"))


def test_cli_invalid_reference_zero_write_and_owner_loss_no_overwrite(setup, capsys):
    repo, vault, _ = setup
    atlas = load_registry(repo / "docs/research-atlas")
    data = properties(atlas)
    data[0]["search_refs"] = ["SEARCH-MISSING"]
    write_records(vault, data)
    args = ["--repo-root", str(repo), "--vault-root", str(vault)]
    before = filesystem_state(vault)
    assert intake.main(args) == 2
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "missing-reference" for d in result["diagnostics"])
    assert filesystem_state(vault) == before
    data[0]["search_refs"] = ["WPAPER-CEDAR"]
    write_records(vault, data)
    wrong_type_state = filesystem_state(vault)
    assert intake.main(args) == 2
    result = json.loads(capsys.readouterr().out)
    assert any(d["code"] == "wrong-type-reference" for d in result["diagnostics"])
    assert filesystem_state(vault) == wrong_type_state
    data[0]["search_refs"] = []
    write_records(vault, data)
    workspace.apply(repo, vault)
    page = next((vault / views.OWNED_ROOT / "research-questions").glob("*.md"))
    page.write_text(page.read_text().replace("research-wiki-derived", "owner-lost"))
    protected = filesystem_state(vault)
    assert intake.main(args + ["--check-generated"]) == 2
    assert filesystem_state(vault) == protected
    protected_bytes = file_bytes(vault)
    with pytest.raises(workspace.WorkspaceError):
        workspace.apply(repo, vault)
    assert file_bytes(vault) == protected_bytes


def test_prior_index_owner_loss_fail_closed_zero_write(setup):
    repo, vault, _ = setup
    workspace.apply(repo, vault)
    path = vault / technical.OWNED_ROOT / technical.INDEX
    path.write_text(path.read_text().replace(technical.OWNER, "lost-owner"))
    before = filesystem_state(vault)
    with pytest.raises(technical.ProjectionError, match="owner marker lost"):
        intake.previous_subjects(vault)
    assert filesystem_state(vault) == before
