"""Accepted final product routes; storage never selects an architectural parent."""

from pathlib import PurePosixPath

from .private_projection import ProjectionError, validate_portable_paths
from .private_views import _identity_filename_stem, identity_page_paths
from .validator import Atlas

PRODUCT = PurePosixPath("Research Map")
INTERNAL = PurePosixPath("_Research Map Internals")
HOME = PurePosixPath("Research Map Home.md")
FAMILIES = {
    "System": "System",
    "Component": "Components",
    "Function": "Functions",
    "Interface": "Interfaces",
    "Contract": "Contracts",
    "DataArtifact": "Data Artifacts",
    "MeasurementPoint": "Measurements",
    "Environment": "Environments",
    "ResearchQuestion": "Program/Research Questions",
    "ResearchThread": "Program/Research Threads",
    "Decision": "Project/Decisions",
}


def containment_paths(atlas: Atlas, identity: str) -> tuple[tuple[str, ...], ...]:
    parents: dict[str, set[str]] = {}
    for edge in atlas.relationships:
        if edge.relation == "part_of":
            parents.setdefault(edge.source, set()).add(edge.target)

    def visit(subject: str, active: frozenset[str]) -> tuple[tuple[str, ...], ...]:
        if subject in active:
            raise ProjectionError("Component containment cycle")
        if not parents.get(subject):
            return ((subject,),)
        return tuple(
            trail + (subject,)
            for parent in sorted(parents[subject])
            for trail in visit(parent, active | {subject})
        )

    return visit(identity, frozenset())


def preferred_paths(atlas: Atlas) -> dict[str, PurePosixPath]:
    identities = set(identity_page_paths(atlas)) | {
        n.id for n in atlas.entities.values() if n.type in FAMILIES
    }
    stems = {i: _identity_filename_stem(atlas.entities[i].name) for i in identities}
    # Same-title siblings must disambiguate every occurrence, including ancestors.
    names: dict[str, str] = {}
    for identity in sorted(identities):
        node = atlas.entities[identity]
        stem, unsafe = stems[identity]
        duplicate = (
            sum(
                atlas.entities[other].type == node.type
                and stems[other][0].casefold() == stem.casefold()
                for other in identities
            )
            > 1
        )
        names[identity] = stem + (f" — {identity}" if unsafe or duplicate else "")
    result = {}
    for identity in sorted(identities):
        node = atlas.entities[identity]
        folder = PRODUCT / FAMILIES[node.type]
        if node.type == "Component":
            trails = containment_paths(atlas, identity)
            if len(trails) == 1 and atlas.entities[trails[0][0]].type == "System":
                folder = folder.joinpath(*(names[i] for i in trails[0][1:-1]))
            else:
                result[identity] = folder / "Identities" / f"{stems[identity][0]} — {identity}.md"
                continue
        result[identity] = folder / (names[identity] + ".md")
    validate_portable_paths(result.values())
    if any(len(path.name.encode()) > 240 for path in result.values()):
        raise ProjectionError("Preferred filename exceeds portable limit")
    return result
