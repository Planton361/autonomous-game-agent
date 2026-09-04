import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.input_executor import BlockedReason, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.game.xdotool_adapters import (
    XdotoolAdapterError,
    XdotoolFocusGuard,
    XdotoolInputBackend,
)


def completed(
    command: list[str],
    stdout: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr="")


def test_constructors_do_not_run_subprocesses() -> None:
    with patch("fh_agent.game.xdotool_adapters.subprocess.run") as run:
        XdotoolInputBackend({PrimitiveAction.CONFIRM: "Return"})
        XdotoolFocusGuard()

    run.assert_not_called()


def test_focus_guard_requires_an_exact_active_window_title() -> None:
    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Fear & Hunger\n"),
        ],
    ) as run:
        focused = XdotoolFocusGuard().is_focused(WindowTarget(title="Fear & Hunger"))

    assert focused
    assert run.call_count == 2


def test_focus_guard_rejects_a_wrong_title() -> None:
    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Other Window\n"),
        ],
    ):
        assert not XdotoolFocusGuard().is_focused(WindowTarget(title="Fear & Hunger"))


def test_focus_guard_rejects_a_supplied_window_id_mismatch() -> None:
    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        return_value=completed(["xdotool", "getactivewindow"], "12345\n"),
    ) as run:
        assert not XdotoolFocusGuard().is_focused(
            WindowTarget(title="Fear & Hunger", window_id="67890")
        )

    run.assert_called_once()


def test_focus_guard_rejects_probe_failure_and_unverifiable_class() -> None:
    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=FileNotFoundError("xdotool"),
    ):
        assert not XdotoolFocusGuard().is_focused(WindowTarget(title="Fear & Hunger"))

    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Fear & Hunger\n"),
            completed(["xdotool", "getwindowclassname", "12345"], ""),
        ],
    ):
        assert not XdotoolFocusGuard().is_focused(
            WindowTarget(title="Fear & Hunger", class_name="Game.exe")
        )


def test_focus_guard_validates_configured_class_and_process_identity() -> None:
    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Fear & Hunger\n"),
            completed(["xdotool", "getwindowclassname", "12345"], "Game.exe\n"),
            completed(["xdotool", "getwindowpid", "12345"], "77\n"),
            completed(["ps", "-p", "77", "-o", "comm="], "Game.exe\n"),
        ],
    ):
        assert XdotoolFocusGuard().is_focused(
            WindowTarget(
                title="Fear & Hunger",
                window_id="12345",
                class_name="Game.exe",
                process_name="Game.exe",
            )
        )


def test_input_backend_sends_one_configured_key_tap() -> None:
    backend = XdotoolInputBackend({PrimitiveAction.CONFIRM: "Return"})

    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        return_value=completed(["xdotool", "key", "--clearmodifiers", "Return"]),
    ) as run:
        backend.send(PrimitiveAction.CONFIRM)

    run.assert_called_once_with(
        ["xdotool", "key", "--clearmodifiers", "Return"],
        capture_output=True,
        check=False,
        shell=False,
        text=True,
        timeout=1.0,
    )


def test_wait_sends_no_key_command_and_missing_mapping_fails_closed() -> None:
    backend = XdotoolInputBackend({})

    with patch("fh_agent.game.xdotool_adapters.subprocess.run") as run:
        backend.send(PrimitiveAction.WAIT)
        with pytest.raises(XdotoolAdapterError, match="no xdotool key binding"):
            backend.send(PrimitiveAction.CONFIRM)

    run.assert_not_called()


def test_failed_key_command_raises_adapter_error() -> None:
    backend = XdotoolInputBackend({PrimitiveAction.CONFIRM: "Return"})

    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        return_value=completed(["xdotool", "key", "--clearmodifiers", "Return"], returncode=1),
    ):
        with pytest.raises(XdotoolAdapterError, match="key command failed"):
            backend.send(PrimitiveAction.CONFIRM)


def test_real_input_executor_uses_adapters_only_when_target_is_focused() -> None:
    target = WindowTarget(title="Fear & Hunger")
    backend = XdotoolInputBackend({PrimitiveAction.CONFIRM: "Return"})
    executor = InputExecutor(target, XdotoolFocusGuard(), backend, min_interval_seconds=0)

    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Fear & Hunger\n"),
            completed(["xdotool", "key", "--clearmodifiers", "Return"]),
        ],
    ) as run:
        result = executor.execute(PrimitiveAction.CONFIRM)

    assert result.executed
    assert run.call_count == 3


def test_real_input_executor_blocks_wrong_target_without_a_key_send() -> None:
    target = WindowTarget(title="Fear & Hunger")
    executor = InputExecutor(
        target,
        XdotoolFocusGuard(),
        XdotoolInputBackend({PrimitiveAction.CONFIRM: "Return"}),
        min_interval_seconds=0,
    )

    with patch(
        "fh_agent.game.xdotool_adapters.subprocess.run",
        side_effect=[
            completed(["xdotool", "getactivewindow"], "12345\n"),
            completed(["xdotool", "getwindowname", "12345"], "Other Window\n"),
        ],
    ) as run:
        result = executor.execute(PrimitiveAction.CONFIRM)

    assert not result.executed
    assert result.blocked_reason == BlockedReason.NOT_FOCUSED
    assert run.call_count == 2


def test_adapter_source_never_uses_shell_or_window_activation() -> None:
    source = (
        Path(__file__)
        .parents[1]
        .joinpath("src/fh_agent/game/xdotool_adapters.py")
        .read_text(encoding="utf-8")
    )

    assert "shell=True" not in source
    assert "windowactivate" not in source
