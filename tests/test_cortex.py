import json

import pytest
from pydantic import ValidationError

from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.planner.cortex import (
    Cortex,
    build_plan_next_goal_messages,
    build_post_mortem_messages,
    load_prompt,
)
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.planner.planner_output import PlannerOutputError


def valid_planner_payload() -> dict[str, object]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "A visible message is currently on screen.",
                "evidence_ids": ["shot-1"],
            }
        ],
        "open_questions": ["Which visible exit is safest?"],
        "next_goal": "Continue the visible dialogue until the message changes.",
        "selected_skill": "continue_dialogue",
        "success_condition": ["visible_text_changed"],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [],
    }


def visible_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Visible text.",
        screenshot_id="shot-1",
        evidence_ids=["shot-1"],
    )


def later_visible_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        visible_message_text="Changed visible text.",
        screenshot_id="shot-2",
        evidence_ids=["shot-2"],
    )


def valid_post_mortem_payload() -> dict[str, object]:
    return {
        "observed_outcome": "The visible text changed after the skill result.",
        "likely_causes": [
            {
                "status": "hypothesis",
                "note": "The universal dialogue skill may have advanced visible text.",
                "evidence_ids": [],
            }
        ],
        "evidence_backed_notes": [
            {
                "status": "observed_fact",
                "note": "The later observation contains changed visible text.",
                "evidence_ids": ["shot-2"],
            }
        ],
        "hypotheses": [
            {
                "status": "hypothesis",
                "note": "A follow-up observation may reveal whether dialogue closed.",
                "evidence_ids": [],
            }
        ],
        "next_safe_experiments": ["Observe for another visible text change."],
        "memory_updates_requested": [
            {
                "claim": "Visible text changed after continue_dialogue.",
                "evidence_ids": ["shot-2"],
            }
        ],
    }


def test_cortex_validates_fake_llm_output() -> None:
    payload = valid_planner_payload()
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    output = cortex.plan_next_goal(
        visible_observation(),
        {"known_facts": [{"claim": "Visible text exists.", "evidence_ids": ["shot-1"]}]},
    )

    assert output.selected_skill == "continue_dialogue"
    assert output.current_belief_state[0].evidence_ids == ["shot-1"]
    assert len(client.requests) == 1


def test_cortex_accepts_retrieved_known_fact_evidence() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": "fact",
            "claim": "A previously observed visible fact remains relevant.",
            "evidence_ids": ["shot-prior"],
        }
    ]
    client = FakeLLMClient(responses=[json.dumps(payload)])

    output = Cortex(client).plan_next_goal(
        visible_observation().model_copy(
            update={"screenshot_id": "shot-current", "evidence_ids": ["shot-current"]}
        ),
        {
            "known_facts": [
                {
                    "claim": "Previously observed visible fact.",
                    "evidence_ids": ["shot-prior"],
                }
            ]
        },
    )

    assert output.current_belief_state[0].evidence_ids == ["shot-prior"]
    assert len(client.requests) == 1


def test_cortex_accepts_evidence_bearing_retrieved_hypothesis_support() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": "hypothesis",
            "claim": "The visible state may support a cautious next observation.",
            "evidence_ids": ["shot-hypothesis-support"],
        }
    ]
    client = FakeLLMClient(responses=[json.dumps(payload)])

    output = Cortex(client).plan_next_goal(
        visible_observation(),
        {
            "hypotheses": [
                {
                    "claim": "A prior visible observation may be relevant.",
                    "evidence_ids": ["shot-hypothesis-support"],
                }
            ]
        },
    )

    assert output.current_belief_state[0].kind == "hypothesis"
    assert len(client.requests) == 1


