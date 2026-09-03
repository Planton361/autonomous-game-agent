from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import BlockedReason, DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.observation.schemas import ActionResult


class ManualClock:
    def __init__(self, timestamp: float = 100.0) -> None:
        self.timestamp = timestamp

    def __call__(self) -> float:
        return self.timestamp

    def advance(self, seconds: float) -> None:
        self.timestamp += seconds


def make_executor(
    *,
    focused: bool = True,
    min_interval_seconds: float = 0.5,
    clock: ManualClock | None = None,
) -> tuple[InputExecutor, DryRunInputBackend, ManualClock]:
    manual_clock = clock or ManualClock()
    backend = DryRunInputBackend()
    executor = InputExecutor(
        target=WindowTarget(title="Fear & Hunger"),
        focus_guard=FakeFocusGuard(focused=focused),
        backend=backend,
        min_interval_seconds=min_interval_seconds,
        clock=manual_clock,
    )
    return executor, backend, manual_clock


def test_primitive_actions_are_exactly_the_allowed_set() -> None:
    assert {action.value for action in PrimitiveAction} == {
        "move_up_short",
        "move_down_short",
        "move_left_short",
        "move_right_short",
        "confirm",
        "cancel",
        "open_menu",
        "wait",
    }


def test_blocks_action_when_target_is_not_focused() -> None:
    executor, backend, _clock = make_executor(focused=False)

    result = executor.execute(PrimitiveAction.CONFIRM)

    assert isinstance(result, ActionResult)
    assert not result.executed
    assert result.blocked_reason == BlockedReason.NOT_FOCUSED
    assert result.action == PrimitiveAction.CONFIRM.value
    assert result.evidence_ids == []
    assert backend.actions == []


def test_executes_action_when_target_is_focused() -> None:
    executor, backend, _clock = make_executor(focused=True)

    result = executor.execute(PrimitiveAction.CONFIRM)

    assert isinstance(result, ActionResult)
    assert result.executed
    assert result.blocked_reason is None
    assert result.action == PrimitiveAction.CONFIRM.value
    assert result.evidence_ids == []
    assert backend.actions == [PrimitiveAction.CONFIRM]


def test_emergency_stop_blocks_action_even_when_focused() -> None:
    executor, backend, _clock = make_executor(focused=True)
    executor.enable_emergency_stop()

    result = executor.execute(PrimitiveAction.CANCEL)

    assert not result.executed
    assert result.blocked_reason == BlockedReason.EMERGENCY_STOP
    assert result.evidence_ids == []
    assert backend.actions == []


def test_rate_limit_blocks_actions_until_interval_passes() -> None:
    executor, backend, clock = make_executor(min_interval_seconds=0.5)

    first = executor.execute(PrimitiveAction.MOVE_UP_SHORT)
    clock.advance(0.1)
    second = executor.execute(PrimitiveAction.MOVE_DOWN_SHORT)
    clock.advance(0.4)
    third = executor.execute(PrimitiveAction.MOVE_DOWN_SHORT)

    assert first.executed
    assert not second.executed
    assert second.blocked_reason == BlockedReason.RATE_LIMITED
    assert second.evidence_ids == []
    assert third.executed
    assert backend.actions == [
        PrimitiveAction.MOVE_UP_SHORT,
        PrimitiveAction.MOVE_DOWN_SHORT,
    ]
