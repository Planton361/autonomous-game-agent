from datetime import UTC, datetime
from pathlib import Path

from fh_agent.memory.evidence import sha256_bytes
from fh_agent.perception.screen_capture import ScreenFrame


def screen_signature(frame: ScreenFrame) -> str:
    """Return a stable visible-screen signature for exact offline comparisons."""
    return sha256_bytes(frame.to_ppm_bytes())


def average_rgb(frame: ScreenFrame) -> tuple[int, int, int]:
    """Compute a tiny image summary without image dependencies."""
    pixel_count = frame.width * frame.height
    red = sum(frame.rgb[index] for index in range(0, len(frame.rgb), 3))
    green = sum(frame.rgb[index] for index in range(1, len(frame.rgb), 3))
    blue = sum(frame.rgb[index] for index in range(2, len(frame.rgb), 3))
    return red // pixel_count, green // pixel_count, blue // pixel_count


def load_ppm_frame(path: Path) -> ScreenFrame:
    """Load a minimal PPM screenshot for offline fixture processing."""
    payload = path.read_bytes()
    captured_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    if payload.startswith(b"P3"):
        return _load_plain_ppm_frame(payload, captured_at=captured_at)
    if not payload.startswith(b"P6"):
        msg = "only PPM P3 and P6 screenshots are supported"
        raise ValueError(msg)

    header_parts: list[bytes] = []
    cursor = 0
    while len(header_parts) < 4:
        next_space = _next_ppm_separator(payload, cursor)
        header_parts.append(payload[cursor:next_space])
        cursor = next_space + 1

    if header_parts[0] != b"P6":
        msg = "only binary PPM P6 screenshots are supported"
        raise ValueError(msg)
    width = int(header_parts[1])
    height = int(header_parts[2])
    max_value = int(header_parts[3])
    if max_value != 255:
        msg = "only 8-bit PPM screenshots are supported"
        raise ValueError(msg)

    rgb = payload[cursor:]
    return ScreenFrame(width=width, height=height, rgb=rgb, captured_at=captured_at)


def _load_plain_ppm_frame(payload: bytes, *, captured_at: datetime) -> ScreenFrame:
    parts = payload.decode("ascii").split()
    if len(parts) < 4 or parts[0] != "P3":
        msg = "invalid plain PPM header"
        raise ValueError(msg)

    width = int(parts[1])
    height = int(parts[2])
    max_value = int(parts[3])
    if max_value != 255:
        msg = "only 8-bit PPM screenshots are supported"
        raise ValueError(msg)

    channels = [int(part) for part in parts[4:]]
    expected_channels = width * height * 3
    if len(channels) != expected_channels:
        msg = f"plain PPM payload must contain {expected_channels} channels"
        raise ValueError(msg)

    return ScreenFrame(
        width=width,
        height=height,
        rgb=bytes(channels),
        captured_at=captured_at,
    )


def _next_ppm_separator(payload: bytes, start: int) -> int:
    separators = (payload.find(b" ", start), payload.find(b"\n", start))
    candidates = [index for index in separators if index >= 0]
    if not candidates:
        msg = "invalid PPM header"
        raise ValueError(msg)
    return min(candidates)