@pytest.mark.parametrize(
    ("field", "payload_evidence"),
    [
        ("fact", "shot-never-seen"),
        ("hypothesis", "fabricated-hypothesis-evidence"),
    ],
)
def test_cortex_rejects_fabricated_claim_evidence(field: str, payload_evidence: str) -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": field,
            "claim": "A proposed visible-state claim.",
            "evidence_ids": [payload_evidence],
        }
    ]
    client = FakeLLMClient(responses=[json.dumps(payload)])

    with pytest.raises(PlannerOutputError, match=payload_evidence):
        Cortex(client).plan_next_goal(visible_observation(), {})

    assert len(client.requests) == 1


def test_cortex_rejects_fabricated_memory_update_evidence() -> None:
    payload = valid_planner_payload()
    payload["memory_updates_requested"] = [
        {"claim": "Remember this visible claim.", "evidence_ids": ["fabricated-memory-evidence"]}
    ]
    client = FakeLLMClient(responses=[json.dumps(payload)])

    with pytest.raises(PlannerOutputError, match="fabricated-memory-evidence"):
        Cortex(client).plan_next_goal(visible_observation(), {})

    assert len(client.requests) == 1


def test_cortex_rejects_mixed_valid_and_invalid_evidence_without_filtering() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": "fact",
            "claim": "A visible message is currently on screen.",
            "evidence_ids": ["shot-1", "shot-invalid"],
        }
    ]
    client = FakeLLMClient(responses=[json.dumps(payload)])

    with pytest.raises(
        PlannerOutputError,
        match="outside CortexContext: shot-invalid",
    ):
        Cortex(client).plan_next_goal(visible_observation(), {})

    assert len(client.requests) == 1


def test_cortex_accepts_evidence_free_hypothesis() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": "hypothesis",
            "claim": "A visible state may change after a safe interaction.",
            "evidence_ids": [],
        }
    ]
    payload["memory_updates_requested"] = []
    client = FakeLLMClient(responses=[json.dumps(payload)])

    output = Cortex(client).plan_next_goal(visible_observation(), {})

    assert output.current_belief_state[0].evidence_ids == []
    assert len(client.requests) == 1


def test_cortex_does_not_treat_screenshot_id_as_evidence_authority() -> None:
    payload = valid_planner_payload()
    payload["current_belief_state"] = [
        {
            "kind": "hypothesis",
            "claim": "A descriptive screenshot identifier may support a claim.",
            "evidence_ids": ["shot-descriptive-only"],
        }
    ]
    payload["memory_updates_requested"] = []
    client = FakeLLMClient(responses=[json.dumps(payload)])
    observation = visible_observation().model_copy(
        update={"screenshot_id": "shot-descriptive-only", "evidence_ids": []}
    )

    with pytest.raises(PlannerOutputError, match="shot-descriptive-only"):
        Cortex(client).plan_next_goal(observation, {})

    assert len(client.requests) == 1


def test_cortex_rejects_invalid_llm_output() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "solve_specific_quest"
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    with pytest.raises(ValidationError):
        cortex.plan_next_goal(visible_observation(), {})


def test_cortex_rejects_globally_known_but_runtime_unavailable_skill() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "safe_reach_target"
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    with pytest.raises(PlannerOutputError, match="unavailable.*safe_reach_target"):
        cortex.plan_next_goal(visible_observation(), {})


def test_cortex_respects_per_call_available_skill_subset() -> None:
    payload = valid_planner_payload()
    payload["selected_skill"] = "basic_reach_target"
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    with pytest.raises(PlannerOutputError, match="unavailable.*basic_reach_target"):
        cortex.plan_next_goal(
            visible_observation(),
            {},
            available_skills=("continue_dialogue",),
        )

    context_payload = json.loads(client.requests[0][1]["content"].split("CortexContext JSON:\n")[1])
    assert context_payload["allowed_skills"] == ["continue_dialogue"]


def test_cortex_rejects_hidden_state_in_planning_context_before_llm_call() -> None:
    client = FakeLLMClient(responses=[json.dumps(valid_planner_payload())])
    cortex = Cortex(client)
    hidden_state_observation = visible_observation().model_copy(
        update={"visible_message_text": "Forbidden source: map_id"}
    )

    with pytest.raises(ValidationError, match="hidden-state terms"):
        cortex.plan_next_goal(hidden_state_observation, {})

    assert client.requests == []


