"""Public #170 editable candidates, sharing the native-proven B3 renderer.

Call prototype_files(atlas) with public Registry data only. No plugin installation,
network, vault discovery or production migration is performed by this module.
"""

from pathlib import PurePosixPath

from .diagram_svg import (
    BOXES as BOXES,
)
from .diagram_svg import (
    CANDIDATE_DRAWIO,
    CANDIDATE_EXCALIDRAW,
    REGISTRY_TRIPLES,
    _excalidraw,
    candidate_drawio,
    candidate_system_overview,
)
from .diagram_svg import (
    FLOWS as FLOWS,
)
from .diagram_svg import (
    _drawio as _drawio,
)
from .diagram_svg import (
    candidate_navigation as candidate_navigation,
)
from .preferred_paths import PRODUCT
from .private_projection import ProjectionError
from .validator import Atlas

EXCALIDRAW = PRODUCT / "Diagrams/System Overview Prototype.excalidraw.md"
DRAWIO = PRODUCT / "Diagrams/Grounded Contract Prototype.drawio"
PREVIEW = PRODUCT / "Diagrams/Reference Slice Prototypes.md"


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
    """Unowned final-path trials; ordinary Guide counterparts supply routing."""
    return {
        CANDIDATE_EXCALIDRAW: candidate_system_overview(atlas),
        CANDIDATE_DRAWIO: candidate_drawio(atlas),
    }
