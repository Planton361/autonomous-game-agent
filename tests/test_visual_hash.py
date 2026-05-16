from datetime import UTC, datetime

from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.visual_hash import average_rgb, load_ppm_frame, screen_signature


def test_screen_signature_is_stable_for_same_frame() -> None:
    frame = ScreenFrame(
        width=1,
        height=2,
        rgb=b"\x00\x10\x20\x30\x40\x50",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )

    assert screen_signature(frame) == screen_signature(frame)


def test_average_rgb_summarizes_frame_pixels() -> None:
    frame = ScreenFrame(
        width=2,
        height=1,
        rgb=b"\x00\x10\x20\x20\x30\x40",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )

    assert average_rgb(frame) == (16, 32, 48)


def test_load_ppm_frame_reads_saved_screen_frame(tmp_path) -> None:
    source = ScreenFrame(
        width=1,
        height=1,
        rgb=b"\x01\x02\x03",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )
    path = tmp_path / "frame.ppm"
    path.write_bytes(source.to_ppm_bytes())

    loaded = load_ppm_frame(path)

    assert loaded.width == 1
    assert loaded.height == 1
    assert loaded.rgb == b"\x01\x02\x03"