def test_cortex_rejects_direct_key_plan_from_llm() -> None:
    payload = valid_planner_payload()
    payload["key_sequence"] = ["confirm", "open_menu"]
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    with pytest.raises(ValidationError, match="direct primitive controls"):
        cortex.plan_next_goal(visible_observation(), {})


def test_cortex_post_mortem_validates_fake_llm_output() -> None:
    client = FakeLLMClient(responses=[json.dumps(valid_post_mortem_payload())])
    cortex = Cortex(client)

    output = cortex.post_mortem(
        [visible_observation(), later_visible_observation()],
        skill_results=[
            SkillResult(
                skill_name="continue_dialogue",
                success=True,
                evidence_ids=["shot-2"],
            )
        ],
        outcome_summary={"summary": "Visible text changed."},
    )

    assert output.observed_outcome.startswith("The visible text changed")
    assert output.evidence_backed_notes[0].evidence_ids == ["shot-2"]
    assert len(client.requests) == 1
    assert "CortexContext JSON" in client.requests[0][1]["content"]


def test_cortex_post_mortem_rejects_malformed_json() -> None:
    client = FakeLLMClient(responses=["{not json"])
    cortex = Cortex(client)

    with pytest.raises(ValidationError):
        cortex.post_mortem([visible_observation()])


def test_cortex_post_mortem_rejects_hidden_state_terms() -> None:
    payload = valid_post_mortem_payload()
    payload["observed_outcome"] = "Do not use map_id in a reflection."
    client = FakeLLMClient(responses=[json.dumps(payload)])
    cortex = Cortex(client)

    with pytest.raises(ValidationError, match="hidden-state terms"):
        cortex.post_mortem([visible_observation()])


def test_build_plan_prompt_contains_visible_input_and_no_spoiler_rules() -> None:
    messages = build_plan_next_goal_messages(
        visible_observation(),
        {"hypotheses": ["Visible text may indicate a dialogue state."]},
    )

    assert messages[0]["role"] == "system"
    assert "Do not use external Fear & Hunger facts" in messages[0]["content"]
    assert "Do not output keys" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Visible text." in messages[1]["content"]
    assert "shot-1" in messages[1]["content"]


def test_build_post_mortem_prompt_contains_visible_inputs_and_rules() -> None:
    messages = build_post_mortem_messages(
        [visible_observation(), later_visible_observation()],
        skill_results=[
            SkillResult(
                skill_name="continue_dialogue",
                success=True,
                evidence_ids=["shot-2"],
            )
        ],
        outcome_summary={"summary": "Visible text changed."},
    )

    assert messages[0]["role"] == "system"
    assert "Do not use external Fear & Hunger facts" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "post-mortem" in messages[1]["content"]
    assert "CortexContext JSON" in messages[1]["content"]
    assert "Changed visible text." in messages[1]["content"]
    assert "shot-2" in messages[1]["content"]


def test_prompt_files_include_required_no_spoiler_constraints() -> None:
    prompt_text = "\n".join(
        [
            load_prompt("system_no_spoiler.md"),
            load_prompt("plan_next_goal.md"),
            load_prompt("post_mortem.md"),
        ]
    )

    assert "guides" in prompt_text
    assert "wikis" in prompt_text
    assert "datamining" in prompt_text
    assert "map IDs" in prompt_text
    assert "enemy databases" in prompt_text
    assert "switches" in prompt_text
    assert "variables" in prompt_text
    assert "savegame internals" in prompt_text
    assert "ending flags" in prompt_text
    assert "Facts require evidence_ids" in prompt_text
    assert "Do not output keys" in prompt_text
    assert "actions" in prompt_text
    assert "PostMortemOutput" in prompt_text
    assert "CortexContext is the only allowed source" in prompt_text
