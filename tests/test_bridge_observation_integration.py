import pytest

from fh_agent.bridge.bridge_server import observation_from_bridge_payload
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError, InvalidBridgePayloadError
from fh_agent.observation.schemas import Observation


def test_raw_bridge_payload_converts_to_observation() -> None:
    observation = observation_from_bridge_payload(
        {
            "run_mode": "official",
            "ui_state": "menu",
            "visible_message_text": "A visible line.",
            "visible_menu_items": ["Items", "Skills"],
            "player_screen_position": [10, 20],
            "visible_sprite_screen_positions": [[30, 40]],
            "visible_sprite_visual_hashes": ["dhash:0123456789abcdef"],
            "screenshot_id": "shot-001",
        },
        run_id="run-1",
    )

    assert isinstance(observation, Observation)
    assert observation.run_id == "run-1"
    assert observation.ui_state == "menu"
    assert observation.screenshot_id == "shot-001"
    assert observation.evidence_ids == ["shot-001"]
    assert observation.visible_message_text == "A visible line."
    assert observation.visible_menu_items == ["Items", "Skills"]
    assert [span.text for span in observation.visible_text_spans] == [
        "A visible line.",
        "Items",
        "Skills",
    ]
    assert {span.evidence_id for span in observation.visible_text_spans} == {"shot-001"}
    assert observation.player_screen_position == (10, 20)
    assert observation.visible_sprite_screen_positions == [(30, 40)]
    assert observation.visible_sprite_visual_hashes == ["dhash:0123456789abcdef"]
    assert len(observation.visible_sprites) == 1
    assert observation.visible_sprites[0].screen_position == (30, 40)
    assert observation.visible_sprites[0].visual_hash == "dhash:0123456789abcdef"
    assert observation.visible_sprites[0].evidence_id == "shot-001"


def test_run_mode_is_not_observation_content() -> None:
    observation = observation_from_bridge_payload(
        {
            "run_mode": "debug",
            "ui_state": "field",
            "screenshot_id": "shot-002",
        },
        run_id="run-1",
    )

    assert "run_mode" not in observation.model_dump()


def test_invalid_ui_state_is_rejected_before_observation_creation() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        observation_from_bridge_payload(
            {
                "run_mode": "official",
                "ui_state": "inventory",
                "screenshot_id": "shot-003",
            },
            run_id="run-1",
        )


def test_nested_forbidden_fields_are_rejected_before_observation_creation() -> None:
    with pytest.raises(ForbiddenBridgeFieldError) as exc_info:
        observation_from_bridge_payload(
            {
                "run_mode": "official",
                "ui_state": "field",
                "visible_menu_items": [{"event_id": 9}],
                "screenshot_id": "shot-004",
            },
            run_id="run-1",
        )

    assert exc_info.value.field_paths == ("visible_menu_items[0].event_id",)


def test_sprite_positions_must_be_screen_coordinates() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        observation_from_bridge_payload(
            {
                "run_mode": "official",
                "visible_sprite_screen_positions": [[-3, 8]],
            },
            run_id="run-1",
        )


def test_sprite_visual_hashes_must_not_be_entity_names() -> None:
    with pytest.raises(InvalidBridgePayloadError):
        observation_from_bridge_payload(
            {
                "run_mode": "official",
                "visible_sprite_visual_hashes": ["guard"],
            },
            run_id="run-1",
        )
