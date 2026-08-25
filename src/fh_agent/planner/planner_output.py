from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from fh_agent.skill_capabilities import UniversalSkillName

ClaimKind = Literal["fact", "hypothesis"]
ReflectionNoteStatus = Literal["observed_fact", "validated_rule", "hypothesis"]

FORBIDDEN_CONTROL_FIELDS = frozenset({"keys", "key_sequence", "primitive_actions", "actions"})
PRIMITIVE_ACTION_NAMES = frozenset(
    {
        "move_up_short",
        "move_down_short",
        "move_left_short",
        "move_right_short",
        "confirm",
        "cancel",
        "open_menu",
        "wait",
    }
)
FORBIDDEN_HIDDEN_STATE_TERMS = frozenset(
    {
        "map_id",
        "event_id",
        "event_name",
        "event_comments",
        "event_trigger_conditions",
        "game_switches",
        "game_variables",
        "enemy_database",
        "enemy_hp",
        "enemy_resistances",
        "item_database_effects",
        "ending_flags",
        "savegame_variables",
    }
)


class PlannerOutputError(ValueError):
    """Raised when planner output violates the no-spoiler control contract."""


class EvidenceBackedClaim(BaseModel):
    """A visible-evidence fact or an explicitly non-factual hypothesis."""

    model_config = ConfigDict(extra="forbid")

    kind: ClaimKind
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def facts_require_evidence(self) -> "EvidenceBackedClaim":
        if self.kind == "fact" and not self.evidence_ids:
            msg = "fact claims require at least one evidence_id"
            raise ValueError(msg)
        return self


class MemoryUpdateRequest(BaseModel):
    """Request to persist only evidence-backed planner-derived memory."""

    model_config = ConfigDict(extra="forbid")

    claim: str
    evidence_ids: list[str] = Field(min_length=1)
    reason: str | None = None


class ReflectionNote(BaseModel):
    """Evidence-backed post-mortem note or explicitly marked hypothesis."""

    model_config = ConfigDict(extra="forbid")

    status: ReflectionNoteStatus
    note: str
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def factual_notes_require_evidence(self) -> "ReflectionNote":
        if self.status in {"observed_fact", "validated_rule"} and not self.evidence_ids:
            msg = "observed_fact and validated_rule notes require at least one evidence_id"
            raise ValueError(msg)
        return self


class RiskLimit(BaseModel):
    """Planner risk budget expressed without low-level controls."""

    model_config = ConfigDict(extra="forbid")

    avoid_known_dangers: bool = True
    max_danger_score: float = Field(default=0.4, ge=0.0, le=1.0)


class PlannerOutput(BaseModel):
    """Structured Cortex output. This is never a primitive input plan."""

    model_config = ConfigDict(extra="forbid")

    current_belief_state: list[EvidenceBackedClaim] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_goal: str
    selected_skill: UniversalSkillName
    success_condition: list[str] = Field(default_factory=list)
    risk_limit: RiskLimit = Field(default_factory=RiskLimit)
    memory_updates_requested: list[MemoryUpdateRequest] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_direct_control_plans(cls, data: Any) -> Any:
        violations = find_direct_control_violations(data)
        if violations:
            joined = ", ".join(violations)
            msg = f"planner output must not contain direct primitive controls: {joined}"
            raise ValueError(msg)
        return data


class PostMortemOutput(BaseModel):
    """Structured reflection output, never a controller or memory writer."""

    model_config = ConfigDict(extra="forbid")

    observed_outcome: str
    likely_causes: list[ReflectionNote] = Field(default_factory=list)
    evidence_backed_notes: list[ReflectionNote] = Field(default_factory=list)
    hypotheses: list[ReflectionNote] = Field(default_factory=list)
    next_safe_experiments: list[str] = Field(default_factory=list)
    memory_updates_requested: list[MemoryUpdateRequest] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_unsafe_content(cls, data: Any) -> Any:
        control_violations = find_direct_control_violations(data)
        if control_violations:
            joined = ", ".join(control_violations)
            msg = f"planner output must not contain direct primitive controls: {joined}"
            raise ValueError(msg)

        hidden_state_violations = find_hidden_state_term_violations(data)
        if hidden_state_violations:
            joined = ", ".join(hidden_state_violations)
            msg = f"planner output must not contain hidden-state terms: {joined}"
            raise ValueError(msg)

        return data


def parse_planner_output_json(raw_json: str) -> PlannerOutput:
    """Parse model JSON and validate it against the planner contract."""

    try:
        return PlannerOutput.model_validate_json(raw_json)
    except ValidationError:
        raise


def parse_post_mortem_output_json(raw_json: str) -> PostMortemOutput:
    """Parse model JSON and validate it against the post-mortem contract."""

    try:
        return PostMortemOutput.model_validate_json(raw_json)
    except ValidationError:
        raise


def find_direct_control_violations(value: Any, *, path: str = "") -> tuple[str, ...]:
    """Find forbidden direct-control fields or primitive action lists recursively."""

    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            if key_text in FORBIDDEN_CONTROL_FIELDS:
                violations.append(next_path)
            violations.extend(find_direct_control_violations(nested_value, path=next_path))
    elif _is_non_string_sequence(value):
        items = list(value)
        if items and all(
            isinstance(item, str) and item in PRIMITIVE_ACTION_NAMES for item in items
        ):
            violations.append(path or "<root>")
        for index, nested_value in enumerate(items):
            next_path = f"{path}[{index}]" if path else f"[{index}]"
            violations.extend(find_direct_control_violations(nested_value, path=next_path))

    return tuple(sorted(set(violations)))


def find_hidden_state_term_violations(value: Any, *, path: str = "") -> tuple[str, ...]:
    """Find hidden-state terms recursively in keys and string values."""

    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            if _contains_hidden_state_term(key_text):
                violations.append(next_path)
            violations.extend(find_hidden_state_term_violations(nested_value, path=next_path))
    elif _is_non_string_sequence(value):
        for index, nested_value in enumerate(value):
            next_path = f"{path}[{index}]" if path else f"[{index}]"
            violations.extend(find_hidden_state_term_violations(nested_value, path=next_path))
    elif isinstance(value, str) and _contains_hidden_state_term(value):
        violations.append(path or "<root>")

    return tuple(sorted(set(violations)))


def _contains_hidden_state_term(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in FORBIDDEN_HIDDEN_STATE_TERMS)


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray)
