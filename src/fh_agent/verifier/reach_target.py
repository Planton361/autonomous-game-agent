"""Deterministic visible verification for grounded screen-point targets."""

from dataclasses import dataclass
from math import hypot, isfinite

from fh_agent.manager.target_ref import VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


@dataclass(frozen=True, slots=True)
class ReachTargetVerifier:
    """Verify visible arrival at an already grounded screen-point target."""

    target: VisibleScreenPointTarget
    tolerance_px: float = 4.0

    def __post_init__(self) -> None:
        if not isfinite(self.tolerance_px) or self.tolerance_px < 0:
            msg = "tolerance_px must be finite and non-negative"
            raise ValueError(msg)

    def verify(
        self,
        before: Observation,
        after: Observation,
    ) -> VerifierResult:
        """Return only a visible, evidence-backed terminal outcome or abstention."""

        outcome_evidence_ids = after.evidence_ids
        if self._visibly_dead(after):
            if outcome_evidence_ids:
                return VerifierResult(
                    status=VerifierStatus.FAILURE,
                    failure_kind=FailureKind.DEATH,
                    evidence_ids=_deduplicated_evidence_ids(outcome_evidence_ids),
                )
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        if after.player_screen_position is None or not outcome_evidence_ids:
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        if _distance(after.player_screen_position, self.target.screen_position) > self.tolerance_px:
            return VerifierResult(status=VerifierStatus.ABSTAIN)

        return VerifierResult(
            status=VerifierStatus.SUCCESS,
            evidence_ids=_deduplicated_evidence_ids(self.target.evidence_ids, outcome_evidence_ids),
        )

    @staticmethod
    def _visibly_dead(observation: Observation) -> bool:
        return observation.ui_state == "death" or observation.death_screen_visible is True


def _distance(first: tuple[int, int], second: tuple[int, int]) -> float:
    return hypot(second[0] - first[0], second[1] - first[1])


def _deduplicated_evidence_ids(*sources: tuple[str, ...] | list[str]) -> list[str]:
    evidence_ids: list[str] = []
    for source in sources:
        for evidence_id in source:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids
