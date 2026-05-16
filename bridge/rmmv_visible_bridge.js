(function () {
  "use strict";

  const ALLOWED_FIELDS = Object.freeze([
    "visible_message_text",
    "visible_menu_items",
    "ui_state",
    "player_screen_position",
    "visible_sprite_screen_positions",
    "visible_sprite_visual_hashes",
    "screenshot_id",
  ]);

  const FORBIDDEN_FIELDS = Object.freeze([
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
  ]);

  function emptyVisiblePayload(runMode, screenshotId) {
    return {
      run_mode: runMode,
      ui_state: "unknown",
      visible_message_text: null,
      visible_menu_items: [],
      player_screen_position: null,
      visible_sprite_screen_positions: [],
      visible_sprite_visual_hashes: [],
      screenshot_id: screenshotId || null,
    };
  }

  function visibleBridgeMetadata() {
    return {
      policy: "visible_only",
      allowed_fields: ALLOWED_FIELDS.slice(),
      forbidden_fields: FORBIDDEN_FIELDS.slice(),
    };
  }

  window.FHVisibleBridge = Object.freeze({
    allowedFields: ALLOWED_FIELDS,
    forbiddenFields: FORBIDDEN_FIELDS,
    emptyVisiblePayload: emptyVisiblePayload,
    metadata: visibleBridgeMetadata,
  });
})();
