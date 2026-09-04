import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import fh_agent.observation.primed_source as primed_source_module
from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
)
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.primed_source import PrimedObservationSource
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSource, ObservationSourceExhausted
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import VerifierResult, VerifierStatus


class RecordingObservationSource:
    def __init__(self, *observations: Observation) -> None:
        self._observations = observations
        self._next_index = 0
        self.observe_calls = 0

    def observe(self) -> Observation:
        self.observe_calls += 1
        if self._next_index >= len(self._observations):
            raise ObservationSourceExhausted
        observation = self._observations[self._next_index]
        self._next_index += 1
        return observation


class ExplodingObservationSource:
    def __init__(self, error: RuntimeError) -> None:
        self.error = error
        self.observe_calls = 0

    def observe(self) -> Observation:
        self.observe_calls += 1
        raise self.error


class EvidenceRecordingBridgePayloadSource:
    def __init__(self, event_logger: EventLogger, *payloads: Mapping[str, Any]) -> None:
        self._event_logger = event_logger
        self._payloads = payloads
        self._next_index = 0
        self.next_payload_calls = 0

    def next_payload(self) -> Mapping[str, Any]:
        self.next_payload_calls += 1
        if self._next_index >= len(self._payloads):
            raise BridgePayloadSourceExhausted
        payload = self._payloads[self._next_index]
        self._next_index += 1
        screenshot_id = payload.get("screenshot_id")
        if isinstance(screenshot_id, str):
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=[screenshot_id],
            )
        return payload


class RecordingDialogueVerifier:
    def __init__(self) -> None:
        self._delegate = ContinueDialogueVerifier()
        self.before: Observation | None = None
        self.after: Observation | None = None

    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        self.before = before
        self.after = after
        return self._delegate.verify(before, after)


def observation(observation_id: str) -> Observation:
    return Observation(
        observation_id=observation_id,
        run_id="run-1",
        ui_state="field",
        evidence_ids=[f"evidence-{observation_id}"],
    )


def test_construction_and_first_observe_do_not_read_remaining_source() -> None:
    initial = observation("initial")
    remaining = RecordingObservationSource(observation("later"))

    source = PrimedObservationSource(initial, remaining)

    assert remaining.observe_calls == 0
    assert source.observe() is initial
    assert remaining.observe_calls == 0


def test_later_observes_delegate_in_order_and_preserve_exact_instances() -> None:
    initial = observation("initial")
    second = observation("second")
    third = observation("third")
    remaining = RecordingObservationSource(second, third)
    source = PrimedObservationSource(initial, remaining)

    assert source.observe() is initial
    assert source.observe() is second
    assert source.observe() is third
    assert remaining.observe_calls == 2


def test_initial_observation_is_returned_exactly_once() -> None:
    initial = observation("initial")
    delegated = observation("delegated")
    source = PrimedObservationSource(initial, RecordingObservationSource(delegated))

    assert source.observe() is initial
    assert source.observe() is delegated


def test_delegated_exhaustion_and_repeated_behavior_are_preserved() -> None:
    remaining = RecordingObservationSource()
    source = PrimedObservationSource(observation("initial"), remaining)

    assert source.observe().observation_id == "initial"
    for expected_calls in (1, 2):
        with pytest.raises(ObservationSourceExhausted):
            source.observe()
        assert remaining.observe_calls == expected_calls


def test_arbitrary_delegated_error_propagates_unchanged() -> None:
    error = RuntimeError("source failure")
    remaining = ExplodingObservationSource(error)
    source = PrimedObservationSource(observation("initial"), remaining)

    source.observe()
    with pytest.raises(RuntimeError) as exc_info:
        source.observe()

    assert exc_info.value is error
    assert remaining.observe_calls == 1


def test_adapter_does_not_mutate_initial_or_delegated_observations() -> None:
    initial = observation("initial")
    delegated = observation("delegated")
    initial_before = initial.model_dump()
    delegated_before = delegated.model_dump()
    source = PrimedObservationSource(initial, RecordingObservationSource(delegated))

    assert source.observe() is initial
    assert source.observe() is delegated
    assert initial.model_dump() == initial_before
    assert delegated.model_dump() == delegated_before


def test_source_structurally_satisfies_observation_source() -> None:
    initial = observation("initial")

    def consume(source: ObservationSource) -> Observation:
        return source.observe()

    assert consume(PrimedObservationSource(initial, RecordingObservationSource())) is initial


def test_module_has_only_generic_observation_dependencies() -> None:
    source = inspect.getsource(primed_source_module)

    for forbidden in (
        "fh_agent.bridge",
        "fh_agent.manager",
        "fh_agent.body",
        "fh_agent.game",
        "fh_agent.verifier",
        "fh_agent.planner",
        "fh_agent.memory",
        "InputExecutor",
        "SkillRunner",
        "Cortex",
    ):
        assert forbidden not in source


def test_bridge_planning_observation_is_skillrunner_start_without_second_initial_pull(
    tmp_path: Path,
) -> None:
    event_log_path = tmp_path / "events.jsonl"
    payload_source = EvidenceRecordingBridgePayloadSource(
        EventLogger(event_log_path, run_id="run-1"),
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "First visible line.",
            "screenshot_id": "shot-before",
        },
        {
            "run_mode": "bridge-assisted",
            "ui_state": "dialogue",
            "visible_message_text": "Second visible line.",
            "screenshot_id": "shot-after",
        },
    )
    bridge_source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    planning_observation = bridge_source.observe()
    runtime_source = PrimedObservationSource(planning_observation, bridge_source)
    backend = DryRunInputBackend()
    input_executor = InputExecutor(
        target=WindowTarget(title="M-010 dry-run window"),
        focus_guard=FakeFocusGuard(focused=True),
        backend=backend,
        min_interval_seconds=0.0,
    )
    verifier = RecordingDialogueVerifier()

    assert payload_source.next_payload_calls == 1
    run = SkillRunner().run(
        ContinueDialogueSkill(),
        runtime_source,
        verifier=verifier,
        input_executor=input_executor,
    )

    assert verifier.before is planning_observation
    assert verifier.after is not None
    assert verifier.after.screenshot_id == "shot-after"
    assert payload_source.next_payload_calls == 2
    assert [action.value for action in backend.actions] == [PrimitiveAction.CONFIRM.value]
    assert run.skill_result.success
    assert run.verifier_result is not None
    assert run.verifier_result.status is VerifierStatus.SUCCESS
    assert run.verifier_result.evidence_ids == ["shot-before", "shot-after"]
    assert run.action_execution_results[0].evidence_ids == ["shot-before", "shot-after"]
