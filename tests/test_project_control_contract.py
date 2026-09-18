import json
from pathlib import Path

SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "docs"
    / "orchestration"
    / "releases"
    / "ALIGN-2026-09-19-v1.0"
    / "projectctl-status.schema.json"
)


def test_projectctl_status_schema_declares_issue_control_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["alignment_release"]["const"] == "ALIGN-2026-09-19-v1.0"
    assert {
        "task",
        "dependencies",
        "gates",
        "validation",
        "status",
        "limitations",
        "next_step",
    } <= set(schema["required"])

    assert set(schema["properties"]["task"]["properties"]["class"]["enum"]) == {
        "research",
        "decision",
        "implementation",
        "verification",
        "live",
    }
    assert set(schema["properties"]["gates"]["required"]) == {
        "scope",
        "canonical_or_protocol_change",
        "scientific_freeze",
        "live_authorization",
        "focused_validation",
        "ci",
        "review",
        "merge",
    }

    next_step = schema["properties"]["next_step"]
    assert next_step["type"] == "object"
    assert next_step["additionalProperties"] is False
    assert "next_steps" not in schema["properties"]
