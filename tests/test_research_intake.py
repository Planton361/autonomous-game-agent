"""Synthetic #128 intake/maintenance proofs; never an actual Research corpus."""

import re
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from rq_reader_fixtures import fictional_catalog, fictional_records
from test_workspace_harness import setup  # noqa: F401

from fh_agent.research_atlas import research_intake as intake
from fh_agent.research_atlas.private_reference_index import fingerprint, make_snapshot
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.wiki_schema import WIKI_PREFIXES, validate_wiki_records

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
TYPES = {
    "research_question": "WRQ — Research Question.md",
    "search_record": "SEARCH — Search Record.md",
    "paper": "WPAPER — Paper Identity.md",
    "reading_note": "READ — Reading Note.md",
    "finding": "WFIND — Finding.md",
    "synthesis": "SYN — Synthesis.md",
    "dossier": "DOS — Dossier.md",
    "decision_draft": "WDEC — Decision Draft History.md",
}


@pytest.fixture(scope="module")
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


def properties(atlas):
    return [r.model_dump(mode="json", exclude_unset=True) for r in fictional_records(atlas)]


def inspect(atlas, data, **kwargs):
    return intake.inspect_records(atlas, data, fictional_catalog(), COMMIT, **kwargs)


def codes(report):
    return {d.code for d in report.diagnostics}


def write_records(vault, data):
    directory = vault / "intake"
    directory.mkdir(exist_ok=True)
    for props in data:
        (directory / (props["wiki_id"] + ".md")).write_text(
            "---\n" + yaml.safe_dump(props, sort_keys=True) + "---\n\nAuthored synthetic body.\n"
        )


@pytest.mark.parametrize("kind", TYPES)
def test_templates_create_explicit_drafts_with_current_opt_in(atlas, kind):
    text = (ROOT / "docs/research-atlas/Wiki Templates" / TYPES[kind]).read_text()
    blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.S)
    required, optional = [yaml.safe_load(b) for b in blocks[:2]]
    data = required | optional
    data["wiki_id"] = WIKI_PREFIXES[kind] + "-INTAKE"
    data["title"] = "Synthetic human title"
    for field, values in {
        "subject_refs": ["CMP-CORTEX"],
        "target_refs": ["CMP-CORTEX"],
        "source_refs": ["srcf-cedar"],
        "paper_refs": ["WPAPER-CEDAR"],
        "finding_refs": ["WFIND-CEDAR"],
    }.items():
        if field in data and data[field]:
            data[field] = values
    if len(blocks) == 3:
        data.update(yaml.safe_load(blocks[2]))
    record = validate_wiki_records([data], atlas.entities.keys())[0]
    assert record.document_maturity == "draft"
    assert getattr(record, "review_state", "draft") == "draft"
    assert getattr(record, "decision_record_state", "draft") == "draft"
    assert record.privacy == "private" and record.export_policy == "deny"
    assert "Research%20Intake%20and%20Maintenance.md" in text


def test_empty_populated_deterministic_and_nonmutating(atlas):
    assert inspect(atlas, []).valid
    data = properties(atlas)
    before = deepcopy(data)
    report = inspect(atlas, data)
    assert report.valid
    assert "multi-subject-question" in codes(report)
    assert "different-navigation-version" in codes(report)
    assert report == inspect(atlas, list(reversed(data)))
    assert data == before
    assert report.private_input_fingerprint == fingerprint(make_snapshot(data, atlas))
    assert report == inspect(atlas, data)


@pytest.mark.parametrize(
    "target,code", [("WRQ-MISSING", "missing-reference"), ("WPAPER-CEDAR", "wrong-type-reference")]
)
def test_missing_wrong_type_failure_is_actionable_nonmutating(atlas, target, code):
    data = properties(atlas)
    data[0]["search_refs"] = [target]
    before = deepcopy(data)
    report = inspect(atlas, data)
    assert not report.valid and code in codes(report)
    issue = next(d for d in report.diagnostics if d.code == code and d.field == "search_refs")
    assert issue.record == "WRQ-OBSERVER" and issue.action
    assert data == before


