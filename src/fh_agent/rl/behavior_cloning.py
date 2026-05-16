from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.rl.replay_buffer import FORBIDDEN_REPLAY_KEYS, ReplayTransition

ACTION_TO_INDEX: dict[str, int] = {
    "move_up": 0,
    "move_down": 1,
    "move_left": 2,
    "move_right": 3,
    "wait": 4,
}
INDEX_TO_ACTION: dict[int, str] = {index: action for action, index in ACTION_TO_INDEX.items()}


class BehaviorCloningExample(BaseModel):
    """One supervised example derived from synthetic replay data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    features: tuple[float, ...]
    action_index: int
    action_label: str
    weight: float = Field(default=1.0, gt=0.0)
    source_transition_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_hidden_state_metadata(self) -> "BehaviorCloningExample":
        _reject_forbidden_metadata_keys(self.metadata, path="metadata")
        return self


def extract_reach_target_features(obs: Mapping[str, Any]) -> tuple[float, ...]:
    agent_x = _required_number(obs, "agent_x")
    agent_y = _required_number(obs, "agent_y")
    target_x = _required_number(obs, "target_x")
    target_y = _required_number(obs, "target_y")
    step_count = _required_number(obs, "step_count")
    dx = target_x - agent_x
    dy = target_y - agent_y
    return (agent_x, agent_y, target_x, target_y, dx, dy, step_count)


def transition_to_behavior_cloning_example(
    transition: ReplayTransition,
    *,
    weight: float = 1.0,
) -> BehaviorCloningExample:
    if not isinstance(transition, ReplayTransition):
        raise ValueError("transition must be a ReplayTransition")
    if transition.action not in ACTION_TO_INDEX:
        raise ValueError(f"unsupported action for behavior cloning: {transition.action}")

    return BehaviorCloningExample(
        features=extract_reach_target_features(transition.obs),
        action_index=ACTION_TO_INDEX[transition.action],
        action_label=transition.action,
        weight=weight,
        source_transition_id=_source_transition_id(transition),
        metadata={
            "task_type": transition.task.get("task_type", "unknown"),
            "reward": transition.reward,
            "done": transition.done,
        },
    )


def build_behavior_cloning_dataset(
    transitions: Sequence[ReplayTransition],
    *,
    positive_reward_only: bool = False,
) -> list[BehaviorCloningExample]:
    examples: list[BehaviorCloningExample] = []
    for transition in transitions:
        if not isinstance(transition, ReplayTransition):
            raise ValueError("transitions must contain ReplayTransition objects")
        if positive_reward_only and transition.reward <= 0:
            continue
        examples.append(transition_to_behavior_cloning_example(transition))
    return examples


def _required_number(values: Mapping[str, Any], key: str) -> float:
    if key not in values:
        raise ValueError(f"missing required field: {key}")
    value = values[key]
    if type(value) not in (int, float):
        raise ValueError(f"field must be numeric: {key}")
    return float(value)


def _source_transition_id(transition: ReplayTransition) -> str:
    if transition.metadata is None:
        return "unknown"
    transition_id = transition.metadata.get("transition_id")
    if isinstance(transition_id, str) and transition_id:
        return transition_id
    return "unknown"


def _reject_forbidden_metadata_keys(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_name = str(key)
            nested_path = f"{path}.{key_name}"
            if key_name in FORBIDDEN_REPLAY_KEYS:
                raise ValueError(f"forbidden behavior cloning metadata key: {nested_path}")
            _reject_forbidden_metadata_keys(nested_value, path=nested_path)
        return

    if isinstance(value, list | tuple):
        for index, nested_value in enumerate(value):
            _reject_forbidden_metadata_keys(nested_value, path=f"{path}[{index}]")
