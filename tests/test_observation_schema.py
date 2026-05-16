from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fh_agent.observation.schemas import (
    ActionResult,
    Event,
    KnowledgeFact,
    Observation,
    SkillResult,
    VisibleSprite,
    VisibleTextSpan,
)


def test_observation_is_json_serializable() -> None:
    observation = Observation(
        run_id="run-1",
        screenshot_id="evidence-1",
        message_window_visible=True,
        visible_message_text="Visible text",
        visible_text_spans=[
            VisibleTextSpan(text="Visible text", confidence=0.9, evidence_id="evidence-1")
        ],
        menu_open=False,
        visible_menu_items=["Items", "Skills"],
        combat_ui_visible=False,
        death_screen_visible=False,
        player_screen_position=(10, 20),
        visible_sprite_screen_positions=[(30, 40)],
        visible_sprite_visual_hashes=["abc123"],
        visible_sprites=[
            VisibleSprite(
                screen_position=(30, 40),
                visual_hash="abc123",
                evidence_id="evidence-1",
            )
        ],
        evidence_ids=["evidence-1"],
    )

    dumped = observation.model_dump_json()

    assert '"run_id":"run-1"' in dumped
    assert '"screenshot_id":"evidence-1"' in dumped


def test_knowledge_fact_without_evidence_id_is_invalid() -> None:
    with pytest.raises(ValidationError):
        KnowledgeFact(
            subject="visible-object",
            predicate="appeared_near",
            value="doorway",
            claim="A visible object appeared near a doorway.",
            evidence_ids=[],
        )


def test_knowledge_fact_with_evidence_id_is_valid() -> None:
    fact = KnowledgeFact(
        subject="visible-object",
        predicate="appeared_near",
        value="doorway",
        claim="A visible object appeared near a doorway.",
        evidence_ids=["evidence-1"],
    )

    assert fact.evidence_ids == ["evidence-1"]


def test_event_supports_required_fields() -> None:
    event = Event(
        event_id="event-1",
        run_id="run-1",
        event_type="observation",
        created_at=datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        payload={"observation_id": "obs-1"},
        evidence_ids=["evidence-1"],
    )

    assert event.event_id == "event-1"
    assert event.run_id == "run-1"
    assert event.evidence_ids == ["evidence-1"]


def test_skill_result_supports_failure_reason_and_reward() -> None:
    result = SkillResult(
        skill_name="safe_reach_target",
        success=False,
        failure_reason="timeout",
        reward=-0.1,
        evidence_ids=["evidence-1"],
    )

    assert result.skill_name == "safe_reach_target"
    assert result.failure_reason == "timeout"
    assert result.reward == -0.1


def test_action_result_does_not_model_key_sequences() -> None:
    with pytest.raises(ValidationError):
        ActionResult(
            action="wait",
            executed=True,
            key_sequence=["up", "enter"],
        )
