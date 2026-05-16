from collections import deque
from collections.abc import Iterable, Mapping
from random import Random
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

FORBIDDEN_REPLAY_KEYS: frozenset[str] = frozenset(
    {
        "map_id",
        "event_name",
        "game_switches",
        "game_variables",
        "enemy_hp",
        "enemy_database",
        "savegame_variables",
        "ending_flags",
    }
)


class ReplayTransition(BaseModel):
    """One synthetic replay transition for later RL experiments."""

    model_config = ConfigDict(extra="forbid")

    obs: dict[str, Any]
    action: str
    reward: float
    next_obs: dict[str, Any]
    done: bool
    task: dict[str, Any]
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_hidden_state_keys(self) -> "ReplayTransition":
        for field_name in ("obs", "next_obs", "task", "metadata"):
            value = getattr(self, field_name)
            if value is not None:
                _reject_forbidden_keys(value, path=field_name)
        return self


class ReplayBuffer:
    """Fixed-capacity FIFO replay buffer for synthetic transitions."""

    def __init__(self, *, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")
        self.capacity = capacity
        self._transitions: deque[ReplayTransition] = deque(maxlen=capacity)

    def add(self, transition: ReplayTransition) -> None:
        if not isinstance(transition, ReplayTransition):
            raise TypeError("transition must be a ReplayTransition")
        self._transitions.append(transition)

    def extend(self, transitions: Iterable[ReplayTransition]) -> None:
        for transition in transitions:
            self.add(transition)

    def sample(self, count: int, *, seed: int | None = None) -> list[ReplayTransition]:
        if count < 0:
            raise ValueError("count must be greater than or equal to zero")
        if count > len(self._transitions):
            raise ValueError("count cannot exceed the number of stored transitions")
        return Random(seed).sample(list(self._transitions), count)

    def list_transitions(self) -> list[ReplayTransition]:
        return list(self._transitions)

    def __len__(self) -> int:
        return len(self._transitions)


def _reject_forbidden_keys(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_name = str(key)
            nested_path = f"{path}.{key_name}"
            if key_name in FORBIDDEN_REPLAY_KEYS:
                raise ValueError(f"forbidden replay key: {nested_path}")
            _reject_forbidden_keys(nested_value, path=nested_path)
        return

    if isinstance(value, list | tuple):
        for index, nested_value in enumerate(value):
            _reject_forbidden_keys(nested_value, path=f"{path}[{index}]")
