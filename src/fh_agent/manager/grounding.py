"""Deterministic visible-observation grounding for Manager target contracts."""

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.manager.skill_target_requirements import target_requirement_for_skill
from fh_agent.manager.target_ref import (
    EvidenceId,
    GroundedTarget,
    GroundingResult,
    VisibleObjectTarget,
    VisibleScreenPointTarget,
)
from fh_agent.observation.schemas import Observation, VisibleSprite
from fh_agent.skill_capabilities import UniversalSkillName


class GroundingRequest(BaseModel):
    """Auditable Manager request to ground one universal skill from visible evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    selected_skill: UniversalSkillName
    semantic_goal: str = Field(min_length=1)
    evidence_scope_ids: tuple[EvidenceId, ...]


class GroundingPolicy(BaseModel):
    """Conservative, deterministic thresholds for observation-only grounding."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


DEFAULT_GROUNDING_POLICY = GroundingPolicy()


class GroundingService(Protocol):
    """Ground an audited Manager request against a canonical visible observation."""

    def ground(self, request: GroundingRequest, observation: Observation) -> GroundingResult:
        """Return either an evidence-backed target or an auditable grounding failure."""


@dataclass(frozen=True, slots=True)
class _VisibleCandidate:
    screen_position: tuple[int, int]
    visual_hash: str | None
    confidence: float | None
    evidence_id: str | None


class BoundedObservationGroundingService:
    """Ground only unambiguous, confident visible sprites without semantic interpretation."""

    def __init__(self, *, policy: GroundingPolicy | None = None) -> None:
        self.policy = policy or DEFAULT_GROUNDING_POLICY

    def ground(self, request: GroundingRequest, observation: Observation) -> GroundingResult:
        """Ground from visible sprites; semantic_goal is retained only as request audit metadata."""

        requirement = target_requirement_for_skill(request.selected_skill)
        observation_evidence_ids = self._observation_evidence_ids(observation)
        audit_evidence_ids = self._deduplicated_ids(
            request.evidence_scope_ids,
            observation_evidence_ids,
        )
        if requirement is None or requirement == "targetless":
            return self._failure("unsupported_target_type", audit_evidence_ids)
        if not observation_evidence_ids or not request.evidence_scope_ids:
            return self._failure("insufficient_evidence", audit_evidence_ids)
        if not set(request.evidence_scope_ids).issubset(observation_evidence_ids):
            return self._failure("stale_evidence", audit_evidence_ids)

        compatible_candidates = self._compatible_candidates(observation.visible_sprites)
        if not compatible_candidates:
            return self._failure("no_visible_candidate", audit_evidence_ids)

        confident_candidates = [
            candidate
            for candidate in compatible_candidates
            if candidate.confidence is not None
            and candidate.confidence >= self.policy.min_confidence
        ]
        if not confident_candidates:
            return self._failure("insufficient_confidence", audit_evidence_ids)
        if len(confident_candidates) > 1:
            return self._failure("ambiguous_candidates", audit_evidence_ids)

        candidate = confident_candidates[0]
        target_evidence_ids = self._deduplicated_ids(
            request.evidence_scope_ids,
            observation_evidence_ids,
            (candidate.evidence_id,) if candidate.evidence_id else (),
        )
        target = self._target_for_candidate(requirement, candidate, target_evidence_ids)
        return GroundingResult(
            status="grounded",
            target=target,
            evidence_ids=target_evidence_ids,
        )

    def _compatible_candidates(self, sprites: list[VisibleSprite]) -> list[_VisibleCandidate]:
        return [
            _VisibleCandidate(
                screen_position=sprite.screen_position,
                visual_hash=sprite.visual_hash,
                confidence=sprite.confidence,
                evidence_id=sprite.evidence_id,
            )
            for sprite in sprites
            if sprite.screen_position[0] >= 0 and sprite.screen_position[1] >= 0
        ]

    def _target_for_candidate(
        self,
        requirement: str,
        candidate: _VisibleCandidate,
        evidence_ids: tuple[str, ...],
    ) -> GroundedTarget:
        target_id = self._target_id_for_candidate(requirement, candidate, evidence_ids)
        if requirement == "visible_object":
            return VisibleObjectTarget(
                target_id=target_id,
                confidence=candidate.confidence,
                evidence_ids=evidence_ids,
                screen_position=candidate.screen_position,
                visual_hash=candidate.visual_hash,
            )
        return VisibleScreenPointTarget(
            target_id=target_id,
            confidence=candidate.confidence,
            evidence_ids=evidence_ids,
            screen_position=candidate.screen_position,
        )

    def _target_id_for_candidate(
        self,
        target_type: str,
        candidate: _VisibleCandidate,
        evidence_ids: tuple[str, ...],
    ) -> str:
        payload = {
            "confidence": candidate.confidence,
            "evidence_ids": evidence_ids,
            "screen_position": candidate.screen_position,
            "target_type": target_type,
            "visual_hash": candidate.visual_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        return f"target-{digest}"

    def _observation_evidence_ids(self, observation: Observation) -> tuple[str, ...]:
        return self._deduplicated_ids(
            observation.evidence_ids,
            tuple(
                sprite.evidence_id for sprite in observation.visible_sprites if sprite.evidence_id
            ),
        )

    def _failure(self, reason: str, evidence_ids: tuple[str, ...]) -> GroundingResult:
        return GroundingResult(
            status="grounding_failed",
            failure_reason=reason,
            evidence_ids=evidence_ids,
        )

    def _deduplicated_ids(self, *id_groups: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(evidence_id for group in id_groups for evidence_id in group))
