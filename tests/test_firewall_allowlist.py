import pytest

from fh_agent.bridge.firewall import (
    ALLOWED_BRIDGE_FIELDS,
    FORBIDDEN_BRIDGE_FIELDS,
    FirewallViolation,
    NoSpoilerFirewall,
    sanitize_bridge_data,
)
from fh_agent.observation.schemas import Observation


def test_allowed_fields_are_sanitized_and_can_build_observation() -> None:
    raw_data = {
        "message_window_visible": True,
        "visible_message_text": "Visible only",
        "menu_open": False,
        "visible_menu_items": ["Items"],
        "combat_ui_visible": False,
        "death_screen_visible": False,
        "player_screen_position": (12, 34),
        "visible_sprite_screen_positions": [(56, 78)],
        "visible_sprite_visual_hashes": ["hash-1"],
        "screenshot_id": "evidence-1",
        "unknown_debug_noise": "dropped",
    }

    sanitized = sanitize_bridge_data(raw_data)
    observation = Observation(run_id="run-1", evidence_ids=["evidence-1"], **sanitized)

    assert set(sanitized) == ALLOWED_BRIDGE_FIELDS
    assert observation.visible_message_text == "Visible only"
    assert observation.screenshot_id == "evidence-1"


@pytest.mark.parametrize("field", sorted(FORBIDDEN_BRIDGE_FIELDS))
def test_forbidden_fields_are_blocked(field: str) -> None:
    firewall = NoSpoilerFirewall()

    with pytest.raises(FirewallViolation) as exc_info:
        firewall.sanitize({"message_window_visible": True, field: "hidden"})

    assert exc_info.value.forbidden_fields == (field,)


def test_multiple_forbidden_fields_are_reported_sorted() -> None:
    firewall = NoSpoilerFirewall()

    with pytest.raises(FirewallViolation) as exc_info:
        firewall.sanitize(
            {
                "enemy_hp": 10,
                "map_id": 2,
                "visible_message_text": "Visible",
            }
        )

    assert exc_info.value.forbidden_fields == ("enemy_hp", "map_id")


def test_unknown_non_forbidden_fields_are_dropped() -> None:
    sanitized = sanitize_bridge_data(
        {
            "message_window_visible": False,
            "unrecognized_runtime_field": "ignored",
        }
    )

    assert sanitized == {"message_window_visible": False}
