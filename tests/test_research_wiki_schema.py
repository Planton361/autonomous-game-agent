"""Frozen flat contracts and public-safe source templates; no scientific adjudication."""

import copy
import re
from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from fh_agent.research_atlas import private_projection as projection
from fh_agent.research_atlas.validator import load_registry
from fh_agent.research_atlas.wiki_schema import (
    WIKI_PREFIXES,
    EpistemicRecord,
    WikiRecord,
    validate_wiki_records,
)
from fh_agent.research_atlas.workspace import workspace_tree

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/research-atlas"
TEMPLATES = ATLAS / "Wiki Templates"
ROLES = [
    "research_direct_subject_refs",
    "research_method_or_baseline_refs",
    "research_measurement_relevance_refs",
    "research_project_transfer_refs",
    "research_adjacent_context_refs",
]
LEGACY = dict(
    wiki_schema_version="0.1",
    wiki_id="PROC-FIXTURE",
    doc_type="process",
    privacy="private",
    export_policy="deny",
    atlas_refs=[],
)
EXTRA = {
    "dossier": dict(subject_refs=["CMP-CORTEX"]),
    "process": {},
    "topic": {},
    "reading_note": dict(
        paper_refs=["WPAPER-FIXTURE"],
        version_read=None,
        read_date=None,
        reading_depth="lead_only",
        checked_sections=[],
    ),
    "synthesis": dict(finding_refs=["WFIND-FIXTURE"]),
    "search_record": dict(target_refs=["WRQ-FIXTURE"], search_date=None),
    "journal_entry": dict(entry_date="2026-09-09"),
    "paper": dict(source_refs=["synthetic-source-v1"]),
    "finding": dict(
        claim_origin="our_inference", review_state="draft", source_refs=["synthetic-source-v1"]
    ),
    "research_question": dict(question_stage="idea", decision_state="none"),
    "experiment_lead": dict(rq_refs=["WRQ-FIXTURE"], question_stage="idea", decision_state="none"),
    "research_thread": dict(ordered_refs=["CMP-CORTEX"]),
    "decision_draft": dict(
        decision_type="Synthetic proposal",
        decision_scope="research_candidate",
        subject_refs=["WRQ-FIXTURE"],
        decision_record_state="draft",
    ),
}


def props(kind="process", **changes):
    return (
        dict(
            LEGACY,
            **dict(
                epistemic_schema_version="0.1",
                title="Synthetic fixture",
                record_version=1,
                document_maturity="draft",
                doc_type=kind,
                wiki_id=WIKI_PREFIXES[kind] + "-FIXTURE",
                **copy.deepcopy(EXTRA[kind]),
            ),
        )
        | changes
    )


def validate(data):
    return validate_wiki_records([data], {"CMP-CORTEX"})[0]


def test_legacy_is_unmigrated_and_tolerant():
    data = dict(LEGACY, opaque_future_property={"private": "SYNTHETIC-SECRET"})
    before = copy.deepcopy(data)
    result = validate(data)
    assert type(result) is WikiRecord
    assert result.model_dump() == LEGACY
    assert not hasattr(result, "epistemic_schema_version")
    assert not hasattr(result, "document_maturity")
    assert data == before
    assert validate_wiki_records([{}, {"doc_type": "ordinary"}], set()) == ()


@pytest.mark.parametrize("kind", WIKI_PREFIXES)
def test_all_thirteen_typed_profiles(kind):
    data = props(kind)
    before = copy.deepcopy(data)
    result = validate(data)
    assert isinstance(result, EpistemicRecord)
    assert result.doc_type == kind and result.epistemic_schema_version == "0.1"
    assert result.document_maturity == "draft"
    assert data == before


@pytest.mark.parametrize(
    "field",
    [
        "wiki_schema_version",
        "wiki_id",
        "doc_type",
        "privacy",
        "export_policy",
        "atlas_refs",
        "title",
        "record_version",
        "document_maturity",
    ],
)
def test_missing_common_field(field):
    data = props()
    del data[field]
    with pytest.raises(ValueError):
        validate(data)


