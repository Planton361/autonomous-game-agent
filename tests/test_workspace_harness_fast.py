"""Fast fail-closed orchestration contracts for the private Workspace harness."""

import html
import json
import posixpath
import re
from dataclasses import replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import pytest
import yaml
from test_research_wiki_schema import props as wiki_props

from fh_agent.research_atlas import private_projection as technical_projection
from fh_agent.research_atlas import private_views as views
from fh_agent.research_atlas import workspace_harness as workspace
from fh_agent.research_atlas.private_projection import ProjectionError
from fh_agent.research_atlas.private_reference_index import (
    build_index,
    component_navigation_rows,
    make_snapshot,
)
from fh_agent.research_atlas.schema import DataArtifact, Relationship
from fh_agent.research_atlas.validator import Atlas, load_registry, validate_registry
from fh_agent.research_atlas.wiki_schema import WIKI_PREFIXES

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "a" * 40
DETAIL_ENDPOINTS = (
    "IF-MEM-CORTEX",
    "CON-CORTEX-CONTEXT",
    "DAT-RETRIEVAL-SNAPSHOT",
    "MEAS-RETRIEVAL-DELIVERY-001",
    "CON-VERIFIER-RESULT",
    "DAT-OBSERVATION",
    "DAT-VISIBLE-OUTCOME",
)


@pytest.fixture
def atlas():
    return load_registry(ROOT / "docs/research-atlas")


