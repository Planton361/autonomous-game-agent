"""Visible PPM screen capture through an explicit subprocess command."""

import math
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from fh_agent.perception.screen_capture import ScreenFrame

_PPM_WHITESPACE = b" \t\r\n\f\v"


class SubprocessScreenCaptureError(RuntimeError):
    """Raised when a configured visible capture command fails closed."""


class SubprocessPpmScreenCapture:
    """Capture one visible binary-PPM frame without interpreting image semantics."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 5.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        resolved_command = tuple(command)
        if not resolved_command or any(not token for token in resolved_command):
            msg = "capture command must contain non-empty argv tokens"
            raise ValueError(msg)
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int | float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            msg = "timeout_seconds must be a positive finite number"
            raise ValueError(msg)

        self.command = resolved_command
        self.timeout_seconds = float(timeout_seconds)
        self.clock = clock or (lambda: datetime.now(UTC))

    def capture(self) -> ScreenFrame:
        """Execute the configured command once and return one raw RGB frame."""

        try:
            completed = subprocess.run(
                list(self.command),
                capture_output=True,
                check=False,
                shell=False,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            msg = "visible capture command could not be completed"
            raise SubprocessScreenCaptureError(msg) from exc

        if completed.returncode != 0:
            msg = "visible capture command failed"
            raise SubprocessScreenCaptureError(msg)

        try:
            width, height, rgb = _parse_binary_ppm(completed.stdout)
            return ScreenFrame(
                width=width,
                height=height,
                rgb=rgb,
                captured_at=self.clock(),
            )
        except ValueError as exc:
            msg = "visible capture command returned invalid binary PPM data"
            raise SubprocessScreenCaptureError(msg) from exc


def _parse_binary_ppm(payload: bytes) -> tuple[int, int, bytes]:
    magic, cursor = _read_header_token(payload, 0)
    width_token, cursor = _read_header_token(payload, cursor)
    height_token, cursor = _read_header_token(payload, cursor)
    max_value_token, cursor = _read_header_token(payload, cursor)

    if magic != b"P6":
        raise ValueError("PPM magic must be P6")

    try:
        width = int(width_token)
        height = int(height_token)
        max_value = int(max_value_token)
    except ValueError as exc:
        raise ValueError("PPM dimensions and max value must be integers") from exc

    if width <= 0 or height <= 0 or max_value != 255:
        raise ValueError("unsupported PPM dimensions or max value")
    if cursor >= len(payload) or payload[cursor] not in _PPM_WHITESPACE:
        raise ValueError("PPM header must be followed by one whitespace separator")

    if payload[cursor : cursor + 2] == b"\r\n":
        cursor += 2
    else:
        cursor += 1

    rgb = payload[cursor:]
    expected_size = width * height * 3
    if len(rgb) != expected_size:
        raise ValueError(f"PPM raster must contain exactly {expected_size} bytes")
    return width, height, rgb


def _read_header_token(payload: bytes, cursor: int) -> tuple[bytes, int]:
    cursor = _skip_header_spacing(payload, cursor)
    if cursor >= len(payload):
        raise ValueError("PPM header is incomplete")

    start = cursor
    while cursor < len(payload) and payload[cursor] not in _PPM_WHITESPACE + b"#":
        cursor += 1
    if cursor == start:
        raise ValueError("PPM header token is empty")
    return payload[start:cursor], cursor


def _skip_header_spacing(payload: bytes, cursor: int) -> int:
    while True:
        while cursor < len(payload) and payload[cursor] in _PPM_WHITESPACE:
            cursor += 1
        if cursor >= len(payload) or payload[cursor] != ord("#"):
            return cursor
        newline = payload.find(b"\n", cursor)
        if newline < 0:
            raise ValueError("unterminated PPM comment")
        cursor = newline + 1
