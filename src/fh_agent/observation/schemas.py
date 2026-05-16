from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class VisibleTextSpan(BaseModel):
    """Visible text observed on screen, with optional evidence linkage."""

    model_config = ConfigDict(extra="forbid")

    text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_id: str | None = None


class VisibleSprite(BaseModel):
    """Visible sprite-like object described only by screen-derived data."""

    model_config = ConfigDict(extra="forbid")

    screen_position: tuple[int, int]
    visual_hash: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_id: str | None = None


class Observation(BaseModel):
    """Canonical visible-state observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str | None = None
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    screenshot_id: str | None = None
    message_window_visible: bool | None = None
    visible_message_text: str | None = None
    visible_text_spans: list[VisibleTextSpan] = Field(default_factory=list)
    menu_open: bool | None = None
    visible_menu_items: list[str] = Field(default_factory=list)
    combat_ui_visible: bool | None = None
    death_screen_visible: bool | None = None
    player_screen_position: tuple[int, int] | None = None
    visible_sprite_screen_positions: list[tuple[int, int]] = Field(default_factory=list)
    visible_sprite_visual_hashes: list[str] = Field(default_factory=list)
    visible_sprites: list[VisibleSprite] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ActionResult(BaseModel):
    """Result of a primitive action attempt, without raw key sequences."""

    model_config = ConfigDict(extra="forbid")

    action: str
    executed: bool
    created_at: datetime = Field(default_factory=utc_now)
    blocked_reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class Event(BaseModel):
    """Canonical event record shape for observation-adjacent workflows."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    run_id: str
    event_type: str
    created_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)


class SkillResult(BaseModel):
    """Result of a reusable skill contract."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str
    success: bool
    created_at: datetime = Field(default_factory=utc_now)
    evidence_ids: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    reward: float | None = None


class KnowledgeFact(BaseModel):
    """Evidence-backed claim learned from visible observations or outcomes."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str | None = None
    subject: str
    predicate: str
    value: str | int | float | bool | None = None
    claim: str
    source: Literal["visible_observation", "observed_outcome", "sanitized_bridge"] = (
        "visible_observation"
    )
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(min_length=1)
