"""Closed, per-file ownership equivalences; never discard project or visual meaning."""

import base64
import json
import math
import re
from enum import StrEnum
from pathlib import PurePosixPath

from . import private_projection as public
from . import private_views as views
from .preferred_paths import INTERNAL
from .private_projection import ProjectionError, digest, markdown_parts, utf8

# Exact save-time editor preferences in the pinned plugin getSceneWithAppState.
# No prefix/wildcard rule: every other appState field stays in the digest.
EDITOR_FIELDS = frozenset(
    {
        "theme",
        "scrollX",
        "scrollY",
        "zoom",
        "activeTool",
        "gridSize",
        "gridStep",
        "gridModeEnabled",
        "gridColor",
        "colorPalette",
        "colorTopPicks",
        "fontTopPicks",
        "currentStrokeOptions",
        "frameRendering",
        "objectsSnapModeEnabled",
        "disableContextMenu",
        "bindingPreference",
        "isMidpointSnappingEnabled",
        "boxSelectionMode",
        "inputDevice",
        "currentItemStrokeColor",
        "currentItemBackgroundColor",
        "currentItemFillStyle",
        "currentItemStickynoteStrokeColor",
        "currentItemStrokeWidth",
        "currentItemStrokeWidthKey",
        "currentItemStrokeVariability",
        "currentItemStrokeStyle",
        "currentItemRoughness",
        "currentItemOpacity",
        "currentItemFontFamily",
        "currentItemFontSize",
        "currentItemTextAlign",
        "currentItemStartArrowhead",
        "currentItemEndArrowhead",
        "currentItemArrowType",
        "currentItemFrameRole",
        "currentItemRoundness",
    }
)


class Ownership(StrEnum):
    STRICT = "strict-bytes"
    BASE = "obsidian-base-semantics"
    CANVAS = "obsidian-canvas-semantics"
    EXCALIDRAW = "obsidian-excalidraw-semantics"


def classification(path: PurePosixPath) -> Ownership:
    if path.name.endswith(".excalidraw.md"):
        return Ownership.EXCALIDRAW
    if path.suffix == ".canvas":
        return Ownership.CANVAS
    if path.suffix == ".base":
        return Ownership.BASE
    return Ownership.STRICT


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionError("Duplicate JSON key in managed presentation")
        result[key] = value
    return result


def _json(text: str) -> dict:
    def invalid(value: str) -> None:
        raise ProjectionError("Non-finite JSON value in managed presentation")

    def number(value: str) -> int | float:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ProjectionError("Non-finite JSON number in managed presentation")
        return int(numeric) if numeric.is_integer() else numeric

    value = json.loads(text, object_pairs_hook=_object, parse_constant=invalid, parse_float=number)
    if not isinstance(value, dict):
        raise ProjectionError("Managed presentation must be an object")
    return value


def _elements(value: object) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ProjectionError("Invalid managed presentation elements")
    identities = [item.get("id") for item in value]
    if not all(isinstance(identity, str) and identity for identity in identities):
        raise ProjectionError("Missing managed presentation element identity")
    if len(set(identities)) != len(identities):
        raise ProjectionError("Duplicate managed presentation element identity")
    return value


def _drawing_order(elements: list[dict]) -> None:
    """Validate cached fractional keys against array order before discarding keys.

    Pinned Excalidraw fractional-indexing validateOrderKey uses Base62, a
    letter-encoded integer length and no trailing fractional zero (CC0).
    Missing keys in older generated scenes are allowed only as a whole.
    """
    keys = [element.get("index") for element in elements]
    if all(key is None for key in keys):
        return
    previous = None
    for key in keys:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]+", key):
            raise ProjectionError("Invalid Excalidraw ordering key")
        head = key[0]
        length = ord(head) - ord("a") + 2 if head.islower() else ord("Z") - ord(head) + 2
        if (
            len(key) < length
            or key == "A" + "0" * 26
            or key[length:].endswith("0")
            or (previous is not None and key <= previous)
        ):
            raise ProjectionError("Excalidraw ordering keys change or invalidate stacking order")
        previous = key


