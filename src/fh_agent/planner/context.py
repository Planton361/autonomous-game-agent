import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fh_agent.observation.schemas import Observation, SkillResult
from fh_agent.planner.planner_output import (
    ReflectionNote,
    RiskLimit,
    UniversalSkillName,
    find_direct_control_violations,
    find_hidden_state_term_violations,
)

DEFAULT_ALLOWED_SKILLS: tuple[UniversalSkillName, ...] = (
    "continue_dialogue",
    "basic_reach_target",
    "interact_visible",
    "interact_visible_object",
    "safe_reach_target",
)


class CortexContext(BaseModel):
    """Evidence-gated prompt context for planner and reflection calls."""

    model_config = ConfigDict(extra="forbid")

    observation_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_backed_facts: list[ReflectionNote] = Field(default_factory=list)
    hypotheses: list[ReflectionNote] = Field(default_factory=list)
    recent_skill_outcomes: list[ReflectionNote] = Field(default_factory=list)
    allowed_skills: list[UniversalSkillName] = Field(
        default_factory=lambda: list(DEFAULT_ALLOWED_SKILLS)
    )
    risk_constraints: RiskLimit = Field(default_factory=RiskLimit)
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_unsafe_content(cls, data: Any) -> Any:
        control_violations = find_direct_control_violations(data)
        if control_violations:
            joined = ", ".join(control_violations)
            msg = f"cortex context must not contain direct primitive controls: {joined}"
            raise ValueError(msg)

        hidden_state_violations = find_hidden_state_term_violations(data)
        if hidden_state_violations:
            joined = ", ".join(hidden_state_violations)
            msg = f"cortex context must not contain hidden-state terms: {joined}"
            raise ValueError(msg)

        return data

    @model_validator(mode="after")
    def validate_note_statuses(self) -> "CortexContext":
        for note in self.evidence_backed_facts:
            if note.status not in {"observed_fact", "validated_rule"}:
                msg = "evidence_backed_facts must use observed_fact or validated_rule"
                raise ValueError(msg)
        for note in self.hypotheses:
            if note.status != "hypothesis":
                msg = "hypotheses must use hypothesis status"
                raise ValueError(msg)
        return self

    def to_prompt_json(self) -> str:
        """Serialize deterministically for prompt construction."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )


def build_plan_context(
    observation: Observation,
    memory_summary: Mapping[str, Any],
) -> CortexContext:
    """Build validated prompt context from visible observation and supplied memory summary."""

    return CortexContext(
        observation_summary=_summarize_observation(observation),
        evidence_backed_facts=_coerce_reflection_notes(
            memory_summary.get("known_facts", []),
            default_status="observed_fact",
        ),
        hypotheses=_coerce_reflection_notes(
            memory_summary.get("hypotheses", []),
            default_status="hypothesis",
        ),
        recent_skill_outcomes=_coerce_reflection_notes(
            memory_summary.get("recent_skill_outcomes", []),
            default_status="observed_fact",
        ),
        allowed_skills=list(DEFAULT_ALLOWED_SKILLS),
        risk_constraints=_coerce_risk_limit(memory_summary.get("risk_constraints")),
        open_questions=list(cast(Sequence[str], memory_summary.get("open_questions", []))),
    )


def build_post_mortem_context(
    observations: Sequence[Observation],
    *,
    skill_results: Sequence[SkillResult] = (),
    outcome_summary: Mapping[str, Any] | None = None,
) -> CortexContext:
    """Build validated reflection context from visible observations and outcomes."""

    latest_observation = observations[-1] if observations else None
    summary: dict[str, Any] = {
        "observations": [_summarize_observation(observation) for observation in observations],
        "outcome_summary": dict(outcome_summary or {}),
    }
    if latest_observation is not None:
        summary["latest_observation"] = _summarize_observation(latest_observation)

    return CortexContext(
        observation_summary=summary,
        evidence_backed_facts=[],
        hypotheses=_coerce_reflection_notes(
            (outcome_summary or {}).get("hypotheses", []),
            default_status="hypothesis",
        ),
        recent_skill_outcomes=[
            ReflectionNote(
                status="observed_fact",
                note=(
                    f"Skill {skill_result.skill_name} "
                    f"{'succeeded' if skill_result.success else 'failed'}."
                ),
                evidence_ids=skill_result.evidence_ids,
            )
            for skill_result in skill_results
            if skill_result.evidence_ids
        ],
        allowed_skills=list(DEFAULT_ALLOWED_SKILLS),
        risk_constraints=_coerce_risk_limit((outcome_summary or {}).get("risk_constraints")),
        open_questions=list(cast(Sequence[str], (outcome_summary or {}).get("open_questions", []))),
    )


def _summarize_observation(observation: Observation) -> dict[str, Any]:
    return {
        "run_id": observation.run_id,
        "ui_state": observation.ui_state,
        "screenshot_id": observation.screenshot_id,
        "evidence_ids": observation.evidence_ids,
        "visible_message_text": observation.visible_message_text,
        "visible_menu_items": observation.visible_menu_items,
        "player_screen_position": observation.player_screen_position,
        "visible_sprite_screen_positions": observation.visible_sprite_screen_positions,
        "visible_sprite_visual_hashes": observation.visible_sprite_visual_hashes,
    }


def _coerce_reflection_notes(
    raw_notes: object,
    *,
    default_status: str,
) -> list[ReflectionNote]:
    notes: list[ReflectionNote] = []
    if not isinstance(raw_notes, Sequence) or isinstance(raw_notes, str | bytes | bytearray):
        return notes

    for raw_note in raw_notes:
        if isinstance(raw_note, ReflectionNote):
            notes.append(raw_note)
        elif isinstance(raw_note, Mapping):
            payload = dict(raw_note)
            payload.setdefault("status", default_status)
            if "note" not in payload and "claim" in payload:
                payload["note"] = payload["claim"]
            payload.pop("claim", None)
            notes.append(ReflectionNote.model_validate(payload))
        elif isinstance(raw_note, str):
            notes.append(ReflectionNote(status=default_status, note=raw_note, evidence_ids=[]))

    return notes


def _coerce_risk_limit(raw_risk_limit: object) -> RiskLimit:
    if isinstance(raw_risk_limit, RiskLimit):
        return raw_risk_limit
    if isinstance(raw_risk_limit, Mapping):
        return RiskLimit.model_validate(dict(raw_risk_limit))
    return RiskLimit()