def component_research_fixture_records():
    """Synthetic RA-2 rows for every accepted N-C prefix and audit boundary."""
    memory = "CMP-MEM-RETRIEVAL"
    return [
        wiki_props("paper", wiki_id="WPAPER-K0", research_direct_subject_refs=[memory]),
        wiki_props("paper", wiki_id="WPAPER-K1-INVERSE"),
        wiki_props(
            "reading_note",
            wiki_id="READ-K1-INVERSE",
            paper_refs=["WPAPER-K1-INVERSE"],
            research_measurement_relevance_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K1-FORWARD", reading_note_refs=["READ-K1-FORWARD"]),
        wiki_props(
            "reading_note",
            wiki_id="READ-K1-FORWARD",
            paper_refs=["WPAPER-K1-FORWARD"],
            research_project_transfer_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K2"),
        wiki_props(
            "finding",
            wiki_id="WFIND-K2",
            source_refs=["WPAPER-K2"],
            research_adjacent_context_refs=[memory],
        ),
        wiki_props("paper", wiki_id="WPAPER-K3"),
        wiki_props(
            "reading_note",
            wiki_id="READ-K3",
            paper_refs=["WPAPER-K3"],
            finding_refs=["WFIND-K3"],
        ),
        wiki_props(
            "finding",
            wiki_id="WFIND-K3",
            research_method_or_baseline_refs=[memory],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-VERIFIER",
            research_direct_subject_refs=["CMP-INDEPENDENT-VERIFIER"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-OTHER-COMPONENT",
            research_direct_subject_refs=["CMP-CORTEX"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-DOMAIN-SIBLING",
            research_direct_subject_refs=["CMP-MEMORY"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-INTERFACE",
            research_direct_subject_refs=["IF-MEM-CORTEX"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-CONTRACT",
            research_direct_subject_refs=["CON-VERIFIER-RESULT"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-DATA",
            research_direct_subject_refs=["DAT-OBSERVATION"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-MEASUREMENT",
            research_direct_subject_refs=["MEAS-RETRIEVAL-DELIVERY-001"],
        ),
        wiki_props("reading_note", wiki_id="READ-WRONG-TYPE", paper_refs=[memory]),
        wiki_props("reading_note", wiki_id="READ-UNRESOLVED", paper_refs=["WPAPER-MISSING"]),
    ]


def component_research_tree(atlas, records=None, *, locators=None):
    records = component_research_fixture_records() if records is None else records
    snapshot = make_snapshot(records, atlas)
    private_records = views.landscape_private_records(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    if locators is None:
        locators = {
            record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
            for record in records
        }
    if "WFIND-K3" in locators:
        locators["WFIND-K3"] = PurePosixPath("authored/finding [fixture] #3.md")
    return (
        views.reference_views_tree(
            SOURCE_COMMIT,
            (ROOT / views.PUBLIC_SOURCE).read_bytes(),
            (ROOT / views.DIRECT_SOURCE).read_bytes(),
            reference,
            atlas,
            locators,
            snapshot,
            False,
            private_records,
        ),
        snapshot,
        reference,
        locators,
    )


def identity_page_tree(atlas, records=None):
    """Build the finite identity-page slice with synthetic authored Research only."""
    records = [] if records is None else records
    snapshot = make_snapshot(records, atlas)
    private_records = views.landscape_private_records(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
        for record in records
    }
    tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        private_records,
    )
    return tree, snapshot, reference, locators


def identity_page_audit_text(page):
    """Return collapsed audit content while asserting native disclosure syntax."""
    visible = page.split(views.IDENTITY_PAGE_METADATA_MARKER, 1)[0]
    section = visible.split("## Registry / Audit\n", 1)[1].split("## Return Navigation\n", 1)[0]
    assert section.startswith("\n> [!aga-audit]- Registry / Audit\n")
    quoted_lines = section.splitlines()[1:]
    assert quoted_lines[0] == "> [!aga-audit]- Registry / Audit"
    assert all(not line.strip() or line.startswith(">") for line in quoted_lines)
    return "\n".join(line[2:] for line in quoted_lines[1:] if line.startswith("> "))


def test_rm1_identity_pages_reuse_one_human_first_model_and_exact_routes(atlas):
    secret_title = "SYNTHETIC-PRIVATE-IDENTITY-PAGE-SECRET"
    records = [
        wiki_props(
            "paper",
            wiki_id="WPAPER-RM1-PERCEPTION",
            title=secret_title,
            research_direct_subject_refs=["CMP-PERCEPTION"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-RM1-OBSERVATION",
            title=secret_title,
            research_direct_subject_refs=["DAT-OBSERVATION"],
        ),
    ]
    tree, _, reference, _ = identity_page_tree(atlas, records)
    expected_types = {
        "CMP-PERCEPTION": "Component",
        "CMP-OBSERVATION-BUILDER": "Component",
        "CMP-PERCEPTION-UI-STATE": "Component",
        "DAT-OBSERVATION": "DataArtifact",
    }
    assert set(views.IDENTITY_PAGE_TYPES.items()) == set(expected_types.items())
    assert set(views.IDENTITY_PAGE_PATHS) == set(expected_types)
    assert views.IDENTITY_PAGE_PAYLOADS == frozenset(views.IDENTITY_PAGE_PATHS.values())

    audit_rows_by_identity = {}
    for identity, expected_type in expected_types.items():
        path = views.IDENTITY_PAGE_PATHS[identity]
        rendered = tree[path].decode()
        properties, body = views.markdown_parts(rendered)
        subject = atlas.entities[identity]
        assert properties == {}
        assert not rendered.startswith("---\n")
        assert rendered.startswith(f"# {subject.name}\n")
        metadata = views._identity_page_generated_metadata(rendered, path)
        assert metadata == {
            "generated_by": views.OWNER,
            "source_repository": views.REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "identity_page_schema_version": views.IDENTITY_PAGE_SCHEMA_VERSION,
            "identity_page_subject_id": identity,
            "identity_page_registry_type": expected_type,
            "identity_page_path": str(path),
            "source_registry_revision": views.registry_content_revision(atlas),
            "reference_index_schema_version": "1.1",
            "private_input_fingerprint": reference.private_input_fingerprint,
        }
        assert rendered.count(views.IDENTITY_PAGE_METADATA_MARKER) == 1
        visible = rendered.split(views.IDENTITY_PAGE_METADATA_MARKER, 1)[0]
        first_view = visible.split("## Technical\n", 1)[0]
        assert first_view.index(f"# {subject.name}") < first_view.index(subject.description)
        identity_metadata = f"*{expected_type} · Stable ID `{identity}`*"
        assert first_view.index(subject.description) < first_view.index(identity_metadata)
        assert first_view.index(identity_metadata) < first_view.index("[!aga-nav] On this page")
        assert first_view.index("[!aga-nav] On this page") < first_view.index(
            "## Overview / General"
        )
        assert body.startswith(f"# {subject.name}\n\n> [!aga-hero] Responsibility\n")
        assert f"> {subject.description}\n> \n> {identity_metadata}" in body
        assert "**Implementation:** " in first_view
        assert "**Verification:** " in first_view
        assert "Back to Observe" not in visible
        assert "## Functional Context" in visible
        for predicate in (
            "part_of",
            "consumes",
            "supplies",
            "presented_in_domain",
            "supports",
            "related_to_research_question",
        ):
            assert f"`{predicate}`" not in first_view
        section_names = (
            "Overview / General",
            "Technical",
            "Research",
            "Evidence / Provenance",
            "Registry / Audit",
        )
        assert [visible.index(f"## {section}") for section in section_names] == sorted(
            visible.index(f"## {section}") for section in section_names
        )
        for section, label in zip(
            section_names, ("Overview", "Technical", "Research", "Evidence", "Audit"), strict=True
        ):
            assert f"[[#{section}|{label}]]" in visible
        assert visible.index("## Registry / Audit") > visible.index("## Evidence / Provenance")
        assert visible[visible.index("## Registry / Audit\n") :].startswith(
            "## Registry / Audit\n\n> [!aga-audit]- Registry / Audit\n"
        )
        assert "- Public Registry source commit:" in identity_page_audit_text(visible)
        assert "- Public Registry source commit:" not in first_view
        assert "W05" not in visible
        assert "No direct Interface endpoint" not in visible
        assert "No direct Contract endpoint" not in visible
        assert "No direct DataArtifact endpoint" not in visible
        assert "No direct MeasurementPoint endpoint" not in visible
        assert rendered.endswith("-->\n")
        assert identity_metadata in visible
        technical = visible.split("## Technical\n", 1)[1].split("## Research\n", 1)[0]
        assert "**Architecture:**" in first_view
        assert "**Implementation:**" in first_view
        assert "**Verification:**" in first_view
        assert "### Implementation notes" in technical
        assert (
            views.private_link(
                technical_projection.private_path(subject), "Open raw Registry record"
            )
            in visible
        )
        assert secret_title not in visible

        audit_text = identity_page_audit_text(visible)
        audit = audit_text.split("### Exact Registry relations\n", 1)[1].split(
            "### Evidence source locators\n", 1
        )[0]
        expected_edges = tuple(
            edge for edge in atlas.relationships if identity in {edge.source, edge.target}
        )
        audit_rows_by_identity[identity] = expected_edges
        for edge in expected_edges:
            source = views._identity_page_audit_link(atlas, edge.source)
            target = views._identity_page_audit_link(atlas, edge.target)
            assert f"| {source} | `{edge.relation}` | {target} |" in audit
        assert audit.count("\n| ") == len(expected_edges) + 2

    perception = tree[views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]].decode()
    perception_summary = perception.split("## Technical\n", 1)[0]
    expected_children = tuple(
        sorted(
            (
                edge.source
                for edge in audit_rows_by_identity["CMP-PERCEPTION"]
                if edge.relation == "part_of"
                and edge.target == "CMP-PERCEPTION"
                and atlas.entities[edge.source].type == "Component"
            ),
            key=lambda child_id: atlas.entities[child_id].name.casefold(),
        )
    )
    assert expected_children == ("CMP-OBSERVATION-BUILDER", "CMP-PERCEPTION-UI-STATE")
    anatomy = perception.split("## Local Anatomy\n", 1)[1].split("## Visual Context", 1)[0]
    assert "Registered direct subcomponents: **2**." in anatomy
    for child_id in expected_children:
        assert views._identity_page_human_link(atlas, child_id) in anatomy
        child = tree[views.IDENTITY_PAGE_PATHS[child_id]].decode()
        assert "No registered direct subcomponents in this snapshot." in child
        assert "### Go deeper" not in child
        assert views._identity_page_human_link(atlas, "CMP-PERCEPTION") in child
    related = perception.split("## Related Objects\n", 1)[1].split("## Research\n", 1)[0]
    assert f"**Uses:** {views._identity_page_human_link(atlas, 'DAT-SCREEN-FRAME')}" in related
    assert f"**Produces:** {views._identity_page_human_link(atlas, 'DAT-OBSERVATION')}" in related
    assert "`part_of`" not in perception_summary
    assert "EVID-48-BUILDER" in identity_page_audit_text(perception)

    observation = tree[views.IDENTITY_PAGE_PATHS["DAT-OBSERVATION"]].decode()
    detail_markdown, detail_canvas = views.technical_detail_paths("DAT-OBSERVATION")
    assert detail_markdown == PurePosixPath("workbenches/Technical Details/DAT-OBSERVATION.md")
    assert detail_canvas == PurePosixPath("workbenches/Technical Details/DAT-OBSERVATION.canvas")
    observation_summary = observation.split("## Registry / Audit\n", 1)[0]
    assert "*DataArtifact · Stable ID `DAT-OBSERVATION`*" in observation_summary
    assert (
        f"**Produced by:** {views._identity_page_human_link(atlas, 'CMP-PERCEPTION')}"
        in observation_summary
    )
    used_by_line = next(line for line in observation_summary.splitlines() if "**Used by:**" in line)
    expected_consumers = (
        "CMP-CORTEX",
        "CMP-MEMORY",
        "CMP-INDEPENDENT-VERIFIER",
        "CMP-TEMPORAL-STATE",
    )
    for consumer_id in expected_consumers:
        assert views._identity_page_human_link(atlas, consumer_id) in used_by_line
    assert used_by_line.index("Cortex") < used_by_line.index("Memory")
    assert used_by_line.index("Memory") < used_by_line.index("Independent Verifier")
    assert used_by_line.index("Independent Verifier") < used_by_line.index("Temporal State")
    assert "**Part of:**" not in observation_summary
    assert "**Contains:**" not in observation_summary
    assert views._derived_link(detail_markdown, "Exact technical relations") in observation
    assert views._canvas_link(detail_canvas, "Visual relation map") in observation
    assert detail_markdown in tree and detail_canvas in tree
    assert "DataArtifact targeting is outside this slice" in observation
    assert "WPAPER-RM1-OBSERVATION" not in observation

    for identity, expected_edges in audit_rows_by_identity.items():
        page_bytes = tree[views.IDENTITY_PAGE_PATHS[identity]]
        page = page_bytes.decode()
        audit_text = identity_page_audit_text(page)
        audit = audit_text.split("### Exact Registry relations\n", 1)[1].split(
            "### Evidence source locators\n", 1
        )[0]
        assert audit.count("\n| ") == len(expected_edges) + 2
        for edge in expected_edges:
            assert f"`{edge.relation}`" in audit
            assert f"`{edge.source}`" in audit and f"`{edge.target}`" in audit
        assert f"`{SOURCE_COMMIT}`" in audit_text
        assert f"`{views.registry_content_revision(atlas)}`" in audit_text
        model = views.identity_page_model(atlas, reference, identity)
        assert f"`{model.private_input_fingerprint}`" in audit_text
        assert "Generated owner: `research-wiki-derived`" in audit_text
        assert "derived navigation page" in audit_text
        assert "No literature exists" not in page
        assert "Research is complete" not in page
        for evidence, _edge in views._identity_page_supporting_evidence(atlas, model):
            source, revision, locator = views._identity_page_evidence_locator(evidence)
            for audit_value in (
                evidence.id,
                f"`{revision}`",
                f"`{source}` · `{locator}`",
                evidence.checked_date.isoformat(),
            ):
                assert audit_value.encode() in page_bytes
        research_summary = page.split("## Research\n", 1)[1].split("## Evidence / Provenance\n", 1)[
            0
        ]
        for row in model.literature_paths:
            assert row.row_id not in research_summary
            assert f"`{row.row_id}`" in audit_text
            if row.recipe:
                assert row.recipe not in research_summary
                assert f"`{row.recipe}`" in audit_text

    observe = tree[views.OBSERVE_SCOPE].decode()
    for identity, label in (
        ("CMP-PERCEPTION", "Open Perception"),
        ("DAT-OBSERVATION", "Open Observation"),
    ):
        assert views._derived_link(views.IDENTITY_PAGE_PATHS[identity], label) in observe
    for identity, label in (
        ("CMP-NO-SPOILER-FIREWALL", "Open No-Spoiler Firewall"),
        ("CMP-VISIBLE-STATE-BRIDGE", "Open Visible-State Bridge"),
    ):
        assert views._derived_link(views.identity_page_paths(atlas)[identity], label) in observe

    manifest = views.read_yaml(tree[views.MANIFEST].decode())
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert manifest["view_schema_version"] == "2.11"
    assert views.IDENTITY_PAGE_PAYLOADS <= owned
    assert views.MEMORY_HUB_TECHNICAL in owned and views.VERIFIER_HUB_TECHNICAL in owned


def test_identity_page_relation_labels_keep_accepted_direction(atlas):
    cases = (
        ("part_of", "CMP-OBSERVATION-BUILDER", "CMP-PERCEPTION", "Part of", "Contains"),
        ("consumes", "CMP-PERCEPTION", "DAT-SCREEN-FRAME", "Uses", "Used by"),
        ("supplies", "CMP-PERCEPTION", "DAT-OBSERVATION", "Produces", "Produced by"),
        (
            "supplies",
            "CMP-PERCEPTION",
            "CON-VERIFIER-RESULT",
            "Provides to",
            "Provided by",
        ),
        ("controls", "CMP-PERCEPTION", "CMP-CORTEX", "Controls", "Controlled by"),
        ("executes", "CMP-PERCEPTION", "CMP-CORTEX", "Executes", "Executed by"),
        ("grounds", "CMP-PERCEPTION", "CMP-CORTEX", "Grounds", "Grounded by"),
        ("measured_at", "CMP-PERCEPTION", "CMP-CORTEX", "Measures", "Measured by"),
        ("observes", "CMP-PERCEPTION", "CMP-CORTEX", "Observes", "Observed by"),
        (
            "proposes_to",
            "CMP-PERCEPTION",
            "CMP-CORTEX",
            "Proposes to",
            "Receives proposals from",
        ),
        ("constrains", "CMP-PERCEPTION", "CMP-CORTEX", "Constrains", "Constrained by"),
        ("verifies", "CMP-PERCEPTION", "CMP-CORTEX", "Verifies", "Verified by"),
        ("supports", "EVID-48-BUILDER", "CMP-PERCEPTION", "Supports", "Supported by"),
    )
    for relation, source, target, forward_label, reverse_label in cases:
        edge = Relationship(relation=relation, source=source, target=target)
        assert views._identity_page_relation_label(atlas, source, edge) == forward_label
        assert views._identity_page_relation_label(atlas, target, edge) == reverse_label

    presentation = Relationship(
        relation="presented_in_domain",
        source="CMP-PERCEPTION",
        target="DOM-OBS-INTEGRITY-STATE",
    )
    assert views._identity_page_relation_label(atlas, "CMP-PERCEPTION", presentation) == (
        "Browse area"
    )
    assert (
        views._identity_page_relation_label(atlas, "DOM-OBS-INTEGRITY-STATE", presentation) is None
    )
    question = Relationship(
        relation="related_to_research_question",
        source="CMP-PERCEPTION",
        target="RQ-PROGRAM-AB-001",
    )
    assert views._identity_page_relation_label(atlas, "CMP-PERCEPTION", question) is None


def test_identity_page_native_fallback_keeps_semantics_and_outline(atlas):
    """Exercise the document alone: no stylesheet, plugin or Mermaid renderer loaded."""
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    hooks = set()
    for model in views.identity_page_models(atlas, reference):
        page = views.render_identity_page(SOURCE_COMMIT, atlas, model).decode()
        visible = page.split(views.IDENTITY_PAGE_METADATA_MARKER)[0]
        fallback = re.sub(r"```mermaid\n.*?```\n", "", visible, flags=re.S)
        hooks.update(re.findall(r"\[!(aga-[a-z-]+)\]", fallback))
        assert fallback.count('<span class="aga-primary-section"></span>') == 2
        assert "<" not in fallback.replace('<span class="aga-primary-section"></span>', "")
        assert "css" not in fallback
        assert not fallback.startswith("---")
        headings = re.findall(r"^## (.+)$", fallback, re.M)
        expected = [
            "Overview / General",
            *(
                ["Explicit participants"]
                if model.subject.type == "Function"
                else [
                    "Functional Context",
                    *(["Local Anatomy"] if model.subject.type != "Function" else []),
                ]
            ),
            "Technical",
            "Related Objects",
            "Research",
            "Gap Analysis",
            "Evidence / Provenance",
            "Registry / Audit",
            "Return Navigation",
        ]
        assert [h for h in headings if h != "Visual Context"] == expected
        anchors = re.findall(r"\[\[#([^|]+)\|[^]]+\]\]", fallback)[:5]
        assert anchors == [
            "Overview / General",
            "Technical",
            "Research",
            "Evidence / Provenance",
            "Registry / Audit",
        ]
        assert all(re.search(rf"^## {re.escape(anchor)}$", fallback, re.M) for anchor in anchors)
        if views._identity_page_supporting_evidence(atlas, model):
            assert (
                "### Implementation notes\n" in fallback
                or "### Technical and decision support\n" in fallback
            )
        assert model.subject.description in fallback
        if model.subject.type != "Function":
            status = model.subject.technical
            assert (
                f"**Implementation:** {status.implementation_status.replace('-', ' ').title()}"
                in fallback
            )
            assert (
                f"**Verification:** {status.verification_status.replace('-', ' ').title()}"
                in fallback
            )
        else:
            assert "**Type:** Function" in fallback
            assert "## Local Anatomy" not in fallback
        # Flatten ordinary blockquote markers only, retaining every title, fact and link.
        plain = re.sub(r"^(?:> ?)+", "", fallback, flags=re.M)
        for label, identities in views._identity_page_human_relation_groups(atlas, model):
            if label in {"Part of", "Contains", "Browse area"}:
                continue
            assert f"**{label}:**" in plain
            for identity in identities:
                assert views._identity_page_human_link(atlas, identity) in plain
        if model.child_component_ids:
            depth = plain.split("### Go deeper\n", 1)[1].split("## Technical", 1)[0]
            for child in model.child_component_ids:
                assert (
                    views._markdown_table_cell(views._identity_page_human_link(atlas, child))
                    in depth
                    if len(model.child_component_ids) >= 5
                    else views._identity_page_human_link(atlas, child) in depth
                )
        else:
            assert "Go deeper" not in fallback and "[!aga-depth]" not in fallback
        assert "[!aga-hero] Responsibility" in plain
        assert "TECHNICAL — How does it work?" in plain
        assert "RESEARCH — What do we know or need to know?" in plain
        assert plain.index("TECHNICAL — How does it work?") < plain.index(
            "RESEARCH — What do we know or need to know?"
        )
        assert "[!aga-grid] At a glance" in plain
        assert "[!aga-status] Current state" in plain
        assert "[!aga-context] Context" not in plain
        if model.subject.type == "Environment":
            assert "direct environment research attachment is deferred" in plain.lower()
        else:
            assert "research completeness have not been assessed" in plain.lower()
        assert "Source inspection alone is not live or measurement validation." in plain
        assert "[!aga-audit]- Registry / Audit" in plain
        assert "Generated owner: `research-wiki-derived`" in identity_page_audit_text(page)
        warning = "[!warning]- Current limitations — baseline source inspection"
        assert (warning in plain) == (
            model.subject.id in {"CMP-PERCEPTION", "CMP-PERCEPTION-UI-STATE"}
        )
        if warning in plain:
            limitation = plain.split(warning, 1)[1].split("Back to Observe", 1)[0]
            evidence_ids = (
                {"EVID-48-OCR-LIMIT", "EVID-48-SPATIAL-LIMIT"}
                if model.subject.id == "CMP-PERCEPTION"
                else {"EVID-48-UI"}
            )
            for identity in evidence_ids:
                assert atlas.entities[identity].description in limitation
    assert hooks == {
        "aga-hero",
        "aga-nav",
        "aga-grid",
        "aga-status",
        "aga-child",
        "aga-pillars",
        "aga-technical-entry",
        "aga-research-entry",
        "aga-research",
        "aga-evidence",
        "aga-audit",
    }


def test_identity_page_mermaid_exact_direct_facts_and_textual_fallback(atlas):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    expected = {
        "CMP-PERCEPTION": {
            ("CMP-PERCEPTION", "Part of", "SYS-AGA"),
            ("CMP-OBSERVATION-BUILDER", "Part of", "CMP-PERCEPTION"),
            ("CMP-PERCEPTION-UI-STATE", "Part of", "CMP-PERCEPTION"),
            ("CMP-PERCEPTION", "Uses", "DAT-SCREEN-FRAME"),
            ("CMP-PERCEPTION", "Produces", "DAT-OBSERVATION"),
        },
        "DAT-OBSERVATION": {
            ("CMP-PERCEPTION", "Produces", "DAT-OBSERVATION"),
            *(
                (identity, "Uses", "DAT-OBSERVATION")
                for identity in (
                    "CMP-CORTEX",
                    "CMP-MEMORY",
                    "CMP-INDEPENDENT-VERIFIER",
                    "CMP-TEMPORAL-STATE",
                )
            ),
        },
    }
    for model in views.identity_page_models(atlas, reference):
        page = views.render_identity_page(SOURCE_COMMIT, atlas, model).decode()
        if model.subject.id not in expected:
            continue
        diagram = page.split("```mermaid\n")[1].split("```", 1)[0]
        names_to_ids = {node.name: node.id for node in atlas.entities.values()}
        nodes = {
            node: names_to_ids[name]
            for node, name in re.findall(r'    (n\d+)\["([^"]+)"\]', diagram)
        }
        assert nodes["n0"] == model.subject.id
        assert len(nodes) == 6
        assert list(nodes.values())[1:] == sorted(list(nodes.values())[1:])
        edges = re.findall(r'    (n\d+) -->\|"([^"]+)"\| (n\d+)', diagram)
        actual = {(nodes[source], label, nodes[target]) for source, label, target in edges}
        assert actual == expected[model.subject.id]
        assert len(edges) == len(actual)
        assert set(nodes.values()) == {
            endpoint for source, _, target in actual for endpoint in (source, target)
        }
        # Independently check every rendered edge against the Registry's exact direction.
        predicates = {"Part of": "part_of", "Uses": "consumes", "Produces": "supplies"}
        registry_facts = {(e.source, e.relation, e.target) for e in atlas.relationships}
        for source, label, target in actual:
            assert (source, predicates[label], target) in registry_facts
        fallback = re.sub(r"```mermaid\n.*?```", "", page, flags=re.S)
        audit = identity_page_audit_text(fallback)
        overview = fallback.split("## Registry / Audit")[0]
        for source, label, target in actual:
            assert (
                f"| {views._identity_page_audit_link(atlas, source)} | `{predicates[label]}` | "
                f"{views._identity_page_audit_link(atlas, target)} |" in audit
            )
            other = source if source != model.subject.id else target
            assert views._identity_page_human_link(atlas, other) in overview
        shuffled = replace(model, direct_relationships=tuple(reversed(model.direct_relationships)))
        assert views._identity_page_mermaid(atlas, model) == views._identity_page_mermaid(
            atlas, shuffled
        )


def test_identity_page_mermaid_excludes_neighbors_research_and_trivial_graphs(atlas):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    model = views.identity_page_model(atlas, reference, "CMP-PERCEPTION")
    original = views._identity_page_mermaid(atlas, model)
    excluded = (
        Relationship(relation="controls", source="CMP-PERCEPTION", target="CMP-CORTEX"),
        Relationship(relation="supplies", source="CMP-PERCEPTION", target="CON-VERIFIER-RESULT"),
        Relationship(relation="consumes", source="CMP-CORTEX", target="DAT-SCREEN-FRAME"),
        Relationship(
            relation="related_to_research_question",
            source="CMP-PERCEPTION",
            target="RQ-PROGRAM-AB-001",
        ),
    )
    assert (
        views._identity_page_mermaid(
            atlas, replace(model, direct_relationships=(*model.direct_relationships, *excluded))
        )
        == original
    )
    parent_only = tuple(
        e
        for e in model.direct_relationships
        if e.relation == "part_of" and e.source == model.subject.id
    )
    assert (
        views._identity_page_mermaid(atlas, replace(model, direct_relationships=parent_only)) == []
    )
    entities = dict(atlas.entities)
    entities[model.subject.id] = model.subject.model_copy(
        update={"name": 'Perception "quoted" <tag> # | `'}
    )
    escaped = "\n".join(views._identity_page_mermaid(replace(atlas, entities=entities), model))
    assert "Perception #34;quoted#34; #60;tag#62; #35; #124; #96;" in escaped
    assert "<tag>" not in escaped


def test_identity_page_css_is_finite_optional_and_presentation_only():
    asset = ROOT / "docs/research-atlas/presentation/aga-identity-pages.css"
    assert list(asset.parent.glob("*.css")) == [asset]
    data = asset.read_bytes()
    assert data == asset.read_bytes() and len(data) < 8000
    css = re.sub(r"/\*.*?\*/", "", data.decode(), flags=re.S)
    hooks = set(re.findall(r'data-callout="([^"]+)"', css))
    assert hooks == {
        "aga-hero",
        "aga-nav",
        "aga-grid",
        "aga-status",
        "aga-context",
        "aga-depth",
        "aga-child",
        "aga-pillars",
        "aga-technical-entry",
        "aga-research-entry",
        "aga-research",
        "aga-evidence",
        "aga-audit",
    }
    selector_words = hooks | {
        "callout",
        "is",
        "data-callout",
        "callout-content",
        "p",
        "last-child",
        "code",
        "strong",
        "internal-link",
        "hover",
        "focus-visible",
        "media",
        "max-width",
        "rem",
        "has",
        "markdown-reading-view",
        "inline-title",
        "markdown-preview-view",
        "h",
        "markdown-source-view",
        "HyperMD-header-",
        "body",
        "show-inline-title",
        "markdown-preview-sizer",
        "el-h",
        "el-hr",
        "hr",
        "HyperMD-hr",
        "mod-cm",
        "is-live-preview",
        "cm-content",
        "cm-line",
        "not",
        "markdown-embed",
        "el-p",
        "aga-primary-section",
        "data-heading",
        "Technical",
        "Research",
        "cm-html-embed",
        "br",
        "only-child",
    }
    for block in css.split("{")[:-1]:
        selector = block.rsplit("}", 1)[-1]
        assert set(re.findall(r"[a-zA-Z][a-zA-Z-]*", selector)) <= selector_words
    assert not re.search(
        r"url\s*\(|@import|@font-face|font-family|https?:|file:|/Users/|/home/|[A-Z]:\\", css, re.I
    )
    assert not re.search(
        r"#[\w-]+|(?<![\w-])(?:content|visibility|opacity|overflow|height|max-height|text-indent|position|clip|clip-path)\s*:",
        css,
    )
    assert "display: none" not in css and "!important" not in css
    assert "display: grid" in css and "repeat(auto-fit, minmax(min(100%, 18rem), 1fr))" in css
    assert "repeat(auto-fit, minmax(min(100%, 20rem), 1fr))" in css
    assert not re.search(r"(?<![\w-])height\s*:", css) and "overflow-x:" not in css
    assert "@media (max-width: 40rem)" in css and "grid-template-columns: minmax(0, 1fr)" in css
    declarations = re.findall(r"([\w-]+)\s*:\s*([^;{}]+);", css)
    allowed = {
        "color",
        "background",
        "border",
        "border-radius",
        "padding",
        "margin-block",
        "min-width",
        "overflow-wrap",
        "border-inline-start",
        "font-size",
        "font-weight",
        "line-height",
        "--h1-size",
        "--h1-weight",
        "--h1-color",
        "--h1-line-height",
        "box-sizing",
        "--h2-size",
        "--h2-weight",
        "--h2-line-height",
        "--hr-color",
        "--hr-thickness",
        "display",
        "text-decoration",
        "outline",
        "outline-offset",
        "grid-template-columns",
        "gap",
        "margin",
    }
    assert {prop for prop, _ in declarations} <= allowed
    for prop, value in declarations:
        if (
            prop in {"color", "background", "border", "border-inline-start", "outline"}
            and value.strip() != "0"
        ):
            assert re.search(r"var\(--(?:text-|background-|interactive-|link-)", value)
    # CSS never enters manifest ownership or the vault writer; source is operator-installed at G6.
    assert not any(str(path).endswith(".css") for path in views.IDENTITY_PAGE_PAYLOADS)


def test_rm1_identity_pages_reject_wrong_types_parents_and_nonpilot_ids(atlas):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    with pytest.raises(ProjectionError, match="Unsupported Identity Page subject"):
        views.identity_page_model(atlas, reference, "DOM-COGNITION")

    entities = dict(atlas.entities)
    perception_record = entities["CMP-PERCEPTION"].model_dump(mode="python")
    perception_record["type"] = "DataArtifact"
    entities["CMP-PERCEPTION"] = DataArtifact.model_validate(perception_record)
    wrong_type_atlas = replace(atlas, entities=entities)
    with pytest.raises(ProjectionError, match="wrong Registry type"):
        views.identity_page_model(wrong_type_atlas, reference, "CMP-PERCEPTION")

    wrong_parent = Relationship(
        relation="part_of", source="CMP-OBSERVATION-BUILDER", target="DAT-OBSERVATION"
    )
    parent_atlas = replace(atlas, relationships=(*atlas.relationships, wrong_parent))
    with pytest.raises(ProjectionError, match="parent is not a System or Component"):
        views.identity_page_model(parent_atlas, reference, "CMP-OBSERVATION-BUILDER")

    wrong_dataartifact_parent = Relationship(
        relation="part_of", source="DAT-OBSERVATION", target="CMP-PERCEPTION"
    )
    dataartifact_atlas = replace(
        atlas, relationships=(*atlas.relationships, wrong_dataartifact_parent)
    )
    with pytest.raises(ProjectionError, match="does not infer Component containment"):
        views.identity_page_model(dataartifact_atlas, reference, "DAT-OBSERVATION")


def test_rm1_identity_pages_are_deterministic_under_shuffled_inputs(atlas):
    records = [
        wiki_props(
            "paper",
            wiki_id="WPAPER-RM1-PERCEPTION",
            research_direct_subject_refs=["CMP-PERCEPTION"],
        ),
        wiki_props(
            "paper",
            wiki_id="WPAPER-RM1-OBSERVATION",
            research_direct_subject_refs=["DAT-OBSERVATION"],
        ),
    ]
    current_tree, _, _, _ = identity_page_tree(atlas, records)
    shuffled_atlas = replace(atlas, relationships=tuple(reversed(atlas.relationships)))
    shuffled_tree, _, _, _ = identity_page_tree(shuffled_atlas, list(reversed(records)))
    assert current_tree == shuffled_tree
    for path in views.IDENTITY_PAGE_PAYLOADS:
        assert (
            current_tree[path].split(views.IDENTITY_PAGE_METADATA_MARKER.encode(), 1)[1]
            == (shuffled_tree[path].split(views.IDENTITY_PAGE_METADATA_MARKER.encode(), 1)[1])
        )


def test_rm1_identity_page_ownership_is_finite(tmp_path, atlas):
    tree, _, _, _ = identity_page_tree(atlas)
    root = tmp_path / "derived"
    manifest_path = root / views.MANIFEST
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(tree[views.MANIFEST])
    for path in views.identity_page_paths(atlas).values():
        if path in tree:
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(tree[path])
    prior = views.validate_prior(root)
    assert set(prior).intersection(views.IDENTITY_PAGE_PAYLOADS) == views.IDENTITY_PAGE_PAYLOADS

    manifest = views.read_yaml(manifest_path.read_text())
    sample = next(
        item
        for item in manifest["owned_files"]
        if item["path"] in map(str, views.IDENTITY_PAGE_PAYLOADS)
    )
    manifest["owned_files"].append({**sample, "path": "identity-pages/Unregistered?.md"})
    manifest_path.write_text(views.yaml_text(manifest))
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)


def w10_private_fixtures():
    records = []
    for index in range(25):
        paper_id = f"WPAPER-W10-{index:02d}"
        reading_id = f"READ-W10-{index:02d}"
        paper_fields = {
            "wiki_id": paper_id,
            "title": f"Synthetic W10 Paper {index:02d}",
            "record_version": 2,
            "document_maturity": "archived" if index == 1 else "in_review",
            "source_refs": [f"zsrc-synthetic-{index:02d}"],
            "authors": ["Synthetic Author"],
            "publication_year": 2024,
            "venue": "Synthetic Venue",
            "reading_note_refs": [reading_id],
            "related_version_refs": [f"zsv-synthetic-{index:02d}"],
            "research_direct_subject_refs": ["CMP-CORTEX"],
            "research_method_or_baseline_refs": ["CMP-CORTEX"],
            "research_measurement_relevance_refs": ["CMP-MEMORY"],
            "research_project_transfer_refs": ["CMP-BODY"],
            "research_adjacent_context_refs": ["CMP-SKILL-TRAINER"],
        }
        if index == 0:
            paper_fields.update(doi="10.9999/synthetic.00", url="https://example.invalid/w10")
        records.append(wiki_props("paper", **paper_fields))
        records.append(
            wiki_props(
                "reading_note",
                wiki_id=reading_id,
                title=f"Synthetic W10 ReadingNote {index:02d}",
                record_version=3,
                document_maturity="in_review",
                paper_refs=[paper_id],
                version_read=f"zsv-synthetic-{index:02d}",
                read_date="2026-09-25",
                reading_depth="methods_checked",
                checked_sections=["methods"],
                finding_refs=[f"WFIND-W10-{index:02d}"],
                search_refs=[f"SEARCH-W10-{index:02d}"],
                rq_refs=[f"WRQ-W10-{index:02d}"],
                research_measurement_relevance_refs=["CMP-CORTEX"],
            )
        )
    records.append(wiki_props("finding", wiki_id="WFIND-W10-EXCLUDED"))
    records.append(
        {
            "wiki_schema_version": "0.1",
            "wiki_id": "PROC-W10-LEGACY",
            "doc_type": "process",
            "privacy": "private",
            "export_policy": "deny",
            "atlas_refs": [],
        }
    )
    return records


def w10_reference_tree(atlas, records):
    snapshot = make_snapshot(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    private_records = views.landscape_private_records(records, atlas)
    locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
        for record in records
    }
    tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        private_records,
    )
    return tree, snapshot, reference, locators


@pytest.fixture
def context(tmp_path: Path) -> workspace.WorkspaceContext:
    repo = tmp_path / "repo"
    vault = tmp_path / "vault"
    repo.mkdir()
    vault.mkdir()
    return workspace.WorkspaceContext(repo, vault, "a" * 40)


def test_apply_orders_one_exact_head_and_both_final_checks(context, monkeypatch, tmp_path):
    restore_point = tmp_path / "restore"
    calls: list[tuple[str, str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(
        workspace,
        "create_restore_point",
        lambda *_: restore_point,
    )

    def technical(repo_root, vault_root, source_ref, *, check=False):
        calls.append(("technical", source_ref, check))

    def views(repo_root, vault_root, source_ref, *, check=False):
        calls.append(("views", source_ref, check))

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(workspace, "views_project", views)
    result = workspace.apply(context.repo_root, context.vault_root)

    assert result.restore_point == restore_point
    assert calls == [
        ("technical", context.source_commit, False),
        ("views", context.source_commit, False),
        ("technical", context.source_commit, True),
        ("views", context.source_commit, True),
    ]


def test_apply_stops_at_first_failed_projector_and_names_restore_point(
    context, monkeypatch, tmp_path
):
    restore_point = tmp_path / "restore"
    calls: list[str] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(workspace, "create_restore_point", lambda *_: restore_point)

    def technical(*args, **kwargs):
        calls.append("technical")
        raise ProjectionError("synthetic failure")

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(workspace, "views_project", lambda *args, **kwargs: calls.append("views"))
    with pytest.raises(workspace.WorkspaceError, match="technical projection failed.*restore"):
        workspace.apply(context.repo_root, context.vault_root)
    assert calls == ["technical"]


def test_final_check_failure_is_nonzero_apply_failure(context, monkeypatch, tmp_path):
    restore_point = tmp_path / "restore"
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(workspace, "create_restore_point", lambda *_: restore_point)

    def technical(*args, check=False, **kwargs):
        calls.append(("technical", check))
        if check:
            raise ProjectionError("synthetic check failure")

    monkeypatch.setattr(workspace, "technical_project", technical)
    monkeypatch.setattr(
        workspace,
        "views_project",
        lambda *args, check=False, **kwargs: calls.append(("views", check)),
    )
    with pytest.raises(
        workspace.WorkspaceError, match="technical projection check failed.*restore"
    ):
        workspace.apply(context.repo_root, context.vault_root)
    assert calls == [("technical", False), ("views", False), ("technical", True)]


def test_check_is_restore_free_and_runs_only_both_checks(context, monkeypatch):
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(workspace, "resolve_context", lambda *_: context)
    monkeypatch.setattr(
        workspace,
        "create_restore_point",
        lambda *_: pytest.fail("check must not create a restore point"),
    )
    monkeypatch.setattr(
        workspace,
        "technical_project",
        lambda *args, check=False, **kwargs: calls.append(("technical", check)),
    )
    monkeypatch.setattr(
        workspace,
        "views_project",
        lambda *args, check=False, **kwargs: calls.append(("views", check)),
    )
    result = workspace.check(context.repo_root, context.vault_root)
    assert result.restore_point is None
    assert calls == [("technical", True), ("views", True)]


def test_w05_detail_endpoint_set_and_empty_verifier_lanes(atlas):
    models = views.technical_detail_models(atlas)
    assert tuple(model.endpoint_id for model in models) == DETAIL_ENDPOINTS
    assert views.TECHNICAL_DETAIL_ENDPOINT_TYPES == {
        "IF-MEM-CORTEX": "Interface",
        "CON-CORTEX-CONTEXT": "Contract",
        "DAT-RETRIEVAL-SNAPSHOT": "DataArtifact",
        "MEAS-RETRIEVAL-DELIVERY-001": "MeasurementPoint",
        "CON-VERIFIER-RESULT": "Contract",
        "DAT-OBSERVATION": "DataArtifact",
        "DAT-VISIBLE-OUTCOME": "DataArtifact",
    }
    assert all(
        atlas.entities[model.endpoint_id].type
        == views.TECHNICAL_DETAIL_ENDPOINT_TYPES[model.endpoint_id]
        for model in models
    )
    verifier = views._component_hub_model(atlas, "CMP-INDEPENDENT-VERIFIER")
    assert verifier.interface_ids == ()
    assert verifier.measurement_point_ids == ()
    verifier_interface_lane = "\n".join(views._render_component_hub_interface_lane(atlas, verifier))
    assert "No corresponding `IF-*` Registry record exists" in verifier_interface_lane
    assert not any("MeasurementPoint" in identity for identity in DETAIL_ENDPOINTS)


def test_w05_canvas_markdown_links_and_relation_sets_match(atlas):
    models = views.technical_detail_models(atlas)
    technical_tree = technical_projection.projection_tree(
        atlas,
        SOURCE_COMMIT,
        {name: "b" * 64 for name in technical_projection.REGISTRY_FILES},
    )
    for model in models:
        markdown = views.render_technical_detail_workbench(SOURCE_COMMIT, atlas, model).decode()
        canvas = json.loads(views.render_technical_detail_canvas(atlas, model))
        assert set(canvas) == {
            "generated_by",
            "canvas_view_schema_version",
            "nodes",
            "edges",
        }
        assert canvas["generated_by"] == views.OWNER
        assert canvas["canvas_view_schema_version"] == "1.0"
        assert all(
            isinstance(node[key], int)
            for node in canvas["nodes"]
            for key in ("x", "y", "width", "height")
        )
        assert all(
            edge["toEnd"] == "arrow" and edge["fromEnd"] == "none" for edge in canvas["edges"]
        )

        identity_by_node_id = {
            views._canvas_node_id(identity): identity
            for edge in model.direct_relationships
            for identity in (edge.source, edge.target)
        } | {views._canvas_node_id(model.endpoint_id): model.endpoint_id}
        canvas_relations = {
            (
                identity_by_node_id[edge["fromNode"]],
                edge["label"],
                identity_by_node_id[edge["toNode"]],
            )
            for edge in canvas["edges"]
        }
        expected_relations = {
            (edge.source, edge.relation, edge.target) for edge in model.direct_relationships
        }
        assert canvas_relations == expected_relations

        relation_section = markdown.split("## Exact direct Registry relations\n\n", 1)[1].split(
            "\n## Scoped Canvas map\n", 1
        )[0]
        markdown_relations = {
            line for line in relation_section.splitlines() if line.startswith("- [[")
        }
        expected_markdown = {
            f"- {views._technical_link(atlas, edge.source)} — `{edge.relation}` → "
            f"{views._technical_link(atlas, edge.target)}"
            for edge in model.direct_relationships
        }
        assert markdown_relations == expected_markdown

        canvas_links = [
            target
            for node in canvas["nodes"]
            for target in re.findall(r"\[\[([^\]|]+)\|[^\]]+\]\]", node["text"])
        ]
        assert len(canvas_links) == len(canvas["nodes"])
        for target in canvas_links:
            assert not target.startswith("/") and "Users/" not in target
            relative = PurePosixPath(target).relative_to(technical_projection.OWNED_ROOT)
            assert relative.with_suffix(".md") in technical_tree

        assert "| Architecture authority |" in markdown
        assert "| Implementation status |" in markdown
        assert "| Technical verification |" in markdown
        if model.endpoint_id == "MEAS-RETRIEVAL-DELIVERY-001":
            assert "measurement target relation only" in markdown
            assert "Measurement validity: **not established here**" in markdown
            assert "Scientific evidence or effect: **not established here**" in markdown
            assert "Accepted scientific claim: **none created or implied**" in markdown
        if model.endpoint_id == "DAT-RETRIEVAL-SNAPSHOT":
            assert len(canvas["nodes"]) == 4
        if model.endpoint_id == "DAT-OBSERVATION":
            assert len(canvas["nodes"]) >= 8


def test_w05_rendering_manifest_and_hub_links_are_order_invariant(atlas):
    snapshot = make_snapshot([], atlas)
    shuffled = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )

    def render_registry(source):
        private_snapshot = make_snapshot([], source)
        reference = build_index(source, private_snapshot, SOURCE_COMMIT)
        return views.reference_views_tree(
            SOURCE_COMMIT,
            (ROOT / views.PUBLIC_SOURCE).read_bytes(),
            (ROOT / views.DIRECT_SOURCE).read_bytes(),
            reference,
            source,
            {},
            private_snapshot,
            False,
        )

    current_tree = render_registry(atlas)
    shuffled_tree = render_registry(shuffled)
    assert current_tree == shuffled_tree
    technical_tree = technical_projection.projection_tree(
        atlas,
        SOURCE_COMMIT,
        {name: "b" * 64 for name in technical_projection.REGISTRY_FILES},
    )
    assert technical_projection.ANATOMY in technical_tree
    assert technical_projection.DOMAIN_SLICE in technical_tree
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.11"
    assert {
        PurePosixPath(item["path"])
        for item in manifest["owned_files"]
        if PurePosixPath(item["path"]).parent == views.TECHNICAL_DETAIL_ROOT
    } == views.TECHNICAL_DETAIL_PAYLOADS

    for hub_id in views.COMPONENT_HUB_PATHS:
        hub = views._component_hub_model(atlas, hub_id)
        research_model = views._component_research_model(
            atlas, build_index(atlas, snapshot, SOURCE_COMMIT), hub_id
        )
        technical = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "technical", snapshot, False
        ).decode()
        overview = views.render_component_hub_view(
            SOURCE_COMMIT, atlas, hub, "overview", snapshot, False
        ).decode()
        research = views.render_component_hub_view(
            SOURCE_COMMIT,
            atlas,
            hub,
            "research",
            snapshot,
            False,
            research_model,
            {},
        ).decode()
        expected_ids = (
            *hub.interface_ids,
            *hub.contract_ids,
            *hub.data_artifact_ids,
            *hub.measurement_point_ids,
        )
        for identity in expected_ids:
            workbench, canvas = views.technical_detail_paths(identity)
            assert str(views.OWNED_ROOT / workbench.with_suffix("")) in technical
            assert str(views.OWNED_ROOT / canvas) in technical
            assert workbench in current_tree and canvas in current_tree
            detail_markdown = current_tree[workbench].decode()
            links = re.findall(r"\[\[([^\]|]+)\|[^\]]+\]\]", detail_markdown)
            assert links
            for target in links:
                path = PurePosixPath(target)
                if path.is_relative_to(views.OWNED_ROOT):
                    relative = path.relative_to(views.OWNED_ROOT)
                    if relative.suffix != ".canvas":
                        relative = relative.with_suffix(".md")
                    assert relative in current_tree
                else:
                    assert path.is_relative_to(technical_projection.OWNED_ROOT)
                    relative = path.relative_to(technical_projection.OWNED_ROOT)
                    if relative.suffix == ".excalidraw":
                        relative = PurePosixPath(f"{relative}.md")
                    else:
                        relative = relative.with_suffix(".md")
                    assert relative in technical_tree
        detail_prefix = str(views.OWNED_ROOT / views.TECHNICAL_DETAIL_ROOT)
        assert detail_prefix not in overview
        assert detail_prefix not in research


def test_w06_component_research_renders_exact_registry_and_all_nc_rows(atlas):
    tree, snapshot, reference, locators = component_research_tree(atlas)
    memory_model = views._component_research_model(atlas, reference, "CMP-MEM-RETRIEVAL")
    verifier_model = views._component_research_model(atlas, reference, "CMP-INDEPENDENT-VERIFIER")
    memory_rows = component_navigation_rows(reference, "CMP-MEM-RETRIEVAL")
    assert memory_model.research_question_relationships == (
        next(
            edge
            for edge in atlas.relationships
            if edge.source == "CMP-MEM-RETRIEVAL"
            and edge.relation == "related_to_research_question"
        ),
    )
    assert verifier_model.research_question_relationships == ()
    assert {row.target_identifier for row in memory_rows} == {"CMP-MEM-RETRIEVAL"}
    assert len(memory_rows) == 6
    assert {row.recipe for row in memory_rows} == {
        "N-C/K0/E9:forward",
        "N-C/K1/E1:inverse/E9:forward",
        "N-C/K1/E2:forward/E9:forward",
        "N-C/K2/E3:inverse/E9:forward",
        "N-C/K3/E1:inverse/E4:forward/E9:forward",
    }
    assert sum(row.recipe.startswith("N-C/K1/E1:") for row in memory_rows) == 2
    assert all(row.recipe.startswith("N-C/") and row.path_eligible for row in memory_rows)
    assert {row.recipe.split("/")[1] for row in memory_rows} == {"K0", "K1", "K2", "K3"}
    assert {row.path_kind for row in memory_rows} == {"direct", "derived"}
    assert any(row.prerequisite_refs for row in memory_rows)
    assert {row.originating_role for row in memory_rows} == {
        "research_direct_subject_refs",
        "research_method_or_baseline_refs",
        "research_measurement_relevance_refs",
        "research_project_transfer_refs",
        "research_adjacent_context_refs",
    }

    memory = tree[views.MEMORY_HUB_RESEARCH].decode()
    verifier = tree[views.VERIFIER_HUB_RESEARCH].decode()
    question = atlas.entities["RQ-PROGRAM-AB-001"]
    assert f"{question.name} · `RQ-PROGRAM-AB-001`" in memory
    assert "`related_to_research_question` →" in memory
    assert (
        "No current Registry Research Question relation is declared for this Component." in verifier
    )
    assert "RQ-PROGRAM-AB-001" not in verifier

    for row in memory_rows:
        assert memory.count(row.row_id) == 1
        assert f"`{row.path_kind}`" in memory
        assert f"`{row.recipe}`" in memory
    k3 = next(row for row in memory_rows if "/K3/" in row.recipe)
    assert k3.source_wiki_id == "WFIND-K3"
    assert k3.source_doc_type == "finding"
    assert k3.navigation_start is not None
    assert k3.navigation_start.identifier == "WPAPER-K3"
    k3_number = memory_rows.index(k3) + 1
    k3_block = memory.split(f"### Path {k3_number} · `{k3.path_kind}`\n", 1)[1].split(
        "\n### Path ", 1
    )[0]
    assert "Declaring record: [WFIND-K3](" in k3_block
    assert "Paper/source identity: [WPAPER-K3](" in k3_block
    assert "Declaring record: [WPAPER-K3]" not in k3_block
    assert "Originating property: `research_method_or_baseline_refs`" in memory
    assert "Originating role: `research_method_or_baseline_refs`" in memory
    assert "Target Component: [CMP-MEM-RETRIEVAL](" in k3_block
    assert "resolved-public`; type `Component`; record version `none`; profile `none`" in k3_block
    assert "Index row: `navigation-path` · view `component` · eligible `true`" in k3_block
    assert "Final reference type check: `not-constrained`" in k3_block
    assert "Index diagnostics: none" in k3_block
    assert "Declared target:" in memory and "Prerequisite references:" in memory
    assert "`E9`" in memory and "direction `forward`" in memory
    assert "revision `v1`" in k3_block
    assert "finding%20%5Bfixture%5D%20%233.md" in k3_block
    locator_link = re.search(r"\[WFIND-K3\]\(([^)]+)\)", k3_block)
    assert locator_link is not None
    research_parent = (views.OWNED_ROOT / views.MEMORY_HUB_RESEARCH).parent.as_posix()
    resolved_locator = PurePosixPath(
        posixpath.normpath(posixpath.join(research_parent, unquote(locator_link[1])))
    )
    assert resolved_locator == locators["WFIND-K3"]
    k1_forward = next(row for row in memory_rows if "E2:forward" in row.recipe)
    k1_forward_block = memory.split(
        f"### Path {memory_rows.index(k1_forward) + 1} · `{k1_forward.path_kind}`\n", 1
    )[1].split("\n### Path ", 1)[0]
    assert "Prerequisite references:\n  1. Edge `E1`" in k1_forward_block
    assert "property `paper_refs`" in k1_forward_block
    assert "method used" not in memory
    assert "best baseline" not in memory
    assert "implementation studied" not in memory

    for unrelated_identity in (
        "WPAPER-VERIFIER",
        "WPAPER-OTHER-COMPONENT",
        "WPAPER-DOMAIN-SIBLING",
        "WPAPER-INTERFACE",
        "WPAPER-CONTRACT",
        "WPAPER-DATA",
        "WPAPER-MEASUREMENT",
        "READ-WRONG-TYPE",
        "READ-UNRESOLVED",
        "CMP-CORTEX",
        "CMP-MEMORY",
        "IF-MEM-CORTEX",
    ):
        assert unrelated_identity not in memory
    assert "Open Declared Literature Navigation" in memory
    assert "Direct Reference Audit" in memory
    navigation = html.unescape(tree[views.NAVIGATION].decode())
    assert "READ-WRONG-TYPE" in navigation and "wrong-target-type" in navigation
    assert "READ-UNRESOLVED" in navigation and "unresolved-reference" in navigation
    assert all("/Users/" not in data.decode() for data in tree.values())
    assert all(not path.is_absolute() for path in locators.values())


def test_w06_component_research_does_not_roll_up_parent_or_domain_sibling(atlas):
    parent_edge = Relationship(
        relation="part_of",
        source="CMP-MEM-RETRIEVAL",
        target="CMP-CORTEX",
    )
    with_parent = Atlas(atlas.entities, (*atlas.relationships, parent_edge))
    hub = views._component_hub_model(with_parent, "CMP-MEM-RETRIEVAL")
    memory_domains = views._relationship_targets(atlas, "CMP-MEM-RETRIEVAL", "presented_in_domain")
    sibling_domains = views._relationship_targets(atlas, "CMP-MEMORY", "presented_in_domain")
    assert "CMP-CORTEX" in hub.technical_parent_ids
    assert memory_domains and set(memory_domains) & set(sibling_domains)

    tree, snapshot, reference, locators = component_research_tree(with_parent)
    model = views._component_research_model(with_parent, reference, "CMP-MEM-RETRIEVAL")
    memory = views.render_component_hub_view(
        SOURCE_COMMIT,
        with_parent,
        hub,
        "research",
        snapshot,
        False,
        model,
        locators,
    ).decode()
    assert {row.target_identifier for row in model.literature_paths} == {"CMP-MEM-RETRIEVAL"}
    assert "WPAPER-OTHER-COMPONENT" not in memory
    assert "WPAPER-DOMAIN-SIBLING" not in memory
    assert "CMP-CORTEX" not in memory and "CMP-MEMORY" not in memory
    assert tree[views.MEMORY_HUB_RESEARCH].decode() == memory


def test_w06_component_research_empty_state_is_neutral_and_keeps_exact_rq(atlas):
    snapshot = make_snapshot([], atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    hub = views._component_hub_model(atlas, "CMP-MEM-RETRIEVAL")
    research_model = views._component_research_model(atlas, reference, hub.subject_id)
    memory = views.render_component_hub_view(
        SOURCE_COMMIT,
        atlas,
        hub,
        "research",
        snapshot,
        False,
        research_model,
        {},
    ).decode()
    assert "No matching declared Component literature paths are present in this snapshot." in memory
    assert "No current Registry Research Question relation is declared" not in memory
    assert "No literature is present" not in memory
    assert "research gap" not in memory
    assert "No authored private research records are present in this snapshot." in memory
    assert "Direct Reference Audit" in memory


def w07_private_fixtures():
    records = []
    for kind in views.LANDSCAPE_PRIVATE_TYPES:
        identity = f"{WIKI_PREFIXES[kind]}-W07-001"
        changes = {
            "wiki_id": identity,
            "title": f"Synthetic W07 {kind.replace('_', ' ')}",
            "record_version": 7,
            "document_maturity": "in_review",
            "research_direct_subject_refs": ["CMP-CORTEX"],
        }
        if kind == "research_question":
            changes.update(question_stage="literature_mapped", decision_state="none")
        elif kind == "finding":
            changes.update(review_state="checked")
        elif kind == "search_record":
            changes["document_maturity"] = "draft"
        records.append(wiki_props(kind, **changes))
    records.extend(
        wiki_props(
            "search_record",
            wiki_id=f"SEARCH-W07-MANY-{index:02d}",
            title=f"Synthetic W07 search record {index:02d}",
            target_refs=["WRQ-FIXTURE"],
            research_direct_subject_refs=["CMP-CORTEX"],
        )
        for index in range(24)
    )
    return records


def test_w07_global_landscape_is_complete_markdown_and_order_invariant(atlas):
    records = w07_private_fixtures()
    snapshot = make_snapshot(records, atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"synthetic note [{record['wiki_id']}] #1.md"
        for record in records
    }
    private_records = views.landscape_private_records(records, atlas)
    page = views.render_research_landscape(
        SOURCE_COMMIT, atlas, snapshot, locators, private_records
    )
    text = page.decode()

    assert text.startswith("---\ngenerated_by: research-wiki-derived\n")
    assert text.startswith("---") and "# Research Landscape" in text
    assert "derived navigation projection" in text
    assert "Research Knowledge Home" in text and "Agent Anatomy" in text
    assert "Technical Hierarchy" in text
    assert "Declared Literature Navigation" in text
    assert "Direct Reference Audit" in text and "Direct Views Index" in text
    assert "No new" not in text
    for node in atlas.entities.values():
        if node.type in views.LANDSCAPE_PUBLIC_TYPES:
            assert node.name in text and node.id in text and node.type in text
    exact_relation_count = sum(
        edge.relation == "related_to_research_question" for edge in atlas.relationships
    )
    assert text.count("`related_to_research_question`") == exact_relation_count + 1
    assert "`part_of`" not in text
    assert "domain-member" not in text.lower()

    for kind in views.LANDSCAPE_PRIVATE_TYPES:
        assert f"### {views.LANDSCAPE_PRIVATE_LABELS[kind]}" in text
        assert f"Synthetic W07 {kind.replace('_', ' ')}" in text
    public_section = text.split("## Private authored RA-2 inventory", 1)[0]
    assert "Synthetic W07 research question" not in public_section
    for index in range(24):
        assert f"SEARCH-W07-MANY-{index:02d}" in text
        assert f"Synthetic W07 search record {index:02d}" in text
    assert "Record class: `research_question`" in text
    assert "Record version: `7`" in text
    assert "Document maturity: `in_review`" in text
    assert "`question_stage`: `literature_mapped`" in text
    assert "`decision_state`: `none`" in text
    assert "`review_state`: `checked`" in text
    assert "`research_direct_subject_refs`: `CMP-CORTEX`" in text
    assert "synthetic%20note%20%5BSEARCH-W07-MANY-00%5D%20%231.md" in text
    assert "No current records are present for this record class in this snapshot." in text
    assert "No current declared relationships are present" not in text
    assert "evidence score" not in text.lower()
    assert "confidence score" not in text.lower()
    assert "priority score" not in text.lower()
    assert "top-k" not in text.lower()
    assert ".base" not in text.lower()

    shuffled = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    shuffled_snapshot = make_snapshot(reversed(records), shuffled)
    shuffled_reference = build_index(shuffled, shuffled_snapshot, SOURCE_COMMIT)
    shuffled_locators = dict(reversed(tuple(locators.items())))
    shuffled_records = views.landscape_private_records(list(reversed(records)), shuffled)
    shuffled_tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        shuffled_reference,
        shuffled,
        shuffled_locators,
        shuffled_snapshot,
        False,
        shuffled_records,
    )
    current_tree = views.reference_views_tree(
        SOURCE_COMMIT,
        (ROOT / views.PUBLIC_SOURCE).read_bytes(),
        (ROOT / views.DIRECT_SOURCE).read_bytes(),
        reference,
        atlas,
        locators,
        snapshot,
        False,
        private_records,
    )
    assert current_tree == shuffled_tree
    assert views.RESEARCH_LANDSCAPE in current_tree
    assert views.RESEARCH_LANDSCAPE in views.K3_PAYLOADS
    assert b"Research Landscape" in current_tree[views.K3_HOME]
    assert b"Research Landscape" in current_tree[views.INDEX]
    home_text = current_tree[views.K3_HOME].decode()
    assert home_text.index("Open the Global Research Landscape") < home_text.index(
        "Preferred Component identities"
    )
    for subject_id, paths in views.COMPONENT_HUB_PATHS.items():
        assert subject_id in text
        assert str(views.OWNED_ROOT / paths.research.with_suffix("")) in text
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    owned = {item["path"] for item in manifest["owned_files"]}
    assert str(views.RESEARCH_LANDSCAPE) in owned
    assert str(SOURCE_COMMIT).encode() in page
    assert b"/Users/" not in page and b"C:\\" not in page


def test_w07_landscape_keeps_public_and_navigation_sections_useful_when_private_empty(atlas):
    snapshot = make_snapshot([], atlas)
    page = views.render_research_landscape(SOURCE_COMMIT, atlas, snapshot, {}, ()).decode()
    assert "Program A–B working question" in page
    assert "Experience to Action" in page
    assert "No current records are present for this record class in this snapshot." in page
    for record_type in ("Paper", "Finding", "ExperimentLead"):
        section = page.split(f"### {record_type}\n", 1)[1].split("\n### ", 1)[0]
        assert "No current records are present for this record class in this snapshot." in section
    assert "Declared Literature Navigation" in page
    assert "Direct Reference Audit" in page and "Direct Views Index" in page
    assert "Technical Hierarchy" in page and "Memory Retrieval" in page
    assert "research absence" in page and "does not state" in page
    no_question_relations = replace(
        atlas,
        relationships=tuple(
            edge for edge in atlas.relationships if edge.relation != "related_to_research_question"
        ),
    )
    no_relations_page = views.render_research_landscape(
        SOURCE_COMMIT, no_question_relations, snapshot, {}, ()
    ).decode()
    assert "No current declared relationships are present in this snapshot." in no_relations_page
    legacy_record = {
        "wiki_schema_version": "0.1",
        "wiki_id": "PROC-W07-LEGACY",
        "doc_type": "process",
        "privacy": "private",
        "export_policy": "deny",
        "atlas_refs": [],
    }
    legacy_snapshot = make_snapshot([legacy_record], atlas)
    legacy_page = views.render_research_landscape(
        SOURCE_COMMIT, atlas, legacy_snapshot, {}, ()
    ).decode()
    process_section = legacy_page.split("### Process\n", 1)[1].split("\n### ", 1)[0]
    assert "No current RA-2 records are present" in process_section


def test_w10_literature_inspection_is_complete_typed_and_order_invariant(atlas):
    records = w10_private_fixtures()
    tree, _, _, locators = w10_reference_tree(atlas, records)
    page = tree[views.LITERATURE_INSPECTION].decode()
    landscape = tree[views.RESEARCH_LANDSCAPE].decode()

    assert page.startswith("---\ngenerated_by: research-wiki-derived\n")
    assert "# Literature Inspection" in page
    assert "Generated, derived navigation projection" in page
    assert "Open Literature Inspection" in landscape
    assert "Paper/source records" in page and "ReadingNote records" in page
    assert "No current matching records are present in this snapshot." not in page
    assert "Record class: `paper`" in page and "Record class: `reading_note`" in page
    assert "Record version: `2`" in page and "Record version: `3`" in page
    assert "Document maturity: `archived`" in page
    assert "Profile: `RA-2`" in page and "Epistemic schema version" in page
    assert "[Synthetic W10 Paper 00](../../../authored/WPAPER-W10-00.md)" in page
    assert "[Synthetic W10 ReadingNote 00](../../../authored/READ-W10-00.md)" in page
    assert '`source_refs`: ` ["zsrc-synthetic-00"] `' in page
    assert '`doi`: ` "10.9999/synthetic.00" `' in page
    assert '`authors`: ` ["Synthetic Author"] `' in page
    assert "`publication_year`: ` 2024 `" in page
    assert '`venue`: ` "Synthetic Venue" `' in page
    assert '`reading_note_refs`: ` ["READ-W10-00"] `' in page
    assert '`related_version_refs`: ` ["zsv-synthetic-00"] `' in page
    assert '`paper_refs`: ` ["WPAPER-W10-00"] `' in page
    assert '`version_read`: ` "zsv-synthetic-00" `' in page
    assert '`read_date`: ` "2026-09-25" `' in page
    assert '`reading_depth`: ` "methods_checked" `' in page
    assert '`checked_sections`: ` ["methods"] `' in page
    assert '`finding_refs`: ` ["WFIND-W10-00"] `' in page
    assert '`search_refs`: ` ["SEARCH-W10-00"] `' in page
    assert '`rq_refs`: ` ["WRQ-W10-00"] `' in page
    assert '`research_direct_subject_refs`: ` ["CMP-CORTEX"] `' in page
    assert '`research_method_or_baseline_refs`: ` ["CMP-CORTEX"] `' in page
    assert '`research_measurement_relevance_refs`: ` ["CMP-MEMORY"] `' in page
    assert '`research_project_transfer_refs`: ` ["CMP-BODY"] `' in page
    assert '`research_adjacent_context_refs`: ` ["CMP-SKILL-TRAINER"] `' in page
    assert '`research_measurement_relevance_refs`: ` ["CMP-CORTEX"] `' in page
    assert '`url`: ` "https://example.invalid/w10" `' in page
    assert "](https://example.invalid/w10)" not in page
    assert (
        "`url`:"
        not in page.split("Synthetic W10 Paper 01", 1)[1].split("## ReadingNote records", 1)[0]
    )

    for index in range(25):
        assert f"Synthetic W10 Paper {index:02d}" in page
        assert f"WPAPER-W10-{index:02d}" in page
        assert f"Synthetic W10 ReadingNote {index:02d}" in page
        assert f"READ-W10-{index:02d}" in page
    assert "Synthetic view fixture" not in page
    assert "WFIND-W10-EXCLUDED" not in page
    assert "PROC-W10-LEGACY" not in page
    assert "does not read ReadingNote bodies" in page and "SYNTHETIC-PRIVATE" not in page
    assert "curated excerpt" not in page.lower()
    assert "summary" not in page.lower()
    assert "resolved-private" not in page
    assert "source-family" not in page.lower()
    assert "Open Direct Reference Audit" in page
    assert "Declared Literature Navigation" in page
    assert "Direct Views Index" in page
    assert "Research Landscape" in page
    assert "Research Knowledge Home" in page
    assert "https://example.invalid/w10" in page

    shuffled_atlas = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    shuffled_tree, _, _, _ = w10_reference_tree(shuffled_atlas, list(reversed(records)))
    assert tree == shuffled_tree
    manifest = views.read_yaml(tree[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.11"
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert views.LITERATURE_INSPECTION in owned
    assert "example.invalid" not in tree[views.REFERENCE_INDEX].decode()
    assert "example.invalid" not in tree[views.NAVIGATION].decode()
    assert set(locators) == {record["wiki_id"] for record in records}
    assert all(b"/Users/" not in content and b"C:\\" not in content for content in tree.values())


def test_w10_empty_inspection_keeps_navigation_and_uses_neutral_state(atlas):
    tree, _, _, _ = w10_reference_tree(atlas, [])
    page = tree[views.LITERATURE_INSPECTION].decode()
    assert page.count("No current matching records are present in this snapshot.") == 2
    assert "Declared Literature Navigation" in page
    assert "Direct Reference Audit" in page
    assert "Direct Views Index" in page
    assert "Research Landscape" in page and "Research Knowledge Home" in page
    assert "no research exists" not in page.lower()
    assert "research gap" not in page.lower()
    assert "novelty" in page.lower()
    assert "coverage" in page.lower() and "priority" in page.lower()


def test_w06_component_research_is_order_invariant_and_adds_no_owned_paths(atlas):
    records = component_research_fixture_records()
    current_tree, _, _, _ = component_research_tree(atlas, records)
    shuffled_atlas = replace(
        atlas,
        entities=dict(reversed(tuple(atlas.entities.items()))),
        relationships=tuple(reversed(atlas.relationships)),
    )
    reversed_records = tuple(reversed(records))
    shuffled_locators = {
        record["wiki_id"]: PurePosixPath("authored") / f"{record['wiki_id']}.md"
        for record in reversed_records
    }
    shuffled_tree, _, _, _ = component_research_tree(
        shuffled_atlas, reversed_records, locators=shuffled_locators
    )
    assert current_tree == shuffled_tree
    manifest = views.read_yaml(current_tree[views.MANIFEST].decode())
    assert manifest["view_schema_version"] == "2.11"
    owned = {PurePosixPath(item["path"]) for item in manifest["owned_files"]}
    assert views.K3_PAYLOADS <= owned
    assert not any("Component Research" in str(path) for path in owned)
    assert not any(path.suffix == ".base" and "Component" in path.name for path in owned)


def test_w05_manifest_ownership_is_exact_and_version_bounded(tmp_path: Path):
    root = tmp_path / "derived"
    manifest_path = root / views.MANIFEST
    manifest_path.parent.mkdir(parents=True)

    def write_manifest(version, paths):
        manifest = {
            "view_schema_version": version,
            "generated_by": views.OWNER,
            "source_repository": "Planton361/autonomous-game-agent",
            "source_commit": SOURCE_COMMIT,
            "source_atlas_schema": "0.2",
            "source_sha256": {
                "public_atlas_base": "c" * 64,
                "research_wiki_direct_base": "d" * 64,
            },
            "reference_index_schema_version": "1.0",
            "private_input_fingerprint": "e" * 64,
            "owned_files": [
                {
                    "path": str(path),
                    "sha256": "f" * 64,
                    "ownership": views.STRICT_OWNERSHIP,
                }
                for path in paths
            ],
        }
        manifest_path.write_bytes(views.yaml_text(manifest).encode())

    write_manifest("2.4", sorted(views.TECHNICAL_DETAIL_PAYLOADS))
    prior = views.validate_prior(root)
    assert set(prior) == views.TECHNICAL_DETAIL_PAYLOADS

    write_manifest("2.3", [views.technical_detail_paths("IF-MEM-CORTEX")[0]])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    unknown = views.TECHNICAL_DETAIL_ROOT / "UNOWNED.md"
    write_manifest("2.4", [unknown])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.4", [views.RESEARCH_LANDSCAPE])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.5", [views.RESEARCH_LANDSCAPE])
    assert set(views.validate_prior(root)) == {views.RESEARCH_LANDSCAPE}
    write_manifest("2.5", [views.LITERATURE_INSPECTION])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.6", [views.LITERATURE_INSPECTION])
    assert set(views.validate_prior(root)) == {views.LITERATURE_INSPECTION}
    unknown_index = PurePosixPath("indexes/Unowned Landscape.md")
    write_manifest("2.6", [unknown_index])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)
    write_manifest("2.7", [views.OBSERVE_SCOPE])
    assert set(views.validate_prior(root)) == {views.OBSERVE_SCOPE}
    write_manifest("2.7", [unknown_index])
    with pytest.raises(ProjectionError, match="Invalid direct-view ownership path/type"):
        views.validate_prior(root)


@pytest.mark.parametrize(
    ("version", "paths"),
    [
        ("1.0", (views.INDEX,)),
        ("2.0", (views.REFERENCE_INDEX,)),
        ("2.1", (views.K3_HOME,)),
        ("2.2", (views.HIERARCHY, views.HIERARCHY_DIR / "SYS-AGA.md")),
        ("2.3", (views.MEMORY_HUB_TECHNICAL,)),
        ("2.4", (views.technical_detail_paths("IF-MEM-CORTEX")[1],)),
        ("2.5", (views.RESEARCH_LANDSCAPE,)),
        ("2.6", (views.LITERATURE_INSPECTION,)),
        ("2.7", (views.OBSERVE_SCOPE,)),
    ],
)
def test_w05_manifest_prior_versions_keep_bounded_paths(tmp_path: Path, version, paths):
    root = tmp_path / "derived"
    manifest_path = root / views.MANIFEST
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "view_schema_version": version,
        "generated_by": views.OWNER,
        "source_repository": "Planton361/autonomous-game-agent",
        "source_commit": SOURCE_COMMIT,
        "source_atlas_schema": "0.2",
        "source_sha256": {
            "public_atlas_base": "a" * 64,
            "research_wiki_direct_base": "b" * 64,
        },
        "owned_files": [
            {
                "path": str(path),
                "sha256": "c" * 64,
                **(
                    {"ownership": views.STRICT_OWNERSHIP}
                    if version in {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"}
                    else {}
                ),
            }
            for path in paths
        ],
    }
    if version != "1.0":
        manifest.update(
            reference_index_schema_version="1.0",
            private_input_fingerprint="d" * 64,
        )
    manifest_path.write_bytes(views.yaml_text(manifest).encode())
    assert set(views.validate_prior(root)) == set(paths)


ATLAS_ROOT = ROOT / "docs/research-atlas"


def six_level_payloads():
    registry = ATLAS_ROOT / "registry"
    nodes, relationships, evidence = (
        yaml.safe_load((registry / name).read_text())
        for name in ("nodes.yaml", "relationships.yaml", "evidence.yaml")
    )
    template = next(node for node in nodes["nodes"] if node["id"] == "CMP-PERCEPTION")
    parent = "CMP-PERCEPTION"
    for level in range(1, 7):
        identity = f"CMP-SYN-LEVEL-{level}"
        node = {**template, "id": identity, "name": f"Synthetic level {level}"}
        node.update(
            description=f"Synthetic technical responsibility at level {level}.",
            atlas_level=None,
            overview_visibility=None,
            overview_order=None,
        )
        nodes["nodes"].append(node)
        relationships["relationships"].append(
            {"relation": "part_of", "source": identity, "target": parent}
        )
        parent = identity
    for identity, name, parent in (
        ("CMP-SYN-SIB-A", "Alpha sibling", "CMP-SYN-LEVEL-2"),
        ("CMP-SYN-SIB-B", "Beta sibling", "CMP-SYN-LEVEL-2"),
        ("CMP-SYN-SIB-C", "Gamma sibling", "CMP-SYN-LEVEL-4"),
    ):
        node = {**template, "id": identity, "name": name}
        node.update(
            description=f"Synthetic {name} responsibility.",
            atlas_level=None,
            overview_visibility=None,
            overview_order=None,
        )
        nodes["nodes"].append(node)
        relationships["relationships"].append(
            {"relation": "part_of", "source": identity, "target": parent}
        )
    return nodes, relationships, evidence


def model(atlas: Atlas, identity: str):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    return views.identity_page_model(atlas, reference, identity)


def page(atlas: Atlas, identity: str) -> str:
    return views.render_identity_page(SOURCE_COMMIT, atlas, model(atlas, identity)).decode()


def test_six_level_reciprocal_navigation_leaf_and_all_authorized_types():
    baseline = load_registry(ATLAS_ROOT)
    nodes, relationships, evidence = six_level_payloads()
    deep = validate_registry(nodes, relationships, evidence)
    paths = views.identity_page_paths(deep)
    assert len(paths) == len(views.identity_page_paths(baseline)) + 9
    assert {
        deep.entities[identity].type for identity in paths
    } == views.SUPPORTED_IDENTITY_PAGE_TYPES
    assert paths["CMP-MEM-RETRIEVAL"] == views.MEMORY_WORKBENCH
    assert paths["CMP-INDEPENDENT-VERIFIER"] == views.VERIFIER_WORKBENCH
    assert paths["CMP-PERCEPTION"] == views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]
    assert paths["CMP-SYN-LEVEL-6"] == PurePosixPath("identity-pages/Synthetic level 6.md")
    assert len(set(paths.values())) == len(paths)
    memory_children = model(deep, "CMP-MEMORY").child_component_ids
    assert set(memory_children) == {
        "CMP-MEM-EPISODIC",
        "CMP-MEM-FACTS",
        "CMP-MEM-HYPOTHESES",
        "CMP-MEM-TOPOLOGY",
        "CMP-MEM-STRATEGY",
        "CMP-SKILL-COMPETENCE",
    }
    assert "CMP-MEM-RETRIEVAL" not in memory_children
    assert model(deep, "CMP-SYN-LEVEL-2").child_component_ids == (
        "CMP-SYN-SIB-A",
        "CMP-SYN-SIB-B",
        "CMP-SYN-LEVEL-3",
    )
    for level in range(1, 6):
        parent = f"CMP-SYN-LEVEL-{level}"
        child = f"CMP-SYN-LEVEL-{level + 1}"
        assert child in model(deep, parent).child_component_ids
        assert parent in model(deep, child).technical_parent_ids
        assert views._identity_page_human_link(deep, child) in page(deep, parent)
        assert views._identity_page_human_link(deep, parent) in page(deep, child)
    level2 = page(deep, "CMP-SYN-LEVEL-2")
    depth = level2.split("### Go deeper", 1)[1].split("## Technical", 1)[0]
    assert depth.index("Alpha sibling") < depth.index("Beta sibling")
    assert "CMP-SYN-LEVEL-4" not in depth
    leaf = page(deep, "CMP-SYN-LEVEL-6")
    assert "Go deeper" not in leaf
    assert "**Back up to direct parent(s):**" in leaf
    trail = leaf.split("**Location:**", 1)[1].split("**Back up", 1)[0]
    assert all(f"Synthetic level {level}" in trail for level in range(1, 7))
    assert "Browse area" not in trail
    assert leaf.index("aga-technical-entry") < leaf.index("aga-research-entry")
    assert leaf.index("## Technical") < leaf.index("## Research")
    assert "No literature exists" not in leaf and "Research is complete" not in leaf
    assert "<div" not in leaf and not leaf.startswith("---")
    assert "Direct Research deferred" in page(deep, "ENV-GAME-INSTANCE")


def test_multiple_parents_rename_removal_order_and_collision(monkeypatch):
    nodes, relationships, evidence = six_level_payloads()
    relationships["relationships"].append(
        {"relation": "part_of", "source": "CMP-SYN-LEVEL-6", "target": "CMP-SYN-LEVEL-4"}
    )
    multi = validate_registry(nodes, relationships, evidence)
    leaf = model(multi, "CMP-SYN-LEVEL-6")
    assert leaf.technical_parent_ids == ("CMP-SYN-LEVEL-4", "CMP-SYN-LEVEL-5")
    rendered = page(multi, leaf.subject.id)
    assert rendered.count("→ Synthetic level 6") == 2
    shuffled = Atlas(
        dict(reversed(tuple(multi.entities.items()))), tuple(reversed(multi.relationships))
    )
    assert rendered == page(shuffled, leaf.subject.id)
    assert views.identity_page_paths(multi) == views.identity_page_paths(shuffled)

    renamed_nodes = yaml.safe_load(yaml.safe_dump(nodes))
    next(node for node in renamed_nodes["nodes"] if node["id"] == leaf.subject.id)["name"] = (
        "Renamed leaf"
    )
    renamed = validate_registry(renamed_nodes, relationships, evidence)
    assert views.identity_page_paths(renamed)[leaf.subject.id] == PurePosixPath(
        "identity-pages/Renamed leaf.md"
    )
    assert "Renamed leaf" in page(renamed, leaf.subject.id)
    removed_nodes = yaml.safe_load(yaml.safe_dump(nodes))
    removed_nodes["nodes"] = [
        node for node in removed_nodes["nodes"] if node["id"] != "CMP-SYN-SIB-C"
    ]
    removed_relationships = {
        **relationships,
        "relationships": [
            edge for edge in relationships["relationships"] if edge["source"] != "CMP-SYN-SIB-C"
        ],
    }
    removed = validate_registry(removed_nodes, removed_relationships, evidence)
    assert "CMP-SYN-SIB-C" not in views.identity_page_paths(removed)
    assert "Gamma sibling" not in page(removed, "CMP-SYN-LEVEL-4")

    monkeypatch.setattr(
        views,
        "IDENTITY_PAGE_PATHS",
        {**views.IDENTITY_PAGE_PATHS, leaf.subject.id: views.IDENTITY_PAGE_PATHS["CMP-PERCEPTION"]},
    )
    with pytest.raises(ProjectionError, match="path collision"):
        views.identity_page_paths(multi)


def test_human_first_identity_paths_sanitize_and_disambiguate(atlas):
    assert views.identity_page_paths(atlas)["CMP-MEMORY"] == PurePosixPath(
        "identity-pages/Memory.md"
    )
    assert views.identity_page_paths(atlas)["CMP-CORTEX"] == PurePosixPath(
        "identity-pages/Cortex.md"
    )
    assert all(
        views.identity_page_paths(atlas)[identity] == path
        for identity, path in views.IDENTITY_PAGE_PATHS.items()
    )
    assert views.identity_page_paths(atlas)["CMP-MEM-RETRIEVAL"] == views.MEMORY_WORKBENCH
    assert views.identity_page_paths(atlas)["CMP-INDEPENDENT-VERIFIER"] == views.VERIFIER_WORKBENCH
    assert all(
        not path.stem.startswith(identity)
        for identity, path in views.identity_page_paths(atlas).items()
        if identity not in views.IDENTITY_PAGE_PATHS | views.COMPONENT_HUB_PATHS
    )

    template = atlas.entities["CMP-MEMORY"]
    names = {
        "CMP-SYN-DUP-A": "Same name",
        "CMP-SYN-DUP-B": "Same name",
        "CMP-SYN-CASE-A": "Case name",
        "CMP-SYN-CASE-B": "case name",
        "CMP-SYN-UNSAFE": 'A/B:C*D?E"F<G>H|I#J^K[L]',
        "CMP-SYN-CONTROL": "Alpha/\\Beta\nGamma\x00",
        "CMP-SYN-EMPTY": "///...",
        "CMP-SYN-DEVICE": "CON",
        "CMP-SYN-DEVICE-EXT": "CON.txt",
        "CMP-SYN-PILOT": "Perception",
        "CMP-SYN-HUB": "Memory Retrieval",
    }
    synthetic = Atlas(
        {
            **atlas.entities,
            **{
                identity: template.model_copy(update={"id": identity, "name": name})
                for identity, name in names.items()
            },
        },
        atlas.relationships,
    )
    paths = views.identity_page_paths(synthetic)
    expected = {
        "CMP-SYN-DUP-A": "Same name — CMP-SYN-DUP-A.md",
        "CMP-SYN-DUP-B": "Same name — CMP-SYN-DUP-B.md",
        "CMP-SYN-CASE-A": "Case name — CMP-SYN-CASE-A.md",
        "CMP-SYN-CASE-B": "case name — CMP-SYN-CASE-B.md",
        "CMP-SYN-UNSAFE": "A B C D E F G H I J K L.md",
        "CMP-SYN-CONTROL": "Alpha Beta Gamma.md",
        "CMP-SYN-EMPTY": "Untitled — CMP-SYN-EMPTY.md",
        "CMP-SYN-DEVICE": "CON — CMP-SYN-DEVICE.md",
        "CMP-SYN-DEVICE-EXT": "CON.txt — CMP-SYN-DEVICE-EXT.md",
        "CMP-SYN-PILOT": "Perception — CMP-SYN-PILOT.md",
        "CMP-SYN-HUB": "Memory Retrieval — CMP-SYN-HUB.md",
    }
    assert {identity: paths[identity].name for identity in names} == expected
    assert paths == views.identity_page_paths(
        Atlas(dict(reversed(tuple(synthetic.entities.items()))), atlas.relationships)
    )
    assert len({str(path).casefold() for path in paths.values()}) == len(paths)


def test_human_first_residual_path_collision_fails_closed(atlas):
    template = atlas.entities["CMP-MEMORY"]
    synthetic = Atlas(
        {
            **atlas.entities,
            "CMP-SYN-ONE": template.model_copy(update={"id": "CMP-SYN-ONE", "name": "Memory"}),
            "CMP-SYN-TWO": template.model_copy(
                update={"id": "CMP-SYN-TWO", "name": "Memory — CMP-MEMORY"}
            ),
        },
        atlas.relationships,
    )
    with pytest.raises(ProjectionError, match="path collision"):
        views.identity_page_paths(synthetic)


@pytest.mark.parametrize(
    ("edge", "message"),
    (
        (
            {"relation": "part_of", "source": "CMP-SYN-LEVEL-1", "target": "CMP-SYN-LEVEL-6"},
            "cycle",
        ),
        (
            {"relation": "part_of", "source": "DAT-OBSERVATION", "target": "CMP-PERCEPTION"},
            "Illegal part_of type pairing",
        ),
        (
            {"relation": "part_of", "source": "CMP-SYN-LEVEL-6", "target": "DAT-OBSERVATION"},
            "Illegal part_of type pairing",
        ),
        (
            {"relation": "part_of", "source": "CMP-SYN-LEVEL-6", "target": "CMP-NOT-REGISTERED"},
            "Dangling relationship",
        ),
    ),
)
def test_invalid_containment_is_rejected(edge, message):
    nodes, relationships, evidence = six_level_payloads()
    relationships["relationships"].append(edge)
    with pytest.raises(ValueError, match=message):
        validate_registry(nodes, relationships, evidence)


def test_rm1_evidence_roles_remain_separate_without_scientific_acceptance():
    nodes, relationships, evidence = six_level_payloads()
    evidence["evidence"].append(
        {
            "id": "EVID-SYN-LITERATURE",
            "type": "Evidence",
            "name": "Synthetic primary source",
            "description": "Synthetic source locator for evidence-role testing only.",
            "provenance_kind": "primary_literature",
            "checked_date": "2026-09-29",
            "document": "Synthetic source",
            "version": "v1",
            "section": "1",
        }
    )
    relationships["relationships"].append(
        {
            "relation": "supports",
            "source": "EVID-SYN-LITERATURE",
            "target": "CMP-PERCEPTION",
        }
    )
    atlas = validate_registry(nodes, relationships, evidence)
    content = page(atlas, "CMP-PERCEPTION")
    support = content.split("## Evidence / Provenance", 1)[1].split("## Registry / Audit", 1)[0]
    assert "### Technical and decision support" in support
    assert "### Research and scientific support" in support
    assert support.index("### Technical and decision support") < support.index(
        "### Research and scientific support"
    )
    assert "Synthetic source locator for evidence-role testing only." in support
    assert "Source inspection alone is not live or measurement validation." in support
    assert "accepted claim" not in support.lower()


def test_uip_complete_preferred_pages_and_frozen_local_anatomy(atlas):
    tree, _, reference, _ = identity_page_tree(atlas)
    paths = views.identity_page_paths(atlas)
    models = views.identity_page_models(atlas, reference, page_paths=paths)
    assert len(models) == len(paths) == 58
    expected_counts = {
        "SYS-AGA": 17,
        "CMP-MEMORY": 6,
        "CMP-PERCEPTION": 2,
        "CMP-MANAGER": 2,
        "CMP-BODY": 1,
    }
    leaves = 0
    for model in models:
        identity = model.subject.id
        page = tree[model.path].decode()
        visible = page.split(views.IDENTITY_PAGE_METADATA_MARKER, 1)[0]
        assert visible.startswith(f"# {model.subject.name}\n")
        metadata = views._identity_page_generated_metadata(page, model.path)
        assert metadata["identity_page_subject_id"] == identity
        assert metadata["identity_page_path"] == str(model.path)
        order = [
            "> [!aga-hero]",
            "> [!aga-status]",
            "> [!aga-pillars]",
            *(
                ["## Explicit participants"]
                if model.subject.type == "Function"
                else [
                    "## Functional Context",
                    *(["## Local Anatomy"] if model.subject.type != "Function" else []),
                ]
            ),
            "## Technical",
            "## Related Objects",
            "## Research",
            "## Gap Analysis",
            "## Evidence / Provenance",
            "## Registry / Audit",
            "## Return Navigation",
        ]
        positions = [visible.index(token) for token in order]
        assert positions == sorted(positions)
        if "## Visual Context" in visible:
            if model.subject.type in {"System", "Component"}:
                assert visible.index("## Local Anatomy") < visible.index("## Visual Context")
            assert visible.index("## Visual Context") < visible.index("## Technical")
        state = visible.split("> [!aga-status]", 1)[1].split("> [!aga-pillars]", 1)[0]
        if model.subject.type != "Function":
            assert all(
                f"**{axis}:**" in state
                for axis in ("Architecture", "Implementation", "Verification")
            )
        else:
            assert "**Type:** Function" in state
        assert "**Uses:**" not in state and "**Produces:**" not in state
        anatomy = (
            (
                visible.split("## Local Anatomy", 1)[1]
                .split("## Visual Context", 1)[0]
                .split("## Technical", 1)[0]
            )
            if model.subject.type != "Function"
            else ""
        )
        if model.subject.type == "Function":
            assert "## Local Anatomy" not in visible
        if model.subject.type in {"System", "Component"}:
            count = expected_counts.get(identity, 0)
            assert f"Registered direct subcomponents: **{count}**." in anatomy
            assert len(model.child_component_ids) == count
            expected_order = sorted(
                model.child_component_ids, key=lambda i: (atlas.entities[i].name.casefold(), i)
            )
            assert list(model.child_component_ids) == expected_order
            if count == 0:
                leaves += 1
                assert "No registered direct subcomponents in this snapshot." in anatomy
                assert "Go deeper" not in anatomy
            else:
                assert "[!aga-depth]" not in anatomy
                assert anatomy.count("> [!aga-child]") == (count if count <= 4 else 0)
                if count >= 5:
                    assert "| Direct Component | Responsibility |" in anatomy
                links = [
                    (
                        views._markdown_table_cell(
                            views._identity_page_human_link(atlas, child, paths)
                        )
                        if count >= 5
                        else views._identity_page_human_link(atlas, child, paths)
                    )
                    for child in expected_order
                ]
                assert [anatomy.index(link) for link in links] == sorted(
                    anatomy.index(link) for link in links
                )
            assert "CMP-PERCEPTION-OCR" not in anatomy
            assert "CMP-PERCEPTION-SPATIAL" not in anatomy
        technical = visible.split("## Technical", 1)[1].split("## Related Objects", 1)[0]
        assert "**Contains:**" not in technical and "**Part of:**" not in technical
        related = visible.split("## Related Objects", 1)[1].split("## Research", 1)[0]
        for label, identities in views._identity_page_human_relation_groups(atlas, model):
            for target in identities:
                if label in {"Part of", "Contains", "Browse area"}:
                    continue
                if model.subject.type in {
                    "Interface",
                    "Contract",
                    "DataArtifact",
                    "MeasurementPoint",
                } or atlas.entities[target].type in {
                    "Interface",
                    "Contract",
                    "DataArtifact",
                    "MeasurementPoint",
                }:
                    link = views._identity_page_human_link(atlas, target, paths)
                    assert link in related and link not in technical
                    assert related.count(link) == sum(
                        target in group_ids
                        for group_label, group_ids in views._identity_page_human_relation_groups(
                            atlas, model
                        )
                        if group_label not in {"Part of", "Contains", "Browse area"}
                    )
        research = visible.split("## Research", 1)[1].split("## Gap Analysis", 1)[0]
        assert research.lstrip().startswith("**Scope / availability:**")
        assert "Not assessed / no authorized gap assessment attached." in visible
        bottom = visible.split("## Return Navigation", 1)[1]
        assert "Research Knowledge Home" in bottom
        for parent in model.technical_parent_ids:
            assert views._identity_page_human_link(atlas, parent, paths) in bottom
    assert leaves == 24
    for identity, hub in views.COMPONENT_HUB_PATHS.items():
        assert paths[identity] == hub.overview
        assert PurePosixPath("identity-pages") / f"{atlas.entities[identity].name}.md" not in tree
        assert "Technical auxiliary view" in tree[hub.overview].decode()
        assert "Research auxiliary view" in tree[hub.overview].decode()


def test_uip_title_polish_is_scoped_and_preserves_markdown_h1(atlas):
    tree, _, _, _ = identity_page_tree(atlas)
    css = (ROOT / "docs/research-atlas/presentation/aga-identity-pages.css").read_text()
    assert (
        ':has(.inline-title):has(.callout[data-callout="aga-hero"]:not(.markdown-embed .callout))'
        in css
    )
    assert "display: none" not in css
    title_rule = (
        css.split("/* Obsidian places the inline title", 1)[1]
        .split("*/", 1)[1]
        .split('.callout[data-callout="aga-child"]', 1)[0]
    )
    selectors, declarations = title_rule.split("{", 1)
    selectors = re.sub(r"/\*.*?\*/", "", selectors, flags=re.S).split(",")
    assert len(selectors) == 2
    for selector in selectors:
        assert "body.show-inline-title" in selector
        assert (
            ':has(.inline-title):has(.callout[data-callout="aga-hero"]'
            ":not(.markdown-embed .callout))" in selector
        )
        assert not selector.rstrip().endswith(".inline-title")
    assert "> .markdown-preview-sizer > .el-h1 > h1" in selectors[0]
    assert ".markdown-source-view.mod-cm6.is-live-preview" in selectors[1]
    assert ".cm-content > .cm-line.HyperMD-header-1" in selectors[1]
    assert "font-size: var(--font-text-size);" in declarations
    assert "font-weight: 400;" in declarations
    assert "--h1-size: var(--font-text-size);" in declarations
    assert "--h1-weight: 400;" in declarations
    # Neither a standalone H1 nor an unrelated view can satisfy both page guards.
    assert "visibility:" not in declarations and "opacity:" not in declarations
    assert "display:" not in declarations
    for identity, path in views.identity_page_paths(atlas).items():
        assert tree[path].decode().startswith(f"# {atlas.entities[identity].name}\n")


FUNCTION_PARTICIPANTS = {
    "FUNC-ACQUIRE": {"ENV-GAME-INSTANCE", "CMP-SCREEN-CAPTURE", "CMP-VISIBLE-STATE-BRIDGE"},
    "FUNC-OBSERVE": {
        "CMP-NO-SPOILER-FIREWALL",
        "CMP-PERCEPTION",
        "DAT-OBSERVATION",
        "CMP-TEMPORAL-STATE",
    },
    "FUNC-RETAIN-RETRIEVE": {"CMP-EVIDENCE-LEDGER", "CMP-MEMORY", "CMP-MEM-RETRIEVAL"},
    "FUNC-REASON": {"CMP-CORTEX"},
    "FUNC-EXECUTIVE-CONTROL": {
        "CMP-MANAGER",
        "CMP-MANAGER-GROUNDING",
        "CMP-MANAGER-SCHED-COMP",
        "CON-SKILL-CONTRACT",
    },
    "FUNC-ACT": {"CMP-BODY", "CMP-BOUNDED-REFLEX", "CMP-SAFETY-FILTER", "CMP-INPUT-EXECUTOR"},
    "FUNC-VERIFY": {"DAT-VISIBLE-OUTCOME", "CMP-INDEPENDENT-VERIFIER", "CON-VERIFIER-RESULT"},
    "FUNC-BETWEEN-RUNS": {
        "CMP-REPLAY-BUFFER",
        "CMP-SKILL-TRAINER",
        "DAT-CANDIDATE-BODY-VERSION",
        "CMP-BODY-CERTIFICATION",
    },
}


def section(page, heading, following):
    return page.split(f"## {heading}\n", 1)[1].split(f"## {following}\n", 1)[0].replace(r"\|", "|")


def test_uip_function_schema_exact_memberships_and_one_preferred_identity(atlas):
    assert atlas.source_atlas_schema == "0.3"
    assert {i for i, n in atlas.entities.items() if n.type == "Function"} == set(
        FUNCTION_PARTICIPANTS
    )
    edges = [e for e in atlas.relationships if e.relation == "contributes_to_function"]
    assert len(edges) == 26
    assert all(e.functional_role is None and e.functional_order is None for e in edges)
    tree, _, reference, _ = identity_page_tree(atlas)
    assert yaml.safe_load(tree[views.MANIFEST])["source_atlas_schema"] == "0.3"
    paths = views.identity_page_paths(atlas)
    assert len(paths) == len(set(paths.values())) == 58
    for function, expected in FUNCTION_PARTICIPANTS.items():
        model = views.identity_page_model(atlas, reference, function, page_paths=paths)
        assert model.subject.type == "Function"
        assert (
            model.technical_parent_ids == model.child_component_ids == model.literature_paths == ()
        )
        page = tree[paths[function]].decode()
        assert page.startswith(f"# {model.subject.name}\n")
        assert f"*Function · Stable ID `{function}`*" in page
        assert "## Local Anatomy" not in page and "Go deeper" not in page
        assert "Membership is non-containment" in page
        participants = section(page, "Explicit participants", "Technical")
        actual = set(re.findall(r"`((?:CMP|CON|DAT|ENV)-[A-Z0-9-]+)` ·", participants))
        assert actual == expected
        assert "Authored role" not in participants and "Authored order" not in participants
        assert all(
            views._identity_page_human_link(atlas, i, paths) in participants for i in expected
        )
        for i in expected:
            context = section(tree[paths[i]].decode(), "Functional Context", "Technical")
            assert views._identity_page_human_link(atlas, function, paths) in context
            assert f"`{function}` · Function" in context
        assert "## Technical\n" in page and "## Research\n" in page
        assert "EVID-FUNCTION-SEMANTICS-137" in identity_page_audit_text(page)


def test_function_context_is_exact_and_never_domain_assembly_or_ancestry_inferred(atlas):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    # The child shares technical ancestry and Observe navigation, but no Function relation.
    child = page(atlas, "CMP-OBSERVATION-BUILDER")
    assert "No explicit Function mapping" in section(child, "Functional Context", "Local Anatomy")
    assert "FUNC-OBSERVE" not in child
    changed = replace(
        atlas,
        relationships=tuple(
            e
            for e in atlas.relationships
            if not (e.relation == "contributes_to_function" and e.source == "CMP-PERCEPTION")
        ),
    )
    without = views.identity_page_model(changed, reference, "CMP-PERCEPTION")
    original = views.identity_page_model(atlas, reference, "CMP-PERCEPTION")
    assert without.technical_parent_ids == original.technical_parent_ids == ("SYS-AGA",)
    assert without.child_component_ids == original.child_component_ids
    text = views.render_identity_page(SOURCE_COMMIT, changed, without).decode()
    assert "No explicit Function mapping" in section(text, "Functional Context", "Local Anatomy")
    assert "FUNC-OBSERVE" not in text
    assert section(text, "Research", "Gap Analysis") == section(
        page(atlas, "CMP-PERCEPTION"), "Research", "Gap Analysis"
    )
    reordered = replace(
        atlas,
        relationships=tuple(reversed(atlas.relationships)),
        entities=dict(reversed(list(atlas.entities.items()))),
    )
    assert page(reordered, "FUNC-OBSERVE") == page(atlas, "FUNC-OBSERVE")


def test_function_membership_metadata_is_authored_only_and_research_is_not_inherited(atlas):
    edges = tuple(
        e.model_copy(update={"functional_role": "Integrity | <check>", "functional_order": 2})
        if e.relation == "contributes_to_function" and e.source == "CMP-PERCEPTION"
        else e
        for e in atlas.relationships
    )
    changed = replace(atlas, relationships=edges)
    technical = page(changed, "CMP-PERCEPTION")
    functional = page(changed, "FUNC-OBSERVE")
    for text, title in ((technical, "Functional Context"), (functional, "Explicit participants")):
        context = section(text, title, "Technical")
        assert "Authored role" in context and "Authored order" in context
        assert "Integrity &#124; &#60;check&#62;" in context
        assert " | 2 |" in context
        assert "| — | — |" in context if title == "Explicit participants" else True
    assert section(technical, "Research", "Gap Analysis") == section(
        page(atlas, "CMP-PERCEPTION"), "Research", "Gap Analysis"
    )
    assert section(functional, "Research", "Gap Analysis") == section(
        page(atlas, "FUNC-OBSERVE"), "Research", "Gap Analysis"
    )
    assert "No direct research question" in section(functional, "Research", "Gap Analysis")
    assert "RQ-PERCEPTION" not in section(functional, "Research", "Gap Analysis")


def test_preferred_function_routes_and_legacy_observe_are_non_structural(atlas):
    tree, _, _, _ = identity_page_tree(atlas)
    paths = views.identity_page_paths(atlas)
    observe_link = views._identity_page_human_link(atlas, "FUNC-OBSERVE", paths)
    perception = tree[paths["CMP-PERCEPTION"]].decode()
    location = perception.split("**Location:**", 1)[1].split("## Overview", 1)[0]
    assert "Observe" not in location and "FUNC-OBSERVE" not in location
    assert observe_link in section(perception, "Functional Context", "Local Anatomy")
    assert "Back to Observe" not in perception
    assert "Functional context: " + observe_link in section(
        perception, "Return Navigation", "unused"
    )
    compatibility = tree[views.OBSERVE_SCOPE].decode()
    assert "Legacy Assembly compatibility surface" in compatibility
    assert "Observe · FUNC-OBSERVE" in compatibility
    home = tree[views.K3_HOME].decode()
    assert observe_link in home
    assert views._identity_page_human_link(atlas, "SYS-AGA", paths) in home
    projection = technical_projection.projection_tree(atlas, SOURCE_COMMIT, {})
    anatomy = projection[technical_projection.ANATOMY].decode()
    assert views._derived_link(paths["FUNC-OBSERVE"], "Observe · Functional Context") in anatomy
    assert "Observe Assembly Scope]]" not in anatomy
    assert (
        views._identity_page_human_link(atlas, "SYS-AGA", paths) in tree[views.HIERARCHY].decode()
    )


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4, 5, 6])
def test_local_anatomy_density_thresholds_keep_every_direct_child(atlas, count):
    reference = build_index(atlas, make_snapshot([], atlas), SOURCE_COMMIT)
    base = views.identity_page_model(atlas, reference, "CMP-MEMORY")
    subset = replace(base, child_component_ids=base.child_component_ids[:count])
    rendered = views.render_identity_page(SOURCE_COMMIT, atlas, subset).decode()
    anatomy = section(rendered, "Local Anatomy", "Technical").split("## Visual Context", 1)[0]
    assert f"Registered direct subcomponents: **{count}**." in anatomy
    assert anatomy.count("[!aga-child]") == (count if count <= 4 else 0)
    assert ("| Direct Component | Responsibility |" in anatomy) == (count >= 5)
    assert ("No registered direct subcomponents" in anatomy) == (count == 0)
    assert "[!aga-depth]" not in anatomy
    for identity in subset.child_component_ids:
        assert anatomy.count(views._identity_page_human_link(atlas, identity)) == 1


def test_uip_native_tables_escape_wikilink_delimiters_and_function_name_collisions(atlas):
    for identity, heading, expected_rows in (
        ("SYS-AGA", "Local Anatomy", 17),
        ("CMP-MEMORY", "Local Anatomy", 6),
        ("FUNC-OBSERVE", "Explicit participants", 4),
        ("CMP-PERCEPTION", "Functional Context", 1),
    ):
        raw = page(atlas, identity).split(f"## {heading}\n", 1)[1].split("## Technical", 1)[0]
        rows = [line for line in raw.splitlines() if line.startswith("|")]
        assert len(rows) == expected_rows + 2
        assert all(len(re.split(r"(?<!\\)\|", row)) == 4 for row in rows)
        assert all(r"\|" in row for row in rows[2:])
    entities = dict(atlas.entities)
    entities["FUNC-OBSERVE"] = entities["FUNC-OBSERVE"].model_copy(
        update={"name": "Memory Retrieval"}
    )
    collision = replace(atlas, entities=entities)
    paths = views.identity_page_paths(collision)
    assert paths["FUNC-OBSERVE"] == PurePosixPath(
        "identity-pages/Memory Retrieval — FUNC-OBSERVE.md"
    )
    assert paths["CMP-MEM-RETRIEVAL"] == views.MEMORY_WORKBENCH
    assert len(paths) == len(set(paths.values()))
    rendered = page(collision, "FUNC-OBSERVE")
    assert "*Function · Stable ID `FUNC-OBSERVE`*" in rendered
    assert (
        views._identity_page_generated_metadata(rendered, paths["FUNC-OBSERVE"])[
            "identity_page_registry_type"
        ]
        == "Function"
    )


@pytest.mark.parametrize("identity", ["CMP-PERCEPTION", "FUNC-OBSERVE"])
def test_full_primary_sections_keep_native_h2s_and_scannable_css_off_dividers(atlas, identity):
    rendered = page(atlas, identity)
    visible = rendered.split(views.IDENTITY_PAGE_METADATA_MARKER, 1)[0]
    headings = re.findall(r"^## (.+)$", visible, re.M)
    assert headings.count("Technical") == headings.count("Research") == 1
    assert (
        headings.index("Technical")
        < headings.index("Research")
        < headings.index("Evidence / Provenance")
    )
    marker = '<span class="aga-primary-section"></span>'
    assert re.findall(r"^---\n\n" + re.escape(marker) + r"\n\n## (.+)$", visible, re.M) == [
        "Technical",
        "Research",
    ]
    assert visible.count(marker) == 2
    assert len(re.findall(r"^---$", visible, re.M)) == 2
    assert "\n---\n\n## Evidence / Provenance" not in visible
    assert "[!aga-technical-entry] TECHNICAL — How does it work?" in visible
    assert "[!aga-research-entry] RESEARCH — What do we know or need to know?" in visible
    assert visible.index("[!aga-technical-entry]") < visible.index("\n## Technical\n")
    assert visible.index("[!aga-research-entry]") < visible.index("\n## Research\n")
    assert "[[#Technical|Read Technical on this page]]" in visible
    assert "[[#Research|Read Research on this page]]" in visible
    assert "<" not in visible.replace(marker, "")  # Real Markdown H2s remain.
    assert "## Evidence / Provenance\n" in visible and "## Return Navigation\n" in visible
    if identity == "FUNC-OBSERVE":
        assert "*Function · Stable ID `FUNC-OBSERVE`*" in visible
        assert "## Local Anatomy" not in visible
    else:
        assert "*Component · Stable ID `CMP-PERCEPTION`*" in visible
        assert "Registered direct subcomponents: **2**." in visible


def test_full_primary_section_css_scopes_native_rules_in_both_obsidian_modes():
    css = (ROOT / "docs/research-atlas/presentation/aga-identity-pages.css").read_text()
    rule = css.split("/* Native thematic breaks", 1)[1].split("/* Primary H2 bands", 1)[0]
    rule = re.sub(r"/\*.*?\*/", "", "/* Native thematic breaks" + rule, flags=re.S)
    selectors, declarations = rule.split("{", 1)
    selectors = [s.strip() for s in selectors.split(",\n")]
    assert len(selectors) == 2
    guard = ':has(.callout[data-callout="aga-hero"]:not(.markdown-embed .callout))'
    assert all(guard in selector for selector in selectors)
    assert selectors[0].startswith(".markdown-preview-view")
    assert "> .markdown-preview-sizer > .el-hr > hr" in selectors[0]
    assert selectors[1].startswith(".markdown-source-view.mod-cm6.is-live-preview")
    assert ".cm-content > .cm-line:is(.HyperMD-hr, .hr)" in selectors[1]
    assert "--hr-thickness: 0.2rem;" in declarations
    assert "margin-block: 2rem 0.75rem;" in declarations
    assert "--hr-color: var(--text-muted);" in declarations
    assert not re.search(
        r"(?<![\w-])(?:display|height|overflow|visibility|opacity|clip|content)\s*:", declarations
    )
    assert "Evidence" not in selectors and "h2" not in selectors
    assert "aga-technical-entry" not in selectors and "aga-research-entry" not in selectors
    assert "@media (max-width: 40rem)" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css


def test_primary_h2_bands_are_local_to_marked_native_headings():
    css = (ROOT / "docs/research-atlas/presentation/aga-identity-pages.css").read_text()
    rule = css.split("/* Primary H2 bands", 1)[1].split("/* Narrow panes", 1)[0]
    selectors, declarations = rule.split("*/", 1)[1].split("{", 1)
    reading, live = selectors.split(",\n")
    assert "> .el-hr + .el-p:has(> p > .aga-primary-section) + .el-h2" in reading
    assert '> h2:is([data-heading="Technical"], [data-heading="Research"])' in reading
    assert ".markdown-source-view.mod-cm6.is-live-preview .cm-content" in live
    assert "> .cm-line:has(> .cm-html-embed > .aga-primary-section)" in live
    assert "+ .cm-line:has(> br:only-child) + .cm-line.HyperMD-header-2" in live
    assert "aga-hero" not in selectors and selectors.count("aga-primary-section") == 2
    for other in (
        "Evidence",
        "Functional Context",
        "Local Anatomy",
        "Related Objects",
        "Gap Analysis",
    ):
        assert other not in selectors
    for declaration in (
        "margin-block: 1.5rem 1rem;",
        "padding: 0.65rem 0.9rem;",
        "border-inline-start: 0.3rem solid",
        "background: var(--background-secondary);",
        "--h2-weight: 700;",
        "box-sizing: border-box;",
        "overflow-wrap: anywhere;",
    ):
        assert declaration in declarations
    assert not re.search(
        r"(?<![\w-])(?:display|height|overflow|visibility|opacity|clip|content)\s*:", declarations
    )


def engineering_seed(atlas):
    from fh_agent.research_atlas.engineering_provenance import CATALOG_PATH, parse_catalog

    return parse_catalog((ROOT / CATALOG_PATH).read_bytes(), atlas)


def engineering_page(atlas, bindings, subject="CMP-PERCEPTION"):
    snapshot = make_snapshot([], atlas)
    reference = build_index(atlas, snapshot, SOURCE_COMMIT)
    model = views.identity_page_model(atlas, reference, subject)
    return views.render_identity_page(
        SOURCE_COMMIT, atlas, model, engineering_bindings=bindings
    ).decode()


def test_engineering_many_to_many_and_separate_roles(atlas):
    bindings = engineering_seed(atlas)
    assert {binding.subject_id for binding in bindings} == {"CMP-PERCEPTION", "DAT-OBSERVATION"}
    for subject in ("CMP-PERCEPTION", "DAT-OBSERVATION"):
        page = engineering_page(atlas, bindings, subject)
        panel = page.split("> [!info]- Engineering provenance", 1)[1].split(
            "### Implementation notes", 1
        )[0]
        assert "**Implementation source**" in panel
        assert "**PR / change provenance**" in panel
        assert "**Documentation**" in panel
        assert "**Accepted rationale / Decision**" in panel
        assert "**Technical verification**" in panel
        assert "Introduction: **unknown / unavailable**" in panel
        assert "Explicit documented reference: [133]" in panel
        assert "**Accepted Decision record**" in panel
        assert "not current live status" in panel
        assert "technical checks are not experiments" in panel
        assert "2026-10-01" in panel
        assert "36326a78783b40c94838a0944832ac63853a4a93" in panel
        assert page.index("Engineering provenance") < page.index("## Research")
        assert "src/fh_agent/observation/" in panel
        assert "docs/canonical/02_ARCHITECTURE_CANONICAL.md" in panel
    # The same explicitly documented PR and documentation artifact bind both subjects.
    assert (
        sum(bool(binding.reference and "/pull/133" in binding.reference) for binding in bindings)
        == 2
    )
    assert sum(binding.role == "documented" for binding in bindings) == 4


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"subject_id": "CMP-MISSING"}, "Missing or unsupported"),
        ({"subject_id": "CMP-CORTEX"}, "Wrong-subject"),
        ({"evidence_id": "EVID-MISSING"}, "Missing engineering Evidence"),
        ({"subject_id": "RQ-PROGRAM-AB-001"}, "Missing or unsupported"),
        ({"path": "src/fh_agent/planner/cortex.py"}, "exact Evidence locator"),
    ],
)
def test_engineering_references_fail_closed(atlas, mutation, message):
    from fh_agent.research_atlas.engineering_provenance import Catalog, validated_bindings

    binding = next(item for item in engineering_seed(atlas) if item.role == "implementation")
    with pytest.raises(ProjectionError, match=message):
        validated_bindings(
            Catalog(
                presentation_binding_version="1.0", bindings=(binding.model_copy(update=mutation),)
            ),
            atlas,
        )


