import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from fh_agent.rl import FORBIDDEN_REPLAY_KEYS, ReplayBuffer, ReplayTransition


def make_transition(index: int) -> ReplayTransition:
    return ReplayTransition(
        obs={"screen_signature": f"obs-{index}", "player": {"x": index, "y": index + 1}},
        action="move_right_short",
        reward=float(index),
        next_obs={"screen_signature": f"next-{index}"},
        done=False,
        task={"goal": "reach_visible_target", "target": {"x": index + 2, "y": index + 3}},
        metadata={"synthetic_step": index},
    )


def test_replay_transition_stores_required_fields() -> None:
    transition = make_transition(1)

    assert transition.obs["screen_signature"] == "obs-1"
    assert transition.action == "move_right_short"
    assert transition.reward == 1.0
    assert transition.next_obs["screen_signature"] == "next-1"
    assert transition.done is False
    assert transition.task["goal"] == "reach_visible_target"
    assert transition.metadata == {"synthetic_step": 1}


def test_replay_buffer_capacity_is_fifo() -> None:
    buffer = ReplayBuffer(capacity=3)

    buffer.extend(make_transition(index) for index in range(5))

    assert len(buffer) == 3
    assert [transition.obs["screen_signature"] for transition in buffer.list_transitions()] == [
        "obs-2",
        "obs-3",
        "obs-4",
    ]


def test_replay_buffer_sampling_is_deterministic_with_seed() -> None:
    buffer = ReplayBuffer(capacity=10)
    buffer.extend(make_transition(index) for index in range(5))

    first_sample = buffer.sample(3, seed=123)
    second_sample = buffer.sample(3, seed=123)

    assert first_sample == second_sample
    assert [transition.obs["screen_signature"] for transition in first_sample] == [
        "obs-0",
        "obs-2",
        "obs-4",
    ]


def test_replay_buffer_rejects_invalid_capacity_and_sample_counts() -> None:
    with pytest.raises(ValueError, match="capacity"):
        ReplayBuffer(capacity=0)

    buffer = ReplayBuffer(capacity=2)
    buffer.add(make_transition(1))

    with pytest.raises(ValueError, match="count"):
        buffer.sample(-1)
    with pytest.raises(ValueError, match="count"):
        buffer.sample(2)


@pytest.mark.parametrize("field_name", ["obs", "next_obs", "task", "metadata"])
@pytest.mark.parametrize("forbidden_key", sorted(FORBIDDEN_REPLAY_KEYS))
def test_replay_transition_rejects_hidden_state_keys_recursively(
    field_name: str,
    forbidden_key: str,
) -> None:
    kwargs = {
        "obs": {"visible": True},
        "action": "wait",
        "reward": 0.0,
        "next_obs": {"visible": False},
        "done": False,
        "task": {"goal": "synthetic_goal"},
        "metadata": {"synthetic": True},
    }
    kwargs[field_name] = {"outer": [{"inner": {forbidden_key: "blocked"}}]}

    with pytest.raises(ValidationError, match=forbidden_key):
        ReplayTransition(**kwargs)


def test_replay_buffer_has_no_architecture_layer_imports() -> None:
    source_path = Path("src/fh_agent/rl/replay_buffer.py")
    tree = ast.parse(source_path.read_text())
    forbidden_imports = {
        "fh_agent.game",
        "fh_agent.bridge",
        "fh_agent.memory",
        "fh_agent.planner",
        "fh_agent.manager",
        "fh_agent.body",
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
