"""Screen-derived perception boundaries."""

from fh_agent.perception.ocr import NoOpOcrEngine, OcrEngine, OcrResult, StaticOcrEngine
from fh_agent.perception.offline_processor import observation_to_json, process_saved_frame
from fh_agent.perception.ui_state import UIStateClassification, classify_ui_state
from fh_agent.perception.visual_hash import average_rgb, load_ppm_frame, screen_signature

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