def test_engineering_duplicates_fail_even_with_different_inspection(atlas):
    from fh_agent.research_atlas.engineering_provenance import Catalog, validated_bindings

    binding = engineering_seed(atlas)[0]
    with pytest.raises(ProjectionError, match="Duplicate"):
        validated_bindings(
            Catalog(
                presentation_binding_version="1.0",
                bindings=(binding, binding.model_copy(update={"inspected_revision": "b" * 40})),
            ),
            atlas,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        {"subject_id": None},
        {"inspected_revision": "main"},
        {"checked_date": "not-a-date"},
        {"path": "."},
        {"path": "src"},
        {"path": "../private/secret.md"},
        {"path": "/private/secret.md"},
        {"path": "private/secret.md"},
        {"reference": "https://example.com/private"},
        {"private_research_payload": "SYNTHETIC-SECRET"},
        {"role": "decision", "accepted_reference": None},
    ],
)
def test_engineering_closed_public_contract(atlas, mutation):
    from pydantic import ValidationError

    from fh_agent.research_atlas.engineering_provenance import Binding

    data = engineering_seed(atlas)[0].model_dump()
    data.update(mutation)
    with pytest.raises(ValidationError):
        Binding.model_validate(data)


def test_engineering_merge_does_not_accept_rationale(atlas):
    bindings = tuple(item for item in engineering_seed(atlas) if item.role != "decision")
    page = engineering_page(atlas, bindings)
    assert "PR status at inspection: **merged**" in page
    assert "Rationale: **unknown / unavailable**" in page
    assert "**Accepted Decision record**" not in page
    assert "Introduction: **unknown / unavailable**" in page
    # Unknown states are bounded inside a collapsed panel, not repeated empty lanes.
    empty = engineering_page(atlas, ())
    assert "**Implementation source**" not in empty
    assert "**Documentation**" not in empty
    assert "**Technical verification**" not in empty


