"""Normalize structured visible sprite data into canonical Observation values."""

from collections.abc import Sequence

from fh_agent.observation.schemas import VisibleSprite


class VisibleSpriteNormalizationError(ValueError):
    """Raised when structured visible sprite representations disagree or lack evidence."""


def normalize_visible_sprites(
    *,
    visible_sprites: Sequence[VisibleSprite] = (),
    visible_sprite_screen_positions: Sequence[tuple[int, int]] = (),
    visible_sprite_visual_hashes: Sequence[str] = (),
    screenshot_id: str | None = None,
    evidence_ids: Sequence[str] = (),
    source_confidence: float | None = None,
) -> list[VisibleSprite]:
    """Return canonical visible sprites while preserving compatible legacy arrays.

    ``source_confidence`` describes confidence in visible structured-data extraction only;
    it is not a semantic entity-classification confidence.
    """

    _validate_source_confidence(source_confidence)
    positions = tuple(visible_sprite_screen_positions)
    visual_hashes = tuple(visible_sprite_visual_hashes)
    canonical_sprites = tuple(visible_sprites)
    if len(visual_hashes) > len(positions):
        msg = "visible_sprite_visual_hashes cannot outnumber visible_sprite_screen_positions"
        raise VisibleSpriteNormalizationError(msg)

    if canonical_sprites:
        _validate_compatible_representations(canonical_sprites, positions, visual_hashes)
        return [
            _with_visible_evidence(sprite, screenshot_id=screenshot_id, evidence_ids=evidence_ids)
            for sprite in canonical_sprites
        ]

    return [
        VisibleSprite(
            screen_position=position,
            visual_hash=visual_hashes[index] if index < len(visual_hashes) else None,
            confidence=source_confidence,
            evidence_id=_visible_evidence_id(
                screenshot_id=screenshot_id,
                evidence_ids=evidence_ids,
            ),
        )
        for index, position in enumerate(positions)
    ]


def _validate_source_confidence(source_confidence: float | None) -> None:
    if source_confidence is not None and not 0.0 <= source_confidence <= 1.0:
        msg = "source_confidence must be between 0 and 1"
        raise VisibleSpriteNormalizationError(msg)


def _validate_compatible_representations(
    canonical_sprites: tuple[VisibleSprite, ...],
    positions: tuple[tuple[int, int], ...],
    visual_hashes: tuple[str, ...],
) -> None:
    if not positions:
        return
    if len(canonical_sprites) != len(positions):
        msg = "canonical visible_sprites must match legacy visible sprite positions"
        raise VisibleSpriteNormalizationError(msg)

    for index, sprite in enumerate(canonical_sprites):
        if sprite.screen_position != positions[index]:
            msg = "canonical visible_sprites conflict with legacy visible sprite positions"
            raise VisibleSpriteNormalizationError(msg)
        if index < len(visual_hashes) and sprite.visual_hash != visual_hashes[index]:
            msg = "canonical visible_sprites conflict with legacy visible sprite visual hashes"
            raise VisibleSpriteNormalizationError(msg)


def _with_visible_evidence(
    sprite: VisibleSprite,
    *,
    screenshot_id: str | None,
    evidence_ids: Sequence[str],
) -> VisibleSprite:
    if sprite.evidence_id is not None:
        return sprite
    return sprite.model_copy(
        update={
            "evidence_id": _visible_evidence_id(
                screenshot_id=screenshot_id,
                evidence_ids=evidence_ids,
            )
        }
    )


def _visible_evidence_id(*, screenshot_id: str | None, evidence_ids: Sequence[str]) -> str:
    if screenshot_id:
        return screenshot_id
    unique_evidence_ids = tuple(dict.fromkeys(evidence_ids))
    if len(unique_evidence_ids) == 1:
        return unique_evidence_ids[0]
    msg = "visible sprites require a screenshot_id or one unambiguous evidence_id"
    raise VisibleSpriteNormalizationError(msg)
