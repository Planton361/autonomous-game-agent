from collections.abc import Callable
from typing import Protocol

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.focus_guard import FocusGuard
from fh_agent.game.window import WindowTarget
from fh_agent.observation.schemas import ActionResult


class BlockedReason:
    """Stable blocked-reason values for action execution results."""

    NOT_FOCUSED = "not_focused"
    EMERGENCY_STOP = "emergency_stop"
    RATE_LIMITED = "rate_limited"


class InputBackend(Protocol):
    """Backend boundary for sending primitive inputs."""

    def send(self, action: PrimitiveAction) -> None:
        """Send one primitive action."""


class DryRunInputBackend:
    """Input backend that records actions without sending real inputs."""

    def __init__(self) -> None:
        self.actions: list[PrimitiveAction] = []

    def send(self, action: PrimitiveAction) -> None:
        self.actions.append(action)


class InputExecutor:
    """Safety wrapper around primitive input execution."""

    def __init__(
        self,
        target: WindowTarget,
        focus_guard: FocusGuard,
        backend: InputBackend,
        *,
        min_interval_seconds: float = 0.05,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if min_interval_seconds < 0:
            msg = "min_interval_seconds must be non-negative"
            raise ValueError(msg)

        self.target = target
        self.focus_guard = focus_guard
        self.backend = backend
        self.min_interval_seconds = min_interval_seconds
        self.clock = clock
        self.emergency_stop_enabled = False
        self._last_execution_timestamp: float | None = None

    def enable_emergency_stop(self) -> None:
        self.emergency_stop_enabled = True

    def clear_emergency_stop(self) -> None:
        self.emergency_stop_enabled = False

    def execute(self, action: PrimitiveAction) -> ActionResult:
        timestamp = self._now()

        if self.emergency_stop_enabled:
            return self._blocked(action, BlockedReason.EMERGENCY_STOP)

        if not self.focus_guard.is_focused(self.target):
            return self._blocked(action, BlockedReason.NOT_FOCUSED)

        if self._is_rate_limited(timestamp):
            return self._blocked(action, BlockedReason.RATE_LIMITED)

        self.backend.send(action)
        self._last_execution_timestamp = timestamp
        return ActionResult(
            action=action.value,
            executed=True,
            blocked_reason=None,
        )

    def _now(self) -> float:
        if self.clock is not None:
            return self.clock()

        import time

        return time.monotonic()

    def _is_rate_limited(self, timestamp: float) -> bool:
        if self._last_execution_timestamp is None:
            return False

        elapsed = timestamp - self._last_execution_timestamp
        return elapsed < self.min_interval_seconds

    def _blocked(
        self,
        action: PrimitiveAction,
        blocked_reason: str,
    ) -> ActionResult:
        return ActionResult(
            action=action.value,
            executed=False,
            blocked_reason=blocked_reason,
        )