@pytest.mark.parametrize("value", [None, "", "0.2", 0.1])
def test_bad_profile_version_cannot_fall_back_to_legacy(value):
    with pytest.raises(ValueError):
        validate(props(epistemic_schema_version=value))


@pytest.mark.parametrize("value", [0, -1, True, False, 1.0, "1"])
def test_strict_positive_record_version(value):
    with pytest.raises(ValueError):
        validate(props(record_version=value))


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_maturity", "accepted"),
        ("title", "  "),
        ("wiki_id", "READ-FIXTURE"),
        ("doc_type", "unrecognized"),
        ("atlas_refs", ["CMP-MISSING"]),
        ("atlas_refs", "CMP-CORTEX"),
        ("privacy", "public"),
        ("export_policy", "allow"),
        ("atlas_id", "CMP-CORTEX"),
    ],
)
def test_common_safety_guards(field, value):
    with pytest.raises(ValueError):
        validate(props(**{field: value}))


def test_duplicate_identity_across_legacy_and_profile():
    with pytest.raises(ValueError, match="Duplicate"):
        validate_wiki_records([LEGACY, props()], set())


@pytest.mark.parametrize(
    "field",
    [
        "confidence",
        "gap_confidence",
        "research_exhaustion",
        "maturity_score",
        "unknown_property",
        "implementation_status",
        "verification_status",
        "architecture_authority",
        "part_of",
        "research_direction",
    ],
)
@pytest.mark.parametrize("kind", WIKI_PREFIXES)
def test_unknown_profile_fields_fail_closed(kind, field):
    with pytest.raises(ValidationError, match="Extra inputs"):
        validate(props(kind, **{field: 0.9}))


@pytest.mark.parametrize("role", ROLES)
def test_research_roles_are_flat_and_non_implicative(role):
    result = validate(props(**{role: ["CMP-CORTEX"]}))
    assert getattr(result, role) == ["CMP-CORTEX"]
    assert all(getattr(result, other) == [] for other in ROLES if other != role)
    assert result.atlas_refs == [] and result.document_maturity == "draft"
    for invalid in ("CMP-CORTEX", {"target": "CMP-CORTEX"}, [["CMP-CORTEX"]], [" "], None):
        with pytest.raises(ValueError):
            validate(props(**{role: invalid}))


def test_dossier_subject_and_revision_lineage():
    with pytest.raises(ValueError, match="Dossier"):
        validate(props("dossier", subject_refs=[]))
    validate(props("dossier", subject_refs=[], atlas_refs=["CMP-CORTEX"]))
    with pytest.raises(ValueError, match="lineage"):
        validate(props(document_maturity="superseded"))
    validate(props(document_maturity="superseded", supersedes_refs=["PROC-PREVIOUS"]))


@pytest.mark.parametrize(
    "sources",
    [
        {},
        {"paper_refs": [], "source_refs": []},
        {"paper_refs": ["WPAPER-A"], "source_refs": ["SOURCE-A"]},
        {"paper_refs": ["WPAPER-A"], "source_refs": []},
        {"paper_refs": ["WPAPER-A", "WPAPER-B"]},
        {"source_refs": ["A", "B"]},
    ],
)
def test_reading_exactly_one_source(sources):
    data = props("reading_note")
    del data["paper_refs"]
    with pytest.raises(ValueError):
        validate(data | sources)


def test_reading_source_alternative():
    data = props("reading_note")
    del data["paper_refs"]
    assert validate(data | {"source_refs": ["source-version"]}).source_refs == ["source-version"]


@pytest.mark.parametrize(
    "changes",
    [
        {"checked_sections": ["metadata"]},
        {"read_date": "2026-09-09"},
    ],
)
def test_lead_only_rules(changes):
    with pytest.raises(ValueError):
        validate(props("reading_note", **changes))


