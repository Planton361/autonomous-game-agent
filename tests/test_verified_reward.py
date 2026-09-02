import inspect

import pytest
from pydantic import ValidationError

import fh_agent.manager.verified_reward as verified_reward
from fh_agent.manager.reward_profiles import RewardProfile, RewardTerm
from fh_agent.manager.verified_reward import (
    VerifiedRewardBreakdown,
    VerifiedRewardContribution,
    derive_verified_reward,
)
from fh_agent.verifier.schemas import FailureKind, VerifierResult, VerifierStatus


def profile(*terms: tuple[str, float]) -> RewardProfile:
    return RewardProfile(
        profile_name="test_profile",
        terms=tuple(RewardTerm(name=name, weight=weight) for name, weight in terms),
    )


def result(
    status: VerifierStatus,
    *,
    failure_kind: FailureKind | None = None,
    evidence_ids: list[str] | None = None,
) -> VerifierResult:
    return VerifierResult(
        status=status,
        failure_kind=failure_kind,
        evidence_ids=[] if evidence_ids is None else evidence_ids,
    )


def test_success_derives_only_configured_skill_success_and_retains_provenance() -> None:
    verifier_result = result(VerifierStatus.SUCCESS, evidence_ids=["visible-evidence"])
    reward = derive_verified_reward(profile(("skill_success", 2.5)), verifier_result)

    assert reward.profile_name == "test_profile"
    assert reward.verifier_result == verifier_result
    assert reward.verifier_result.evidence_ids == ["visible-evidence"]
    assert reward.contributions == (VerifiedRewardContribution(name="skill_success", value=2.5),)
    assert reward.total == 2.5


def test_success_without_skill_success_produces_zero() -> None:
    reward = derive_verified_reward(profile(("avoid_death", 4.0)), result(VerifierStatus.SUCCESS))

    assert reward.contributions == ()
    assert reward.total == 0.0


@pytest.mark.parametrize(
    "term_name",
    [
        "new_visible_text",
        "screen_transition",
        "information_gain",
        "hypothesis_tested",
        "avoid_death",
        "avoid_timeout",
    ],
)
def test_success_does_not_activate_unsupported_or_avoidance_terms(term_name: str) -> None:
    reward = derive_verified_reward(profile((term_name, 999.0)), result(VerifierStatus.SUCCESS))

    assert reward.contributions == ()
    assert reward.total == 0.0


def test_death_derives_only_configured_avoid_death() -> None:
    reward = derive_verified_reward(
        profile(("avoid_death", 3.0), ("skill_success", 9.0)),
        result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH),
    )

    assert reward.contributions == (VerifiedRewardContribution(name="avoid_death", value=-3.0),)
    assert reward.total == -3.0


def test_death_without_avoid_death_produces_zero() -> None:
    reward = derive_verified_reward(
        profile(("skill_success", 1.0)),
        result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH),
    )

    assert reward.contributions == ()
    assert reward.total == 0.0


@pytest.mark.parametrize(
    ("failure_kind", "term_name"),
    [
        (FailureKind.TIMEOUT, "avoid_timeout"),
        (FailureKind.NO_PROGRESS, "avoid_repeated_no_progress"),
    ],
)
def test_supported_failure_kinds_apply_only_their_configured_avoidance_term(
    failure_kind: FailureKind,
    term_name: str,
) -> None:
    reward = derive_verified_reward(
        profile((term_name, 1.75)),
        result(VerifierStatus.FAILURE, failure_kind=failure_kind),
    )

    assert reward.contributions == (VerifiedRewardContribution(name=term_name, value=-1.75),)
    assert reward.total == -1.75


@pytest.mark.parametrize(
    "failure_kind",
    [
        FailureKind.PERCEPTION_UNCERTAIN,
        FailureKind.GROUNDING_FAILED,
        FailureKind.CAPABILITY_REJECTED,
        FailureKind.PLANNING_FAILED,
        FailureKind.SKILL_FAILED,
        FailureKind.TARGET_LOST,
        FailureKind.SAFETY_INTERVENTION,
        FailureKind.FOCUS_LOST,
        FailureKind.REPLAN_REQUIRED,
        FailureKind.CONTAMINATED,
    ],
)
def test_currently_unsupported_failure_kinds_produce_zero(failure_kind: FailureKind) -> None:
    reward = derive_verified_reward(
        profile(("skill_success", 20.0), ("avoid_death", 20.0), ("avoid_timeout", 20.0)),
        result(VerifierStatus.FAILURE, failure_kind=failure_kind),
    )

    assert reward.contributions == ()
    assert reward.total == 0.0


@pytest.mark.parametrize("status", [VerifierStatus.ABSTAIN, VerifierStatus.PROGRESS])
def test_abstain_and_progress_produce_zero(status: VerifierStatus) -> None:
    reward = derive_verified_reward(profile(("skill_success", 3.0)), result(status))

    assert reward.contributions == ()
    assert reward.total == 0.0


def test_unsupported_high_weight_terms_cannot_change_the_breakdown() -> None:
    reward = derive_verified_reward(
        profile(
            ("new_visible_text", 1_000_000.0),
            ("screen_transition", 1_000_000.0),
            ("avoid_combat", 1_000_000.0),
            ("information_gain", 1_000_000.0),
            ("hypothesis_tested", 1_000_000.0),
        ),
        result(VerifierStatus.SUCCESS),
    )

    assert reward.contributions == ()
    assert reward.total == 0.0


def test_configured_weight_sign_is_preserved_without_absolute_value_rewriting() -> None:
    success = derive_verified_reward(
        profile(("skill_success", -2.0)), result(VerifierStatus.SUCCESS)
    )
    death = derive_verified_reward(
        profile(("avoid_death", -3.0)),
        result(VerifierStatus.FAILURE, failure_kind=FailureKind.DEATH),
    )

    assert success.total == -2.0
    assert death.total == 3.0


def test_breakdown_total_must_equal_contribution_sum() -> None:
    with pytest.raises(ValidationError, match="total must equal"):
        VerifiedRewardBreakdown(
            profile_name="test_profile",
            verifier_result=result(VerifierStatus.SUCCESS),
            contributions=(VerifiedRewardContribution(name="skill_success", value=1.0),),
            total=0.0,
        )


def test_derivation_is_deterministic_and_preserves_profile_term_order() -> None:
    reward_profile = profile(("new_visible_text", 9.0), ("skill_success", 1.0))
    verifier_result = result(VerifierStatus.SUCCESS, evidence_ids=["evidence-1"])

    first = derive_verified_reward(reward_profile, verifier_result)
    second = derive_verified_reward(reward_profile, verifier_result)

    assert first == second
    assert [item.name for item in first.contributions] == ["skill_success"]
    assert first.total == sum(item.value for item in first.contributions)


def test_derivation_module_has_only_canonical_inputs_and_no_runtime_dependencies() -> None:
    source = inspect.getsource(verified_reward)
    parameters = inspect.signature(derive_verified_reward).parameters

    assert tuple(parameters) == ("profile", "verifier_result")
    for forbidden_dependency in (
        "fh_agent.observation",
        "fh_agent.body",
        "InputExecutor",
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.cortex",
        "fh_agent.rl",
        "SkillResult",
        "TaskCompletion",
        "SkillRunResult",
        "skill_name",
    ):
        assert forbidden_dependency not in source
    assert ".verify(" not in source
