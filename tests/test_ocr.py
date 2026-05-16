from datetime import UTC, datetime

from fh_agent.observation.schemas import VisibleTextSpan
from fh_agent.perception.ocr import NoOpOcrEngine, StaticOcrEngine
from fh_agent.perception.screen_capture import ScreenFrame


def make_frame() -> ScreenFrame:
    return ScreenFrame(
        width=1,
        height=1,
        rgb=b"\x00\x00\x00",
        captured_at=datetime(2026, 5, 16, tzinfo=UTC),
    )


def test_noop_ocr_returns_empty_result() -> None:
    result = NoOpOcrEngine().read_text(make_frame(), evidence_id="evidence-1")

    assert result.spans == []
    assert result.text == ""


def test_static_ocr_attaches_evidence_id_and_confidence() -> None:
    engine = StaticOcrEngine([VisibleTextSpan(text="Visible text", confidence=0.91)])

    result = engine.read_text(make_frame(), evidence_id="evidence-1")

    assert result.text == "Visible text"
    assert result.spans[0].confidence == 0.91
    assert result.spans[0].evidence_id == "evidence-1"
