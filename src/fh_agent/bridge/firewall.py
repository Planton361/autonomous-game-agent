from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

ALLOWED_BRIDGE_FIELDS = frozenset(
    {
        "message_window_visible",
        "visible_message_text",
        "menu_open",
        "visible_menu_items",
        "combat_ui_visible",
        "death_screen_visible",
        "player_screen_position",
        "visible_sprite_screen_positions",
        "visible_sprite_visual_hashes",
        "screenshot_id",
    }
)

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


@dataclass(frozen=True, slots=True)
class FirewallViolation(Exception):
    """Raised when bridge input attempts to expose hidden state."""

    forbidden_fields: tuple[str, ...]

    def __str__(self) -> str:
        fields = ", ".join(self.forbidden_fields)
        return f"forbidden bridge fields blocked: {fields}"


class NoSpoilerFirewall:
    """Sanitizes bridge-like raw dicts to visible allowlisted fields only."""

    def __init__(
        self,
        *,
        allowed_fields: frozenset[str] = ALLOWED_BRIDGE_FIELDS,
        forbidden_fields: frozenset[str] = FORBIDDEN_BRIDGE_FIELDS,
    ) -> None:
        self.allowed_fields = allowed_fields
        self.forbidden_fields = forbidden_fields

    def sanitize(self, raw_data: Mapping[str, Any]) -> dict[str, Any]:
        forbidden = tuple(sorted(field for field in raw_data if field in self.forbidden_fields))
        if forbidden:
            raise FirewallViolation(forbidden)

        return {field: value for field, value in raw_data.items() if field in self.allowed_fields}


def sanitize_bridge_data(raw_data: Mapping[str, Any]) -> dict[str, Any]:
    return NoSpoilerFirewall().sanitize(raw_data)
