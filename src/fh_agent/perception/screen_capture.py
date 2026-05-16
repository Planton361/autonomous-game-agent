from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ScreenFrame:
    """Raw RGB screen frame captured from a visible source."""

    width: int
    height: int
    rgb: bytes
    captured_at: datetime

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            msg = "frame width and height must be positive"
            raise ValueError(msg)

        expected_size = self.width * self.height * 3
        if len(self.rgb) != expected_size:
            msg = f"rgb payload must be {expected_size} bytes"
            raise ValueError(msg)

    def to_ppm_bytes(self) -> bytes:
        """Serialize the frame as binary PPM without external image dependencies."""
        header = f"P6\n{self.width} {self.height}\n255\n".encode("ascii")
        return header + self.rgb


class ScreenCapture(Protocol):
    """Captures a visible frame without interpreting game state."""

    def capture(self) -> ScreenFrame:
        """Return one screen frame."""


class DummyScreenCapture:
    """Deterministic capture source for tests and offline smoke checks."""

    def __init__(
        self,
        *,
        width: int = 2,
        height: int = 2,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.clock = clock or (lambda: datetime.now(UTC))
        self.capture_count = 0

    def capture(self) -> ScreenFrame:
        pixel_value = self.capture_count % 256
        self.capture_count += 1
        return ScreenFrame(
            width=self.width,
            height=self.height,
            rgb=bytes([pixel_value]) * self.width * self.height * 3,
            captured_at=self.clock(),
        )
