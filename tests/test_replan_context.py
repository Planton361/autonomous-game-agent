import inspect
import json

import pytest

from fh_agent.manager.replan_context import ReplanContextError, build_replan_memory_summary
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskStatus
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.observation.schemas import Observation
from fh_agent.planner.cortex import Cortex
from fh_agent.planner.llm_client import FakeLLMClient
from fh_agent.planner.planner_output import PlannerOutputError
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def completion_event(
    verifier_result: VerifierResult | None,
    *,
    manager_stop_result: ManagerStopResult | None = None,
) -> TaskCompletionEvent:
    return TaskCompletionEvent(
        event_id="completion-event-1",
        run_id="run-1",
        task_id="task-1",
        selected_skill="continue_dialogue",
        goal="Continue the visible dialogue.",
        target=None,
        status=TaskStatus.SUCCEEDED if verifier_result is not None else TaskStatus.FAILED,
        condition="visible_text_changed",
        elapsed_steps=1,
        timeout_steps=3,
        source_evidence_ids=["source-shot"],
        completion_evidence_ids=["completion-shot"],
        verifier_result=verifier_result,
        verifier_event_id="verifier-event-1" if verifier_result is not None else None,
        manager_stop_result=manager_stop_result,
        manager_stop_event_id="stop-event-1" if manager_stop_result is not None else None,
        created_at="2026-09-04T12:00:00+00:00",
    )


def success_completion(*, evidence_ids: list[str] | None = None) -> TaskCompletionEvent:
    return completion_event(
        VerifierResult(
            status=VerifierStatus.SUCCESS,
            evidence_ids=evidence_ids if evidence_ids is not None else ["shot-outcome"],
        )
    )


def failure_completion(*, evidence_ids: list[str] | None = None) -> TaskCompletionEvent:
    return completion_event(
        VerifierResult(
            status=VerifierStatus.FAILURE,
            failure_kind=FailureKind.TARGET_LOST,
            evidence_ids=evidence_ids if evidence_ids is not None else ["shot-failure"],
        )
    )


def valid_planner_payload(evidence_id: str) -> dict[str, object]:
    return {
        "current_belief_state": [
            {
                "kind": "fact",
                "claim": "A verified earlier outcome remains relevant.",
                "evidence_ids": [evidence_id],
            }
        ],
        "open_questions": [],
        "next_goal": "Continue the visible dialogue.",
        "selected_skill": "continue_dialogue",
        "success_condition": ["visible_text_changed"],
        "risk_limit": {"avoid_known_dangers": True, "max_danger_score": 0.4},
        "memory_updates_requested": [],
    }


def current_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text="Current visible text.",
        screenshot_id="shot-current",
        evidence_ids=["shot-current"],
    )


def test_success_appends_evidence_backed_observed_fact() -> None:
    result = build_replan_memory_summary({}, success_completion())

    assert result["recent_skill_outcomes"] == [
        {
            "status": "observed_fact",
            "note": "Skill continue_dialogue completed with verifier status success.",
            "evidence_ids": ["shot-outcome"],
        }
    ]


def test_failure_appends_canonical_failure_kind_and_verifier_evidence() -> None:
    result = build_replan_memory_summary({}, failure_completion())

    assert result["recent_skill_outcomes"] == [
        {
            "status": "observed_fact",
            "note": "Skill continue_dialogue completed with verifier failure target_lost.",
            "evidence_ids": ["shot-failure"],
        }
    ]


@pytest.mark.parametrize(
    "verifier_result",
    [
        VerifierResult(status=VerifierStatus.PROGRESS, evidence_ids=["shot-progress"]),
        VerifierResult(status=VerifierStatus.ABSTAIN, evidence_ids=["shot-abstain"]),
    ],
)
def test_nonterminal_verifier_results_are_rejected(verifier_result: VerifierResult) -> None:
    with pytest.raises(ReplanContextError, match="terminal verifier"):
        build_replan_memory_summary({}, completion_event(verifier_result))


@pytest.mark.parametrize(
    "completion",
    [success_completion(evidence_ids=[]), failure_completion(evidence_ids=[])],
)
def test_verifier_outcomes_without_evidence_are_rejected(completion: TaskCompletionEvent) -> None:
    with pytest.raises(ReplanContextError, match="verifier evidence"):
        build_replan_memory_summary({}, completion)


def test_completion_without_verifier_or_manager_stop_only_is_rejected() -> None:
    manager_stop = ManagerStopResult(
        failure_kind=FailureKind.FOCUS_LOST,
        reason="target window is not focused",
        evidence_ids=["stop-shot"],
    )

    with pytest.raises(ReplanContextError, match="verifier-backed"):
        build_replan_memory_summary({}, completion_event(None))
    with pytest.raises(ReplanContextError, match="verifier-backed"):
        build_replan_memory_summary({}, completion_event(None, manager_stop_result=manager_stop))


def test_context_is_copied_and_existing_outcomes_and_keys_are_preserved() -> None:
    existing_outcomes = [
        {"status": "observed_fact", "note": "Earlier note.", "evidence_ids": ["old"]}
    ]
    base = {
        "known_facts": [{"claim": "Known visible fact.", "evidence_ids": ["known"]}],
        "risk_constraints": {"avoid_known_dangers": True},
        "custom": object(),
        "recent_skill_outcomes": existing_outcomes,
    }

    result = build_replan_memory_summary(base, success_completion())

    assert result is not base
    assert result["known_facts"] is base["known_facts"]
    assert result["risk_constraints"] is base["risk_constraints"]
    assert result["custom"] is base["custom"]
    assert result["recent_skill_outcomes"][:-1] == existing_outcomes
    assert result["recent_skill_outcomes"] is not existing_outcomes
    assert len(result["recent_skill_outcomes"]) == 2
    assert base["recent_skill_outcomes"] == existing_outcomes


@pytest.mark.parametrize("existing", [None, "not-a-sequence", b"bytes", bytearray(b"bytes")])
def test_malformed_existing_recent_outcomes_are_rejected(existing: object) -> None:
    with pytest.raises(ReplanContextError, match="non-string sequence"):
        build_replan_memory_summary({"recent_skill_outcomes": existing}, success_completion())


def test_verified_outcome_is_accepted_as_context_evidence_by_cortex() -> None:
    client = FakeLLMClient(responses=[json.dumps(valid_planner_payload("shot-outcome"))])
    memory_summary = build_replan_memory_summary({}, success_completion())

    output = Cortex(client).plan_next_goal(current_observation(), memory_summary)

    assert output.current_belief_state[0].evidence_ids == ["shot-outcome"]
    prompt_context = json.loads(client.requests[0][1]["content"].split("CortexContext JSON:\n")[1])
    assert prompt_context["recent_skill_outcomes"] == memory_summary["recent_skill_outcomes"]


def test_fabricated_evidence_remains_rejected_by_cortex() -> None:
    client = FakeLLMClient(responses=[json.dumps(valid_planner_payload("shot-fabricated"))])
    memory_summary = build_replan_memory_summary({}, success_completion())

    with pytest.raises(PlannerOutputError, match="shot-fabricated"):
        Cortex(client).plan_next_goal(current_observation(), memory_summary)

    assert len(client.requests) == 1


def test_helper_has_no_automatic_planning_or_execution_calls() -> None:
    source = inspect.getsource(build_replan_memory_summary)

    for forbidden in (
        "plan_next_goal",
        "run_once",
        "start_next",
        "submit_planner_output",
        "execute_current_task",
    ):
        assert forbidden not in source
