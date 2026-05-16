import ast
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.rl import (
    ReplayTransition,
    extract_achieved_goal,
    recompute_reach_target_reward,
    relabel_episode_with_future_goals,
)


def make_transition(
    index: int,
    *,
    agent_x: int,
    agent_y: int,
    next_x: int,
    next_y: int,
) -> ReplayTransition:
    return ReplayTransition(
        obs={
            "agent_x": agent_x,
            "agent_y": agent_y,
            "target_x": 9,
            "target_y": 9,
            "step_count": index,
        },
        action="move_right",
        reward=-0.01,
        next_obs={
            "agent_x": next_x,
            "agent_y": next_y,
            "target_x": 9,
            "target_y": 9,
            "step_count": index + 1,
        },
        done=False,
        task={"task_type": "reach_target", "target": {"x": 9, "y": 9}},
        metadata={"transition_id": f"source_{index}", "run_id": "synthetic_run"},
    )


def make_episode() -> list[ReplayTransition]:
    return [
        make_transition(0, agent_x=0, agent_y=0, next_x=1, next_y=0),
        make_transition(1, agent_x=1, agent_y=0, next_x=2, next_y=0),
        make_transition(2, agent_x=2, agent_y=0, next_x=2, next_y=1),
    ]


def test_extract_achieved_goal_reads_agent_position() -> None:
    assert extract_achieved_goal({"agent_x": 3, "agent_y": 4, "step_count": 2}) == {
        "x": 3,
        "y": 4,
    }


@pytest.mark.parametrize(
    "obs",
    [
        {"agent_y": 4},
        {"agent_x": 3},
        {"agent_x": "3", "agent_y": 4},
        {"agent_x": 3, "agent_y": 4.0},
        {"agent_x": True, "agent_y": 4},
    ],
)
def test_extract_achieved_goal_rejects_missing_or_non_int_fields(obs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        extract_achieved_goal(obs)


def test_recompute_reach_target_reward_returns_success_reward_and_done() -> None:
    reward, done = recompute_reach_target_reward(
        {"agent_x": 2, "agent_y": 1},
        {"x": 2, "y": 1},
    )

    assert reward == 1.0
    assert done is True


def test_recompute_reach_target_reward_returns_step_cost_when_not_done() -> None:
    reward, done = recompute_reach_target_reward(
        {"agent_x": 1, "agent_y": 1},
        {"x": 2, "y": 1},
        step_cost=-0.2,
        success_reward=2.0,
    )

    assert reward == -0.2
    assert done is False


def test_relabel_episode_with_future_goals_creates_new_transitions() -> None:
    episode = make_episode()

    relabeled = relabel_episode_with_future_goals(episode, seed=1)

    assert len(relabeled) == len(episode)
    assert all(
        new_transition is not source
        for new_transition, source in zip(relabeled, episode, strict=True)
    )
    assert all(isinstance(new_transition, ReplayTransition) for new_transition in relabeled)


def test_relabel_episode_does_not_mutate_original_transitions() -> None:
    episode = make_episode()
    original_dump = deepcopy([transition.model_dump() for transition in episode])

    relabel_episode_with_future_goals(episode, seed=1)

    assert [transition.model_dump() for transition in episode] == original_dump


def test_relabel_episode_updates_observations_task_reward_and_done() -> None:
    episode = make_episode()

    relabeled = relabel_episode_with_future_goals(episode, seed=0)
    first = relabeled[0]

    assert first.obs["target_x"] == 2
    assert first.obs["target_y"] == 0
    assert first.next_obs["target_x"] == 2
    assert first.next_obs["target_y"] == 0
    assert first.task == {
        "task_type": "reach_target",
        "target": {"x": 2, "y": 0},
        "relabeling": "future_achieved_goal",
    }
    assert first.reward == -0.01
    assert first.done is False

    final = relabeled[2]
    assert final.task["target"] == {"x": 2, "y": 1}
    assert final.reward == 1.0
    assert final.done is True


def test_relabel_episode_is_deterministic_with_same_seed() -> None:
    episode = make_episode()

    first = relabel_episode_with_future_goals(episode, relabels_per_transition=2, seed=99)
    second = relabel_episode_with_future_goals(episode, relabels_per_transition=2, seed=99)

    assert [transition.model_dump() for transition in first] == [
        transition.model_dump() for transition in second
    ]


def test_relabel_episode_handles_empty_and_single_step_episodes() -> None:
    assert relabel_episode_with_future_goals([], seed=1) == []

    single = [make_transition(0, agent_x=0, agent_y=0, next_x=1, next_y=0)]
    relabeled = relabel_episode_with_future_goals(single, seed=1)

    assert len(relabeled) == 1
    assert relabeled[0].task["target"] == {"x": 1, "y": 0}
    assert relabeled[0].reward == 1.0
    assert relabeled[0].done is True


def test_relabel_episode_rejects_invalid_relabel_count() -> None:
    with pytest.raises(ValueError, match="relabels_per_transition"):
        relabel_episode_with_future_goals(make_episode(), relabels_per_transition=-1)


def test_hidden_state_keys_are_still_blocked_by_replay_transition() -> None:
    with pytest.raises(ValidationError, match="event_name"):
        ReplayTransition(
            obs={"agent_x": 0, "agent_y": 0},
            action="wait",
            reward=0.0,
            next_obs={"agent_x": 0, "agent_y": 0},
            done=False,
            task={"task_type": "reach_target", "target": {"x": 0, "y": 0}},
            metadata={"event_name": "blocked"},
        )


def test_her_relabel_has_no_architecture_layer_or_gym_imports() -> None:
    source_path = Path("src/fh_agent/rl/her_relabel.py")
    tree = ast.parse(source_path.read_text())
    forbidden_imports = {
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.body",
        "fh_agent.perception",
        "gymnasium",
        "stable_baselines3",
    }

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    assert not {
        module
        for module in imported_modules
        if any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for forbidden in forbidden_imports
        )
    }
