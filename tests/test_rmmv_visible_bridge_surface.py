from pathlib import Path

from fh_agent.bridge.sanitizer import sanitize_bridge_payload

BRIDGE_SOURCE_PATH = Path(__file__).parents[1] / "bridge" / "rmmv_visible_bridge.js"


def _bridge_source() -> str:
    return BRIDGE_SOURCE_PATH.read_text(encoding="utf-8")


def test_surface_extractor_and_composition_helper_are_exported() -> None:
    source = _bridge_source()

    assert "function collectVisibleSurface(sceneRoot)" in source
    assert "function buildSnapshotFromScene(request, sceneRoot)" in source
    assert "collectVisibleSurface: collectVisibleSurface" in source
    assert "buildSnapshotFromScene: buildSnapshotFromScene" in source


def test_visible_open_rendered_message_window_is_the_only_dialogue_signal() -> None:
    source = _bridge_source()

    assert "node instanceof messageWindowType" in source
    assert "node.visible === true" in source
    assert 'typeof node.openness === "number"' in source
    assert "node.openness > 0" in source
    assert 'return { ui_state: "dialogue" };' in source


def test_hidden_closed_or_non_renderable_message_windows_fail_safely_to_unknown() -> None:
    source = _bridge_source()

    assert "node.renderable === true" in source
    assert 'return { ui_state: "unknown" };' in source
    assert "messageWindowType === null" in source


def test_hidden_ancestor_is_included_in_render_visibility_check() -> None:
    source = _bridge_source()

    assert "function ancestorsAreVisible(node)" in source
    assert "ancestor.visible !== true || ancestor.renderable !== true" in source
    assert "ancestorsAreVisible(node)" in source


def test_no_message_window_fails_safely_and_surface_output_only_contains_ui_state() -> None:
    source = _bridge_source()

    assert "const pending = [sceneRoot]" in source
    assert "Array.isArray(node.children)" in source
    assert source.count('return { ui_state: "dialogue" };') == 1
    assert source.count('return { ui_state: "unknown" };') == 2


def test_surface_extractor_has_no_game_model_state_or_text_access() -> None:
    source = _bridge_source()
    forbidden_identifiers = (
        "$gameMessage",
        "$gameMap",
        "$gamePlayer",
        "$gameSwitches",
        "$gameVariables",
        "$data",
        "Game_Event",
        "_textState",
        "messageQueue",
        "saveData",
    )

    assert not any(identifier in source for identifier in forbidden_identifiers)


def test_surface_extractor_has_no_io_transport_timer_or_input_access() -> None:
    source = _bridge_source()
    forbidden_identifiers = (
        "require(",
        "fs.",
        "setInterval(",
        "setTimeout(",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "child_process",
        "Input",
    )

    assert not any(identifier in source for identifier in forbidden_identifiers)


def test_representative_request_bound_dialogue_payload_passes_existing_sanitizer() -> None:
    source = _bridge_source()
    payload = {
        "run_mode": "bridge-assisted",
        "ui_state": "dialogue",
        "screenshot_id": "shot-1",
    }

    assert "return buildSnapshotPayload(request, collectVisibleSurface(sceneRoot));" in source
    assert sanitize_bridge_payload(payload) == {
        "ui_state": "dialogue",
        "screenshot_id": "shot-1",
    }
