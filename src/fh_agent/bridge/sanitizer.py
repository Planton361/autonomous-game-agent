import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

RunMode = Literal["official", "debug"]

VISIBLE_BRIDGE_FIELDS = frozenset(
    {
        "visible_message_text",
        "visible_menu_items",
        "ui_state",
        "player_screen_position",
        "visible_sprite_screen_positions",
        "visible_sprite_visual_hashes",
        "screenshot_id",
    }
)

REQUIRED_BRIDGE_FIELDS = frozenset({"run_mode"})
ACCEPTED_BRIDGE_FIELDS = VISIBLE_BRIDGE_FIELDS | REQUIRED_BRIDGE_FIELDS

FORBIDDEN_BRIDGE_FIELDS = frozenset(
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

VISUAL_HASH_PATTERN = re.compile(
    r"^(?:[a-fA-F0-9]{8,128}|(?:a|d|p)hash:[a-fA-F0-9]{8,128}|"
    r"sha256:[a-fA-F0-9]{64})$"
)


class BridgeSanitizerError(ValueError):
    """Base error for rejected visible bridge payloads."""


class ForbiddenBridgeFieldError(BridgeSanitizerError):
    """Raised when hidden-state fields are present anywhere in a payload."""

    def __init__(self, field_paths: Iterable[str]) -> None:
        self.field_paths = tuple(sorted(field_paths))
        fields = ", ".join(self.field_paths)
        super().__init__(f"forbidden bridge fields blocked: {fields}")


class UnknownBridgeFieldError(BridgeSanitizerError):
    """Raised when a top-level payload field is not explicitly allowlisted."""

    def __init__(self, field_names: Iterable[str]) -> None:
        self.field_names = tuple(sorted(field_names))
        fields = ", ".join(self.field_names)
        super().__init__(f"unknown bridge fields rejected: {fields}")


class InvalidBridgePayloadError(BridgeSanitizerError):
    """Raised when an allowlisted payload has an invalid shape."""


class SanitizedBridgePayload(BaseModel):
    """Strict visible-state shape accepted from the bridge boundary."""

    model_config = ConfigDict(extra="forbid")

    run_mode: RunMode
    visible_message_text: str | None = None
    visible_menu_items: list[str] | None = None
    ui_state: Literal["field", "dialogue", "menu", "combat", "death", "unknown"] | None = None
    player_screen_position: tuple[int, int] | None = None
    visible_sprite_screen_positions: list[tuple[int, int]] | None = None
    visible_sprite_visual_hashes: list[str] | None = None
    screenshot_id: str | None = None

    @field_validator("player_screen_position")
    @classmethod
    def validate_player_screen_position(
        cls,
        value: tuple[int, int] | None,
    ) -> tuple[int, int] | None:
        if value is not None and any(coordinate < 0 for coordinate in value):
            msg = "player_screen_position must contain non-negative screen coordinates"
            raise ValueError(msg)
        return value

    @field_validator("visible_sprite_screen_positions")
    @classmethod
    def validate_sprite_screen_positions(
        cls,
        value: list[tuple[int, int]] | None,
    ) -> list[tuple[int, int]] | None:
        if value is not None:
            for position in value:
                if any(coordinate < 0 for coordinate in position):
                    msg = (
                        "visible_sprite_screen_positions must contain "
                        "non-negative screen coordinates"
                    )
                    raise ValueError(msg)
        return value

    @field_validator("visible_sprite_visual_hashes")
    @classmethod
    def validate_sprite_visual_hashes(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            for visual_hash in value:
                if VISUAL_HASH_PATTERN.fullmatch(visual_hash) is None:
                    msg = (
                        "visible_sprite_visual_hashes must contain visual hashes, not entity names"
                    )
                    raise ValueError(msg)
        return value

    def visible_output(self) -> dict[str, Any]:
        """Return only visible fields, excluding run-mode metadata."""

        return self.model_dump(
            mode="python",
            exclude={"run_mode"},
            exclude_none=True,
        )


def find_forbidden_field_paths(
    value: Any,
    *,
    forbidden_fields: frozenset[str] = FORBIDDEN_BRIDGE_FIELDS,
    path: str = "",
) -> tuple[str, ...]:
    """Find forbidden keys recursively in nested mappings and sequences."""

    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            if key_text in forbidden_fields:
                found.append(next_path)
            found.extend(
                find_forbidden_field_paths(
                    nested_value,
                    forbidden_fields=forbidden_fields,
                    path=next_path,
                )
            )
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, nested_value in enumerate(value):
            next_path = f"{path}[{index}]" if path else f"[{index}]"
            found.extend(
                find_forbidden_field_paths(
                    nested_value,
                    forbidden_fields=forbidden_fields,
                    path=next_path,
                )
            )

    return tuple(found)


def sanitize_bridge_payload(raw_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and sanitize a raw bridge payload to visible fields only."""

    forbidden_paths = find_forbidden_field_paths(raw_payload)
    if forbidden_paths:
        raise ForbiddenBridgeFieldError(forbidden_paths)

    unknown_fields = set(raw_payload) - ACCEPTED_BRIDGE_FIELDS
    if unknown_fields:
        raise UnknownBridgeFieldError(unknown_fields)

    try:
        payload = SanitizedBridgePayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise InvalidBridgePayloadError(str(exc)) from exc

    return payload.visible_output()
