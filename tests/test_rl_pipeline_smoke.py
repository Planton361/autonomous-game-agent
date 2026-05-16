import ast
from copy import deepcopy
from pathlib import Path
from typing import Any

from fh_agent.rl import (
    ACTION_TO_INDEX,
    FORBIDDEN_REPLAY_KEYS,
    ReplayBuffer,
    ReplayRecordingWrapper,
    ReplayTransition,
    SyntheticReachTargetEnv,
    build_behavior_cloning_dataset,
    relabel_episode_with_future_goals,
)

ACTION_SEQUENCE = [3, 3, 1]


def run_synthetic_pipeline(*, seed: int) -> dict[str, Any]:
    replay_buffer = ReplayBuffer(capacity=16)
    env = ReplayRecordingWrapper(
        SyntheticReachTargetEnv(
            width=4,
            height=4,
            start_position=(0, 0),
            target_position=(2, 1),
            max_steps=8,
        ),
        replay_buffer,
    )
    env.reset(seed=seed)

    for action in ACTION_SEQUENCE:
        _obs, _reward, terminated, truncated, _info = env.step(action)
        if terminated or truncated:
            break

    transitions = replay_buffer.list_transitions()
    original_dump = deepcopy([transition.model_dump() for transition in transitions])
    her_transitions = relabel_episode_with_future_goals(transitions, seed=seed)
    dataset = build_behavior_cloning_dataset([*transitions, *her_transitions])
    positive_dataset = build_behavior_cloning_dataset(
        [*transitions, *her_transitions],
        positive_reward_only=True,
    )
    return {
        "transitions": transitions,
        "original_dump": original_dump,
        "her_transitions": her_transitions,
        "dataset": dataset,
        "positive_dataset": positive_dataset,
    }


def test_synthetic_reach_target_replay_her_bc_pipeline_smoke() -> None:
    pipeline = run_synthetic_pipeline(seed=123)
    transitions: list[ReplayTransition] = pipeline["transitions"]
    her_transitions: list[ReplayTransition] = pipeline["her_transitions"]

    assert len(transitions) == len(ACTION_SEQUENCE)
    assert any(transition.done for transition in transitions)
    for transition in transitions:
        assert transition.obs
        assert transition.action
        assert isinstance(transition.reward, float)
        assert transition.next_obs
        assert isinstance(transition.done, bool)
        assert transition.task
        assert_no_forbidden_keys(transition.model_dump())

    assert her_transitions
    assert all(
        her_transition is not source
        for her_transition, source in zip(her_transitions, transitions, strict=True)
    )
    assert [transition.model_dump() for transition in transitions] == pipeline["original_dump"]
    for transition in her_transitions:
        assert transition.metadata is not None
        assert transition.metadata["her_relabel"] is True
        assert_no_forbidden_keys(transition.metadata)

    dataset = pipeline["dataset"]
    assert dataset
    for example in dataset:
        assert len(example.features) == 7
        assert example.action_label in ACTION_TO_INDEX
        assert example.action_index == ACTION_TO_INDEX[example.action_label]

    positive_dataset = pipeline["positive_dataset"]
    assert positive_dataset


def test_pipeline_is_deterministic_with_seed() -> None:
    first = run_synthetic_pipeline(seed=123)
    second = run_synthetic_pipeline(seed=123)

    assert transition_actions(first["transitions"]) == transition_actions(second["transitions"])
    assert her_task_targets(first["her_transitions"]) == her_task_targets(second["her_transitions"])
    assert her_rewards_and_done(first["her_transitions"]) == her_rewards_and_done(
        second["her_transitions"]
    )
    assert bc_features_and_actions(first["dataset"]) == bc_features_and_actions(second["dataset"])


def test_pipeline_does_not_import_training_or_live_modules() -> None:
    rl_sources = [
        Path("src/fh_agent/rl/gym_env.py"),
        Path("src/fh_agent/rl/replay_buffer.py"),
        Path("src/fh_agent/rl/her_relabel.py"),
        Path("src/fh_agent/rl/behavior_cloning.py"),
    ]
    forbidden_imports = {
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.body",
        "fh_agent.perception",
        "torch",
        "stable_baselines3",
    }

    imported_modules: set[str] = set()
    for source_path in rl_sources:
        tree = ast.parse(source_path.read_text())
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


def assert_no_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        assert not (set(value) & FORBIDDEN_REPLAY_KEYS)
        for nested_value in value.values():
            assert_no_forbidden_keys(nested_value)
        return

    if isinstance(value, list | tuple):
        for nested_value in value:
            assert_no_forbidden_keys(nested_value)


def transition_actions(transitions: list[ReplayTransition]) -> list[str]:
    return [transition.action for transition in transitions]


def her_task_targets(transitions: list[ReplayTransition]) -> list[dict[str, int]]:
    return [transition.task["target"] for transition in transitions]


def her_rewards_and_done(transitions: list[ReplayTransition]) -> list[tuple[float, bool]]:
    return [(transition.reward, transition.done) for transition in transitions]


def bc_features_and_actions(dataset: list[Any]) -> list[tuple[tuple[float, ...], int]]:
    return [(example.features, example.action_index) for example in dataset]
