import json

import pytest
from pydantic import ValidationError

from fh_agent.planner.planner_output import (
    PlannerOutput,
    PostMortemOutput,
    parse_planner_output_json,
    parse_post_mortem_output_json,
)


def valid_planner_payload() -> dict[str, object]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "A visible message is currently on screen.",
                "evidence_ids": ["shot-1"],
            },
            {
                "kind": "hypothesis",
                "claim": "There may be an unexplored exit to inspect.",
                "evidence_ids": [],
            },
        ],
        "open_questions": ["Which visible exit is safest?"],
        "next_goal": "Continue the visible dialogue until the message changes.",
        "selected_skill": "continue_dialogue",
        "success_condition": ["visible_text_changed"],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [
            {
                "claim": "A visible message is currently on screen.",
                "evidence_ids": ["shot-1"],
                "reason": "Observed in the current screenshot.",
            }
        ],
    }


def test_planner_output_accepts_universal_skill_and_evidence_backed_fact() -> None:
    output = PlannerOutput.model_validate(valid_planner_payload())

    assert output.selected_skill == "continue_dialogue"
    assert output.current_belief_state[0].evidence_ids == ["shot-1"]


def test_fact_claims_require_evidence_ids() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {"kind": "fact", "claim": "This is a game-specific claim.", "evidence_ids": []}
    ]

    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(payload)


def test_hypothesis_can_have_no_evidence() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {"kind": "hypothesis", "claim": "A visible object may be useful.", "evidence_ids": []}
    ]
    payload["memory_updates_requested"] = []

    output = PlannerOutput.model_validate(payload)

    assert output.current_belief_state[0].kind == "hypothesis"


def test_rejects_fh_specific_skill_names() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "kill_guard_x"

    with pytest.raises(ValidationError):
        PlannerOutput.model_validate(payload)


@pytest.mark.parametrize("field_name", ["keys", "key_sequence", "primitive_actions"])
def test_rejects_direct_control_fields(field_name: str) -> None:
    payload = valid_planner_payload()
    payload[field_name] = ["confirm"]

    with pytest.raises(ValidationError, match="direct primitive controls"):
        PlannerOutput.model_validate(payload)


def test_rejects_nested_primitive_action_sequence() -> None:
    payload = valid_planner_payload()
    payload["memory_updates_requested"] = []
    payload["current_belief_state"] = [
        {
            "kind": "hypothesis",
            "claim": "Try a direct list.",
            "evidence_ids": [],
            "notes": ["move_up_short", "confirm"],
        }
    ]

    with pytest.raises(ValidationError, match="direct primitive controls"):
        PlannerOutput.model_validate(payload)


def test_parse_planner_output_json() -> None:
    output = parse_planner_output_json(json.dumps(valid_planner_payload()))

    assert output.next_goal.startswith("Continue")


def valid_post_mortem_payload() -> dict[str, object]:
    return {
        "observed_outcome": "The visible dialogue text changed after the skill result.",
        "likely_causes": [
            {
                "status": "hypothesis",
                "note": "The interaction may have advanced a visible message.",
                "evidence_ids": [],
            }
        ],
        "evidence_backed_notes": [
            {
                "status": "observed_fact",
                "note": "The final observation shows different visible text.",
                "evidence_ids": ["shot-2"],
            },
            {
                "status": "validated_rule",
                "note": "Visible text change is a successful outcome for dialogue continuation.",
                "evidence_ids": ["skill-result-1"],
            },
        ],
        "hypotheses": [
            {
                "status": "hypothesis",
                "note": "Repeating the universal dialogue skill may close the message.",
                "evidence_ids": [],
            }
        ],
        "next_safe_experiments": ["Observe whether the visible message changes again."],
        "memory_updates_requested": [
            {
                "claim": "Visible text changed after the skill result.",
                "evidence_ids": ["shot-2"],
                "reason": "Outcome was visible in the supplied observation.",
            }
        ],
    }


def test_post_mortem_output_accepts_evidence_backed_notes() -> None:
    output = PostMortemOutput.model_validate(valid_post_mortem_payload())

    assert output.evidence_backed_notes[0].status == "observed_fact"
    assert output.evidence_backed_notes[0].evidence_ids == ["shot-2"]


def test_post_mortem_observed_fact_requires_evidence_ids() -> None:
    payload = valid_post_mortem_payload()
    payload["evidence_backed_notes"] = [
        {"status": "observed_fact", "note": "Visible fact without evidence.", "evidence_ids": []}
    ]

    with pytest.raises(ValidationError):
        PostMortemOutput.model_validate(payload)


def test_post_mortem_hypothesis_can_have_no_evidence() -> None:
    payload = valid_post_mortem_payload()
    payload["hypotheses"] = [
        {
            "status": "hypothesis",
            "note": "A safer route may be visible later.",
            "evidence_ids": [],
        }
    ]

    output = PostMortemOutput.model_validate(payload)

    assert output.hypotheses[0].status == "hypothesis"
    assert output.hypotheses[0].evidence_ids == []


@pytest.mark.parametrize("field_name", ["keys", "key_sequence", "primitive_actions", "actions"])
def test_post_mortem_rejects_direct_control_fields(field_name: str) -> None:
    payload = valid_post_mortem_payload()
    payload[field_name] = ["confirm"]

    with pytest.raises(ValidationError, match="direct primitive controls"):
        PostMortemOutput.model_validate(payload)


def test_post_mortem_rejects_nested_primitive_action_sequence() -> None:
    payload = valid_post_mortem_payload()
    payload["hypotheses"] = [
        {
            "status": "hypothesis",
            "note": "Unsafe direct sequence.",
            "evidence_ids": [],
            "plan": ["move_up_short", "confirm"],
        }
    ]

    with pytest.raises(ValidationError, match="direct primitive controls"):
        PostMortemOutput.model_validate(payload)


@pytest.mark.parametrize(
    "hidden_term",
    ["game_switches", "map_id", "enemy_hp", "savegame_variables"],
)
def test_post_mortem_rejects_hidden_state_terms(hidden_term: str) -> None:
    payload = valid_post_mortem_payload()
    payload["observed_outcome"] = f"Rejected hidden source: {hidden_term}"

    with pytest.raises(ValidationError, match="hidden-state terms"):
        PostMortemOutput.model_validate(payload)


def test_parse_post_mortem_output_json_rejects_malformed_json() -> None:
    with pytest.raises(ValidationError):
        parse_post_mortem_output_json("{not json")
