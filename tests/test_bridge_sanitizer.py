import pytest

from fh_agent.bridge.sanitizer import (
    FORBIDDEN_BRIDGE_FIELDS,
    VISIBLE_BRIDGE_FIELDS,
    ForbiddenBridgeFieldError,
    InvalidBridgePayloadError,
    UnknownBridgeFieldError,
    sanitize_bridge_payload,
)


def test_sanitizer_outputs_only_visible_fields_and_keeps_screenshot_id() -> None:
    sanitized = sanitize_bridge_payload(
        {
            "run_mode": "bridge-assisted",
            "visible_message_text": "A visible line.",
            "visible_menu_items": ["Items", "Skills"],
            "ui_state": "dialogue",
            "player_screen_position": [10, 20],
            "visible_sprite_screen_positions": [[30, 40]],
            "visible_sprite_visual_hashes": ["ahash:0123456789abcdef"],
            "screenshot_id": "shot-001",
        }
    )

    assert set(sanitized) == VISIBLE_BRIDGE_FIELDS
    assert sanitized["screenshot_id"] == "shot-001"
    assert "run_mode" not in sanitized


def test_sanitizer_requires_run_mode() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        sanitize_bridge_payload({"visible_message_text": "Visible."})


@pytest.mark.parametrize("run_mode", ["bridge-assisted", "debug"])
def test_forbidden_top_level_fields_are_rejected_in_all_modes(run_mode: str) -> None:
    with pytest.raises(ForbiddenBridgeFieldError) as exc_info:
        sanitize_bridge_payload(
            {
                "run_mode": run_mode,
                "visible_message_text": "Visible.",
                "enemy_hp": 12,
            }
        )

    assert exc_info.value.field_paths == ("enemy_hp",)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_BRIDGE_FIELDS))
def test_all_forbidden_fields_are_rejected(field: str) -> None:
    with pytest.raises(ForbiddenBridgeFieldError):
        sanitize_bridge_payload({"run_mode": "bridge-assisted", field: "hidden"})


def test_forbidden_fields_are_detected_when_nested() -> None:
    with pytest.raises(ForbiddenBridgeFieldError) as exc_info:
        sanitize_bridge_payload(
            {
                "run_mode": "debug",
                "visible_menu_items": [
                    "Items",
                    {"label": "Status", "game_switches": {"door": True}},
                ],
                "visible_sprite_screen_positions": [{"event_name": "hidden"}],
            }
        )

    assert exc_info.value.field_paths == (
        "visible_menu_items[1].game_switches",
        "visible_sprite_screen_positions[0].event_name",
    )


def test_unknown_top_level_fields_are_rejected_not_ignored() -> None:
    with pytest.raises(UnknownBridgeFieldError) as exc_info:
        sanitize_bridge_payload(
            {
                "run_mode": "bridge-assisted",
                "visible_message_text": "Visible.",
                "unknown_debug_noise": "must fail",
            }
        )

    assert exc_info.value.field_names == ("unknown_debug_noise",)


def test_debug_mode_still_excludes_mode_metadata_from_sanitized_output() -> None:
    sanitized = sanitize_bridge_payload(
        {
            "run_mode": "debug",
            "ui_state": "field",
            "screenshot_id": "shot-debug",
        }
    )

    assert sanitized == {"ui_state": "field", "screenshot_id": "shot-debug"}


@pytest.mark.parametrize(
    "run_mode",
    ["official", "screen-only", "networked-api-exploratory", "contaminated", "training"],
)
def test_non_bridge_run_modes_are_rejected(run_mode: str) -> None:
    with pytest.raises(InvalidBridgePayloadError):
        sanitize_bridge_payload({"run_mode": run_mode, "screenshot_id": "shot-001"})


def test_negative_screen_coordinates_are_rejected() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        sanitize_bridge_payload(
            {
                "run_mode": "bridge-assisted",
                "player_screen_position": [-1, 20],
            }
        )


def test_sprite_visual_hashes_reject_entity_names() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        sanitize_bridge_payload(
            {
                "run_mode": "bridge-assisted",
                "visible_sprite_visual_hashes": ["guard"],
            }
        )
