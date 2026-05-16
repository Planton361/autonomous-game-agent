from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fh_agent.observation.schemas import UIState, VisibleTextSpan


@dataclass(frozen=True, slots=True)
class UIStateClassification:
    state: UIState
    confidence: float
    evidence_id: str | None = None


def classify_ui_state(
    *,
    bridge_data: dict[str, Any] | None = None,
    text_spans: Sequence[VisibleTextSpan] = (),
    screen_signature: str | None = None,
    evidence_id: str | None = None,
) -> UIStateClassification:
    """Classify visible UI state using only screen-derived or sanitized fields."""
    del screen_signature
    data = bridge_data or {}

    if data.get("death_screen_visible") is True:
        return UIStateClassification("death", 0.99, evidence_id)
    if data.get("combat_ui_visible") is True:
        return UIStateClassification("combat", 0.95, evidence_id)
    if data.get("menu_open") is True:
        return UIStateClassification("menu", 0.95, evidence_id)
    if data.get("message_window_visible") is True or data.get("visible_message_text"):
        return UIStateClassification("dialogue", 0.9, evidence_id)
    if text_spans:
        return UIStateClassification("dialogue", 0.55, evidence_id)
    has_player_position = data.get("player_screen_position") is not None
    has_sprite_positions = bool(data.get("visible_sprite_screen_positions"))
    if has_player_position or has_sprite_positions:
        return UIStateClassification("field", 0.65, evidence_id)

    return UIStateClassification("unknown", 0.0, evidence_id)
