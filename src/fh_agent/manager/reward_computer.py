from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.observation.schemas import Observation

RewardTerm = Literal[
    "dialogue_continued",
    "visible_text_changed",
    "ui_state_changed",
    "no_change",
    "timeout",
    "failure",
]


class RewardProfile(BaseModel):
    """Generic reward weights for visible-state skill outcomes."""

    model_config = ConfigDict(extra="forbid")

    dialogue_continued: float = 1.0
    visible_text_changed: float = 0.5
    ui_state_changed: float = 0.25
    no_change: float = -0.05
    timeout: float = -1.0
    failure: float = -1.0


class RewardBreakdown(BaseModel):
    """Deterministic reward result with named generic terms."""

    model_config = ConfigDict(extra="forbid")

    total: float
    terms: dict[RewardTerm, float] = Field(default_factory=dict)


class RewardComputer:
    """Computes rewards from visible observations and generic outcomes only."""

    def __init__(self, profile: RewardProfile | None = None) -> None:
        self.profile = profile or RewardProfile()

    def compute(
        self,
        before: Observation,
        after: Observation,
        *,
        timeout: bool = False,
        failure: bool = False,
    ) -> RewardBreakdown:
        terms: dict[RewardTerm, float] = {}

        visible_text_changed = observation_visible_text(before) != observation_visible_text(after)
        ui_state_changed = before.ui_state != after.ui_state
        dialogue_continued = is_dialogue_progress(before, after)

        if dialogue_continued:
            terms["dialogue_continued"] = self.profile.dialogue_continued
        if visible_text_changed:
            terms["visible_text_changed"] = self.profile.visible_text_changed
        if ui_state_changed:
            terms["ui_state_changed"] = self.profile.ui_state_changed
        if not visible_text_changed and not ui_state_changed:
            terms["no_change"] = self.profile.no_change
        if timeout:
            terms["timeout"] = self.profile.timeout
        if failure:
            terms["failure"] = self.profile.failure

        return RewardBreakdown(total=sum(terms.values()), terms=terms)


def observation_visible_text(observation: Observation) -> tuple[str, ...]:
    texts: list[str] = []
    if observation.visible_message_text:
        texts.append(observation.visible_message_text)
    texts.extend(span.text for span in observation.visible_text_spans)
    return tuple(texts)


def is_dialogue_progress(before: Observation, after: Observation) -> bool:
    if before.ui_state != "dialogue" and not before.visible_message_text:
        return False

    text_changed = observation_visible_text(before) != observation_visible_text(after)
    dialogue_closed = before.ui_state == "dialogue" and after.ui_state != "dialogue"
    new_evidence = bool(set(after.evidence_ids) - set(before.evidence_ids))
    return text_changed or dialogue_closed or new_evidence
