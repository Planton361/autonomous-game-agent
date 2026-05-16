from typing import Any

import gymnasium as gym
from gymnasium import spaces

from fh_agent.rl.replay_buffer import ReplayBuffer, ReplayTransition

ACTION_NAMES: dict[int, str] = {
    0: "move_up",
    1: "move_down",
    2: "move_left",
    3: "move_right",
    4: "wait",
}

Observation = dict[str, int]
GridPosition = tuple[int, int]


class SyntheticReachTargetEnv(gym.Env[Observation, int]):
    """Deterministic synthetic grid task for RL plumbing tests."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        width: int = 5,
        height: int = 5,
        start_position: GridPosition = (0, 0),
        target_position: GridPosition = (4, 4),
        max_steps: int = 25,
        step_cost: float = -0.01,
        goal_reward: float = 1.0,
    ) -> None:
        super().__init__()
        if width <= 0:
            raise ValueError("width must be greater than zero")
        if height <= 0:
            raise ValueError("height must be greater than zero")
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")

        self.width = width
        self.height = height
        self.start_position = self._validate_position(start_position, name="start_position")
        self.target_position = self._validate_position(target_position, name="target_position")
        self.max_steps = max_steps
        self.step_cost = step_cost
        self.goal_reward = goal_reward

        self.action_space = spaces.Discrete(len(ACTION_NAMES))
        self.observation_space = spaces.Dict(
            {
                "agent_x": spaces.Discrete(width),
                "agent_y": spaces.Discrete(height),
                "target_x": spaces.Discrete(width),
                "target_y": spaces.Discrete(height),
                "step_count": spaces.Discrete(max_steps + 1),
            }
        )
        self.agent_position = self.start_position
        self.step_count = 0

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[Observation, dict[str, Any]]:
        super().reset(seed=seed)
        if options is not None and options:
            raise ValueError("SyntheticReachTargetEnv does not accept reset options")
        self.agent_position = self.start_position
        self.step_count = 0
        return self._observation(), self._info()

    def step(self, action: int) -> tuple[Observation, float, bool, bool, dict[str, Any]]:
        if not self.action_space.contains(action):
            raise ValueError(f"invalid action: {action}")

        self.agent_position = self._next_position(action)
        self.step_count += 1

        terminated = self.agent_position == self.target_position
        truncated = not terminated and self.step_count >= self.max_steps
        reward = self.goal_reward if terminated else self.step_cost
        return self._observation(), reward, terminated, truncated, self._info()

    def task(self) -> dict[str, Any]:
        target_x, target_y = self.target_position
        return {
            "task_type": "reach_target",
            "target": {"x": target_x, "y": target_y},
        }

    def _validate_position(self, position: GridPosition, *, name: str) -> GridPosition:
        x, y = position
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ValueError(f"{name} must be inside the grid")
        return position

    def _next_position(self, action: int) -> GridPosition:
        x, y = self.agent_position
        if action == 0:
            y -= 1
        elif action == 1:
            y += 1
        elif action == 2:
            x -= 1
        elif action == 3:
            x += 1
        return min(max(x, 0), self.width - 1), min(max(y, 0), self.height - 1)

    def _observation(self) -> Observation:
        agent_x, agent_y = self.agent_position
        target_x, target_y = self.target_position
        return {
            "agent_x": agent_x,
            "agent_y": agent_y,
            "target_x": target_x,
            "target_y": target_y,
            "step_count": self.step_count,
        }

    def _info(self) -> dict[str, Any]:
        return {"task": self.task()}


class ReplayRecordingWrapper(gym.Wrapper[Observation, int, Observation, int]):
    """Record synthetic env steps into a ReplayBuffer."""

    def __init__(self, env: SyntheticReachTargetEnv, replay_buffer: ReplayBuffer) -> None:
        super().__init__(env)
        self.replay_buffer = replay_buffer
        self._last_obs: Observation | None = None

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[Observation, dict[str, Any]]:
        obs, info = self.env.reset(seed=seed, options=options)
        self._last_obs = dict(obs)
        return obs, info

    def step(self, action: int) -> tuple[Observation, float, bool, bool, dict[str, Any]]:
        if self._last_obs is None:
            raise RuntimeError("reset must be called before step")

        previous_obs = dict(self._last_obs)
        obs, reward, terminated, truncated, info = self.env.step(action)
        self._last_obs = dict(obs)

        self.replay_buffer.add(
            ReplayTransition(
                obs=previous_obs,
                action=ACTION_NAMES[int(action)],
                reward=reward,
                next_obs=dict(obs),
                done=terminated or truncated,
                task=dict(info["task"]),
            )
        )
        return obs, reward, terminated, truncated, info