@pytest.mark.parametrize("section", ["metadata", "abstract", "methods", "results"])
def test_checked_depth_needs_named_section_without_ladder(section):
    data = props(
        "reading_note",
        reading_depth=section + "_checked",
        checked_sections=[section],
        version_read="v1",
        read_date="2026-09-09",
    )
    result = validate(data)
    assert result.checked_sections == [section]
    assert result.read_date == date(2026, 9, 9)
    for invalid in ([], ["discussion"]):
        with pytest.raises(ValueError):
            validate(data | {"checked_sections": invalid})


@pytest.mark.parametrize(
    "depth",
    [
        "metadata_checked",
        "abstract_checked",
        "methods_checked",
        "results_checked",
        "relevant_fulltext_checked",
    ],
)
@pytest.mark.parametrize(
    "field,value",
    [
        ("version_read", None),
        ("version_read", ""),
        ("version_read", "  "),
        ("read_date", None),
    ],
)
def test_checked_reading_needs_version_date(depth, field, value):
    data = props(
        "reading_note",
        reading_depth=depth,
        version_read="v1",
        read_date="2026-09-09",
        checked_sections=["metadata", "abstract", "methods", "results"],
    )
    with pytest.raises(ValueError):
        validate(data | {field: value})


def test_fulltext_scope_and_closed_reading_enums():
    data = props(
        "reading_note",
        reading_depth="relevant_fulltext_checked",
        version_read="v1",
        read_date="2026-09-09",
        checked_sections=["methods", "limitations"],
    )
    assert validate(data).checked_sections == ["methods", "limitations"]
    for changes in (
        {"checked_sections": []},
        {"checked_sections": ["all"]},
        {"reading_depth": "fully_verified"},
    ):
        with pytest.raises(ValueError):
            validate(data | changes)


@pytest.mark.parametrize(
    "kind,field",
    [
        ("synthesis", "finding_refs"),
        ("search_record", "target_refs"),
        ("paper", "source_refs"),
        ("finding", "source_refs"),
        ("experiment_lead", "rq_refs"),
        ("research_thread", "ordered_refs"),
    ],
)
def test_required_nonempty_references(kind, field):
    for invalid in ([], [" "], None):
        with pytest.raises(ValueError):
            validate(props(kind, **{field: invalid}))


@pytest.mark.parametrize("maturity", ["in_review", "domain_accepted", "superseded", "archived"])
def test_non_draft_search_needs_actual_date(maturity):
    data = props("search_record", document_maturity=maturity, supersedes_refs=["SEARCH-OLD"])
    with pytest.raises(ValueError):
        validate(data)
    validate(data | {"search_date": "2026-09-09"})


@pytest.mark.parametrize("kind", WIKI_PREFIXES)
def test_each_declared_required_property_is_required(kind):
    data = props(kind)
    for field in EXTRA[kind]:
        # Dossier's alternate subject condition is tested separately.
        missing = data.copy()
        del missing[field]
        with pytest.raises(ValueError):
            validate(missing)


@pytest.mark.parametrize("field", ["claim_origin", "review_state"])
def test_finding_enums(field):
    with pytest.raises(ValueError):
        validate(props("finding", **{field: "unknown"}))


@pytest.mark.parametrize("origin", ["authors_result", "authors_limitation"])
def test_author_finding_needs_reading_note(origin):
    data = props("finding", claim_origin=origin)
    with pytest.raises(ValueError):
        validate(data)
    validate(data | {"reading_note_refs": ["READ-FIXTURE"]})


@pytest.mark.parametrize("origin", ["our_inference", "own_empirical_result"])
@pytest.mark.parametrize("state", ["draft", "checked", "domain_accepted"])
def test_finding_origin_review_do_not_promote_document(origin, state):
    result = validate(props("finding", claim_origin=origin, review_state=state))
    assert result.document_maturity == "draft" and result.reading_note_refs == []


