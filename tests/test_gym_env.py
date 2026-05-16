import ast
from pathlib import Path

import pytest

from fh_agent.rl import ReplayBuffer, ReplayRecordingWrapper, SyntheticReachTargetEnv


def test_reset_returns_observation_and_info() -> None:
    env = SyntheticReachTargetEnv(start_position=(1, 2), target_position=(3, 4))

    obs, info = env.reset()

    assert obs == {
        "agent_x": 1,
        "agent_y": 2,
        "target_x": 3,
        "target_y": 4,
        "step_count": 0,
    }
    assert info == {"task": {"task_type": "reach_target", "target": {"x": 3, "y": 4}}}
    assert env.observation_space.contains(obs)


def test_step_moves_agent_and_clips_to_grid_boundaries() -> None:
    env = SyntheticReachTargetEnv(width=3, height=3, start_position=(0, 0), target_position=(2, 2))
    env.reset()

    obs, reward, terminated, truncated, _info = env.step(0)

    assert obs["agent_x"] == 0
    assert obs["agent_y"] == 0
    assert reward == -0.01
    assert terminated is False
    assert truncated is False

    obs, _reward, _terminated, _truncated, _info = env.step(3)
    assert obs["agent_x"] == 1
    assert obs["agent_y"] == 0

    obs, _reward, _terminated, _truncated, _info = env.step(1)
    assert obs["agent_x"] == 1
    assert obs["agent_y"] == 1


def test_target_reach_terminates_episode() -> None:
    env = SyntheticReachTargetEnv(width=2, height=1, start_position=(0, 0), target_position=(1, 0))
    env.reset()

    obs, reward, terminated, truncated, _info = env.step(3)

    assert obs["agent_x"] == 1
    assert reward == 1.0
    assert terminated is True
    assert truncated is False


def test_max_steps_truncates_episode() -> None:
    env = SyntheticReachTargetEnv(
        width=3,
        height=3,
        start_position=(0, 0),
        target_position=(2, 2),
        max_steps=1,
    )
    env.reset()

    _obs, _reward, terminated, truncated, _info = env.step(4)

    assert terminated is False
    assert truncated is True


def test_reset_with_same_seed_is_deterministic() -> None:
    env = SyntheticReachTargetEnv(start_position=(2, 1), target_position=(4, 3))

    first_obs, first_info = env.reset(seed=123)
    env.step(0)
    second_obs, second_info = env.reset(seed=123)

    assert first_obs == second_obs
    assert first_info == second_info


def test_invalid_action_raises_value_error() -> None:
    env = SyntheticReachTargetEnv()
    env.reset()

    with pytest.raises(ValueError, match="invalid action"):
        env.step(99)


def test_replay_recording_wrapper_records_one_transition_per_step() -> None:
    replay_buffer = ReplayBuffer(capacity=10)
    env = ReplayRecordingWrapper(
        SyntheticReachTargetEnv(width=2, height=1, start_position=(0, 0), target_position=(1, 0)),
        replay_buffer,
    )
    env.reset()

    obs, reward, terminated, truncated, _info = env.step(3)

    assert obs["agent_x"] == 1
    assert reward == 1.0
    assert terminated is True
    assert truncated is False
    assert len(replay_buffer) == 1

    transition = replay_buffer.list_transitions()[0]
    assert transition.obs == {
        "agent_x": 0,
        "agent_y": 0,
        "target_x": 1,
        "target_y": 0,
        "step_count": 0,
    }
    assert transition.action == "move_right"
    assert transition.reward == 1.0
    assert transition.next_obs == {
        "agent_x": 1,
        "agent_y": 0,
        "target_x": 1,
        "target_y": 0,
        "step_count": 1,
    }
    assert transition.done is True
    assert transition.task == {"task_type": "reach_target", "target": {"x": 1, "y": 0}}


def test_replay_recording_wrapper_marks_truncated_transition_done() -> None:
    replay_buffer = ReplayBuffer(capacity=10)
    env = ReplayRecordingWrapper(
        SyntheticReachTargetEnv(
            width=3,
            height=3,
            start_position=(0, 0),
            target_position=(2, 2),
            max_steps=1,
        ),
        replay_buffer,
    )
    env.reset()

    _obs, _reward, terminated, truncated, _info = env.step(4)

    assert terminated is False
    assert truncated is True
    assert replay_buffer.list_transitions()[0].done is True


def test_replay_recording_wrapper_requires_reset_before_step() -> None:
    replay_buffer = ReplayBuffer(capacity=10)
    env = ReplayRecordingWrapper(SyntheticReachTargetEnv(), replay_buffer)

    with pytest.raises(RuntimeError, match="reset"):
        env.step(4)


def test_gym_env_has_no_architecture_layer_imports() -> None:
    source_path = Path("src/fh_agent/rl/gym_env.py")
    tree = ast.parse(source_path.read_text())
    forbidden_imports = {
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.body",
        "fh_agent.perception",
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