def test_engineering_revision_date_and_input_order_are_deterministic(atlas):
    from datetime import date

    from fh_agent.research_atlas.engineering_provenance import Catalog, validated_bindings

    bindings = engineering_seed(atlas)
    ordered = validated_bindings(
        Catalog(presentation_binding_version="1.0", bindings=bindings), atlas
    )
    reversed_order = validated_bindings(
        Catalog(presentation_binding_version="1.0", bindings=tuple(reversed(bindings))), atlas
    )
    assert engineering_page(atlas, ordered) == engineering_page(atlas, reversed_order)
    changed = tuple(
        item.model_copy(update={"inspected_revision": "b" * 40, "checked_date": date(2026, 10, 2)})
        for item in bindings
    )
    new_page = engineering_page(atlas, changed)
    assert new_page != engineering_page(atlas, ordered)
    assert "b" * 40 in new_page and "2026-10-02" in new_page
    assert new_page == engineering_page(atlas, changed)


def test_engineering_cannot_promote_scientific_evidence(atlas):
    from fh_agent.research_atlas.engineering_provenance import Catalog, validated_bindings

    binding = engineering_seed(atlas)[0]
    evidence = atlas.entities[binding.evidence_id]
    changed = replace(
        atlas,
        entities={
            identity: item.model_copy(update={"provenance_kind": "primary_literature"})
            if identity == evidence.id
            else item
            for identity, item in atlas.entities.items()
        },
    )
    with pytest.raises(ProjectionError, match="Scientific/private"):
        validated_bindings(
            Catalog(presentation_binding_version="1.0", bindings=(binding,)), changed
        )


