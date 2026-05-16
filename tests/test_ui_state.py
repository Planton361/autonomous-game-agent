from fh_agent.observation.schemas import VisibleTextSpan
from fh_agent.perception.ui_state import classify_ui_state


def test_classifier_prioritizes_death_over_other_visible_ui_flags() -> None:
    result = classify_ui_state(
        bridge_data={
            "death_screen_visible": True,
            "combat_ui_visible": True,
            "menu_open": True,
        },
        evidence_id="evidence-1",
    )

    assert result.state == "death"
    assert result.evidence_id == "evidence-1"


def test_classifier_detects_dialogue_from_visible_text_spans() -> None:
    result = classify_ui_state(
        text_spans=[VisibleTextSpan(text="Visible line", confidence=0.8, evidence_id="e1")]
    )

    assert result.state == "dialogue"
    assert result.confidence > 0


def test_classifier_detects_field_from_visible_positions() -> None:
    result = classify_ui_state(bridge_data={"player_screen_position": (10, 20)})

    assert result.state == "field"
