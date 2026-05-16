from collections.abc import Sequence
from dataclasses import dataclass
from subprocess import SubprocessError, run
from typing import Protocol

from fh_agent.game.window import WindowInfo, WindowTarget


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str = ""


class CommandRunner(Protocol):
    """Runs a command and returns captured output."""

    def run(self, command: Sequence[str]) -> CommandResult:
        """Run command without raising for non-zero exit status."""


class SubprocessCommandRunner:
    """Standard-library runner used outside tests."""

    def run(self, command: Sequence[str]) -> CommandResult:
        try:
            completed = run(
                list(command),
                capture_output=True,
                check=False,
                text=True,
                timeout=1.0,
            )
        except (OSError, SubprocessError):
            return CommandResult(returncode=1, stdout="")

        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class LinuxFocusGuard:
    """Focus guard backed by xdotool-style active-window queries."""

    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        exact_title_match: bool = False,
    ) -> None:
        self.runner = runner or SubprocessCommandRunner()
        self.exact_title_match = exact_title_match

    def is_focused(self, target: WindowTarget) -> bool:
        active_window_id = self._active_window_id()
        if active_window_id is None:
            return False

        active_window = self._active_window_info(active_window_id)
        if active_window is None:
            return False

        return self._matches(target, active_window)

    def _active_window_id(self) -> str | None:
        stdout = self._run_stdout(["xdotool", "getactivewindow"])
        if stdout is None:
            return None

        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            return None

        window_id = lines[0]
        if any(char.isspace() for char in window_id):
            return None

        return window_id

    def _active_window_info(self, window_id: str) -> WindowInfo | None:
        title = self._run_stdout(["xdotool", "getwindowname", window_id])
        if title is None:
            return None

        class_name = self._run_stdout(["xdotool", "getwindowclassname", window_id])
        process_name = self._process_name(window_id)

        return WindowInfo(
            title=title.strip(),
            process_name=process_name,
            handle=window_id,
            window_id=window_id,
            class_name=class_name.strip() if class_name is not None else None,
        )

    def _process_name(self, window_id: str) -> str | None:
        pid = self._run_stdout(["xdotool", "getwindowpid", window_id])
        if pid is None:
            return None

        pid_value = pid.strip()
        if not pid_value.isdigit():
            return None

        process_name = self._run_stdout(["ps", "-p", pid_value, "-o", "comm="])
        return process_name.strip() if process_name is not None else None

    def _matches(self, target: WindowTarget, active_window: WindowInfo) -> bool:
        if target.window_id is not None and active_window.window_id != target.window_id:
            return False

        if target.title:
            if self.exact_title_match:
                if active_window.title != target.title:
                    return False
            elif target.title not in active_window.title:
                return False

        if target.class_name is not None and active_window.class_name != target.class_name:
            return False

        if target.process_name is not None and active_window.process_name != target.process_name:
            return False

        return True

    def _run_stdout(self, command: Sequence[str]) -> str | None:
        try:
            result = self.runner.run(command)
        except Exception:
            return None

        if result.returncode != 0:
            return None

        return result.stdout
