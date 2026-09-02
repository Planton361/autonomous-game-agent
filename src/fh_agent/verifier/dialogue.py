"""Deterministic visible verification for dialogue continuation outcomes."""

from fh_agent.observation.schemas import Observation
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


class ContinueDialogueVerifier:
    """Verify visible dialogue advance, close, or death without game semantics."""

    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        """Return an evidence-backed visible outcome or abstention."""

        if _visibly_dead(after):
            if after.evidence_ids:
                return VerifierResult(
                    status=VerifierStatus.FAILURE,
                    failure_kind=FailureKind.DEATH,
                    evidence_ids=_deduplicated_evidence_ids(after.evidence_ids),
                )
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        before_is_dialogue = _is_visible_dialogue(before)
        after_is_dialogue = _is_visible_dialogue(after)
        if not before_is_dialogue or not before.evidence_ids or not after.evidence_ids:
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        if after_is_dialogue and _visible_dialogue_text(before) != _visible_dialogue_text(after):
            return VerifierResult(
                status=VerifierStatus.SUCCESS,
                evidence_ids=_deduplicated_evidence_ids(before.evidence_ids, after.evidence_ids),
            )

        if not after_is_dialogue:
            return VerifierResult(
                status=VerifierStatus.SUCCESS,
                evidence_ids=_deduplicated_evidence_ids(before.evidence_ids, after.evidence_ids),
            )

        return VerifierResult(status=VerifierStatus.ABSTAIN)


def _is_visible_dialogue(observation: Observation) -> bool:
    return (
        observation.ui_state == "dialogue"
        or observation.message_window_visible is True
        or bool(observation.visible_message_text)
        or bool(observation.visible_text_spans)
    )


def _visible_dialogue_text(observation: Observation) -> tuple[str, ...]:
    texts: list[str] = []
    if observation.visible_message_text:
        texts.append(observation.visible_message_text)
    texts.extend(span.text for span in observation.visible_text_spans)
    return tuple(texts)


def _visibly_dead(observation: Observation) -> bool:
    return observation.ui_state == "death" or observation.death_screen_visible is True


def _deduplicated_evidence_ids(*sources: list[str]) -> list[str]:
    evidence_ids: list[str] = []
    for source in sources:
        for evidence_id in source:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids
