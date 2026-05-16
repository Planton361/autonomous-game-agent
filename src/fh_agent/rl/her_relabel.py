from collections.abc import Mapping, Sequence
from copy import deepcopy
from random import Random
from typing import Any

from fh_agent.rl.replay_buffer import ReplayTransition


def extract_achieved_goal(obs: Mapping[str, Any]) -> dict[str, int]:
    agent_x = _required_int(obs, "agent_x")
    agent_y = _required_int(obs, "agent_y")
    return {"x": agent_x, "y": agent_y}


def recompute_reach_target_reward(
    next_obs: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    step_cost: float = -0.01,
    success_reward: float = 1.0,
) -> tuple[float, bool]:
    agent_x = _required_int(next_obs, "agent_x")
    agent_y = _required_int(next_obs, "agent_y")
    target_x = _required_int(target, "x")
    target_y = _required_int(target, "y")

    done = agent_x == target_x and agent_y == target_y
    return (success_reward if done else step_cost), done


def relabel_episode_with_future_goals(
    transitions: Sequence[ReplayTransition],
    *,
    relabels_per_transition: int = 1,
    seed: int | None = None,
) -> list[ReplayTransition]:
    if relabels_per_transition < 0:
        raise ValueError("relabels_per_transition must be greater than or equal to zero")
    if not transitions or relabels_per_transition == 0:
        return []

    rng = Random(seed)
    relabeled: list[ReplayTransition] = []
    for source_index, transition in enumerate(transitions):
        if not isinstance(transition, ReplayTransition):
            raise TypeError("transitions must contain ReplayTransition objects")

        for relabel_index in range(relabels_per_transition):
            future_index = rng.randint(source_index, len(transitions) - 1)
            future_transition = transitions[future_index]
            achieved_goal = extract_achieved_goal(future_transition.next_obs)
            obs = deepcopy(transition.obs)
            next_obs = deepcopy(transition.next_obs)
            task = deepcopy(transition.task)

            obs["target_x"] = achieved_goal["x"]
            obs["target_y"] = achieved_goal["y"]
            next_obs["target_x"] = achieved_goal["x"]
            next_obs["target_y"] = achieved_goal["y"]
            task["task_type"] = "reach_target"
            task["target"] = {"x": achieved_goal["x"], "y": achieved_goal["y"]}
            task["relabeling"] = "future_achieved_goal"

            reward, done = recompute_reach_target_reward(next_obs, achieved_goal)
            source_transition_id = _source_transition_id(transition, source_index)
            relabeled.append(
                ReplayTransition(
                    obs=obs,
                    action=transition.action,
                    reward=reward,
                    next_obs=next_obs,
                    done=done,
                    task=task,
                    metadata={
                        "her_relabel": True,
                        "transition_id": f"her_{source_transition_id}_{relabel_index}",
                        "source_transition_id": source_transition_id,
                        "source_index": source_index,
                        "future_index": future_index,
                    },
                )
            )

    return relabeled


def _required_int(values: Mapping[str, Any], key: str) -> int:
    if key not in values:
        raise ValueError(f"missing required field: {key}")
    value = values[key]
    if type(value) is not int:
        raise ValueError(f"field must be int: {key}")
    return value


def _source_transition_id(transition: ReplayTransition, source_index: int) -> str:
    if transition.metadata is None:
        return f"transition_{source_index}"
    transition_id = transition.metadata.get("transition_id")
    if isinstance(transition_id, str) and transition_id:
        return transition_id
    return f"transition_{source_index}"
