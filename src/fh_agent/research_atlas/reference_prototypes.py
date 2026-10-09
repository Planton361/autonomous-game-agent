"""Isolated #170 editable prototypes; deliberately outside production ownership.

Call prototype_files(atlas) with public Registry data only. No plugin installation,
network, vault discovery or production migration is performed by this module.
"""

from pathlib import PurePosixPath
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .diagram_svg import (
    BOXES as BOXES,
)
from .diagram_svg import (
    CANDIDATE_DRAWIO,
    CANDIDATE_EXCALIDRAW,
    REGISTRY_TRIPLES,
    _excalidraw,
    candidate_navigation,
    candidate_system_overview,
)
from .diagram_svg import (
    FLOWS as FLOWS,
)
from .preferred_paths import PRODUCT, preferred_paths
from .private_projection import ProjectionError
from .validator import Atlas

EXCALIDRAW = PRODUCT / "Diagrams/System Overview Prototype.excalidraw.md"
DRAWIO = PRODUCT / "Diagrams/Grounded Contract Prototype.drawio"
PREVIEW = PRODUCT / "Diagrams/Reference Slice Prototypes.md"


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


def candidate_files(atlas: Atlas) -> dict[PurePosixPath, bytes]:
    """B2 final-path trials, still isolated until ownership AND native gates pass.

    Never called by production packaging. No owner marker or ambiguous external
    Obsidian URI is emitted. The two files require the existing Guide counterpart;
    the old prototype companion is deliberately not shipped with these trials.
    """
    source = prototype_files(atlas)
    doc = ET.fromstring(source[DRAWIO])
    for element in doc.iter("UserObject"):
        # Native routing is not verified for multi-Vault use. Remove the unsafe
        # protocol URI entirely; the adjacent ordinary Guide supplies every target.
        element.attrib.pop("link")
        identities = [element.attrib["identity"]]
        label = element.attrib["label"]
        if "Bounded Reflex" in label:
            identities.append("CMP-BOUNDED-REFLEX")
        if "Safety / Input" in label:
            identities.insert(0, "CMP-SAFETY-FILTER")
        element.set("counterpart_ids", " ".join(identities))
    for element in doc.iter("mxCell"):
        if element.get("value") == "PlannerOutput":
            element.set("counterpart_ids", "CON-PLANNER-OUTPUT")
    ET.indent(doc)
    # Validate declarations even if prototype_files changes its own validation.
    candidate_navigation(atlas)
    return {
        CANDIDATE_EXCALIDRAW: candidate_system_overview(atlas),
        CANDIDATE_DRAWIO: ET.tostring(doc, encoding="utf-8", xml_declaration=True),
    }