@pytest.mark.parametrize(
    "target,code", [("WPAPER-MISSING", "missing-reference"), ("READ-CEDAR", "wrong-type-reference")]
)
def test_nested_reference_diagnostics_even_in_draft(atlas, target, code):
    data = properties(atlas)
    data[0]["document_maturity"] = "draft"
    data[0]["presentation_analysis"]["literature_rows"][0]["paper_ref"] = target
    report = inspect(atlas, data)
    assert not report.valid and code in codes(report)
    assert any(
        d.field == "presentation_analysis.literature_rows.paper_ref" for d in report.diagnostics
    )


def test_no_duplicate_identity_and_stale_review_preservation(atlas):
    data = properties(atlas)
    with pytest.raises(ValueError, match="Duplicate"):
        inspect(atlas, data + [deepcopy(data[1])])
    data[1]["record_version"] = 2
    before = deepcopy(data)
    report = inspect(atlas, data)
    assert any("stale" in d.action for d in report.diagnostics)
    assert data == before
    data[0]["document_maturity"] = "superseded"
    data[0]["supersedes_refs"] = ["WRQ-PREDECESSOR"]
    assert "historical-analysis" in codes(inspect(atlas, data))


def test_synthetic_approved_child_and_rename_without_registry_write(atlas):
    prior = {i: {"display_name": n.name} for i, n in atlas.entities.items()}
    entities = dict(atlas.entities)
    entities["CMP-INTAKE-SYNTHETIC"] = entities["CMP-CORTEX"].model_copy(
        update={"id": "CMP-INTAKE-SYNTHETIC", "name": "Synthetic approved child"}
    )
    entities["CMP-CORTEX"] = entities["CMP-CORTEX"].model_copy(
        update={"name": "Renamed synthetic label"}
    )
    changed = replace(atlas, entities=entities)
    data = properties(atlas)
    data[0]["research_direct_subject_refs"].append("CMP-INTAKE-SYNTHETIC")
    report = inspect(changed, data, previous_subjects=prior)
    assert report.valid
    assert {"new-technical-subject", "renamed-technical-subject"} <= codes(report)
    assert "CMP-INTAKE-SYNTHETIC" not in atlas.entities


def test_source_change_fingerprints_preserve_read_and_review_states(atlas):
    data = properties(atlas)
    before = deepcopy(data)
    original = fictional_catalog()
    changed = original.model_copy(
        update={
            "families": [
                original.families[0].model_copy(update={"preferred_version_ref": "srcv-cedar1"})
            ]
        }
    )
    report = intake.inspect_records(atlas, data, changed, COMMIT)
    assert (
        report.source_resolution_input_fingerprint
        != inspect(atlas, data).source_resolution_input_fingerprint
    )
    assert report.private_input_fingerprint == inspect(atlas, data).private_input_fingerprint
    assert (
        report.presentation_input_fingerprint == inspect(atlas, data).presentation_input_fingerprint
    )
    assert data == before
    assert data[2]["version_read"] == "srcv-cedar1"
    assert data[3]["review_state"] == "domain_accepted"


def test_reuse_paper_and_reading_note_in_two_rqs_without_duplicate_identity(atlas):
    data = properties(atlas)
    second = deepcopy(data[0])
    second["wiki_id"] = "WRQ-SECOND"
    second["title"] = "Second synthetic context"
    second["presentation_analysis"]["conclusion"] = None
    second["presentation_analysis"]["nearest_work_rows"] = []
    second["presentation_analysis"]["establishes"] = []
    second["review_refs"] = []
    data[1]["research_direct_subject_refs"].append(second["wiki_id"])
    context = deepcopy(data[1]["presentation_contexts"][0])
    context["target_ref"] = second["wiki_id"]
    context["why_relevant"] = "Explicitly authored second synthetic context."
    data[1]["presentation_contexts"].append(context)
    data.append(second)
    assert inspect(atlas, data).valid
    records = validate_wiki_records(data, atlas.entities.keys())
    assert sum(r.doc_type == "paper" for r in records) == 1
    assert sum(r.doc_type == "reading_note" for r in records) == 1
    assert sum(r.doc_type == "research_question" for r in records) == 2
