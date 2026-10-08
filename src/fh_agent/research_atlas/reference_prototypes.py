"""Isolated #170 editable prototypes; deliberately outside production ownership.

Call prototype_files(atlas) with public Registry data only. No plugin installation,
network, vault discovery or production migration is performed by this module.
"""

import json
from pathlib import PurePosixPath
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .anatomy import _arrow, _shape, _text_item
from .preferred_paths import PRODUCT, preferred_paths
from .private_projection import ProjectionError
from .validator import Atlas

EXCALIDRAW = PRODUCT / "Diagrams/System Overview Prototype.excalidraw.md"
DRAWIO = PRODUCT / "Diagrams/Grounded Contract Prototype.drawio"
PREVIEW = PRODUCT / "Diagrams/Reference Slice Prototypes.md"
# Process arrows are explanatory chronology, NEVER additional Registry triples.
BOXES = (
    ("observation", "DAT-OBSERVATION", 40, 180, "Observation", "Sichtbare Angaben + Belege"),
    ("cortex", "CMP-CORTEX", 40, 330, "Cortex", "Ziel vorschlagen; keine Tasten"),
    ("manager", "CMP-MANAGER", 40, 480, "Manager", "Prüfen · grounden · erlauben"),
    (
        "contract",
        "CON-SKILL-CONTRACT",
        470,
        480,
        "Grounded Contract",
        "Ziel · Grenzen · Stop-Bedingung",
    ),
    ("body", "CMP-BODY", 900, 480, "Body / Bounded Reflex", "Nur im aktiven Contract handeln"),
    (
        "input",
        "CMP-INPUT-EXECUTOR",
        900,
        640,
        "Safety / Input",
        "Fokus · Maske · Rate · Notstopp · Log",
    ),
    ("game", "ENV-GAME-INSTANCE", 900, 800, "GameInstance", "Umgebung reagiert sichtbar"),
    (
        "new-observation",
        "DAT-OBSERVATION",
        470,
        800,
        "Neue Observation",
        "Frische sichtbare Belege",
    ),
    (
        "verifier",
        "CMP-INDEPENDENT-VERIFIER",
        40,
        800,
        "Independent Verifier",
        "Ergebnis unabhängig prüfen",
    ),
    (
        "result",
        "CON-VERIFIER-RESULT",
        40,
        640,
        "VerifierResult",
        "success · progress · failure · abstain",
    ),
    (
        "transition",
        "CMP-MANAGER",
        470,
        640,
        "Manager-Transition",
        "Fortsetzen · abschließen · stoppen",
    ),
    (
        "close",
        "CMP-MANAGER",
        470,
        330,
        "Schließen / suspendieren",
        "Erst danach bedingt neu planen",
    ),
    (
        "retrieval",
        "CMP-MEM-RETRIEVAL",
        470,
        180,
        "Memory Retrieval",
        "Begrenzter Kontext; keine Eingaben",
    ),
    ("memory", "CMP-MEMORY", 900, 180, "Memory", "Erfahrung + Herkunft bewahren"),
)
FLOWS = (
    ("observation", "cortex", ((200, 280), (200, 330)), ""),
    ("cortex", "manager", ((200, 430), (200, 480)), "Vorschlag"),
    ("manager", "contract", ((360, 530), (470, 530)), "Erlaubnis"),
    ("contract", "body", ((790, 530), (900, 530)), ""),
    ("body", "input", ((1060, 580), (1060, 640)), ""),
    ("input", "game", ((1060, 740), (1060, 800)), ""),
    ("game", "new-observation", ((900, 850), (790, 850)), ""),
    ("new-observation", "verifier", ((470, 850), (360, 850)), ""),
    ("verifier", "result", ((200, 800), (200, 740)), ""),
    ("result", "transition", ((360, 690), (470, 690)), "Ergebnis"),
    ("transition", "contract", ((630, 640), (630, 580)), "gültig"),
    ("transition", "close", ((790, 690), (840, 690), (840, 380), (790, 380)), "Stop / Replan"),
    ("close", "cortex", ((470, 380), (360, 380)), "bedingt"),
    ("memory", "retrieval", ((900, 230), (790, 230)), ""),
    (
        "retrieval",
        "cortex",
        ((470, 230), (410, 230), (410, 305), (200, 305), (200, 330)),
        "Kontext",
    ),
)
REGISTRY_TRIPLES = (
    ("CMP-CORTEX", "supplies", "IF-CORTEX-MANAGER"),
    ("CMP-MANAGER", "consumes", "IF-CORTEX-MANAGER"),
    ("CMP-MANAGER", "supplies", "CON-SKILL-CONTRACT"),
    ("CMP-BODY", "executes", "CON-SKILL-CONTRACT"),
    ("CON-SKILL-CONTRACT", "constrains", "CMP-BODY"),
    ("CMP-INDEPENDENT-VERIFIER", "supplies", "CON-VERIFIER-RESULT"),
    ("CMP-MANAGER", "consumes", "CON-VERIFIER-RESULT"),
)


