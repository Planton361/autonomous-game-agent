import ast
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.rl import (
    ACTION_TO_INDEX,
    INDEX_TO_ACTION,
    BehaviorCloningExample,
    ReplayTransition,
    build_behavior_cloning_dataset,
    extract_reach_target_features,
    transition_to_behavior_cloning_example,
)


def make_transition(
    index: int,
    *,
    action: str = "move_right",
    reward: float = -0.01,
) -> ReplayTransition:
    return ReplayTransition(
        obs={
            "agent_x": index,
            "agent_y": 1,
            "target_x": 4,
            "target_y": 3,
            "step_count": index,
        },
        action=action,
        reward=reward,
        next_obs={
            "agent_x": index + 1,
            "agent_y": 1,
            "target_x": 4,
            "target_y": 3,
            "step_count": index + 1,
        },
        done=reward > 0,
        task={"task_type": "reach_target", "target": {"x": 4, "y": 3}},
        metadata={"transition_id": f"transition_{index}", "run_id": "synthetic_run"},
    )


def test_action_mapping_is_deterministic_and_invertible() -> None:
    assert ACTION_TO_INDEX == {
        "move_up": 0,
        "move_down": 1,
        "move_left": 2,
        "move_right": 3,
        "wait": 4,
    }
    assert INDEX_TO_ACTION == {
        0: "move_up",
        1: "move_down",
        2: "move_left",
        3: "move_right",
        4: "wait",
    }


def test_extract_reach_target_features_uses_exact_feature_order() -> None:
    features = extract_reach_target_features(
        {
            "agent_x": 1,
            "agent_y": 2,
            "target_x": 4,
            "target_y": 5,
            "step_count": 7,
        }
    )

    assert features == (1.0, 2.0, 4.0, 5.0, 3.0, 3.0, 7.0)


@pytest.mark.parametrize(
    "obs",
    [
        {"agent_y": 2, "target_x": 4, "target_y": 5, "step_count": 7},
        {"agent_x": 1, "target_x": 4, "target_y": 5, "step_count": 7},
        {"agent_x": 1, "agent_y": 2, "target_y": 5, "step_count": 7},
        {"agent_x": 1, "agent_y": 2, "target_x": 4, "step_count": 7},
        {"agent_x": 1, "agent_y": 2, "target_x": 4, "target_y": 5},
        {"agent_x": "1", "agent_y": 2, "target_x": 4, "target_y": 5, "step_count": 7},
        {"agent_x": True, "agent_y": 2, "target_x": 4, "target_y": 5, "step_count": 7},
    ],
)
def test_extract_reach_target_features_rejects_missing_or_non_numeric_fields(
    obs: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        extract_reach_target_features(obs)


def test_transition_to_behavior_cloning_example_maps_action_and_metadata() -> None:
    transition = make_transition(2, action="move_left", reward=1.0)

    example = transition_to_behavior_cloning_example(transition)

    assert example.features == (2.0, 1.0, 4.0, 3.0, 2.0, 2.0, 2.0)
    assert example.action_index == 2
    assert example.action_label == "move_left"
    assert example.weight == 1.0
    assert example.source_transition_id == "transition_2"
    assert example.metadata == {"task_type": "reach_target", "reward": 1.0, "done": True}


def test_transition_to_behavior_cloning_example_preserves_transition() -> None:
    transition = make_transition(1)
    original = deepcopy(transition.model_dump())

    transition_to_behavior_cloning_example(transition, weight=2.0)

    assert transition.model_dump() == original


def test_transition_to_behavior_cloning_example_rejects_invalid_action() -> None:
    transition = make_transition(1, action="open_menu")

    with pytest.raises(ValueError, match="unsupported action"):
        transition_to_behavior_cloning_example(transition)


def test_build_behavior_cloning_dataset_preserves_input_order() -> None:
    transitions = [
        make_transition(0, action="move_up"),
        make_transition(1, action="move_down"),
        make_transition(2, action="wait"),
    ]

    dataset = build_behavior_cloning_dataset(transitions)

    assert [example.source_transition_id for example in dataset] == [
        "transition_0",
        "transition_1",
        "transition_2",
    ]
    assert [example.action_label for example in dataset] == ["move_up", "move_down", "wait"]


def test_build_behavior_cloning_dataset_positive_reward_filter() -> None:
    transitions = [
        make_transition(0, reward=-0.01),
        make_transition(1, reward=0.0),
        make_transition(2, reward=1.0),
    ]

    dataset = build_behavior_cloning_dataset(transitions, positive_reward_only=True)

    assert [example.source_transition_id for example in dataset] == ["transition_2"]


def test_build_behavior_cloning_dataset_handles_empty_input() -> None:
    assert build_behavior_cloning_dataset([]) == []


def test_build_behavior_cloning_dataset_rejects_invalid_transition_object() -> None:
    with pytest.raises(ValueError, match="ReplayTransition"):
        build_behavior_cloning_dataset([object()])  # type: ignore[list-item]


def test_behavior_cloning_example_blocks_hidden_state_metadata() -> None:
    with pytest.raises(ValidationError, match="game_switches"):
        BehaviorCloningExample(
            features=(0.0,),
            action_index=4,
            action_label="wait",
            source_transition_id="source",
            metadata={"audit": {"game_switches": {"blocked": True}}},
        )


def test_replay_transition_still_blocks_hidden_state_keys() -> None:
    with pytest.raises(ValidationError, match="enemy_hp"):
        ReplayTransition(
            obs={"agent_x": 0, "agent_y": 0, "target_x": 1, "target_y": 0, "step_count": 0},
            action="wait",
            reward=0.0,
            next_obs={"agent_x": 0, "agent_y": 0, "target_x": 1, "target_y": 0, "step_count": 1},
            done=False,
            task={"task_type": "reach_target", "target": {"x": 1, "y": 0}, "enemy_hp": 10},
        )


def test_behavior_cloning_has_no_architecture_or_training_imports() -> None:
    source_path = Path("src/fh_agent/rl/behavior_cloning.py")
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
        "torch",
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
