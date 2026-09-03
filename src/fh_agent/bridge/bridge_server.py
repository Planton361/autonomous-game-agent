from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from fh_agent.bridge.sanitizer import (
    BridgeRunMode,
    InvalidBridgePayloadError,
    sanitize_bridge_payload,
)
from fh_agent.observation.schemas import Observation, VisibleTextSpan
from fh_agent.observation.visible_sprite_normalization import (
    VisibleSpriteNormalizationError,
    normalize_visible_sprites,
)


@dataclass(frozen=True, slots=True)
class BridgeReceipt:
    """Result of accepting one payload from a future visible-state bridge."""

    run_mode: BridgeRunMode
    sanitized_payload: dict[str, Any]
    observation: Observation | None = None


class VisibleBridgeAdapter:
    """Minimal testable adapter for future bridge transports.

    This class intentionally has no socket, HTTP, or game-window behavior. A later
    transport can call ``accept_payload`` after receiving visible RPG Maker MV data.
    """

    def accept_payload(self, raw_payload: Mapping[str, Any]) -> BridgeReceipt:
        run_mode = raw_payload.get("run_mode")
        sanitized_payload = sanitize_bridge_payload(raw_payload)

        return BridgeReceipt(
            run_mode=cast(BridgeRunMode, run_mode),
            sanitized_payload=sanitized_payload,
        )

    def accept_observation_payload(
        self,
        raw_payload: Mapping[str, Any],
        *,
        run_id: str,
    ) -> BridgeReceipt:
        """Accept one raw bridge payload and convert it into an Observation."""

        run_mode = raw_payload.get("run_mode")
        sanitized_payload = sanitize_bridge_payload(raw_payload)
        observation = observation_from_sanitized_bridge_payload(
            sanitized_payload,
            run_id=run_id,
        )

        return BridgeReceipt(
            run_mode=cast(BridgeRunMode, run_mode),
            sanitized_payload=sanitized_payload,
            observation=observation,
        )


def accept_bridge_payload(raw_payload: Mapping[str, Any]) -> BridgeReceipt:
    """Pure helper for tests and later transport glue."""

    return VisibleBridgeAdapter().accept_payload(raw_payload)


def observation_from_sanitized_bridge_payload(
    sanitized_payload: Mapping[str, Any],
    *,
    run_id: str,
) -> Observation:
    """Convert sanitized visible bridge data into a canonical Observation."""

    screenshot_id = cast(str | None, sanitized_payload.get("screenshot_id"))
    evidence_ids = [screenshot_id] if screenshot_id is not None else []
    visible_text_spans = _visible_text_spans_from_payload(sanitized_payload, screenshot_id)
    visible_sprite_screen_positions = list(
        cast(
            list[tuple[int, int]],
            sanitized_payload.get("visible_sprite_screen_positions", []),
        )
    )
    visible_sprite_visual_hashes = list(
        cast(list[str], sanitized_payload.get("visible_sprite_visual_hashes", []))
    )
    try:
        visible_sprites = normalize_visible_sprites(
            visible_sprite_screen_positions=visible_sprite_screen_positions,
            visible_sprite_visual_hashes=visible_sprite_visual_hashes,
            screenshot_id=screenshot_id,
            evidence_ids=evidence_ids,
            # This is confidence in sanitized visible-data extraction, not entity semantics.
            source_confidence=1.0,
        )
    except VisibleSpriteNormalizationError as exc:
        raise InvalidBridgePayloadError(str(exc)) from exc

    return Observation(
        run_id=run_id,
        ui_state=sanitized_payload.get("ui_state", "unknown"),
        screenshot_id=screenshot_id,
        visible_message_text=cast(str | None, sanitized_payload.get("visible_message_text")),
        visible_text_spans=visible_text_spans,
        visible_menu_items=list(cast(list[str], sanitized_payload.get("visible_menu_items", []))),
        player_screen_position=cast(
            tuple[int, int] | None,
            sanitized_payload.get("player_screen_position"),
        ),
        visible_sprite_screen_positions=visible_sprite_screen_positions,
        visible_sprite_visual_hashes=visible_sprite_visual_hashes,
        visible_sprites=visible_sprites,
        evidence_ids=evidence_ids,
    )


def observation_from_bridge_payload(
    raw_payload: Mapping[str, Any],
    *,
    run_id: str,
) -> Observation:
    """Sanitize a raw bridge payload and convert it into an Observation."""

    return observation_from_sanitized_bridge_payload(
        sanitize_bridge_payload(raw_payload),
        run_id=run_id,
    )


def accept_bridge_observation_payload(
    raw_payload: Mapping[str, Any],
    *,
    run_id: str,
) -> BridgeReceipt:
    """Pure helper returning audit metadata plus the converted Observation."""

    return VisibleBridgeAdapter().accept_observation_payload(raw_payload, run_id=run_id)


def _visible_text_spans_from_payload(
    sanitized_payload: Mapping[str, Any],
    screenshot_id: str | None,
) -> list[VisibleTextSpan]:
    spans: list[VisibleTextSpan] = []
    message_text = sanitized_payload.get("visible_message_text")
    if isinstance(message_text, str) and message_text:
        spans.append(VisibleTextSpan(text=message_text, evidence_id=screenshot_id))

    menu_items = sanitized_payload.get("visible_menu_items", [])
    if isinstance(menu_items, list):
        for item in menu_items:
            if item:
                spans.append(VisibleTextSpan(text=item, evidence_id=screenshot_id))

    return spans
