"""Deterministic visible verification for visible-object interaction outcomes."""

from fh_agent.manager.target_ref import VisibleObjectTarget
from fh_agent.observation.schemas import Observation
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


class InteractVisibleObjectVerifier:
    """Verify a narrow, visible interaction outcome without game semantics."""

    def verify(
        self,
        before: Observation,
        after: Observation,
        *,
        target: VisibleObjectTarget | None = None,
    ) -> VerifierResult:
        """Return an evidence-backed visible outcome or abstention."""

        if _visibly_dead(after):
            if after.evidence_ids:
                return VerifierResult(
                    status=VerifierStatus.FAILURE,
                    failure_kind=FailureKind.DEATH,
                    evidence_ids=_deduplicated_evidence_ids(after.evidence_ids),
                )
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        if not before.evidence_ids or not after.evidence_ids:
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        has_interaction_ui_transition = after.ui_state in {"dialogue", "menu", "combat"} and (
            after.ui_state != before.ui_state
        )
        has_first_visible_text = not _has_visible_text(before) and _has_visible_text(after)
        if not has_interaction_ui_transition and not has_first_visible_text:
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        evidence_sources: tuple[tuple[str, ...] | list[str], ...]
        if target is None:
            evidence_sources = (before.evidence_ids, after.evidence_ids)
        else:
            evidence_sources = (target.evidence_ids, before.evidence_ids, after.evidence_ids)
        return VerifierResult(
            status=VerifierStatus.SUCCESS,
            evidence_ids=_deduplicated_evidence_ids(*evidence_sources),
        )


def _visibly_dead(observation: Observation) -> bool:
    return observation.ui_state == "death" or observation.death_screen_visible is True


def _has_visible_text(observation: Observation) -> bool:
    return bool(observation.visible_message_text) or any(
        span.text for span in observation.visible_text_spans
    )


def _deduplicated_evidence_ids(*sources: tuple[str, ...] | list[str]) -> list[str]:
    evidence_ids: list[str] = []
    for source in sources:
        for evidence_id in source:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids
