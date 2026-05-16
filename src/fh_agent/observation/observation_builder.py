from dataclasses import dataclass, field
from typing import Any

from fh_agent.bridge.firewall import NoSpoilerFirewall
from fh_agent.memory.evidence import EvidenceRecord
from fh_agent.observation.schemas import ActionResult, Observation
from fh_agent.perception.ocr import NoOpOcrEngine, OcrEngine
from fh_agent.perception.screen_capture import ScreenFrame
from fh_agent.perception.ui_state import classify_ui_state
from fh_agent.perception.visual_hash import screen_signature


@dataclass(slots=True)
class ObservationBuilder:
    """Build canonical observations from visible frames and sanitized bridge data."""

    run_id: str
    firewall: NoSpoilerFirewall = field(default_factory=NoSpoilerFirewall)
    ocr_engine: OcrEngine = field(default_factory=NoOpOcrEngine)

    def build(
        self,
        *,
        frame: ScreenFrame,
        evidence: EvidenceRecord,
        bridge_data: dict[str, Any] | None = None,
        last_action_result: ActionResult | None = None,
    ) -> Observation:
        sanitized_bridge = self.firewall.sanitize(bridge_data or {})
        signature = screen_signature(frame)
        ocr_result = self.ocr_engine.read_text(frame, evidence_id=evidence.evidence_id)
        classification = classify_ui_state(
            bridge_data=sanitized_bridge,
            text_spans=ocr_result.spans,
            screen_signature=signature,
            evidence_id=evidence.evidence_id,
        )
        visible_message_text = (
            sanitized_bridge.get("visible_message_text") or ocr_result.text or None
        )
        bridge_observation_fields = dict(sanitized_bridge)
        bridge_observation_fields.pop("visible_message_text", None)
        bridge_observation_fields.pop("screenshot_id", None)

        return Observation(
            run_id=self.run_id,
            ui_state=classification.state,
            screenshot_id=evidence.evidence_id,
            screen_signature=signature,
            visible_text_spans=ocr_result.spans,
            visible_message_text=visible_message_text,
            last_action_result=last_action_result,
            evidence_ids=[evidence.evidence_id],
            **bridge_observation_fields,
        )
