import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import fh_agent.bridge.observation_source as bridge_observation_source_module
from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.bridge.evidence_sync import (
    BridgeEvidenceSynchronizationError,
    BridgeScreenshotEvidenceLookup,
    EventLogBridgeScreenshotEvidenceLookup,
)
from fh_agent.bridge.observation_source import (
    BridgeObservationSource,
    BridgePayloadSourceExhausted,
    BridgeRunModeMismatchError,
)
from fh_agent.bridge.sanitizer import (
    BridgeRunMode,
    ForbiddenBridgeFieldError,
    InvalidBridgePayloadError,
    UnknownBridgeFieldError,
)
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.memory.event_log import EventLogger
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSource, ObservationSourceExhausted
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import VerifierStatus


class RecordingBridgePayloadSource:
    def __init__(self, *payloads: Mapping[str, Any]) -> None:
        self._payloads = payloads
        self._next_index = 0
        self.next_payload_calls = 0

    def next_payload(self) -> Mapping[str, Any]:
        self.next_payload_calls += 1
        if self._next_index >= len(self._payloads):
            raise BridgePayloadSourceExhausted

        payload = self._payloads[self._next_index]
        self._next_index += 1
        return payload


class StaticScreenshotEvidenceLookup:
    def __init__(self, evidence_id: str | None) -> None:
        self.evidence_id = evidence_id
        self.run_ids: list[str] = []

    def latest_screenshot_evidence_id(self, *, run_id: str) -> str | None:
        self.run_ids.append(run_id)
        return self.evidence_id


class EvidenceRecordingBridgePayloadSource(RecordingBridgePayloadSource):
    def __init__(self, event_logger: EventLogger, *payloads: Mapping[str, Any]) -> None:
        super().__init__(*payloads)
        self._event_logger = event_logger

    def next_payload(self) -> Mapping[str, Any]:
        payload = super().next_payload()
        screenshot_id = payload.get("screenshot_id")
        if isinstance(screenshot_id, str):
            self._event_logger.append(
                "evidence",
                payload={"kind": "screenshot"},
                evidence_ids=[screenshot_id],
            )
        return payload


def bridge_payload(
    *,
    run_mode: str = "bridge-assisted",
    screenshot_id: str | None = "shot-1",
    ui_state: str = "field",
    message: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "run_mode": run_mode,
        "ui_state": ui_state,
    }
    if screenshot_id is not None:
        payload["screenshot_id"] = screenshot_id
    if message is not None:
        payload["visible_message_text"] = message
    return payload


def source_for(
    payload_source: RecordingBridgePayloadSource,
    *,
    expected_run_mode: BridgeRunMode = "bridge-assisted",
    run_id: str = "run-1",
    screenshot_evidence_lookup: BridgeScreenshotEvidenceLookup | None = None,
) -> BridgeObservationSource:
    if screenshot_evidence_lookup is None and expected_run_mode == "bridge-assisted":
        screenshot_evidence_lookup = StaticScreenshotEvidenceLookup("shot-1")

    return BridgeObservationSource(
        payload_source,
        run_id=run_id,
        expected_run_mode=expected_run_mode,
        screenshot_evidence_lookup=screenshot_evidence_lookup,
    )


def test_construction_does_not_read_a_payload() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload())
    lookup = StaticScreenshotEvidenceLookup("shot-1")

    source_for(payload_source, screenshot_evidence_lookup=lookup)

    assert payload_source.next_payload_calls == 0
    assert lookup.run_ids == []


def test_bridge_assisted_construction_without_lookup_rejects_before_payload_pull() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload())

    with pytest.raises(
        BridgeEvidenceSynchronizationError,
        match="require screenshot evidence lookup",
    ):
        BridgeObservationSource(
            payload_source,
            run_id="run-1",
            expected_run_mode="bridge-assisted",
        )

    assert payload_source.next_payload_calls == 0


def test_debug_construction_without_lookup_remains_valid() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(run_mode="debug"))

    source = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="debug",
    )

    assert source.observe().screenshot_id == "shot-1"


def test_observe_reads_exactly_one_payload() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload())
    source = source_for(payload_source)

    source.observe()

    assert payload_source.next_payload_calls == 1


def test_repeated_observes_pull_payloads_in_exact_order() -> None:
    payload_source = RecordingBridgePayloadSource(
        bridge_payload(run_mode="debug", screenshot_id="shot-1"),
        bridge_payload(run_mode="debug", screenshot_id="shot-2"),
    )
    source = source_for(payload_source, expected_run_mode="debug")

    observations = [source.observe(), source.observe()]

    assert [observation.screenshot_id for observation in observations] == ["shot-1", "shot-2"]
    assert payload_source.next_payload_calls == 2