def _excalidraw(atlas: Atlas) -> bytes:
    paths = preferred_paths(atlas)
    elements = [
        _text_item("slice-title", "VOM SEHEN ZUR NÄCHSTEN ENTSCHEIDUNG", 40, 30, 1200, size=32),
        _text_item(
            "slice-subtitle",
            "Soll-Zyklus · jeder Versuch bleibt begrenzt · unabhängige Prüfung",
            40,
            85,
            1200,
            size=22,
        ),
    ]
    for key, identity, x, y, title, detail in BOXES:
        link = f"[[{paths[identity].with_suffix('')}]]"
        color = "#EAF4F0" if key in {"memory", "retrieval"} else "#EDF3FA"
        elements += [
            _shape(
                key,
                (x, y, 320, 100),
                background=color,
                stroke="#426B86",
                link=link,
                custom_data={"card": key, "identity": identity, "prototype": True},
            ),
            _text_item(
                key + "-title",
                title,
                x + 10,
                y + 12,
                300,
                size=20,
                link=link,
                custom_data={"card": key, "role": "title"},
            ),
            _text_item(
                key + "-detail",
                detail,
                x + 14,
                y + 52,
                292,
                size=17,
                custom_data={"card": key, "role": "detail"},
            ),
        ]
    for source, target, points, label in FLOWS:
        element = _arrow(
            source + ":" + target, points[0], points[-1], presentation_flow=(source, target)
        )
        element["points"] = [[x - points[0][0], y - points[0][1]] for x, y in points]
        element["width"] = max(x for x, _ in points) - min(x for x, _ in points)
        element["height"] = max(y for _, y in points) - min(y for _, y in points)
        element["strokeStyle"] = "dashed" if source in {"memory", "retrieval"} else "solid"
        elements.append(element)
        if label:
            x, y = points[0]
            # Place captions in open routing corridors, not over an arrow or node.
            label_positions = {
                ("cortex", "manager"): (235, 442),
                ("manager", "contract"): (372, 496),
                ("result", "transition"): (373, 655),
                ("transition", "contract"): (644, 601),
                ("transition", "close"): (854, 393),
                ("close", "cortex"): (374, 343),
                ("retrieval", "cortex"): (310, 285),
            }
            x, y = label_positions[source, target]
            elements.append(_text_item(source + target + "-caption", label, x, y, 120, size=16))
    for index, text in enumerate(
        (
            "Fortsetzung: nur durch denselben weiterhin aktiven Contract. "
            "Kein neuer Auftrag pro Schritt.",
            "Soll: Prozesspfeile sind keine Registry-Relationen. Ist: siehe verlinkte Seiten; "
            "keine zertifizierte Live-Schleife.",
            "Offen: gerankter Retrieval-Kontext, Consolidation und Admission. "
            "Body-Gewichte bleiben im Mission Run eingefroren.",
            "Stop blockiert weitere Eingaben; "
            "frühere ausgeführte Schritte und Belege bleiben erhalten.",
        )
    ):
        elements.append(_text_item(f"legend-{index}", text, 40, 960 + index * 37, 1200, size=18))
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "AGA #170 isolated prototype",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#FFFFFF", "gridSize": None},
        "files": {},
    }
    text = "---\nexcalidraw-plugin: parsed\ntags: [aga-reference-prototype]\n---\n\n"
    text += (
        "PROTOTYP — keine Produktionsintegration oder neue Architekturautorität.\n\n"
        "%%\n# Excalidraw Data\n\n## Text Elements\n\n"
    )
    text += "\n\n".join(f"{e['rawText']} ^{e['id']}" for e in elements if e["type"] == "text")
    text += "\n\n## Element Links\n\n" + "\n\n".join(
        f"{e['id']}: {e['link']}" for e in elements if e.get("link")
    )
    text += (
        "\n\n## Drawing\n```json\n"
        + json.dumps(scene, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n```\n%%\n"
    )
    return text.encode()


def _drawio(atlas: Atlas) -> bytes:
    paths = preferred_paths(atlas)
    doc = ET.Element(
        "mxfile", host="AGA isolated offline prototype", version="0.7.1", compressed="false"
    )

    def page(name, nodes, edges):
        diagram = ET.SubElement(doc, "diagram", id=name, name=name)
        model = ET.SubElement(
            diagram,
            "mxGraphModel",
            dx="1000",
            dy="900",
            grid="1",
            gridSize="10",
            page="1",
            pageWidth="1000",
            pageHeight="1100",
        )
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        for key, identity, x, y, label in nodes:
            parent = root
            if identity:
                parent = ET.SubElement(
                    root,
                    "UserObject",
                    id=key,
                    label=label,
                    identity=identity,
                    link="obsidian://open?file="
                    + quote(str(paths[identity].with_suffix("")), safe=""),
                )
            cell = ET.SubElement(
                parent,
                "mxCell",
                **({} if identity else {"id": key, "value": label}),
                style="rounded=1;whiteSpace=wrap;html=0;fillColor=#EDF3FA;strokeColor=#426B86;fontColor=#21384B;fontSize=20;spacing=12;",
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                cell,
                "mxGeometry",
                x=str(x),
                y=str(y),
                width="360",
                height="100",
                **{"as": "geometry"},
            )
        for index, (source, target, label, semantics) in enumerate(edges):
            cell = ET.SubElement(
                root,
                "mxCell",
                id=f"edge-{index}",
                value=label,
                source=source,
                target=target,
                style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;endArrow=block;fontSize=17;labelBackgroundColor=#FFFFFF;strokeColor=#426B86;",
                edge="1",
                parent="1",
                semantics=semantics,
            )
            ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        return root

    page(
        "1 · Vorschlag und Erlaubnis",
        (
            (
                "proposal",
                "CMP-CORTEX",
                60,
                70,
                "Cortex schlägt Ziel und Skill vor\nKeine Eingabeberechtigung",
            ),
            ("validate", "CMP-MANAGER", 60, 250, "Manager prüft Fähigkeit\nNur verfügbare Skills"),
            (
                "ground",
                "CMP-MANAGER-GROUNDING",
                60,
                430,
                "Sichtbares Ziel eindeutig zuordnen\nBei Mehrdeutigkeit ablehnen",
            ),
            (
                "authorize",
                "CON-SKILL-CONTRACT",
                60,
                610,
                "Manager autorisiert Contract\nZiel, Grenzen, Ende",
            ),
            (
                "reject",
                "CMP-MANAGER",
                560,
                250,
                "Ablehnung vor Contract\nKein neuer Auftrag, keine Eingabe",
            ),
            (
                "handoff",
                "CMP-BODY",
                560,
                610,
                "Zu Phase 2: Body-Ausführung\nNur wenn Contract aktiv",
            ),
        ),
        (
            ("proposal", "validate", "PlannerOutput", "process"),
            ("validate", "ground", "verfügbar", "process"),
            ("ground", "authorize", "ausreichend belegt", "process"),
            ("validate", "reject", "nicht verfügbar", "process"),
            ("ground", "reject", "Ziel unklar", "process"),
            ("authorize", "handoff", "aktive Berechtigung", "process"),
        ),
    )
    page(
        "2 · Ausführung und Rückkehr",
        (
            (
                "contract",
                "CON-SKILL-CONTRACT",
                60,
                60,
                "Derselbe aktive Contract\nGrenzen bleiben gültig",
            ),
            ("body", "CMP-BODY", 60, 240, "Body / Bounded Reflex\nErlaubten Vorschlag erzeugen"),
            (
                "input",
                "CMP-INPUT-EXECUTOR",
                60,
                420,
                "Safety / Input prüfen\nFokus, Maske, Rate, Stop, Log",
            ),
            ("game", "ENV-GAME-INSTANCE", 60, 600, "GameInstance\nSichtbare Umgebungsreaktion"),
            ("obs", "DAT-OBSERVATION", 560, 600, "Neue Observation\nBelege zur Reaktion"),
            (
                "verify",
                "CMP-INDEPENDENT-VERIFIER",
                560,
                420,
                "Independent Verifier\nErfolg, Fortschritt, Fehler, abstain",
            ),
            (
                "result",
                "CON-VERIFIER-RESULT",
                560,
                240,
                "VerifierResult\nErgebnis mit Belegreferenzen",
            ),
            (
                "transition",
                "CMP-MANAGER",
                560,
                60,
                "Manager-Transition\nFortsetzen, Ende oder Phase 3",
            ),
        ),
        tuple(
            (a, b, label, "process")
            for a, b, label in (
                ("contract", "body", ""),
                ("body", "input", ""),
                ("input", "game", ""),
                ("game", "obs", ""),
                ("obs", "verify", ""),
                ("verify", "result", ""),
                ("result", "transition", ""),
                ("transition", "contract", "nur weiterhin gültig"),
            )
        ),
    )
    page(
        "3 · Ablehnung, Stop und Replan",
        (
            (
                "reject",
                "CMP-MANAGER",
                60,
                70,
                "Ablehnung vor Contract\nNoch kein neuer Versuch erlaubt",
            ),
            (
                "reject-log",
                "CMP-EVIDENCE-LEDGER",
                60,
                260,
                "Ablehnung mit Belegen protokollieren\nKeine neue Eingabe",
            ),
            (
                "stop",
                "CMP-SAFETY-FILTER",
                560,
                70,
                "Aktiver Stop / Sicherheitsblock\nWeitere Eingaben sofort hemmen",
            ),
            (
                "close",
                "CMP-MANAGER",
                560,
                260,
                "Manager schließt / suspendiert\nAktuellen Contract beenden",
            ),
            (
                "history",
                "CMP-EVIDENCE-LEDGER",
                560,
                450,
                "Frühere Schritte bleiben erhalten\nAusgeführte Aktionen + Belege",
            ),
            ("replan", "CMP-CORTEX", 560, 640, "Bedingt neu planen\nNur bei erlaubter Fortsetzung"),
            ("end", "CMP-MANAGER", 60, 640, "Mission terminal? Stop\nKeine Fortsetzung erzwingen"),
        ),
        (
            ("reject", "reject-log", "", "process"),
            ("stop", "close", "", "process"),
            ("close", "history", "", "process"),
            ("history", "replan", "nicht terminal", "process"),
            ("history", "end", "terminal", "process"),
        ),
    )
    # Separate page keeps actor→payload consumes visibly distinct from chronology.
    nodes, edges = [], []
    for index, (source, relation, target) in enumerate(REGISTRY_TRIPLES):
        y = 40 + index * 145
        nodes.extend(
            (
                (f"s{index}", source, 40, y, atlas.entities[source].name),
                (f"t{index}", target, 580, y, atlas.entities[target].name),
            )
        )
        edges.append((f"s{index}", f"t{index}", relation, f"registry:{source}:{relation}:{target}"))
    page("4 · Registry: Source → Target", nodes, edges)
    ET.indent(doc)
    return ET.tostring(doc, encoding="utf-8", xml_declaration=True)


def prototype_files(atlas: Atlas) -> dict[PurePosixPath, bytes]:
    declared = {(e.source, e.relation, e.target) for e in atlas.relationships}
    if not set(REGISTRY_TRIPLES) <= declared:
        raise ProjectionError("Prototype relation differs from Registry")
    preview = """# Reference Slice Prototypes

Isolierte Kandidaten, keine Produktionsintegration. Excalidraw 2.28.1 und Drawio
`drawio-editor` 0.7.1 mit lokalem Offline-Editor. Keine private Vault-Konfiguration.
Prozesspfeile erklären den Soll-Ablauf; nur Drawio-Seite 4 zeigt Registry-Triple.
`consumes` zeigt vom Verbraucher zum Datenpaket. Keine neuen technischen Eltern.

## System Overview · editierbarer Prototyp

![[Research Map/Diagrams/System Overview Prototype.excalidraw]]

[[Research Map/Diagrams/System Overview Prototype.excalidraw|Excalidraw öffnen]]

## Grounded Contract · vier getrennte Phasen

![[Research Map/Diagrams/Grounded Contract Prototype.drawio]]

[[Research Map/Diagrams/Grounded Contract Prototype.drawio|Drawio offline öffnen]]

Die Seitenfolge ist Vorschlag/Erlaubnis → Ausführung/Rückkehr → Stop/Replan;
die separate vierte Seite ist technische Relationsinspektion, keine Zeitfolge.

## Ohne Plugins weiterlesen

![[Research Map/Diagrams/System Overview.svg]]

[[Research Map/Guides/System Overview|System Overview]] ·
[[Research Map/Diagrams/Execution Flow|Execution Flow und vollständiger Markdown-Fallback]] ·
[[Research Map/Diagrams/Interaction Map|Unverändertes vollständiges Relationsledger]] ·
[[Research Map Home|Home]]
"""
    return {EXCALIDRAW: _excalidraw(atlas), DRAWIO: _drawio(atlas), PREVIEW: preview.encode()}
