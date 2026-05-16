from collections.abc import Mapping
from typing import Protocol

from fh_agent.game.window import WindowTarget


class FocusGuard(Protocol):
    """Checks whether a target window is currently safe to receive inputs."""

    def is_focused(self, target: WindowTarget) -> bool:
        """Return True only when the target window is focused."""


class FakeFocusGuard:
    """Test stub with explicit focus state per target."""

    def __init__(
        self,
        focused: bool = True,
        target_focus: Mapping[WindowTarget, bool] | None = None,
    ) -> None:
        self.focused = focused
        self.target_focus = dict(target_focus or {})

    def is_focused(self, target: WindowTarget) -> bool:
        return self.target_focus.get(target, self.focused)
