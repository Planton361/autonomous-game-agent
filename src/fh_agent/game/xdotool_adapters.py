"""Linux xdotool adapters for the existing guarded input ports."""

import subprocess
from collections.abc import Mapping, Sequence

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.window import WindowTarget


class XdotoolAdapterError(RuntimeError):
    """Raised when xdotool cannot safely send a configured primitive action."""


class XdotoolInputBackend:
    """Send configured primitive-key taps without changing window focus."""

    def __init__(
        self,
        key_bindings: Mapping[PrimitiveAction, str],
        *,
        executable: str = "xdotool",
    ) -> None:
        self._key_bindings = dict(key_bindings)
        self._executable = executable

    def send(self, action: PrimitiveAction) -> None:
        if action is PrimitiveAction.WAIT:
            return

        key = self._key_bindings.get(action)
        if not key:
            msg = f"no xdotool key binding configured for action {action.value}"
            raise XdotoolAdapterError(msg)

        self._run_key_command(key)

    def _run_key_command(self, key: str) -> None:
        command = [self._executable, "key", "--clearmodifiers", key]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=1.0,
            )
        except (OSError, subprocess.SubprocessError) as error:
            msg = "xdotool key command could not be completed"
            raise XdotoolAdapterError(msg) from error

        if result.returncode != 0:
            msg = "xdotool key command failed"
            raise XdotoolAdapterError(msg)


class XdotoolFocusGuard:
    """Verify the active window exactly before guarded input is permitted."""

    def __init__(self, *, executable: str = "xdotool") -> None:
        self._executable = executable

    def is_focused(self, target: WindowTarget) -> bool:
        window_id = self._read_window_id()
        if window_id is None:
            return False

        if target.window_id is not None and target.window_id != window_id:
            return False

        title = self._read_single_line([self._executable, "getwindowname", window_id])
        if title is None or title != target.title:
            return False

        if target.class_name is not None:
            class_name = self._read_single_line([self._executable, "getwindowclassname", window_id])
            if class_name is None or class_name != target.class_name:
                return False

        if target.process_name is not None:
            process_name = self._read_process_name(window_id)
            if process_name is None or process_name != target.process_name:
                return False

        return True

    def _read_window_id(self) -> str | None:
        window_id = self._read_single_line([self._executable, "getactivewindow"])
        if window_id is None or not window_id.isdecimal():
            return None

        return window_id

    def _read_process_name(self, window_id: str) -> str | None:
        process_id = self._read_single_line([self._executable, "getwindowpid", window_id])
        if process_id is None or not process_id.isdecimal():
            return None

        return self._read_single_line(["ps", "-p", process_id, "-o", "comm="])

    def _read_single_line(self, command: Sequence[str]) -> str | None:
        try:
            result = subprocess.run(
                list(command),
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=1.0,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0:
            return None

        output = result.stdout
        if not isinstance(output, str) or not output.endswith("\n"):
            return None

        value = output.removesuffix("\n")
        if not value or "\n" in value or "\r" in value:
            return None

        return value
