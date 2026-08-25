import inspect

import pytest

from fh_agent.observation import visible_sprite_normalization as normalization_module
from fh_agent.observation.schemas import VisibleSprite
from fh_agent.observation.visible_sprite_normalization import (
    VisibleSpriteNormalizationError,
    normalize_visible_sprites,
)


def test_legacy_arrays_normalize_deterministically_with_missing_hashes() -> None:
    sprites = normalize_visible_sprites(
        visible_sprite_screen_positions=((10, 20), (30, 40)),
        visible_sprite_visual_hashes=("dhash:0123456789abcdef",),
        screenshot_id="shot-1",
        source_confidence=1.0,
    )

    assert [sprite.screen_position for sprite in sprites] == [(10, 20), (30, 40)]
    assert [sprite.visual_hash for sprite in sprites] == ["dhash:0123456789abcdef", None]
    assert [sprite.evidence_id for sprite in sprites] == ["shot-1", "shot-1"]
    assert [sprite.confidence for sprite in sprites] == [1.0, 1.0]


def test_more_legacy_hashes_than_positions_is_rejected() -> None:
    with pytest.raises(VisibleSpriteNormalizationError, match="cannot outnumber"):
        normalize_visible_sprites(
            visible_sprite_screen_positions=((10, 20),),
            visible_sprite_visual_hashes=("dhash:0123456789abcdef", "dhash:fedcba9876543210"),
            screenshot_id="shot-1",
        )


def test_existing_canonical_sprites_preserve_visible_values() -> None:
    supplied = VisibleSprite(
        screen_position=(10, 20),
        visual_hash="dhash:0123456789abcdef",
        confidence=0.7,
        evidence_id="sprite-shot-1",
    )

    sprites = normalize_visible_sprites(
        visible_sprites=(supplied,),
        visible_sprite_screen_positions=((10, 20),),
        visible_sprite_visual_hashes=("dhash:0123456789abcdef",),
        screenshot_id="shot-2",
        source_confidence=1.0,
    )

    assert sprites == [supplied]


@pytest.mark.parametrize(
    ("positions", "visual_hashes"),
    [
        (((11, 20),), ("dhash:0123456789abcdef",)),
        (((10, 20),), ("dhash:fedcba9876543210",)),
    ],
)
def test_contradictory_canonical_and_legacy_data_is_rejected(
    positions: tuple[tuple[int, int], ...],
    visual_hashes: tuple[str, ...],
) -> None:
    with pytest.raises(VisibleSpriteNormalizationError, match="conflict"):
        normalize_visible_sprites(
            visible_sprites=(
                VisibleSprite(
                    screen_position=(10, 20),
                    visual_hash="dhash:0123456789abcdef",
                    evidence_id="sprite-shot-1",
                ),
            ),
            visible_sprite_screen_positions=positions,
            visible_sprite_visual_hashes=visual_hashes,
            screenshot_id="shot-1",
        )


def test_missing_canonical_evidence_uses_screenshot_or_single_observation_evidence() -> None:
    supplied = VisibleSprite(screen_position=(10, 20), confidence=0.7)

    from_screenshot = normalize_visible_sprites(
        visible_sprites=(supplied,),
        screenshot_id="shot-1",
    )
    from_single_evidence = normalize_visible_sprites(
        visible_sprites=(supplied,),
        evidence_ids=("visible-receipt-1",),
    )

    assert from_screenshot[0].evidence_id == "shot-1"
    assert from_single_evidence[0].evidence_id == "visible-receipt-1"


def test_missing_or_ambiguous_visible_evidence_is_rejected() -> None:
    with pytest.raises(VisibleSpriteNormalizationError, match="require"):
        normalize_visible_sprites(
            visible_sprite_screen_positions=((10, 20),),
        )
    with pytest.raises(VisibleSpriteNormalizationError, match="unambiguous"):
        normalize_visible_sprites(
            visible_sprite_screen_positions=((10, 20),),
            evidence_ids=("visible-receipt-1", "visible-receipt-2"),
        )


def test_missing_confidence_is_not_promoted() -> None:
    sprites = normalize_visible_sprites(
        visible_sprite_screen_positions=((10, 20),),
        screenshot_id="shot-1",
    )

    assert sprites[0].confidence is None


def test_source_confidence_is_explicit_and_bounded() -> None:
    sprites = normalize_visible_sprites(
        visible_sprite_screen_positions=((10, 20),),
        screenshot_id="shot-1",
        source_confidence=0.6,
    )

    assert sprites[0].confidence == 0.6
    with pytest.raises(VisibleSpriteNormalizationError, match="between 0 and 1"):
        normalize_visible_sprites(
            visible_sprite_screen_positions=((10, 20),),
            screenshot_id="shot-1",
            source_confidence=1.1,
        )


def test_normalizer_has_no_manager_or_game_specific_dependencies() -> None:
    source = inspect.getsource(normalization_module)

    assert "fh_agent.manager" not in source
    assert "fh_agent.bridge" not in source
    assert "fh_agent.game" not in source
    assert "enemy" not in source
    assert "door" not in source