@pytest.mark.parametrize("kind", ["research_question", "experiment_lead"])
@pytest.mark.parametrize("state", ["accepted", "deprioritized", "killed", "superseded"])
def test_candidate_decisions_need_refs(kind, state):
    data = props(kind, question_stage="candidate", decision_state=state)
    with pytest.raises(ValueError):
        validate(data)
    result = validate(data | {"decision_refs": ["WDEC-FIXTURE"]})
    assert result.document_maturity == "draft"


@pytest.mark.parametrize("kind", ["research_question", "experiment_lead"])
@pytest.mark.parametrize("stage", ["idea", "researchable", "literature_mapped", "needs_closure"])
def test_accepted_requires_candidate(kind, stage):
    with pytest.raises(ValueError):
        validate(
            props(
                kind,
                question_stage=stage,
                decision_state="accepted",
                decision_refs=["WDEC-FIXTURE"],
            )
        )


@pytest.mark.parametrize("kind", ["research_question", "experiment_lead"])
@pytest.mark.parametrize("field", ["question_stage", "decision_state"])
def test_candidate_enums(kind, field):
    with pytest.raises(ValueError):
        validate(props(kind, **{field: "unknown"}))


@pytest.mark.parametrize("kind", ["topic", "research_thread"])
@pytest.mark.parametrize("field", ["question_stage", "decision_state", "research_direction"])
def test_non_candidates_have_no_candidate_properties(kind, field):
    with pytest.raises(ValidationError, match="Extra inputs"):
        validate(props(kind, **{field: "candidate"}))


def test_paper_does_not_have_reading_depth():
    with pytest.raises(ValidationError, match="Extra inputs"):
        validate(props("paper", reading_depth="lead_only"))


@pytest.mark.parametrize("subjects", [[], ["A", "B"]])
def test_decision_one_subject(subjects):
    with pytest.raises(ValueError):
        validate(props("decision_draft", subject_refs=subjects))


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision_scope", "research"),
        ("decision_record_state", "accepted"),
        ("decision_type", " "),
    ],
)
def test_decision_closed_fields(field, value):
    with pytest.raises(ValueError):
        validate(props("decision_draft", **{field: value}))


@pytest.mark.parametrize(
    "scope", ["research_candidate", "program", "study_protocol", "technical_reference"]
)
def test_recorded_decision_authority_and_independent_maturity(scope):
    data = props("decision_draft", decision_scope=scope, document_maturity="domain_accepted")
    assert validate(data).decision_record_state == "draft"
    with pytest.raises(ValueError):
        validate(data | {"decision_record_state": "recorded"})
    result = validate(
        data | {"decision_record_state": "recorded", "authority_refs": ["authority-v1"]}
    )
    assert result.decision_record_state == "recorded"


def test_private_profile_does_not_modify_public_output_or_ancestry():
    atlas = load_registry(ATLAS)
    before = workspace_tree(atlas)
    ancestry = {key: atlas.ancestors(key) for key in atlas.entities}
    data = props(title="SYNTHETIC-PRIVATE-RA2-SECRET", **{role: ["CMP-CORTEX"] for role in ROLES})
    validate_wiki_records([data], atlas.entities.keys())
    assert workspace_tree(atlas) == before
    assert all(data["title"] not in text for text in before.values())
    assert {key: atlas.ancestors(key) for key in atlas.entities} == ancestry


