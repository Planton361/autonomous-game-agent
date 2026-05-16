from datetime import UTC, datetime, timedelta

from fh_agent.perception.screen_capture import DummyScreenCapture, ScreenFrame


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def test_dummy_screen_capture_returns_deterministic_frames() -> None:
    clock = ManualClock()
    capture = DummyScreenCapture(width=2, height=2, clock=clock)

    first = capture.capture()
    second = capture.capture()

    assert first.width == 2
    assert first.height == 2
    assert first.rgb == bytes([0]) * 12
    assert second.rgb == bytes([1]) * 12
    assert second.captured_at > first.captured_at


def test_screen_frame_serializes_to_stable_ppm_bytes() -> None:
    frame = ScreenFrame(
        width=1,
        height=1,
        rgb=b"\x01\x02\x03",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )

    assert frame.to_ppm_bytes() == b"P6\n1 1\n255\n\x01\x02\x03"