def test_bridge_assisted_payload_becomes_a_canonical_observation() -> None:
    payload_source = RecordingBridgePayloadSource(
        {
            "run_mode": "bridge-assisted",
            "ui_state": "menu",
            "visible_message_text": "Visible.",
            "visible_menu_items": ["Items"],
            "player_screen_position": [10, 20],
            "visible_sprite_screen_positions": [[30, 40]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-1",
        }
    )

    observation = source_for(payload_source, run_id="bridge-run").observe()

    assert isinstance(observation, Observation)
    assert observation.run_id == "bridge-run"
    assert observation.ui_state == "menu"
    assert observation.screenshot_id == "shot-1"
    assert observation.visible_message_text == "Visible."
    assert observation.visible_menu_items == ["Items"]
    assert observation.player_screen_position == (10, 20)
    assert observation.visible_sprite_screen_positions == [(30, 40)]
    assert observation.visible_sprite_visual_hashes == ["dhash:0123456789abcdef"]
    assert observation.evidence_ids == ["shot-1"]
    assert "run_mode" not in observation.model_dump()


def test_debug_source_accepts_debug_payload() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(run_mode="debug"))

    observation = source_for(payload_source, expected_run_mode="debug").observe()

    assert observation.screenshot_id == "shot-1"


def test_debug_payload_without_screenshot_remains_valid() -> None:
    payload_source = RecordingBridgePayloadSource(
        bridge_payload(run_mode="debug", screenshot_id=None)
    )

    observation = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="debug",
    ).observe()

    assert observation.screenshot_id is None
    assert observation.evidence_ids == []


def test_debug_mode_ignores_a_supplied_screenshot_lookup() -> None:
    payload_source = RecordingBridgePayloadSource(
        bridge_payload(run_mode="debug", screenshot_id=None)
    )
    lookup = StaticScreenshotEvidenceLookup(None)

    observation = BridgeObservationSource(
        payload_source,
        run_id="run-1",
        expected_run_mode="debug",
        screenshot_evidence_lookup=lookup,
    ).observe()

    assert observation.screenshot_id is None
    assert lookup.run_ids == []


@pytest.mark.parametrize(
    ("expected_run_mode", "payload_run_mode"),
    [("bridge-assisted", "debug"), ("debug", "bridge-assisted")],
)
def test_source_rejects_valid_payloads_from_another_bridge_mode(
    expected_run_mode: str,
    payload_run_mode: str,
) -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(run_mode=payload_run_mode))

    with pytest.raises(BridgeRunModeMismatchError):
        source_for(payload_source, expected_run_mode=expected_run_mode).observe()


@pytest.mark.parametrize(
    "run_mode",
    ["official", "screen-only", "networked-api-exploratory", "contaminated"],
)
def test_non_bridge_modes_are_rejected_before_mode_mismatch_check(run_mode: str) -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(run_mode=run_mode))

    with pytest.raises(InvalidBridgePayloadError):
        source_for(payload_source).observe()


def test_missing_bridge_assisted_screenshot_id_is_rejected() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(screenshot_id=None))

    with pytest.raises(BridgeEvidenceSynchronizationError, match="missing screenshot_id"):
        source_for(payload_source).observe()


def test_missing_durable_screenshot_evidence_is_rejected() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload())

    with pytest.raises(BridgeEvidenceSynchronizationError, match="no durable screenshot evidence"):
        source_for(
            payload_source,
            screenshot_evidence_lookup=StaticScreenshotEvidenceLookup(None),
        ).observe()


def test_fabricated_screenshot_id_is_rejected() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(screenshot_id="fabricated"))

    with pytest.raises(BridgeEvidenceSynchronizationError, match="does not match"):
        source_for(
            payload_source,
            screenshot_evidence_lookup=StaticScreenshotEvidenceLookup("shot-1"),
        ).observe()


def test_stale_screenshot_id_is_rejected_when_newer_durable_evidence_exists(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_log_path, run_id="run-1")
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-1"])
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-2"])
    payload_source = RecordingBridgePayloadSource(bridge_payload(screenshot_id="shot-1"))

    with pytest.raises(BridgeEvidenceSynchronizationError, match="does not match"):
        source_for(
            payload_source,
            screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
        ).observe()


def test_latest_durable_screenshot_id_succeeds_and_preserves_observation_evidence(
    tmp_path: Path,
) -> None:
    event_log_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_log_path, run_id="run-1")
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-1"])
    event_logger.append("evidence", payload={"kind": "screenshot"}, evidence_ids=["shot-2"])
    payload_source = RecordingBridgePayloadSource(bridge_payload(screenshot_id="shot-2"))

    observation = source_for(
        payload_source,
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    ).observe()

    assert observation.screenshot_id == "shot-2"
    assert observation.evidence_ids == ["shot-2"]


