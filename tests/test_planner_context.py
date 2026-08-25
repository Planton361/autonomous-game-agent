import json

import pytest
from pydantic import ValidationError

from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.planner.context import (
    CortexContext,
    build_plan_context,
    build_post_mortem_context,
)
from fh_agent.skill_capabilities import DEFAULT_RUNTIME_SKILLS


def test_context_accepts_evidence_backed_fact() -> None:
    context = CortexContext(
        observation_summary={"ui_state": "field", "evidence_ids": ["shot-1"]},
        evidence_backed_facts=[
            {
                "status": "observed_fact",
                "note": "A visible message was observed.",
                "evidence_ids": ["shot-1"],
            }
        ],
    )

    assert context.evidence_backed_facts[0].evidence_ids == ["shot-1"]


@pytest.mark.parametrize("status", ["observed_fact", "validated_rule"])
def test_context_rejects_evidence_backed_note_without_evidence(status: str) -> None:
    with pytest.raises(ValidationError):
        CortexContext(
            evidence_backed_facts=[
                {
                    "status": status,
                    "note": "This factual note has no evidence.",
                    "evidence_ids": [],
                }
            ]
        )


def test_context_accepts_hypothesis_without_evidence() -> None:
    context = CortexContext(
        hypotheses=[
            {
                "status": "hypothesis",
                "note": "A visible route may be safer.",
                "evidence_ids": [],
            }
        ]
    )

    assert context.hypotheses[0].status == "hypothesis"
    assert context.hypotheses[0].evidence_ids == []


@pytest.mark.parametrize(
    "hidden_term",
    [
        "map_id",
        "game_switches",
        "game_variables",
        "enemy_hp",
        "enemy_database",
        "savegame_variables",
    ],
)
def test_context_rejects_hidden_state_terms_recursively(hidden_term: str) -> None:
    with pytest.raises(ValidationError, match="hidden-state terms"):
        CortexContext(observation_summary={"nested": {"source": hidden_term}})


@pytest.mark.parametrize("field_name", ["keys", "key_sequence", "primitive_actions", "actions"])
def test_context_rejects_direct_control_fields_recursively(field_name: str) -> None:
    with pytest.raises(ValidationError, match="direct primitive controls"):
        CortexContext(observation_summary={"nested": {field_name: ["confirm"]}})


def test_context_rejects_primitive_action_lists_recursively() -> None:
    with pytest.raises(ValidationError, match="direct primitive controls"):
        CortexContext(
            hypotheses=[
                {
                    "status": "hypothesis",
                    "note": "Unsafe direct sequence.",
                    "evidence_ids": [],
                    "plan": ["move_up_short", "confirm"],
                }
            ]
        )


def test_context_serialization_is_deterministic() -> None:
    left = CortexContext(
        open_questions=["What changed visibly?"],
        observation_summary={"b": 2, "a": 1},
    )
    right = CortexContext(
        observation_summary={"a": 1, "b": 2},
        open_questions=["What changed visibly?"],
    )

    assert left.to_prompt_json() == right.to_prompt_json()


def test_serialized_context_exposes_exactly_default_runtime_skills() -> None:
    context = CortexContext()

    payload = json.loads(context.to_prompt_json())

    assert payload["allowed_skills"] == list(DEFAULT_RUNTIME_SKILLS)


def test_build_plan_context_from_observation_and_memory_summary() -> None:
    observation = Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Visible.",
        screenshot_id="shot-1",
        evidence_ids=["shot-1"],
    )

    context = build_plan_context(
        observation,
        {
            "known_facts": [
                {
                    "claim": "Visible text is on screen.",
                    "evidence_ids": ["shot-1"],
                }
            ],
            "hypotheses": ["The text may advance."],
            "open_questions": ["Will the text change?"],
        },
    )

    assert context.observation_summary["visible_message_text"] == "Visible."
    assert context.evidence_backed_facts[0].status == "observed_fact"
    assert context.hypotheses[0].status == "hypothesis"
    assert context.open_questions == ["Will the text change?"]


def test_build_post_mortem_context_from_visible_outcomes() -> None:
    observation = Observation(run_id="run-1", ui_state="field", evidence_ids=["shot-2"])
    skill_result = SkillResult(
        skill_name="continue_dialogue",
        success=True,
        evidence_ids=["shot-2"],
    )

    context = build_post_mortem_context(
        [observation],
        skill_results=[skill_result],
        outcome_summary={"open_questions": ["What visible state follows?"]},
    )

    assert context.recent_skill_outcomes[0].status == "observed_fact"
    assert context.recent_skill_outcomes[0].evidence_ids == ["shot-2"]
    assert context.open_questions == ["What visible state follows?"]
