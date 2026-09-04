from pathlib import Path
from unittest.mock import patch

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.game.emergency_stop import EmergencyStopCheck, StopFileEmergencyStopCheck
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import BlockedReason, DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import SequenceObservationSource
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.schemas import FailureKind


class RecordingFocusGuard:
    def __init__(self) -> None:
        self.targets: list[WindowTarget] = []

    def is_focused(self, target: WindowTarget) -> bool:
        self.targets.append(target)
        return True


class SequenceEmergencyStopCheck:
    def __init__(self, values: list[bool]) -> None:
        self._values = iter(values)
        self.calls = 0

    def is_triggered(self) -> bool:
        self.calls += 1
        return next(self._values)


class RaisingEmergencyStopCheck:
    def is_triggered(self) -> bool:
        raise RuntimeError("check failed")


def make_executor(
    *,
    focus_guard: FakeFocusGuard | RecordingFocusGuard | None = None,
    emergency_stop_check: EmergencyStopCheck | None = None,
) -> tuple[InputExecutor, DryRunInputBackend]:
    backend = DryRunInputBackend()
    executor = InputExecutor(
        WindowTarget(title="M-017 test window"),
        focus_guard or FakeFocusGuard(),
        backend,
        min_interval_seconds=0,
        emergency_stop_check=emergency_stop_check,
    )
    return executor, backend


def dialogue_observation() -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        message_window_visible=True,
        visible_message_text="Visible dialogue.",
        evidence_ids=["shot-before"],
    )


def test_stop_file_check_constructor_performs_no_io(tmp_path: Path) -> None:
    stop_path = tmp_path / "STOP"

    with patch.object(Path, "stat") as stat:
        StopFileEmergencyStopCheck(stop_path)

    stat.assert_not_called()


def test_stop_file_check_reports_absent_and_present_paths(tmp_path: Path) -> None:
    stop_path = tmp_path / "STOP"
    check = StopFileEmergencyStopCheck(stop_path)

    assert not check.is_triggered()

    stop_path.touch()

    assert check.is_triggered()


def test_stop_file_probe_error_fails_closed(tmp_path: Path) -> None:
    check = StopFileEmergencyStopCheck(tmp_path / "STOP")

    with patch.object(Path, "stat", side_effect=PermissionError):
        assert check.is_triggered()


def test_stop_file_created_after_executor_construction_blocks_next_action(tmp_path: Path) -> None:
    stop_path = tmp_path / "STOP"
    check = StopFileEmergencyStopCheck(stop_path)
    focus_guard = RecordingFocusGuard()
    executor, backend = make_executor(
        focus_guard=focus_guard,
        emergency_stop_check=check,
    )

    stop_path.touch()
    result = executor.execute(PrimitiveAction.CONFIRM)

    assert result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert focus_guard.targets == []
    assert backend.actions == []


def test_dynamic_stop_blocks_before_focus_or_backend_send() -> None:
    focus_guard = RecordingFocusGuard()
    executor, backend = make_executor(
        focus_guard=focus_guard,
        emergency_stop_check=SequenceEmergencyStopCheck([True]),
    )

    result = executor.execute(PrimitiveAction.CONFIRM)

    assert result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert focus_guard.targets == []
    assert backend.actions == []


def test_manual_emergency_stop_and_external_exception_remain_fail_closed() -> None:
    executor, backend = make_executor()
    executor.enable_emergency_stop()

    manual_result = executor.execute(PrimitiveAction.CONFIRM)

    assert manual_result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert backend.actions == []

    executor, backend = make_executor(emergency_stop_check=RaisingEmergencyStopCheck())

    exceptional_result = executor.execute(PrimitiveAction.CONFIRM)

    assert exceptional_result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert backend.actions == []


def test_clearing_manual_latch_does_not_override_external_stop() -> None:
    executor, backend = make_executor(emergency_stop_check=SequenceEmergencyStopCheck([True, True]))
    executor.enable_emergency_stop()
    executor.clear_emergency_stop()

    result = executor.execute(PrimitiveAction.CONFIRM)

    assert result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert backend.actions == []


def test_external_stop_check_runs_on_every_action_without_caching() -> None:
    check = SequenceEmergencyStopCheck([False, True])
    executor, backend = make_executor(emergency_stop_check=check)

    first = executor.execute(PrimitiveAction.CONFIRM)
    second = executor.execute(PrimitiveAction.CONFIRM)

    assert first.executed
    assert second.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert check.calls == 2
    assert backend.actions == [PrimitiveAction.CONFIRM]


def test_skill_runner_maps_dynamic_stop_to_existing_manager_stop() -> None:
    executor, backend = make_executor(emergency_stop_check=SequenceEmergencyStopCheck([True]))

    run = SkillRunner().run(
        ContinueDialogueSkill(),
        SequenceObservationSource([dialogue_observation()]),
        verifier=ContinueDialogueVerifier(),
        input_executor=executor,
    )

    assert backend.actions == []
    assert run.manager_stop_result == ManagerStopResult(
        failure_kind=FailureKind.SAFETY_INTERVENTION,
        reason=BlockedReason.EMERGENCY_STOP,
        evidence_ids=["shot-before"],
    )
