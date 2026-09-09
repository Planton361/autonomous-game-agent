"""Pure deterministic Markdown view; registry remains the sole Atlas authority."""

from .schema import Component
from .validator import Atlas

PILOTS = frozenset({"CMP-MEM-RETRIEVAL", "CMP-CORTEX", "CMP-MANAGER"})


def render_overview(atlas: Atlas) -> str:
    system = atlas.entities["SYS-AGA"]
    lines = [
        "# Research Atlas v0.1",
        "",
        f"{system.id} — {system.name}",
        "",
        "Generated from registry/{nodes,relationships,evidence}.yaml; do not edit.",
        "Domains group navigation only; they are neither technical parents nor canonical taxonomy.",
        "Connections describe targets as well as implementation; consult each node's status.",
        "Dossier sections point into the registry; their ID lists do not author relationships.",
        "",
    ]
    for domain in sorted(atlas.entities.values(), key=lambda n: n.id):
        if domain.type != "Domain":
            continue
        lines.extend([f"## {domain.id} — {domain.name}", ""])
        members = sorted(
            {
                edge.source
                for edge in atlas.relationships
                if edge.relation == "presented_in_domain"
                and edge.target == domain.id
                and edge.source in PILOTS
            }
        )
        for node_id in members:
            component = atlas.entities[node_id]
            assert isinstance(component, Component)
            status = component.technical
            lines.append(
                f"- [{component.id}](dossiers/{component.id}.md) — {component.name}: "
                f"{status.architecture_authority}; {status.implementation_status}; "
                f"{status.verification_status}; research mapping: {component.research_mapping}."
            )
        if not members:
            lines.append("No pilot component mapped.")
        lines.append("")
    lines.extend(["## Interface and contract connections", ""])
    for edge in sorted(atlas.relationships, key=lambda r: (r.source, r.relation, r.target)):
        if edge.source in PILOTS and atlas.entities[edge.target].type in {"Interface", "Contract"}:
            lines.append(f"- `{edge.source}` — {edge.relation} → `{edge.target}`")

    def count(kind: str) -> int:
        return sum(n.type == kind for n in atlas.entities.values())

    lines.extend(
        [
            "",
            "## Indicators",
            "",
            f"{len(PILOTS)} pilot components; {count('Domain')} presentation domains; "
            f"{count('MeasurementPoint')} measurement mappings; "
            f"{count('Evidence')} evidence records.",
            f"Papers: {count('Paper')}; findings: {count('Finding')}; "
            f"contradictions: {sum(r.relation == 'contradicts' for r in atlas.relationships)}.",
            "No literature review, gap analysis, or automatic research-status promotion "
            "in this pilot.",
            "",
        ]
    )
    return "\n".join(lines)
