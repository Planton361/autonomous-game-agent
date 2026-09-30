"""Generated compatibility entry point from the same Registry as the Obsidian workspace."""

from .validator import Atlas
from .workspace import (
    ANATOMY_PATH,
    DOMAIN_SLICE_PATH,
    GENERATED_NOTICE,
    MAP_PATH,
    note_link,
    ordered_entities,
)


def render_overview(atlas: Atlas) -> str:
    lines = [
        f"# Research Atlas v{atlas.source_atlas_schema}",
        "",
        GENERATED_NOTICE,
        "",
        "[[Home/Research Atlas|Research Atlas Home]] · "
        f"[[{ANATOMY_PATH.with_suffix('')}|Agent Anatomy]] · "
        f"[[{DOMAIN_SLICE_PATH.with_suffix('')}|Evidence, Memory & Retrieval slice]] · "
        f"[[{MAP_PATH.with_suffix('')}|System Anatomy reference]]",
        "",
        "Domains are presentation views. `part_of` is technical Component containment only. "
        "`contributes_to_function` records explicit functional participation. Function membership "
        "does not infer Research relevance, create technical ancestry, or imply "
        "authority/subordination. Scientific targeting is explicit and orthogonal. "
        "Domain, Assembly, folder, YAML and Graph presentation cannot assign "
        "Function membership.",
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
    functions = [n for n in ordered_entities(atlas) if n.type == "Function"]
    if functions:
        lines.extend(["## Functions", ""])
        lines.extend(f"- {note_link(node)}" for node in functions)
        lines.append("")
    return "\n".join(lines)
