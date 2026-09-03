from collections.abc import Mapping, Sequence
from importlib import resources
from typing import Any

from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.planner.context import CortexContext, build_plan_context, build_post_mortem_context
from fh_agent.planner.llm_client import LLMClient
from fh_agent.planner.planner_output import (
    PlannerOutput,
    PlannerOutputError,
    PostMortemOutput,
    parse_planner_output_json,
    parse_post_mortem_output_json,
)
from fh_agent.skill_capabilities import (
    DEFAULT_RUNTIME_SKILLS,
    SkillCapabilityContract,
    UniversalSkillName,
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
        *,
        available_skills: Sequence[UniversalSkillName] | None = None,
    ) -> PlannerOutput:
        runtime_skills = DEFAULT_RUNTIME_SKILLS
        call_skills = tuple(available_skills) if available_skills is not None else runtime_skills
        unavailable_call_skills = sorted(set(call_skills) - set(runtime_skills))
        if unavailable_call_skills:
            joined = ", ".join(unavailable_call_skills)
            msg = f"planning context contains skills unavailable from SkillCatalog: {joined}"
            raise PlannerOutputError(msg)

        capabilities = SkillCapabilityContract(available_skills=call_skills)
        context = build_plan_context(
            observation,
            memory_summary,
            allowed_skills=capabilities.available_skills,
        )
        messages = build_plan_next_goal_messages(context)
        raw_output = self.llm_client.complete(messages)
        output = parse_planner_output_json(raw_output)
        _validate_planner_output_evidence_scope(output, context)
        if output.selected_skill not in context.allowed_skills:
            msg = (
                f"planner selected skill unavailable in this CortexContext: {output.selected_skill}"
            )
            raise PlannerOutputError(msg)
        return output

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


def _context_evidence_ids(context: CortexContext) -> frozenset[str]:
    """Return non-empty evidence IDs explicitly present in one CortexContext."""

    evidence_ids: set[str] = set()
    observation_evidence = context.observation_summary.get("evidence_ids", [])
    if isinstance(observation_evidence, Sequence) and not isinstance(
        observation_evidence, str | bytes | bytearray
    ):
        evidence_ids.update(
            evidence_id
            for evidence_id in observation_evidence
            if isinstance(evidence_id, str) and evidence_id
        )

    for note in (
        *context.evidence_backed_facts,
        *context.hypotheses,
        *context.recent_skill_outcomes,
    ):
        evidence_ids.update(evidence_id for evidence_id in note.evidence_ids if evidence_id)
    return frozenset(evidence_ids)


def _planner_output_evidence_ids(output: PlannerOutput) -> frozenset[str]:
    """Return non-empty evidence IDs cited by a proposed planning output."""

    evidence_ids = {
        evidence_id
        for claim in output.current_belief_state
        for evidence_id in claim.evidence_ids
        if evidence_id
    }
    evidence_ids.update(
        evidence_id
        for update in output.memory_updates_requested
        for evidence_id in update.evidence_ids
        if evidence_id
    )
    return frozenset(evidence_ids)


def _validate_planner_output_evidence_scope(
    output: PlannerOutput,
    context: CortexContext,
) -> None:
    """Reject output that cites evidence absent from the supplied context."""

    outside_context = sorted(_planner_output_evidence_ids(output) - _context_evidence_ids(context))
    if outside_context:
        msg = "planner output references evidence outside CortexContext: " + ", ".join(
            outside_context
        )
        raise PlannerOutputError(msg)
