"""Screen-derived perception boundaries."""

from typing import TYPE_CHECKING

from fh_agent.perception.ocr import NoOpOcrEngine, OcrEngine, OcrResult, StaticOcrEngine
from fh_agent.perception.ui_state import UIStateClassification, classify_ui_state
from fh_agent.perception.visual_hash import average_rgb, load_ppm_frame, screen_signature

if TYPE_CHECKING:
    from fh_agent.perception.offline_processor import (
        observation_to_json,
        process_saved_frame,
    )

__all__ = [
    "NoOpOcrEngine",
    "OcrEngine",
    "OcrResult",
    "StaticOcrEngine",
    "UIStateClassification",
    "average_rgb",
    "classify_ui_state",
    "load_ppm_frame",
    "observation_to_json",
    "process_saved_frame",
    "screen_signature",
]


def __getattr__(name: str) -> object:
    """Lazily preserve offline-processing package-root exports."""
    if name not in {"observation_to_json", "process_saved_frame"}:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    from fh_agent.perception.offline_processor import (
        observation_to_json,
        process_saved_frame,
    )

    value = {
        "observation_to_json": observation_to_json,
        "process_saved_frame": process_saved_frame,
    }[name]
    globals()[name] = value
    return value