def _decompress(text: str) -> str:
    """Bounded LZ-string Base64 reader for the plugin's compressed-json encoding.

    Wire algorithm: pieroxy/lz-string (MIT), decompressFromBase64. No execution,
    filesystem access or compression dependency. UTF-16 units match JavaScript.
    """
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    encoded = re.sub(r"[\r\n]", "", text)
    if not re.fullmatch(r"[A-Za-z0-9+/]+={0,3}", encoded):
        raise ProjectionError("Invalid compressed drawing encoding")
    values = [alphabet.index(char) for char in encoded.rstrip("=")]
    position = 0

    def bits(count: int) -> int:
        nonlocal position
        result = 0
        for bit in range(count):
            if position >= len(values) * 6:
                raise ProjectionError("Truncated compressed drawing")
            result |= ((values[position // 6] >> (5 - position % 6)) & 1) << bit
            position += 1
        return result

    first = bits(2)
    if first not in {0, 1}:
        raise ProjectionError("Empty compressed drawing")
    previous = chr(bits(8 if first == 0 else 16))
    dictionary = {3: previous}
    output = [previous]
    size, width, remaining, length = 4, 3, 4, 1
    while True:
        code = bits(width)
        if code == 2:
            return "".join(output).encode("utf-16-le", "surrogatepass").decode("utf-16-le")
        if code in {0, 1}:
            dictionary[size] = chr(bits(8 if code == 0 else 16))
            code = size
            size += 1
            remaining -= 1
        if remaining == 0:
            remaining = 1 << width
            width += 1
        if code in dictionary:
            entry = dictionary[code]
        elif code == size:
            entry = previous + previous[0]
        else:
            raise ProjectionError("Invalid compressed drawing dictionary")
        length += len(entry)
        if length > 4_000_000 or size > 1_000_000:
            raise ProjectionError("Compressed drawing exceeds bounded decoding limit")
        output.append(entry)
        dictionary[size] = previous + entry[0]
        size += 1
        previous = entry
        remaining -= 1
        if remaining == 0:
            remaining = 1 << width
            width += 1


def _cache_text(text: str) -> dict[str, str]:
    result = {}
    position = 0
    for match in re.finditer(r"(?m) \^([A-Za-z0-9_-]+)[ \t]*(?:\n|$)", text):
        identity = match[1]
        if identity in result:
            raise ProjectionError("Duplicate Excalidraw Markdown text identity")
        result[identity] = text[position : match.start()].strip("\n")
        position = match.end()
    if text[position:].strip():
        raise ProjectionError("Unowned text in Excalidraw Markdown cache")
    return result


def _cache_links(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        identity, delimiter, value = line.partition(": ")
        if not delimiter or not identity or identity in result:
            raise ProjectionError("Invalid Excalidraw Markdown link cache")
        result[identity] = value
    return result


def _excalidraw(data: bytes, owner: str) -> dict:
    properties, body = markdown_parts(utf8(data).replace("\r\n", "\n"))
    if (
        properties.get("generated_by") != owner
        or owner != public.OWNER
        or properties.get("source_repository") != public.REPOSITORY
        or properties.get("atlas_workspace_generated") is not True
        or properties.get("excalidraw-plugin") != "parsed"
        or properties.get("atlas_visual_surface") not in ("agent-anatomy", "domain-slice")
    ):
        raise ProjectionError("Excalidraw owner/schema envelope cannot be proven")
    header, separator, content = body.partition("# Excalidraw Data\n")
    if not separator:
        raise ProjectionError("Missing Excalidraw generated section")
    header = re.sub(r"%%\s*$", "", header).rstrip()
    drawing = re.search(r"(?ms)^## Drawing\n```(json|compressed-json)\n(.*?)\n```", content)
    if not drawing or content[drawing.end() :].strip() not in {"", "%%"}:
        raise ProjectionError("Invalid or unowned Excalidraw drawing section")
    scene = _json(_decompress(drawing[2]) if drawing[1] == "compressed-json" else drawing[2])
    if scene.get("type") != "excalidraw" or scene.get("version") != 2:
        raise ProjectionError("Invalid Excalidraw scene schema")
    # These three counters support collaboration bookkeeping only. Everything
    # else, including geometry, stacking order, styles, links and customData stays.
    elements = _elements(scene.get("elements"))
    _drawing_order(elements)
    scene["elements"] = []
    for element in elements:
        normalized = dict(element)
        normalized.pop("index", None)
        # Exact restore defaults from the pinned plugin dependency, not a visual
        # field ignorelist. Non-default values and every binding stay protected.
        normalized.setdefault("created", None)
        normalized.setdefault("hasTextLink", False)
        if normalized.get("boundElements") is None:
            normalized["boundElements"] = []
        if element.get("type") == "text":
            normalized.setdefault("labelPosition", None)
            normalized.setdefault("baseFontSize", None)
        if element.get("type") == "image":
            normalized.setdefault("crop", None)
        for field in ("version", "versionNonce", "updated"):
            if field in normalized and (
                type(normalized[field]) is not int or normalized[field] < 0
            ):
                raise ProjectionError("Invalid Excalidraw bookkeeping counter")
            normalized.pop(field, None)
        scene["elements"].append(normalized)
    sections = re.split(
        r"(?m)^## (Text Elements|Element Links|Embedded Files)\n", content[: drawing.start()]
    )
    if sections[0].strip() or len(sections) % 2 != 1:
        raise ProjectionError("Invalid Excalidraw Markdown sections")
    caches = {}
    for index in range(1, len(sections), 2):
        name, value = sections[index : index + 2]
        if name in caches:
            raise ProjectionError("Duplicate Excalidraw Markdown section")
        caches[name] = _cache_text(value) if name == "Text Elements" else _cache_links(value)
    if "Text Elements" not in caches:
        raise ProjectionError("Missing Excalidraw Markdown text cache")
    for name in ("Element Links", "Embedded Files"):
        caches.setdefault(name, {})
    if scene.get("source") != "research-atlas" and not re.fullmatch(
        r"https://github.com/zsviczian/obsidian-excalidraw-plugin/releases/tag/[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?",
        str(scene.get("source")),
    ):
        raise ProjectionError("Unknown Excalidraw serialization source")
    scene["source"] = "research-atlas"
    if "prevTextMode" in scene:
        if scene["prevTextMode"] not in ("raw", "parsed"):
            raise ProjectionError("Unknown Excalidraw previous editor mode")
        scene.pop("prevTextMode")
    if not isinstance(scene.get("appState"), dict):
        raise ProjectionError("Invalid Excalidraw editor state")
    editor_fields = EDITOR_FIELDS
    if any(e.get("type") == "frame" for e in elements):
        # No generated scene currently uses frame elements. If one is accepted
        # later, frame visibility is presentation meaning, not an editor default.
        editor_fields = editor_fields - {"frameRendering"}
    scene["appState"] = {
        key: value for key, value in scene["appState"].items() if key not in editor_fields
    }
    # The plugin externalizes files on Markdown saves. Normalize only the one
    # generated illustration, bound to its strict SVG asset, image ID and cache.
    files = scene.get("files")
    if not isinstance(files, dict):
        raise ProjectionError("Invalid Excalidraw file store")
    if properties["atlas_visual_surface"] == "agent-anatomy":
        asset = public.anatomy_hero_svg().encode()
        asset_hash = digest(asset)
        file_id = asset_hash[:32]
        route = f"[[{INTERNAL / 'Assets/Agent Anatomy Hero.svg'}]]"
        if caches["Embedded Files"] != {file_id: route}:
            raise ProjectionError("Generated illustration route cannot be proven")
        images = [e for e in scene["elements"] if e.get("type") == "image"]
        if (
            len(images) != 1
            or images[0].get("fileId") != file_id
            or not isinstance(images[0].get("customData"), dict)
            or images[0].get("customData", {}).get("illustration_sha256") != asset_hash
        ):
            raise ProjectionError("Generated illustration identity cannot be proven")
        if files:
            if set(files) != {file_id}:
                raise ProjectionError("Unknown Excalidraw image")
            image = files[file_id]
            allowed = {"id", "mimeType", "dataURL", "created", "lastRetrieved"}
            if (
                not isinstance(image, dict)
                or set(image) - allowed
                or image.get("id") != file_id
                or image.get("mimeType") != "image/svg+xml"
            ):
                raise ProjectionError("Invalid generated illustration metadata")
            expected_url = "data:image/svg+xml;base64," + base64.b64encode(asset).decode("ascii")
            if image.get("dataURL") != expected_url:
                raise ProjectionError("Generated illustration bytes were edited")
            for key in ("created", "lastRetrieved"):
                if key in image and (type(image[key]) is not int or image[key] < 0):
                    raise ProjectionError("Invalid illustration cache timestamp")
        scene["files"] = {file_id: {"asset_sha256": asset_hash}}
    return {"properties": properties, "header": header, "caches": caches, "scene": scene}


def semantic_digest(data: bytes, path: PurePosixPath, owner: str) -> str:
    kind = classification(path)
    if kind == Ownership.BASE:
        return views._base_semantic_digest(data)
    if kind == Ownership.EXCALIDRAW:
        value = _excalidraw(data, owner)
    elif kind == Ownership.CANVAS:
        value = _json(utf8(data))
        if value.get("generated_by") != owner or value.get("canvas_view_schema_version") != "1.0":
            raise ProjectionError("Canvas owner/schema envelope cannot be proven")
        nodes = _elements(value.get("nodes"))
        edges = _elements(value.get("edges"))
        identities = {node["id"] for node in nodes}
        if any(
            edge.get("fromNode") not in identities or edge.get("toNode") not in identities
            for edge in edges
        ):
            raise ProjectionError("Canvas edge points outside the generated node inventory")
        # Official JSON Canvas defaults: absence and explicit defaults agree.
        value["edges"] = [{"fromEnd": "none", "toEnd": "arrow", **edge} for edge in edges]
    else:
        raise ProjectionError("Strict output has no semantic ownership")
    try:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    except (TypeError, ValueError) as exc:
        raise ProjectionError("Invalid managed presentation scalar") from exc
    return digest(encoded)


def record(data: bytes, path: PurePosixPath, owner: str, kind: Ownership | None = None) -> dict:
    kind = kind or classification(path)
    result = {"ownership": kind.value, "sha256": digest(data)}
    if kind != Ownership.STRICT:
        result["semantic_sha256"] = semantic_digest(data, path, owner)
    return result
