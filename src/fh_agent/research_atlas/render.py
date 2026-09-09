"""Generated compatibility entry point from the same Registry as the Obsidian workspace."""

from .validator import Atlas
from .workspace import GENERATED_NOTICE, note_link, ordered_entities


def render_overview(atlas: Atlas) -> str:
    lines = [
        "# Research Atlas v0.2",
        "",
        GENERATED_NOTICE,
        "",
        "[[Home/Research Atlas|Research Atlas Home]] · "
        "[[Assets/Excalidraw/System Anatomy.excalidraw|System Anatomy]]",
        "",
        "Domains are presentation views. Technical ancestry derives only from `part_of`. "
        "Statuses and relationships are in generated record notes, backed by Registry.",
        "",
    ]
    for domain in ordered_entities(atlas):
        if domain.type != "Domain":
            continue
        lines.extend([f"## {domain.name}", "", note_link(domain), ""])
        members = {
            e.source
            for e in atlas.relationships
            if e.relation == "presented_in_domain" and e.target == domain.id
        }
        lines += [f"- {note_link(n)}" for n in ordered_entities(atlas) if n.id in members]
        lines.append("")
    return "\n".join(lines)
