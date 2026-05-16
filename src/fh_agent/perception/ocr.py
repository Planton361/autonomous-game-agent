from dataclasses import dataclass, field
from typing import Protocol

from fh_agent.observation.schemas import VisibleTextSpan
from fh_agent.perception.screen_capture import ScreenFrame


@dataclass(frozen=True, slots=True)
class OcrResult:
    """OCR output tied to screenshot evidence, without game-specific claims."""

    spans: list[VisibleTextSpan] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(span.text for span in self.spans)


class OcrEngine(Protocol):
    def read_text(self, frame: ScreenFrame, *, evidence_id: str | None = None) -> OcrResult:
        """Read visible text from a frame."""


class NoOpOcrEngine:
    """Offline-safe placeholder until a real OCR backend is configured."""

    def read_text(self, frame: ScreenFrame, *, evidence_id: str | None = None) -> OcrResult:
        del frame, evidence_id
        return OcrResult()


class StaticOcrEngine:
    """Deterministic OCR fixture for tests and saved-frame smoke checks."""

    def __init__(self, spans: list[VisibleTextSpan]) -> None:
        self.spans = spans

    def read_text(self, frame: ScreenFrame, *, evidence_id: str | None = None) -> OcrResult:
        del frame
        return OcrResult(
            spans=[
                span.model_copy(update={"evidence_id": span.evidence_id or evidence_id})
                for span in self.spans
            ]
        )
