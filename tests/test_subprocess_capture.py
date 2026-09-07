from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import fh_agent.perception.subprocess_capture as capture_module
from fh_agent.perception.subprocess_capture import (
    SubprocessPpmScreenCapture,
    SubprocessScreenCaptureError,
)

FIXED_TIME = datetime(2026, 9, 7, 0, 0, tzinfo=UTC)


def completed(*, stdout: bytes, returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=b"", returncode=returncode)


def test_capture_returns_raw_screen_frame_without_interpreting_pixels(monkeypatch) -> None:
    rgb = bytes([0, 10, 32, 64, 128, 255])
    ppm = b"P6\n# visible-frame fixture\n2 1\n255\n" + rgb
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return completed(stdout=ppm)

    monkeypatch.setattr(capture_module.subprocess, "run", fake_run)
    capture = SubprocessPpmScreenCapture(
        ("visible-capture", "--ppm"),
        timeout_seconds=1.5,
        clock=lambda: FIXED_TIME,
    )

    frame = capture.capture()

    assert frame.width == 2
    assert frame.height == 1
    assert frame.rgb == rgb
    assert frame.captured_at == FIXED_TIME
    assert calls == [
        {
            "command": ["visible-capture", "--ppm"],
            "capture_output": True,
            "check": False,
            "shell": False,
            "timeout": 1.5,
        }
    ]


def test_capture_rejects_failed_command(monkeypatch) -> None:
    monkeypatch.setattr(
        capture_module.subprocess,
        "run",
        lambda *args, **kwargs: completed(stdout=b"", returncode=2),
    )

    with pytest.raises(SubprocessScreenCaptureError, match="capture command failed"):
        SubprocessPpmScreenCapture(("capture",)).capture()


@pytest.mark.parametrize(
    "payload",
    [
        b"P3\n1 1\n255\n\x00\x00\x00",
        b"P6\n0 1\n255\n",
        b"P6\n1 1\n100\n\x00\x00\x00",
        b"P6\n1 1\n255\n\x00\x00",
        b"P6\n1 1\n255\n\x00\x00\x00\x00",
    ],
)
def test_capture_rejects_invalid_ppm(monkeypatch, payload: bytes) -> None:
    monkeypatch.setattr(
        capture_module.subprocess,
        "run",
        lambda *args, **kwargs: completed(stdout=payload),
    )

    with pytest.raises(SubprocessScreenCaptureError, match="invalid binary PPM"):
        SubprocessPpmScreenCapture(("capture",)).capture()


def test_capture_fails_closed_on_subprocess_exception(monkeypatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise capture_module.subprocess.TimeoutExpired(cmd="capture", timeout=1.0)

    monkeypatch.setattr(capture_module.subprocess, "run", raise_timeout)

    with pytest.raises(SubprocessScreenCaptureError, match="could not be completed"):
        SubprocessPpmScreenCapture(("capture",)).capture()


@pytest.mark.parametrize(
    ("command", "timeout_seconds"),
    [
        ((), 1.0),
        (("capture", ""), 1.0),
        (("capture",), 0.0),
        (("capture",), float("inf")),
    ],
)
def test_capture_configuration_requires_bounded_safe_values(command, timeout_seconds) -> None:
    with pytest.raises(ValueError):
        SubprocessPpmScreenCapture(command, timeout_seconds=timeout_seconds)
