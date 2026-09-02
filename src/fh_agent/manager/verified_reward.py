"""Pure reward derivation from canonical verifier outcomes."""

from pydantic import BaseModel, ConfigDict, model_validator

from fh_agent.manager.reward_profiles import RewardProfile, RewardTermName
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


class VerifiedRewardContribution(BaseModel):
    """One configured reward contribution justified by a verified outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: RewardTermName
    value: float


class VerifiedRewardBreakdown(BaseModel):
    """Deterministic reward derivation retaining its canonical outcome provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_name: str
    verifier_result: VerifierResult
    contributions: tuple[VerifiedRewardContribution, ...] = ()
    total: float

    @model_validator(mode="after")
    def total_must_match_contributions(self) -> "VerifiedRewardBreakdown":
        if self.total != sum(contribution.value for contribution in self.contributions):
            msg = "total must equal the sum of contribution values"
            raise ValueError(msg)
        return self


def derive_verified_reward(
    profile: RewardProfile,
    verifier_result: VerifierResult,
) -> VerifiedRewardBreakdown:
    """Derive only reward terms directly justified by one canonical outcome."""

    term_name, multiplier = _supported_term(verifier_result)
    contributions = tuple(
        VerifiedRewardContribution(name=term.name, value=multiplier * term.weight)
        for term in profile.terms
        if term.name == term_name
    )
    return VerifiedRewardBreakdown(
        profile_name=profile.profile_name,
        verifier_result=verifier_result,
        contributions=contributions,
        total=sum(contribution.value for contribution in contributions),
    )


def _supported_term(verifier_result: VerifierResult) -> tuple[RewardTermName | None, float]:
    if verifier_result.status is VerifierStatus.SUCCESS:
        return "skill_success", 1.0
    if verifier_result.status is not VerifierStatus.FAILURE:
        return None, 0.0
    if verifier_result.failure_kind is FailureKind.DEATH:
        return "avoid_death", -1.0
    if verifier_result.failure_kind is FailureKind.TIMEOUT:
        return "avoid_timeout", -1.0
    if verifier_result.failure_kind is FailureKind.NO_PROGRESS:
        return "avoid_repeated_no_progress", -1.0
    return None, 0.0
