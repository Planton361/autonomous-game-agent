from collections.abc import Sequence

from fh_agent.game.linux_focus_guard import CommandResult, LinuxFocusGuard
from fh_agent.game.window import WindowTarget


class FakeCommandRunner:
    def __init__(self, results: dict[tuple[str, ...], CommandResult | Exception]) -> None:
        self.results = results
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> CommandResult:
        command_key = tuple(command)
        self.commands.append(command_key)
        result = self.results.get(command_key, CommandResult(returncode=1, stdout=""))
        if isinstance(result, Exception):
            raise result
        return result


def test_active_window_matches_target() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): CommandResult(0, "12345\n"),
            ("xdotool", "getwindowname", "12345"): CommandResult(0, "Fear & Hunger\n"),
            ("xdotool", "getwindowclassname", "12345"): CommandResult(0, "Game.exe\n"),
            ("xdotool", "getwindowpid", "12345"): CommandResult(0, "77\n"),
            ("ps", "-p", "77", "-o", "comm="): CommandResult(0, "Game.exe\n"),
        }
    )
    guard = LinuxFocusGuard(runner)

    focused = guard.is_focused(
        WindowTarget(
            title="Fear",
            window_id="12345",
            class_name="Game.exe",
            process_name="Game.exe",
        )
    )

    assert focused
    assert runner.commands


def test_active_window_does_not_match_target() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): CommandResult(0, "12345\n"),
            ("xdotool", "getwindowname", "12345"): CommandResult(0, "Other Window\n"),
            ("xdotool", "getwindowclassname", "12345"): CommandResult(0, "Other.exe\n"),
            ("xdotool", "getwindowpid", "12345"): CommandResult(0, "77\n"),
            ("ps", "-p", "77", "-o", "comm="): CommandResult(0, "Other.exe\n"),
        }
    )
    guard = LinuxFocusGuard(runner)

    assert not guard.is_focused(WindowTarget(title="Fear & Hunger"))


def test_command_missing_returns_false() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): FileNotFoundError("xdotool"),
        }
    )
    guard = LinuxFocusGuard(runner)

    assert not guard.is_focused(WindowTarget(title="Fear & Hunger"))


def test_command_failure_returns_false() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): CommandResult(1, "", "not found"),
        }
    )
    guard = LinuxFocusGuard(runner)

    assert not guard.is_focused(WindowTarget(title="Fear & Hunger"))


def test_malformed_active_window_output_returns_false() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): CommandResult(0, "12345\n67890\n"),
        }
    )
    guard = LinuxFocusGuard(runner)

    assert not guard.is_focused(WindowTarget(title="Fear & Hunger"))


def test_tests_use_injected_runner_without_real_subprocess_calls() -> None:
    runner = FakeCommandRunner(
        {
            ("xdotool", "getactivewindow"): CommandResult(0, "12345\n"),
            ("xdotool", "getwindowname", "12345"): CommandResult(0, "Fear & Hunger\n"),
        }
    )
    guard = LinuxFocusGuard(runner)

    assert guard.is_focused(WindowTarget(title="Fear"))
    assert runner.commands == [
        ("xdotool", "getactivewindow"),
        ("xdotool", "getwindowname", "12345"),
        ("xdotool", "getwindowclassname", "12345"),
        ("xdotool", "getwindowpid", "12345"),
    ]
