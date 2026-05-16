import json
from pathlib import Path

import pytest

from fh_agent.bridge.firewall import FirewallViolation
from fh_agent.observation.schemas import Observation, UIState, VisibleTextSpan
from fh_agent.perception.ocr import StaticOcrEngine
from fh_agent.perception.offline_processor import observation_to_json, process_saved_frame

FIXTURES = Path(__file__).parent / "fixtures" / "perception"


def test_processor_loads_ppm_fixture_and_returns_observation() -> None:
    observation = process_saved_frame(
        FIXTURES / "field.ppm",
        run_id="run-fixture",
        evidence_id="field-evidence",
        ui_hint="field",
    )

    assert isinstance(observation, Observation)
    assert observation.ui_state == "field"
    assert observation.screenshot_id == "field-evidence"
    assert observation.screen_signature
    assert observation.player_screen_position == (0, 0)


def test_processor_attaches_ocr_confidence_and_evidence_id() -> None:
    observation = process_saved_frame(
        FIXTURES / "dialogue.ppm",
        run_id="run-fixture",
        evidence_id="dialogue-evidence",
        ui_hint="dialogue",
        ocr_engine=StaticOcrEngine([VisibleTextSpan(text="A visible line.", confidence=0.87)]),
    )

    assert observation.ui_state == "dialogue"
    assert observation.visible_message_text == "A visible line."
    assert observation.visible_text_spans[0].confidence == 0.87
    assert observation.visible_text_spans[0].evidence_id == "dialogue-evidence"


def test_processor_matches_dialogue_golden_json() -> None:
    observation = process_saved_frame(
        FIXTURES / "dialogue.ppm",
        run_id="run-fixture",
        evidence_id="dialogue-evidence",
        ui_hint="dialogue",
        ocr_engine=StaticOcrEngine([VisibleTextSpan(text="A visible line.", confidence=0.87)]),
    )

    golden = json.loads((FIXTURES / "golden" / "dialogue_observation.json").read_text())
    actual = observation.model_dump(
        mode="json",
        exclude={"created_at"},
        exclude_none=True,
    )

    assert actual == golden


@pytest.mark.parametrize(
    ("fixture_name", "ui_hint", "expected_state"),
    [
        ("menu.ppm", "menu", "menu"),
        ("combat.ppm", "combat", "combat"),
        ("death.ppm", "death", "death"),
    ],
)
def test_processor_uses_visible_ui_hints_for_synthetic_fixtures(
    fixture_name: str,
    ui_hint: UIState,
    expected_state: str,
) -> None:
    observation = process_saved_frame(
        FIXTURES / fixture_name,
        run_id="run-fixture",
        evidence_id=f"{expected_state}-evidence",
        ui_hint=ui_hint,
    )

    assert observation.ui_state == expected_state


@pytest.mark.parametrize("forbidden_field", ["enemy_hp", "map_id", "game_switches"])
def test_processor_blocks_hidden_state_bridge_fields(forbidden_field: str) -> None:
    with pytest.raises(FirewallViolation):
        process_saved_frame(
            FIXTURES / "field.ppm",
            run_id="run-fixture",
            evidence_id="field-evidence",
            sanitized_bridge_data={forbidden_field: "hidden"},
        )


def test_processor_discards_unknown_bridge_fields() -> None:
    observation = process_saved_frame(
        FIXTURES / "menu.ppm",
        run_id="run-fixture",
        evidence_id="menu-evidence",
        sanitized_bridge_data={
            "menu_open": True,
            "debug_overlay": "discard me",
        },
    )

    assert observation.ui_state == "menu"
    assert "debug_overlay" not in observation.model_dump()


def test_processor_output_is_json_serializable() -> None:
    observation = process_saved_frame(
        FIXTURES / "dialogue.ppm",
        run_id="run-fixture",
        evidence_id="dialogue-evidence",
        ui_hint="dialogue",
    )

    dumped = observation_to_json(observation)

    assert '"ui_state":"dialogue"' in dumped
