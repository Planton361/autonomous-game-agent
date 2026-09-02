import sys

import pytest

from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.body.skills.interact_visible import InteractVisibleObjectSkill
from fh_agent.manager.skill_catalog import SkillCatalog, SkillCatalogError
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation
from fh_agent.skill_capabilities import DEFAULT_RUNTIME_SKILLS
from fh_agent.verifier.reach_target import ReachTargetVerifier


def dialogue_observation(text: str = "Visible text") -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="dialogue",
        visible_message_text=text,
        evidence_ids=["e1"],
    )


def field_observation(*, player_pos: tuple[int, int] | None = None) -> Observation:
    return Observation(
        run_id="run-1",
        ui_state="field",
        player_screen_position=player_pos,
        evidence_ids=["e1"],
    )


def reach_target() -> VisibleScreenPointTarget:
    return VisibleScreenPointTarget(
        target_id="exit",
        confidence=0.9,
        evidence_ids=("target-evidence",),
        screen_position=(10, 0),
    )


def visible_object_target() -> VisibleObjectTarget:
    return VisibleObjectTarget(
        target_id="visible-object",
        confidence=0.9,
        evidence_ids=("target-evidence",),
        screen_position=(10, 0),
        visual_hash="visible-hash",
    )


def test_default_catalog_contains_all_milestone_5_skills() -> None:
    catalog = SkillCatalog.default()

    assert catalog.list() == [
        "basic_reach_target",
        "continue_dialogue",
        "interact_visible_object",
    ]


def test_every_default_runtime_skill_is_resolvable() -> None:
    catalog = SkillCatalog.default()

    assert tuple(catalog.list()) == DEFAULT_RUNTIME_SKILLS
    for skill_name in DEFAULT_RUNTIME_SKILLS:
        skill = catalog.get(skill_name)
        assert skill.contract.skill_name == skill_name


def test_get_continue_dialogue_returns_continue_dialogue_skill() -> None:
    skill = SkillCatalog.default().get("continue_dialogue")

    assert isinstance(skill, ContinueDialogueSkill)


def test_get_unknown_skill_raises_clear_error() -> None:
    with pytest.raises(SkillCatalogError, match="unknown skill: missing_skill"):
        SkillCatalog.default().get("missing_skill")


def test_dialogue_observation_selects_continue_dialogue() -> None:
    skill = SkillCatalog.default().select(observation=dialogue_observation())

    assert isinstance(skill, ContinueDialogueSkill)


def test_visible_object_target_selects_interact_visible_object() -> None:
    task = visible_object_target()

    skill = SkillCatalog.default().select(observation=field_observation(), task=task)

    assert isinstance(skill, InteractVisibleObjectSkill)
    assert skill.target is task


def test_visible_screen_point_target_selects_basic_reach_target() -> None:
    task = reach_target()

    skill = SkillCatalog.default().select(
        observation=field_observation(player_pos=(0, 0)), task=task
    )

    assert isinstance(skill, BasicReachTargetSkill)
    assert skill.target is task


def test_explicit_skill_name_wins_over_observation_heuristic() -> None:
    task = reach_target()

    skill = SkillCatalog.default().select(
        observation=dialogue_observation(),
        task=task,
        skill_name="basic_reach_target",
    )

    assert isinstance(skill, BasicReachTargetSkill)
    assert skill.target is task


def test_selected_skill_runs_through_skill_runner() -> None:
    task = reach_target()
    skill = SkillCatalog.default().select(
        observation=field_observation(player_pos=(0, 0)),
        task=task,
    )

    run = SkillRunner().run(
        skill,
        [
            field_observation(player_pos=(0, 0)),
            field_observation(player_pos=(10, 0)),
        ],
        verifier=ReachTargetVerifier(task),
    )

    assert run.skill_result.success
    assert run.skill_result.skill_name == "basic_reach_target"


def test_visible_object_target_is_not_routed_to_basic_reach_target() -> None:
    skill = SkillCatalog.default().select(
        observation=field_observation(),
        task=visible_object_target(),
    )

    assert isinstance(skill, InteractVisibleObjectSkill)


def test_skill_catalog_does_not_import_memory_registry() -> None:
    sys.modules.pop("fh_agent.memory.skill_registry", None)

    catalog = SkillCatalog.default()

    assert catalog.list()
    assert "fh_agent.memory.skill_registry" not in sys.modules
