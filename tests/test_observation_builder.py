from datetime import UTC, datetime
from pathlib import Path

import pytest

from fh_agent.bridge.firewall import FirewallViolation
from fh_agent.memory.evidence import EvidenceStore
from fh_agent.observation.observation_builder import ObservationBuilder
from fh_agent.observation.schemas import ActionResult, VisibleTextSpan
from fh_agent.perception.ocr import StaticOcrEngine
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.visual_hash import screen_signature


def make_frame() -> ScreenFrame:
    return ScreenFrame(
        width=2,
        height=1,
        rgb=b"\x00\x00\x00\xff\xff\xff",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )


def save_evidence(tmp_path: Path, frame: ScreenFrame):
    return EvidenceStore(
        tmp_path,
        run_id="run-1",
        id_factory=lambda: "evidence-1",
    ).save_screenshot(frame)


def test_observation_builder_produces_valid_json_from_frame_bridge_and_ocr(tmp_path: Path) -> None:
    frame = make_frame()
    evidence = save_evidence(tmp_path, frame)
    builder = ObservationBuilder(
        run_id="run-1",
        ocr_engine=StaticOcrEngine([VisibleTextSpan(text="Read from screen", confidence=0.8)]),
    )

    observation = builder.build(
        frame=frame,
        evidence=evidence,
        bridge_data={
            "menu_open": True,
            "visible_menu_items": ["Items", "Skills"],
            "unknown_debug_field": "discarded",
        },
        last_action_result=ActionResult(action="wait", executed=True),
    )

    assert observation.ui_state == "menu"
    assert observation.screen_signature == screen_signature(frame)
    assert observation.screenshot_id == "evidence-1"
    assert observation.visible_text_spans[0].evidence_id == "evidence-1"
    assert observation.visible_message_text == "Read from screen"
    assert observation.visible_menu_items == ["Items", "Skills"]
    assert observation.last_action_result is not None
    assert "unknown_debug_field" not in observation.model_dump()
    assert '"ui_state":"menu"' in observation.model_dump_json()


def test_observation_builder_blocks_forbidden_bridge_fields(tmp_path: Path) -> None:
    frame = make_frame()
    evidence = save_evidence(tmp_path, frame)
    builder = ObservationBuilder(run_id="run-1")

    with pytest.raises(FirewallViolation):
        builder.build(
            frame=frame,
            evidence=evidence,
            bridge_data={"enemy_hp": 10},
        )