def test_existing_projection_checks_profile_without_writes(tmp_path, monkeypatch, capsys):
    vault = tmp_path / "synthetic-vault"
    vault.mkdir()
    (vault / ".research-wiki-private").write_text(
        'research_wiki_private_version: "1.0"\nproject: Planton361/autonomous-game-agent\n'
    )
    note = vault / "authored.md"
    data = props()
    note.write_text("---\n" + yaml.safe_dump(data) + "---\nSYNTHETIC-SECRET\n")
    # Git source safety is exercised by unchanged RA-1 tests; here isolate delegation.
    monkeypatch.setattr(projection, "source_state", lambda *_: "a" * 40)
    projection.project(ROOT, vault, "HEAD")
    args = ["--repo-root", str(ROOT), "--vault-root", str(vault), "--source-ref", "HEAD", "--check"]
    assert projection.main(args) == 0
    data["confidence"] = 0.9
    note.write_text("---\n" + yaml.safe_dump(data) + "---\nSYNTHETIC-SECRET\n")
    before = {
        p: (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
        for p in [vault, *vault.rglob("*")]
    }
    assert projection.main(args) == 2
    assert "Traceback" not in capsys.readouterr().err
    assert {
        p: (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
        for p in [vault, *vault.rglob("*")]
    } == before


TEMPLATE_CONTRACTS = {
    "DOS — Dossier.md": (
        "dossier",
        [
            "Purpose / exact subject",
            "Scope / non-responsibilities",
            "Technical projection references and source state",
            "Interfaces/data/process context",
            "Research roles",
            "Open questions / limits",
        ],
    ),
    "PROC — Process.md": (
        "process",
        [
            "Purpose/scope and descriptive vs proposed character",
            "Trigger/preconditions",
            "Participants",
            "Inputs",
            "Steps/branches",
            "Outputs/closure",
            "Measurements/evidence",
            "Open research questions / uncertainty",
        ],
    ),
    "TOPIC — Topic Method.md": (
        "topic",
        [
            "Definition",
            "Boundaries/synonyms",
            "Method principle/assumptions/conditions/limits",
            "Literature roles",
            "Open questions",
        ],
    ),
    "READ — Reading Note.md": (
        "reading_note",
        [
            "Source identity/version/check protocol",
            "Research question and actual approach",
            "Population/task/environment",
            "Treatment/comparison/fixed factors",
            "Agent information/Memory/training/weights",
            "Resources/budgets/experimental unit",
            "Outcomes/measurement/analysis",
            "Authors' findings with locators",
            "Authors' explicit limitations with locators",
            "Our interpretation/inference",
            "Applicability/transfer limits",
            "Unknown/not-reported/open verification questions",
        ],
    ),
    "SYN — Synthesis.md": (
        "synthesis",
        [
            "Synthesis question and inclusion/exclusion scope",
            "Constituent Findings with revisions/origins/review state",
            "Study/version/data dependencies",
            "Agreement",
            "Differences",
            "Genuine contradictions",
            "Moderators/conditions",
            "Established explanations",
            "Our inference",
            "Alternatives",
            "Unresolved uncertainty",
            "Next check",
        ],
    ),
    "SEARCH — Search Record.md": (
        "search_record",
        [
            "Exact target question/claim revision",
            "Search execution date(s)",
            "Search spaces/access limits",
            "Queries/query families actually executed",
            "Filters/time range",
            "Inclusion/exclusion",
            "Screening method",
            "Checking depth",
            "Relevant results",
            "Relevant exclusions/reasons",
            "Coverage wording",
            "Limitations",
            "Supersession/version history",
        ],
    ),
    "JOURNAL — Journal Discussion.md": (
        "journal_entry",
        [
            "Occasion/date/participants",
            "Origin/chat/discussion locator",
            "Actual ideas/dissent",
            "Open points",
            "Later promoted/derived object links",
        ],
    ),
    "WPAPER — Paper Identity.md": (
        "paper",
        [
            "Identifying metadata/source locator",
            "Publication/preprint character",
            "Version list/date/locator/relationships",
            "ReadingNote links",
            "Identity uncertainties/corrections",
        ],
    ),
    "WFIND — Finding.md": (
        "finding",
        [
            "Atomic proposition",
            "Population/task/environment",
            "Compared/reference conditions",
            "Outcome/measurement",
            "Scope/conditions",
            "Source evidence table with version and concrete locator",
            "Limitations/applicability/counterevidence",
            "supports/contradicts/qualifies assessment",
            "Origin-specific reasoning",
            "Review record",
        ],
    ),
    "WRQ — Research Question.md": (
        "research_question",
        [
            "Exact question/claim revision and scope",
            "Knowledge target/estimand",
            "Closest relevant comparison",
            "Search/literature state and limitations",
            "Discriminating/falsifiable test idea",
            "Validity/resource risks",
            "Closure points",
            "Stage history",
            "Decision history",
        ],
    ),
    "WLEAD — Experiment Lead.md": (
        "experiment_lead",
        [
            "RQ revision",
            "Proposed treatment/reference comparison",
            "Outcome and experimental unit",
            "Proposed fixed/variable factors",
            "Required data/measurement and technical evidence state",
            "Falsifiability/knowledge criterion",
            "Resources/integrity/validity risks",
            "Search/review state",
            "Stage history",
            "Decision history",
            "Not execution authorization",
        ],
    ),
    "WTHREAD — Research Thread.md": (
        "research_thread",
        [
            "Organizing purpose/question",
            "Ordered references with named roles",
            "Meaning/limits of ordering",
            "Related candidates/open connections",
            "Non-causal/non-hierarchical semantics",
        ],
    ),
    "WDEC — Decision Draft History.md": (
        "decision_draft",
        [
            "Decision type/scope",
            "Exact subject ID/version/claim wording",
            "Previous state / new state / named axis",
            "Rationale and criterion",
            "Versioned Search/Synthesis/Review inputs",
            "Authority/actor/date",
            "Verifiable decision record/evidence",
            "Effective scope",
            "Supersedes/overrules or none",
            "Explicit non-scope",
            "Later additions separated from original decision state",
        ],
    ),
}


def test_exact_template_set():
    assert {p.name for p in TEMPLATES.iterdir()} == set(TEMPLATE_CONTRACTS)
    assert len(TEMPLATE_CONTRACTS) == 13


@pytest.mark.parametrize("filename", TEMPLATE_CONTRACTS)
def test_template_contracts_and_public_safe_placeholders(filename):
    kind, headings = TEMPLATE_CONTRACTS[filename]
    text = (TEMPLATES / filename).read_text(encoding="utf-8")
    assert text.startswith("# ") and not text.startswith("---")
    assert "not an active private record" in text
    assert "<TO BE AUTHORED; NOT REVIEWED>" in text
    assert "## B0 — Provenance and revision/review record\n" in text
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
    for field in ("Review actor", "Review role", "Review date", "Review scope", "Review result"):
        assert "| " + field + " | not reviewed |" in text
    for heading in headings:
        assert "\n## " + heading + "\n" in text
    blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.S)
    assert len(blocks) == 2
    required, optional = [yaml.safe_load(block) for block in blocks]
    assert not (required.keys() & optional.keys())
    assert required["doc_type"] == kind
    assert required["wiki_id"] == WIKI_PREFIXES[kind] + "-<UNIQUE-ID>"
    assert required["document_maturity"] == "draft"
    assert required.get("review_state", "draft") == "draft"
    assert required.get("decision_state", "none") == "none"
    assert required.get("decision_record_state", "draft") == "draft"
    # Resolve only explicit syntactic placeholders, not scientific body content.
    required["wiki_id"] = WIKI_PREFIXES[kind] + "-TEMPLATE-FIXTURE"
    if kind == "journal_entry":
        required["entry_date"] = "2026-09-09"
    record = validate(required | optional)
    model_fields = type(record).model_fields
    assert set(required) | set(optional) <= set(model_fields)
    # Expose every permitted property; ReadingNote documents its exclusive alternative.
    alternatives = {"source_refs"} if kind == "reading_note" else set()
    assert set(required) | set(optional) | alternatives == set(model_fields)
    assert {name for name, field in model_fields.items() if field.is_required()} <= set(required)
    assert "atlas_id" not in required and "atlas_id" not in optional
    assert not re.search(r"(?:/home/|/Users/|/private/|[A-Z]:[\\/])", text)
    assert "SYNTHETIC-PRIVATE-RA2-SECRET" not in text
    assert "Placeholders are not evidence" in text
    assert "No automatic private-to-public promotion" in text
    assert "no Wiki-to-Agent-Memory connection" in text