def test_evidence_synchronization_failure_consumes_one_payload_without_lookahead() -> None:
    payload_source = RecordingBridgePayloadSource(
        bridge_payload(screenshot_id="wrong"),
        bridge_payload(screenshot_id="unused"),
    )
    lookup = StaticScreenshotEvidenceLookup("shot-current")

    with pytest.raises(BridgeEvidenceSynchronizationError):
        source_for(payload_source, screenshot_evidence_lookup=lookup).observe()

    assert payload_source.next_payload_calls == 1
    assert lookup.run_ids == ["run-1"]


def test_payload_exhaustion_maps_to_canonical_observation_source_exhaustion() -> None:
    payload_source = RecordingBridgePayloadSource()
    source = source_for(payload_source)

    with pytest.raises(ObservationSourceExhausted) as exc_info:
        source.observe()

    assert isinstance(exc_info.value.__cause__, BridgePayloadSourceExhausted)
    assert payload_source.next_payload_calls == 1


def test_repeated_payload_exhaustion_remains_deterministic() -> None:
    payload_source = RecordingBridgePayloadSource()
    source = source_for(payload_source)

    for expected_calls in (1, 2):
        with pytest.raises(ObservationSourceExhausted):
            source.observe()
        assert payload_source.next_payload_calls == expected_calls


def test_forbidden_bridge_fields_propagate_unchanged() -> None:
    payload_source = RecordingBridgePayloadSource(
        {"run_mode": "bridge-assisted", "game_variables": {"ending": "hidden"}}
    )

    with pytest.raises(ForbiddenBridgeFieldError):
        source_for(payload_source).observe()


def test_unknown_bridge_fields_propagate_unchanged() -> None:
    payload_source = RecordingBridgePayloadSource(
        {"run_mode": "bridge-assisted", "transport_noise": "unexpected"}
    )

    with pytest.raises(UnknownBridgeFieldError):
        source_for(payload_source).observe()


def test_invalid_bridge_payload_shape_propagates_unchanged() -> None:
    payload_source = RecordingBridgePayloadSource(bridge_payload(ui_state="inventory"))

    with pytest.raises(InvalidBridgePayloadError):
        source_for(payload_source).observe()


def test_raw_payload_is_not_mutated() -> None:
    payload = bridge_payload(message="Visible.")
    before = payload.copy()

    source_for(RecordingBridgePayloadSource(payload)).observe()

    assert payload == before


def test_source_structurally_satisfies_observation_source() -> None:
    def consume(source: ObservationSource) -> Observation:
        return source.observe()

    observation = consume(source_for(RecordingBridgePayloadSource(bridge_payload())))

    assert observation.screenshot_id == "shot-1"


def test_source_module_has_no_forbidden_runtime_layer_dependencies() -> None:
    source = inspect.getsource(bridge_observation_source_module)

    for forbidden in (
        "fh_agent.body",
        "fh_agent.manager",
        "InputExecutor",
        "reward",
        "Verifier",
        "socket",
        "http",
        "websocket",
        "subprocess",
        "fh_agent.game",
    ):
        assert forbidden not in source


def test_bridge_payloads_drive_existing_skill_runner_with_dry_run_input(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"
    event_logger = EventLogger(event_log_path, run_id="run-1")
    payload_source = EvidenceRecordingBridgePayloadSource(
        event_logger,
        bridge_payload(
            ui_state="dialogue",
            message="First visible line.",
            screenshot_id="shot-before",
        ),
        bridge_payload(
            ui_state="dialogue",
            message="Second visible line.",
            screenshot_id="shot-after",
        ),
    )
    source = source_for(
        payload_source,
        screenshot_evidence_lookup=EventLogBridgeScreenshotEvidenceLookup(event_log_path),
    )
    backend = DryRunInputBackend()
    input_executor = InputExecutor(
        target=WindowTarget(title="M-003 dry-run window"),
        focus_guard=FakeFocusGuard(focused=True),
        backend=backend,
        min_interval_seconds=0.0,
    )

    run = SkillRunner().run(
        ContinueDialogueSkill(),
        source,
        verifier=ContinueDialogueVerifier(),
        input_executor=input_executor,
    )

    assert run.skill_result.success
    assert run.verifier_result is not None
    assert run.verifier_result.status is VerifierStatus.SUCCESS
    assert run.verifier_result.evidence_ids == ["shot-before", "shot-after"]
    assert backend.actions == [PrimitiveAction.CONFIRM]
    assert payload_source.next_payload_calls == 2
    assert len(run.action_execution_results) == 1
    assert run.action_execution_results[0].evidence_ids == ["shot-before", "shot-after"]
