"""Derive grounding requests from planner intent and current visible evidence."""

from fh_agent.manager.grounding import GroundingRequest
from fh_agent.manager.skill_target_requirements import target_requirement_for_skill
from fh_agent.observation.schemas import Observation
from fh_agent.planner.planner_output import PlannerOutput


def build_grounding_request(
    planner_output: PlannerOutput,
    observation: Observation,
) -> GroundingRequest | None:
    """Build one current-evidence request, or none for a targetless skill."""

    if target_requirement_for_skill(planner_output.selected_skill) == "targetless":
        return None

    evidence_scope_ids = tuple(
        dict.fromkeys(evidence_id for evidence_id in observation.evidence_ids if evidence_id)
    )
    return GroundingRequest(
        selected_skill=planner_output.selected_skill,
        semantic_goal=planner_output.next_goal,
        evidence_scope_ids=evidence_scope_ids,
    )
