"""Validate the complete offline registry without loading referenced runtime code."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from .schema import (
    PREFIXES,
    Entity,
    EvidenceRegistry,
    NodeRegistry,
    Relationship,
    RelationshipRegistry,
)

TECHNICAL = frozenset(
    {
        "System",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
        "MeasurementPoint",
        "Environment",
    }
)
ACTORS = frozenset({"System", "Component"})
PAYLOADS = frozenset({"Interface", "Contract", "DataArtifact"})
ALL_TYPES = frozenset(PREFIXES)
# Explicit admissible pairs; lifecycle relations additionally require equal endpoint types.
RELATION_PAIRS = {
    "part_of": ({"Component"}, ACTORS),
    "supplies": (ACTORS, PAYLOADS),
    "consumes": (ACTORS, PAYLOADS),
    "controls": (ACTORS, ACTORS | {"Environment"}),
    "constrains": ({"Contract", "Decision"}, TECHNICAL),
    "proposes_to": (ACTORS, ACTORS),
    "grounds": (ACTORS, PAYLOADS),
    "executes": (ACTORS, {"Contract"}),
    "observes": (ACTORS, {"Environment", "DataArtifact", "MeasurementPoint"}),
    "verifies": (ACTORS, {"Contract", "DataArtifact"}),
    "updates": (ACTORS, {"DataArtifact"}),
    "retrieves_from": (ACTORS, {"DataArtifact"}),
    "measured_at": ({"MeasurementPoint"}, {"Component", "Interface", "Contract", "DataArtifact"}),
    "studied_by": (TECHNICAL | {"ResearchThread"}, {"Paper"}),
    "supports": ({"Evidence", "Finding", "Paper", "Decision"}, ALL_TYPES - {"Domain"}),
    "contradicts": ({"Evidence", "Finding", "Paper"}, ALL_TYPES - {"Domain"}),
    "derived_from": (ALL_TYPES - {"Domain"}, {"Evidence", "Finding", "Paper", "DataArtifact"}),
    "supersedes": (ALL_TYPES - {"Domain"}, ALL_TYPES - {"Domain"}),
    "decomposed_into": ({"Component"}, {"Component"}),
    "research_suggests_decomposition": ({"ExperimentLead"}, {"Component"}),
    "related_to_research_question": (ALL_TYPES - {"Domain"}, {"ResearchQuestion"}),
    "presented_in_domain": (TECHNICAL | {"ResearchQuestion", "ResearchThread"}, {"Domain"}),
}


@dataclass(frozen=True)
class Atlas:
    entities: Mapping[str, Entity]
    relationships: tuple[Relationship, ...]

    def ancestors(self, node_id: str) -> frozenset[str]:
        """Only authored part_of contributes; domains and work graph edges never do."""
        if node_id not in self.entities:
            raise ValueError(f"Unknown ID: {node_id}")
        result: set[str] = set()
        pending = [node_id]
        while pending:
            current = pending.pop()
            for edge in self.relationships:
                if edge.relation == "part_of" and edge.source == current:
                    if edge.target not in result:
                        result.add(edge.target)
                        pending.append(edge.target)
        return frozenset(result)


def validate_registry(nodes: object, relationships: object, evidence: object) -> Atlas:
    node_file = NodeRegistry.model_validate(nodes)
    edge_file = RelationshipRegistry.model_validate(relationships)
    evidence_file = EvidenceRegistry.model_validate(evidence)
    entities: dict[str, Entity] = {}
    for node in (*node_file.nodes, *evidence_file.evidence):
        if node.id in entities:
            raise ValueError(f"Duplicate ID: {node.id}")
        if not re.fullmatch(re.escape(PREFIXES[node.type]) + r"-[A-Z0-9]+(?:-[A-Z0-9]+)*", node.id):
            raise ValueError(f"ID prefix/type mismatch: {node.id}")
        entities[node.id] = node
    for node in node_file.nodes:
        if node.type == "ResearchThread":
            for reference in node.ordered_refs:
                target = entities.get(reference)
                if target is None:
                    raise ValueError(f"Dangling ResearchThread reference: {reference}")
                if target.type not in {
                    "Component",
                    "Interface",
                    "Contract",
                    "DataArtifact",
                    "MeasurementPoint",
                }:
                    raise ValueError(f"Illegal ResearchThread reference type: {target.type}")
    seen: set[tuple[str, str, str]] = set()
    for edge in edge_file.relationships:
        if edge.source not in entities or edge.target not in entities:
            raise ValueError(f"Dangling relationship: {edge.source} -> {edge.target}")
        key = (edge.relation, edge.source, edge.target)
        if key in seen:
            raise ValueError(f"Duplicate relationship: {key}")
        seen.add(key)
        source, target = entities[edge.source], entities[edge.target]
        sources, targets = RELATION_PAIRS[edge.relation]
        if source.type not in sources or target.type not in targets:
            raise ValueError(f"Illegal {edge.relation} type pairing: {source.type}/{target.type}")
        if edge.relation in {"supersedes", "decomposed_into"}:
            if source.type != target.type or source.id == target.id:
                raise ValueError("Lifecycle edges require distinct IDs of the same type")
        if edge.decision_id is not None:
            decision = entities.get(edge.decision_id)
            if decision is None or decision.type != "Decision":
                raise ValueError("Approval reference must resolve to Decision")
            if edge.relation != "decomposed_into":
                raise ValueError("decision_id is reserved for accepted decomposition")
            if decision.decision_scope != "architecture":
                raise ValueError("Decomposition requires architecture-scoped Decision")
        if edge.relation == "decomposed_into" and edge.decision_id is None:
            raise ValueError("decomposed_into requires explicit Decision approval")
    # Check approval support only after every relationship has passed structural validation.
    approved_decisions = {
        edge.target
        for edge in edge_file.relationships
        if edge.relation == "supports"
        and entities[edge.source].type == "Evidence"
        and entities[edge.source].provenance_kind == "project_decision"
        and entities[edge.target].type == "Decision"
    }
    for edge in edge_file.relationships:
        if edge.relation == "decomposed_into" and edge.decision_id not in approved_decisions:
            raise ValueError("Decomposition Decision requires supporting project_decision Evidence")
    atlas = Atlas(MappingProxyType(entities), edge_file.relationships)
    for node_id in entities:
        if node_id in atlas.ancestors(node_id):
            raise ValueError(f"Technical part_of cycle: {node_id}")
    validate_presentation(atlas)
    return atlas


def validate_presentation(atlas: Atlas) -> None:
    """Depth is a view constraint, never a source of technical parent edges."""
    for node in atlas.entities.values():
        level = node.atlas_level
        if level == "L0" and node.type != "System":
            raise ValueError("L0 is reserved for System presentation")
        if level == "L1" and node.type != "Domain":
            raise ValueError("L1 is reserved for presentation Domains")
        if level in {"L2", "L3"} and node.type not in TECHNICAL - {"System"}:
            raise ValueError("L2/L3 require technical records")
        if node.overview_visibility == "main" and level not in {"L0", "L1", "L2"}:
            raise ValueError("Main presentation requires L0/L1/L2")
        if node.overview_visibility == "expansion" and level not in {"L2", "L3"}:
            raise ValueError("Expansion presentation requires L2/L3")
        if level in {"L2", "L3"}:
            if not any(
                e.relation == "presented_in_domain" and e.source == node.id
                for e in atlas.relationships
            ):
                raise ValueError("L2/L3 technical record requires at least one presentation Domain")
        if node.type != "Component":
            continue
        if node.technical.architecture_authority == "implementation-derived" and level != "L3":
            raise ValueError("implementation-derived Component must be marked L3")
        if level == "L3":
            if node.overview_visibility != "expansion":
                raise ValueError("L3 Component requires expansion presentation")
            parents = [
                atlas.entities[e.target]
                for e in atlas.relationships
                if e.relation == "part_of" and e.source == node.id
            ]
            if not parents or any(p.type != "Component" or p.atlas_level != "L2" for p in parents):
                raise ValueError("L3 Component requires part_of L2 Component")


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently overwriting the first SOT."""


def _unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_registry(root: Path) -> Atlas:
    """Read and validate the three SOT files independently of generated views."""
    payloads = []
    for filename in ("nodes.yaml", "relationships.yaml", "evidence.yaml"):
        payloads.append(
            yaml.load(
                (root / "registry" / filename).read_text(encoding="utf-8"), Loader=UniqueKeyLoader
            )
        )
    return validate_registry(*payloads)
