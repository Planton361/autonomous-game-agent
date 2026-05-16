from pathlib import Path
from typing import Any

from fh_agent.memory.evidence import EvidenceRecord, sha256_file
from fh_agent.observation.observation_builder import ObservationBuilder
from fh_agent.observation.schemas import Observation, UIState
from fh_agent.perception.ocr import NoOpOcrEngine, OcrEngine
from fh_agent.perception.visual_hash import load_ppm_frame


def process_saved_frame(
    path: Path | str,
    *,
    run_id: str,
    screenshot_id: str | None = None,
    evidence_id: str | None = None,
    ocr_engine: OcrEngine | None = None,
    sanitized_bridge_data: dict[str, Any] | None = None,
    ui_hint: UIState | None = None,
) -> Observation:
    """Parse a saved visible screenshot into a canonical Observation."""
    frame_path = Path(path)
    frame = load_ppm_frame(frame_path)
    resolved_evidence_id = evidence_id or screenshot_id or frame_path.stem
    evidence = EvidenceRecord(
        evidence_id=resolved_evidence_id,
        run_id=run_id,
        kind="screenshot",
        path=str(frame_path),
        sha256=sha256_file(frame_path),
        created_at=frame.captured_at,
        width=frame.width,
        height=frame.height,
    )
    bridge_data = _merge_ui_hint(sanitized_bridge_data or {}, ui_hint)

    return ObservationBuilder(
        run_id=run_id,
        ocr_engine=ocr_engine or NoOpOcrEngine(),
    ).build(
        frame=frame,
        evidence=evidence,
        bridge_data=bridge_data,
    )


def observation_to_json(observation: Observation) -> str:
    """Serialize an offline observation with stable key ordering."""
    return observation.model_dump_json(exclude_none=True)


def _merge_ui_hint(bridge_data: dict[str, Any], ui_hint: UIState | None) -> dict[str, Any]:
    if ui_hint is None or ui_hint == "unknown":
        return dict(bridge_data)

    hinted = dict(bridge_data)
    for key, value in _bridge_fields_for_hint(ui_hint).items():
        hinted.setdefault(key, value)
    return hinted


def _bridge_fields_for_hint(ui_hint: UIState) -> dict[str, Any]:
    match ui_hint:
        case "dialogue":
            return {"message_window_visible": True}
        case "menu":
            return {"menu_open": True}
        case "combat":
            return {"combat_ui_visible": True}
        case "death":
            return {"death_screen_visible": True}
        case "field":
            return {"player_screen_position": (0, 0)}
        case "unknown":
            return {}
