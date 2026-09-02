import inspect
from math import inf, nan

import pytest

from fh_agent.manager import verifier_catalog as verifier_catalog_module
from fh_agent.manager.reward_profiles import default_reward_profile_for_skill
from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.manager.verifier_catalog import VerifierCatalog, VerifierSelectionError
from fh_agent.skill_capabilities import DEFAULT_RUNTIME_SKILLS
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.interaction import InteractVisibleObjectVerifier
from fh_agent.verifier.ports import OutcomeVerifier
from fh_agent.verifier.reach_target import ReachTargetVerifier


def task_spec(
    *,
    selected_skill: str,
    target: VisibleScreenPointTarget | VisibleObjectTarget | None,
) -> TaskSpec:
    return TaskSpec(
        task_id="task-1",
        selected_skill=selected_skill,  # type: ignore[arg-type]
        goal="Act on visible evidence.",
        target=target,
        timeout_steps=6,
        reward_profile=default_reward_profile_for_skill(selected_skill),
    )


def screen_point_target() -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="visible-point-1",
        confidence=0.9,
        evidence_ids=("point-evidence",),
        screen_position=(10, 20),
    )


def object_target() -> VisibleObjectTarget:
    return VisibleObjectTarget(
        target_id="visible-object-1",
        confidence=0.9,
        evidence_ids=("object-evidence",),
        screen_position=(10, 20),
        visual_hash="visible-hash",
    )


def as_outcome_verifier(verifier: OutcomeVerifier) -> OutcomeVerifier:
    return verifier


def test_continue_dialogue_selects_targetless_dialogue_verifier() -> None:
    verifier = VerifierCatalog().for_task(
        task_spec(selected_skill="continue_dialogue", target=None)
    )

    assert isinstance(verifier, ContinueDialogueVerifier)


def test_basic_reach_target_selects_bound_reach_verifier_with_default_tolerance() -> None:
    target = screen_point_target()
    verifier = VerifierCatalog().for_task(
        task_spec(selected_skill="basic_reach_target", target=target)
    )

    assert isinstance(verifier, ReachTargetVerifier)
    assert verifier.target is target
    assert verifier.tolerance_px == 4.0


def test_custom_reach_tolerance_is_propagated() -> None:
    verifier = VerifierCatalog(reach_target_tolerance_px=2.5).for_task(
        task_spec(selected_skill="basic_reach_target", target=screen_point_target())
    )

    assert isinstance(verifier, ReachTargetVerifier)
    assert verifier.tolerance_px == 2.5


@pytest.mark.parametrize("tolerance_px", [-0.1, inf, nan])
def test_invalid_reach_tolerance_is_rejected(tolerance_px: float) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        VerifierCatalog(reach_target_tolerance_px=tolerance_px)


def test_interaction_selects_bound_interaction_verifier() -> None:
    target = object_target()
    verifier = VerifierCatalog().for_task(
        task_spec(selected_skill="interact_visible_object", target=target)
    )

    assert isinstance(verifier, InteractVisibleObjectVerifier)
    assert verifier.target is target


@pytest.mark.parametrize(
    ("selected_skill", "target"),
    [
        ("continue_dialogue", screen_point_target()),
        ("basic_reach_target", None),
        ("basic_reach_target", object_target()),
        ("interact_visible_object", None),
        ("interact_visible_object", screen_point_target()),
        ("safe_reach_target", screen_point_target()),
    ],
)
def test_invalid_task_contracts_are_rejected(
    selected_skill: str,
    target: VisibleScreenPointTarget | VisibleObjectTarget | None,
) -> None:
    with pytest.raises(VerifierSelectionError):
        VerifierCatalog().for_task(task_spec(selected_skill=selected_skill, target=target))


def test_registered_verifier_skills_exactly_match_runtime_skills() -> None:
    assert VerifierCatalog().registered_skills == DEFAULT_RUNTIME_SKILLS


def test_all_selected_verifiers_share_the_outcome_verifier_port() -> None:
    catalog = VerifierCatalog()
    verifiers = [
        catalog.for_task(task_spec(selected_skill="continue_dialogue", target=None)),
        catalog.for_task(
            task_spec(selected_skill="basic_reach_target", target=screen_point_target())
        ),
        catalog.for_task(
            task_spec(selected_skill="interact_visible_object", target=object_target())
        ),
    ]

    assert all(as_outcome_verifier(verifier) is verifier for verifier in verifiers)


def test_verifier_catalog_has_no_body_or_evaluation_authority() -> None:
    source = inspect.getsource(verifier_catalog_module)

    assert "fh_agent.body" not in source
    assert "PrimitiveAction" not in source
    assert ".verify(" not in source
