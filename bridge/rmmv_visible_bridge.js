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

  const SNAPSHOT_REQUEST_FIELDS = Object.freeze([
    "request_id",
    "run_id",
    "run_mode",
    "screenshot_id",
  ]);

  function isNonEmptyString(value) {
    return typeof value === "string" && value.trim().length > 0;
  }

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function validateSnapshotRequest(request) {
    if (!isPlainObject(request)) {
      throw new Error("snapshot request must be an object");
    }

    Object.keys(request).forEach(function (field) {
      if (SNAPSHOT_REQUEST_FIELDS.indexOf(field) === -1) {
        throw new Error("snapshot request contains an unknown field: " + field);
      }
    });

    ["request_id", "run_id", "screenshot_id"].forEach(function (field) {
      if (!isNonEmptyString(request[field])) {
        throw new Error("snapshot request requires non-empty " + field);
      }
    });

    if (request.run_mode !== "bridge-assisted") {
      throw new Error("snapshot request run_mode must be bridge-assisted");
    }
  }

  function validateVisibleSurface(visibleSurface) {
    if (!isPlainObject(visibleSurface)) {
      throw new Error("visible surface must be an object");
    }

    Object.keys(visibleSurface).forEach(function (field) {
      if (field === "screenshot_id") {
        throw new Error("visible surface must not provide screenshot_id");
      }
      if (FORBIDDEN_FIELDS.indexOf(field) !== -1) {
        throw new Error("visible surface contains a forbidden field: " + field);
      }
      if (ALLOWED_FIELDS.indexOf(field) === -1) {
        throw new Error("visible surface contains an unknown field: " + field);
      }
    });
  }

  function buildSnapshotPayload(request, visibleSurface) {
    validateSnapshotRequest(request);
    validateVisibleSurface(visibleSurface);

    const payload = {
      run_mode: request.run_mode,
      screenshot_id: request.screenshot_id,
    };
    Object.keys(visibleSurface).forEach(function (field) {
      payload[field] = visibleSurface[field];
    });

    return payload;
  }

  function visibleMessageWindowType() {
    if (typeof window === "undefined" || typeof window.Window_Message !== "function") {
      return null;
    }
    return window.Window_Message;
  }

  function ancestorsAreVisible(node) {
    const visited = [];
    let ancestor = node.parent;

    while (ancestor !== null && ancestor !== undefined) {
      if (!isPlainObject(ancestor) || visited.indexOf(ancestor) !== -1) {
        return false;
      }
      if (ancestor.visible !== true || ancestor.renderable !== true) {
        return false;
      }
      visited.push(ancestor);
      ancestor = ancestor.parent;
    }

    return true;
  }

  function isVisibleMessageWindow(node, messageWindowType) {
    return (
      node instanceof messageWindowType &&
      node.visible === true &&
      node.renderable === true &&
      typeof node.openness === "number" &&
      node.openness > 0 &&
      ancestorsAreVisible(node)
    );
  }

  function collectVisibleSurface(sceneRoot) {
    const messageWindowType = visibleMessageWindowType();
    if (messageWindowType === null || !isPlainObject(sceneRoot)) {
      return { ui_state: "unknown" };
    }

    const pending = [sceneRoot];
    const visited = [];
    while (pending.length > 0) {
      const node = pending.pop();
      if (!isPlainObject(node) || visited.indexOf(node) !== -1) {
        continue;
      }
      visited.push(node);

      if (isVisibleMessageWindow(node, messageWindowType)) {
        return { ui_state: "dialogue" };
      }

      if (Array.isArray(node.children)) {
        node.children.forEach(function (child) {
          pending.push(child);
        });
      }
    }

    return { ui_state: "unknown" };
  }

  function buildSnapshotFromScene(request, sceneRoot) {
    return buildSnapshotPayload(request, collectVisibleSurface(sceneRoot));
  }

  function buildSnapshotResponse(request, sceneRoot) {
    const payload = buildSnapshotFromScene(request, sceneRoot);
    return {
      request_id: request.request_id,
      run_id: request.run_id,
      payload: payload,
    };
  }

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
    buildSnapshotPayload: buildSnapshotPayload,
    collectVisibleSurface: collectVisibleSurface,
    buildSnapshotFromScene: buildSnapshotFromScene,
    buildSnapshotResponse: buildSnapshotResponse,
  });
})();
