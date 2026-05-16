from collections.abc import Mapping, Sequence
from importlib import resources
from typing import Any

from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.planner.context import CortexContext, build_plan_context, build_post_mortem_context
from fh_agent.planner.llm_client import LLMClient
from fh_agent.planner.planner_output import (
    PlannerOutput,
    PostMortemOutput,
    parse_planner_output_json,
    parse_post_mortem_output_json,
)

PROMPT_PACKAGE = "fh_agent.planner.prompts"


class Cortex:
    """Local planner boundary that validates structured LLM output."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def plan_next_goal(
        self,
        observation: Observation,
        memory_summary: Mapping[str, Any],
    ) -> PlannerOutput:
        context = build_plan_context(observation, memory_summary)
        messages = build_plan_next_goal_messages(context)
        raw_output = self.llm_client.complete(messages)
        return parse_planner_output_json(raw_output)

    def post_mortem(
        self,
        observations: Sequence[Observation],
        *,
        skill_results: Sequence[SkillResult] = (),
        outcome_summary: Mapping[str, Any] | None = None,
    ) -> PostMortemOutput:
        context = build_post_mortem_context(
            observations,
            skill_results=skill_results,
            outcome_summary=outcome_summary or {},
        )
        messages = build_post_mortem_messages(context)
        raw_output = self.llm_client.complete(messages)
        return parse_post_mortem_output_json(raw_output)


def build_plan_next_goal_messages(
    context_or_observation: CortexContext | Observation,
    memory_summary: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a no-spoiler prompt from validated CortexContext."""

    context = (
        context_or_observation
        if isinstance(context_or_observation, CortexContext)
        else build_plan_context(context_or_observation, memory_summary or {})
    )
    return [
        {"role": "system", "content": load_prompt("system_no_spoiler.md")},
        {
            "role": "user",
            "content": load_prompt("plan_next_goal.md")
            + "\n\nCortexContext JSON:\n"
            + context.to_prompt_json(),
        },
    ]


def build_post_mortem_messages(
    context_or_observations: CortexContext | Sequence[Observation],
    *,
    skill_results: Sequence[SkillResult] = (),
    outcome_summary: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build a no-spoiler reflection prompt from validated CortexContext."""

    context = (
        context_or_observations
        if isinstance(context_or_observations, CortexContext)
        else build_post_mortem_context(
            context_or_observations,
            skill_results=skill_results,
            outcome_summary=outcome_summary or {},
        )
    )
    return [
        {"role": "system", "content": load_prompt("system_no_spoiler.md")},
        {
            "role": "user",
            "content": load_prompt("post_mortem.md")
            + "\n\nCortexContext JSON:\n"
            + context.to_prompt_json(),
        },
    ]


def load_prompt(filename: str) -> str:
    return resources.files(PROMPT_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