def test_engineering_preserves_all_preferred_routes_and_semantics(atlas):
    bindings = engineering_seed(atlas)
    paths = views.identity_page_paths(atlas)
    before_registry = views.registry_content_revision(atlas)
    for subject, path in paths.items():
        before = engineering_page(atlas, (), subject)
        after = engineering_page(atlas, bindings, subject)
        assert path == views.identity_page_paths(atlas)[subject]

        # Only the collapsed provenance payload changes; all navigation/Research stays exact.
        def remove_panel(text):
            return re.sub(r"> \[!info\]- Engineering provenance\n(?:>[^\n]*\n)*", "", text)

        assert remove_panel(before) == remove_panel(after)
        assert "SYNTHETIC-SECRET" not in after
    assert views.registry_content_revision(atlas) == before_registry
    assert atlas.source_atlas_schema == "0.3"
    assert sum(node.type == "Function" for node in atlas.entities.values()) == 8
    assert sum(edge.relation == "contributes_to_function" for edge in atlas.relationships) == 26


def test_engineering_explicit_change_roles_are_not_generic_related_pr(atlas):
    from fh_agent.research_atlas.engineering_provenance import Binding, Catalog, validated_bindings

    documented = next(
        item for item in engineering_seed(atlas) if item.reference and "/pull/" in item.reference
    )
    data = documented.model_dump()
    introduced = Binding.model_validate(dict(data, role="introduced"))
    modified = Binding.model_validate(dict(data, role="modified"))
    bindings = validated_bindings(
        Catalog(presentation_binding_version="1.0", bindings=(introduced, modified)), atlas
    )
    page = engineering_page(atlas, bindings)
    assert "**Introduced**" in page and "**Modified**" in page
    assert "Introduction: **unknown / unavailable**" not in page
    assert "Rationale: **unknown / unavailable**" in page
    assert "**Accepted Decision record**" not in page


def test_engineering_malformed_or_missing_subject_catalog_fails_closed(atlas):
    from fh_agent.research_atlas.engineering_provenance import parse_catalog

    with pytest.raises(ProjectionError, match="Invalid public engineering"):
        parse_catalog(b'presentation_binding_version: "1.0"\nbindings: [{}]\n', atlas)
    with pytest.raises(ProjectionError):
        parse_catalog(b'presentation_binding_version: "1.0"\nbindings: [\n', atlas)
