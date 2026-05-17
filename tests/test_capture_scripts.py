from pathlib import Path


def test_active_window_capture_script_uses_spectacle_active_window() -> None:
    source = Path("scripts/capture_active_window_ppm.sh").read_text(encoding="utf-8")

    assert "spectacle" in source
    assert "--activewindow" in source
    assert "--fullscreen" not in source
    assert "magick" in source
    assert "ppm:-" in source
