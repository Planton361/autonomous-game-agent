import pytest
from pydantic import ValidationError

from fh_agent.manager.reward_profiles import (
    ALLOWED_REWARD_TERMS,
    DEFAULT_REWARD_PROFILES,
    RewardProfile,
    RewardTerm,
    default_reward_profile_for_skill,
)


def test_unknown_reward_term_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RewardTerm(name="enemy_hp_revealed", weight=1.0)


def test_default_reward_profiles_use_only_allowed_generic_terms() -> None:
    assert DEFAULT_REWARD_PROFILES
    for profile in DEFAULT_REWARD_PROFILES.values():
        assert profile.terms
        assert {term.name for term in profile.terms} <= ALLOWED_REWARD_TERMS


def test_default_reward_profiles_exist_for_m9_universal_skills() -> None:
    expected_skills = {
        "continue_dialogue",
        "reach_visible_target",
        "safe_reach_target",
        "retreat_from_hazard",
        "wait_for_safe_gap",
        "interact_visible_object",
        "select_visible_menu_entry",
    }

    assert expected_skills <= set(DEFAULT_REWARD_PROFILES)


def test_reward_profile_rejects_duplicate_terms() -> None:
    with pytest.raises(ValidationError, match="unique"):
        RewardProfile(
            profile_name="duplicate",
            terms=(
                RewardTerm(name="skill_success", weight=1.0),
                RewardTerm(name="skill_success", weight=0.5),
            ),
        )


def test_default_reward_profile_for_unknown_skill_is_rejected() -> None:
    with pytest.raises(ValueError, match="no default reward profile"):
        default_reward_profile_for_skill("solve_specific_room")
