import pytest

from fh_agent.bridge.bridge_server import (
    VisibleBridgeAdapter,
    accept_bridge_observation_payload,
    accept_bridge_payload,
)
from fh_agent.bridge.sanitizer import ForbiddenBridgeFieldError, UnknownBridgeFieldError


def test_adapter_accepts_payload_without_network_or_game() -> None:
    receipt = accept_bridge_payload(
        {
            "run_mode": "official",
            "ui_state": "menu",
            "visible_menu_items": ["Items"],
            "screenshot_id": "shot-101",
        }
    )

    assert receipt.run_mode == "official"
    assert receipt.sanitized_payload == {
        "visible_menu_items": ["Items"],
        "ui_state": "menu",
        "screenshot_id": "shot-101",
    }


def test_adapter_debug_mode_does_not_allow_forbidden_fields() -> None:
    adapter = VisibleBridgeAdapter()

    with pytest.raises(ForbiddenBridgeFieldError):
        adapter.accept_payload(
            {
                "run_mode": "debug",
                "ui_state": "field",
                "savegame_variables": {"ending": "hidden"},
            }
        )


def test_adapter_rejects_unknown_transport_noise() -> None:
    adapter = VisibleBridgeAdapter()

    with pytest.raises(UnknownBridgeFieldError):
        adapter.accept_payload(
            {
                "run_mode": "official",
                "ui_state": "field",
                "request_id": "transport metadata belongs outside the payload",
            }
        )


def test_adapter_can_return_observation_with_run_mode_audit_metadata() -> None:
    receipt = accept_bridge_observation_payload(
        {
            "run_mode": "debug",
            "ui_state": "dialogue",
            "visible_message_text": "Visible.",
            "screenshot_id": "shot-202",
        },
        run_id="run-1",
    )

    assert receipt.run_mode == "debug"
    assert receipt.observation is not None
    assert receipt.observation.run_id == "run-1"
    assert receipt.observation.visible_message_text == "Visible."
    assert "run_mode" not in receipt.observation.model_dump()
