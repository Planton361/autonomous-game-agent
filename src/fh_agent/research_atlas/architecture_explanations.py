"""Reviewed presentation inputs, never Registry, runtime or scientific authority."""

import ast
import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, ValidationError, model_validator

from .preferred_paths import preferred_paths
from .private_projection import (
    COMMIT,
    REPOSITORY,
    ProjectionError,
    no_symlink_boundary,
    read_yaml,
    utf8,
)
from .schema import Record, RelationName, Text
from .validator import Atlas

SOURCE = PurePosixPath("docs/research-atlas/architecture_explanations.yaml")
AREAS = (
    "Observation & Perception",
    "Evidence, Memory & Retrieval",
    "Strategic Reasoning",
    "Executive Control",
    "Action & Safety",
    "Independent Verification",
    "Between-Mission-Run Learning",
)
GUIDES = ("System Overview", "Experience to Knowledge", "Scientific Experiment")
ESSAY = "Das Experiment verstehen"
REFERENCE_TYPES = {
    "CMP-CORTEX": "Component",
    "CMP-MANAGER": "Component",
    "CMP-MEMORY": "Component",
    "DAT-OBSERVATION": "DataArtifact",
    "CON-SKILL-CONTRACT": "Contract",
    "CON-VERIFIER-RESULT": "Contract",
    "IF-CORTEX-MANAGER": "Interface",
    "FUNC-EXECUTIVE-CONTROL": "Function",
}
TOKEN = re.compile(r"\[\[(id|guide):([^\]]+)\]\]")


class SourceLocator(Record):
    kind: Literal["normative", "implementation", "test"]
    path: Text
    locator: Text
    line: int = Field(gt=0, strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision: COMMIT | None = None

    @model_validator(mode="after")
    def public_path(self) -> "SourceLocator":
        path = PurePosixPath(self.path)
        prefix = {"normative": "docs", "implementation": "src", "test": "tests"}[self.kind]
        if (
            not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or path.parts[0] != prefix
            or str(path) != self.path
            or any(c in self.path for c in "\\\r\n[]<>|#")
        ):
            raise ValueError("Explanation locator must be a public repository path of its kind")
        return self


class Explanation(Record):
    area: Literal[
        "Observation & Perception",
        "Evidence, Memory & Retrieval",
        "Strategic Reasoning",
        "Executive Control",
        "Action & Safety",
        "Independent Verification",
        "Between-Mission-Run Learning",
    ]
    responsibility: Text
    why: Text
    normative: Text
    mechanism: Text
    inputs: Text
    outputs: Text
    implementation: Text
    limitations: Text
    example: Text
    research_relevance: Text
    sources: tuple[Text, ...] = Field(min_length=1)


class Section(Record):
    title: Text
    text: Text


class Guide(Record):
    intro: Text
    sections: tuple[Section, ...] = Field(min_length=1)
    sources: tuple[Text, ...] = Field(min_length=1)


class ReferenceExplanation(Record):
    how_it_works: Text
    normative: Text
    implementation: Text
    limitations: Text
    example: Text
    sources: tuple[Text, ...] = Field(min_length=1)


class PageBinding(Record):
    type: Literal[
        "System",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
        "Function",
        "MeasurementPoint",
        "Environment",
        "ResearchQuestion",
        "ResearchThread",
        "Decision",
    ]
    path: Text
    purpose: Text
    inputs: Text
    outputs: Text


class RelationshipExplanation(Record):
    source: Text
    relation: RelationName
    target: Text
    why: Text
    sources: tuple[Text, ...] = Field(min_length=1)


class ExplanationCatalog(Record):
    explanation_version: Literal["1.0"]
    source_revision: COMMIT
    # Acceptance is a human checkpoint in CONTROL, not a machine-set approval flag.
    review_status: Literal["pending-control-review"]
    control_reference: Literal[
        "https://github.com/Planton361/autonomous-game-agent/issues/170#issuecomment-6065272859"
    ]
    sources: dict[str, SourceLocator]
    components: dict[str, Explanation]
    guides: dict[str, Guide]
    reference_slice: dict[str, ReferenceExplanation] = Field(default_factory=dict)
    # Package A augments the accepted slice; it never overwrites its narratives.
    typed_explanations: dict[str, ReferenceExplanation] = Field(default_factory=dict)
    page_bindings: dict[str, PageBinding] = Field(default_factory=dict)
    relationship_explanations: tuple[RelationshipExplanation, ...] = ()
    package_a_control_reference: (
        Literal[
            "https://github.com/Planton361/autonomous-game-agent/issues/170#issuecomment-6071785139"
        ]
        | None
    ) = None
    optional_essay: Guide | None = None
    reference_control_reference: (
        Literal[
            "https://github.com/Planton361/autonomous-game-agent/issues/170#issuecomment-6070709383"
        ]
        | None
    ) = None
    dependencies: dict[Text, Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]]

    def links(self, keys: tuple[str, ...], kind: str | None = None) -> str:
        return " · ".join(
            f"[{s.locator}](https://github.com/{REPOSITORY}/blob/"
            f"{s.revision or self.source_revision}/"
            f"{quote(s.path)}#L{s.line})"
            for key in dict.fromkeys(keys)
            if (s := self.sources[key]) and (kind is None or s.kind == kind)
        )

    def provenance(self, keys: tuple[str, ...]) -> str:
        rows = [
            "> [!info]- Explanation source freeze / review",
            ">",
            "> Presentation synthesis; pending CONTROL content review. Not an accepted scientific "
            "claim. Test locators identify inspected test source, "
            "not newly executed runtime checks.",
            f"> Inspected source revision: `{self.source_revision}`. Supporting-file changes "
            "require review; an unrelated commit alone does not invalidate this content.",
            f"> [CONTROL contract]({self.control_reference}).",
        ]
        for key in dict.fromkeys(keys):
            s = self.sources[key]
            revision = f"; inspected revision `{s.revision}`" if s.revision else ""
            rows.append(f"> - {s.kind}: {self.links((key,))}; file SHA-256 `{s.sha256}`{revision}.")
        return "\n".join(rows)


def parse_explanations(data: bytes, atlas: Atlas) -> ExplanationCatalog:
    try:
        catalog = ExplanationCatalog.model_validate(read_yaml(utf8(data)))
    except ValidationError as exc:
        raise ProjectionError("Invalid architecture explanation source") from exc
    components = {i for i, n in atlas.entities.items() if n.type == "Component"}
    if set(catalog.components) != components or set(catalog.guides) != set(GUIDES):
        raise ProjectionError("Explanation coverage must match every Component and three Guides")
    if tuple(s.title for s in catalog.guides[GUIDES[0]].sections) != AREAS:
        raise ProjectionError("System Overview must contain the seven functional sections")
    if catalog.reference_slice and (
        set(catalog.reference_slice) != set(REFERENCE_TYPES)
        or catalog.reference_control_reference is None
        or any(
            i not in atlas.entities or atlas.entities[i].type != kind
            for i, kind in REFERENCE_TYPES.items()
        )
    ):
        raise ProjectionError("Reference slice must match the eight existing typed identities")
    if catalog.package_a_control_reference is not None:
        paths = preferred_paths(atlas)
        if (
            set(catalog.page_bindings) != set(paths)
            or set(catalog.typed_explanations) != set(paths) - set(REFERENCE_TYPES)
            or set(catalog.reference_slice) != set(REFERENCE_TYPES)
            or any(
                binding.type != atlas.entities[i].type or binding.path != str(paths[i])
                for i, binding in catalog.page_bindings.items()
            )
        ):
            raise ProjectionError(
                "Package A must bind every preferred identity with exact type/path"
            )
        expected = {
            (e.source, e.relation, e.target)
            for e in atlas.relationships
            if e.source in paths and e.target in paths
        }
        actual = [(e.source, e.relation, e.target) for e in catalog.relationship_explanations]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ProjectionError("Package A reasons must match exact declared preferred relations")
    elif catalog.typed_explanations or catalog.page_bindings or catalog.relationship_explanations:
        raise ProjectionError("Package A content requires its bounded CONTROL contract")
    for item in (*catalog.reference_slice.values(), *catalog.typed_explanations.values()):
        # A linked identity counts as its human-readable title, not its path/token.
        plain = TOKEN.sub(
            lambda m: atlas.entities[m[2]].name if m[2] in atlas.entities else m[0],
            item.how_it_works,
        )
        if len(plain.split()) > 300:
            raise ProjectionError("Reference How it works exceeds 300 words")
    if catalog.optional_essay is not None:
        linked = set(TOKEN.findall(str(catalog.optional_essay.model_dump())))
        if not {("id", i) for i in components} <= linked:
            raise ProjectionError("Optional essay must link all 28 Components")
    items = (
        *catalog.components.values(),
        *catalog.guides.values(),
        *catalog.reference_slice.values(),
        *catalog.typed_explanations.values(),
        *catalog.relationship_explanations,
        *((catalog.optional_essay,) if catalog.optional_essay is not None else ()),
    )
    for item in items:
        if (
            len(set(item.sources)) != len(item.sources)
            or set(item.sources) - catalog.sources.keys()
        ):
            raise ProjectionError("Missing or duplicate explanation source reference")
        kinds = {catalog.sources[key].kind for key in item.sources}
        required = (
            {"normative", "implementation", "test"}
            if isinstance(item, Explanation | ReferenceExplanation)
            else {"normative"}
        )
        if not required <= kinds:
            raise ProjectionError("Explanation lacks normative, code or test boundary locators")
        for value in item.model_dump().values():
            for kind, identity in TOKEN.findall(str(value)):
                if (kind == "id" and identity not in atlas.entities) or (
                    kind == "guide" and identity not in (*GUIDES, ESSAY)
                ):
                    raise ProjectionError("Dangling explanation navigation token")
    for binding in catalog.page_bindings.values():
        for value in (binding.purpose, binding.inputs, binding.outputs):
            if any(
                kind != "id" or i not in catalog.page_bindings for kind, i in TOKEN.findall(value)
            ):
                raise ProjectionError("Dangling Package A page binding token")
    for path in catalog.dependencies:
        value = PurePosixPath(path)
        if (
            not value.parts
            or value.is_absolute()
            or ".." in value.parts
            or str(value) != path
            or value.parts[0] not in {"src", "docs", "tests"}
            or any(c in path for c in "\\\r\n[]<>|#")
        ):
            raise ProjectionError("Invalid explanation dependency path")
    return catalog


def validate_dependencies(catalog: ExplanationCatalog, repo: Path) -> None:
    """Check supporting bytes/locators, independent of the checkout's unrelated HEAD."""
    for relative, fingerprint in catalog.dependencies.items():
        path = repo / relative
        no_symlink_boundary(path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint:
            raise ProjectionError(f"Explanation dependency changed; review required: {relative}")
    checked: dict[str, str] = {}
    for source in catalog.sources.values():
        path = repo / source.path
        no_symlink_boundary(path)
        try:
            if source.path not in checked:
                checked[source.path] = path.read_text(encoding="utf-8")
            text = checked[source.path]
        except OSError as exc:
            raise ProjectionError(f"Missing explanation dependency: {source.path}") from exc
        if hashlib.sha256(text.encode()).hexdigest() != source.sha256:
            raise ProjectionError(f"Explanation dependency changed; review required: {source.path}")
        if source.path.endswith(".py"):
            nodes = ast.parse(text).body
            found = None
            for part in source.locator.split("."):
                found = next(
                    (
                        n
                        for n in nodes
                        if isinstance(n, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
                        and n.name == part
                    ),
                    None,
                )
                if found is None:
                    break
                nodes = found.body
            valid = found is not None and found.lineno == source.line
        else:
            lines = text.splitlines()
            valid = source.line <= len(lines) and (
                lines[source.line - 1].lstrip("# ") == source.locator
            )
        if not valid:
            raise ProjectionError(f"Invalid explanation source locator: {source.path}")


def guide_pages(
    catalog: ExplanationCatalog, atlas: Atlas, preferred: dict[str, PurePosixPath]
) -> dict[PurePosixPath, str]:
    def resolve(text: str) -> str:
        def link(match: re.Match) -> str:
            kind, identity = match.groups()
            path = (
                preferred[identity]
                if kind == "id"
                else PurePosixPath("Research Map/Guides", identity + ".md")
            )
            label = atlas.entities[identity].name if kind == "id" else identity
            return f"[[{path.with_suffix('')}|{label}]]"

        return TOKEN.sub(link, text)

    result = {}
    guides = {title: catalog.guides[title] for title in GUIDES}
    if catalog.optional_essay is not None:
        guides[ESSAY] = catalog.optional_essay
    for title, guide in guides.items():
        keys = list(guide.sources)
        # Guide implementation summaries retain the same Component dependency freeze.
        for section in guide.sections:
            for kind, identity in TOKEN.findall(section.text):
                if kind == "id" and identity in catalog.components:
                    keys.extend(catalog.components[identity].sources)
        lines = [
            f"# {title}",
            "",
            "[[Research Map Home|Home]] · "
            + " · ".join(
                f"[[Research Map/Guides/{other}|{other}]]" for other in GUIDES if other != title
            ),
            "",
            resolve(guide.intro),
            "",
            " · ".join(f"[[#{section.title}|{section.title}]]" for section in guide.sections),
            "",
        ]
        for section in guide.sections:
            lines += [f"## {section.title}", "", resolve(section.text), ""]
        lines += [
            "## Sources",
            "",
            catalog.provenance(tuple(dict.fromkeys(keys))),
            "",
            "[[Research Map Home|Return Home]]",
        ]
        result[PurePosixPath("Research Map/Guides", title + ".md")] = "\n".join(lines)
    return result


def reference_page(
    body: str,
    identity: str,
    catalog: ExplanationCatalog,
    atlas: Atlas,
    preferred: dict[str, PurePosixPath],
) -> str:
    """Replace only the local mechanism section; retain identity/relation/audit bytes."""
    item = catalog.reference_slice[identity]

    def resolve(value: str) -> str:
        return TOKEN.sub(
            lambda m: f"[[{preferred[m[2]].with_suffix('')}|{atlas.entities[m[2]].name}]]",
            value,
        )

    start = body.index("### How it works\n")
    end = body.index("\n### ", start + len("### How it works\n"))
    original = body[start + len("### How it works\n") : end].strip()
    replacement = [
        "### How it works",
        "",
        resolve(item.how_it_works),
        "",
        "### Soll / Ist / Grenzen",
        "",
        "**Soll:** " + resolve(item.normative),
        "",
        "**Ist:** " + resolve(item.implementation),
        "",
        "**Grenzen:** " + resolve(item.limitations),
        "",
        "**Beispiel:** " + resolve(item.example),
        "",
        "Normative Quellen: " + catalog.links(item.sources, "normative"),
        "",
        "Implementierung: " + catalog.links(item.sources, "implementation"),
        "",
        "Testquellen (Quellinspektion, kein neuer Lauf): " + catalog.links(item.sources, "test"),
        "",
        f"[Referenzausschnitt-Vertrag]({catalog.reference_control_reference}).",
        "",
        catalog.provenance(item.sources),
        "",
        "### Code-Details der bisherigen Darstellung",
        "",
        original,
    ]
    return body[:start] + "\n".join(replacement) + "\n" + body[end:]


def typed_page(
    body: str,
    identity: str,
    catalog: ExplanationCatalog,
    atlas: Atlas,
    preferred: dict[str, PurePosixPath],
) -> str:
    """Package A reader template; retain scientific sections and inspection data."""
    binding = catalog.page_bindings[identity]
    item = (catalog.reference_slice | catalog.typed_explanations)[identity]
    node = atlas.entities[identity]

    def link(target: str) -> str:
        return f"[[{preferred[target].with_suffix('')}|{atlas.entities[target].name}]]"

    def resolve(value: str) -> str:
        return TOKEN.sub(lambda m: link(m[2]), value)

    before, marker, rest = body.partition("## Technical\n")
    previous, research_marker, research = rest.partition("## Research\n")
    if not marker or not research_marker:
        raise ProjectionError("Typed reader sections are missing")
    # These obsolete placeholders are presentation copy, not inspection evidence.
    previous = previous.replace(
        "No separate mechanism explanation is authored in this snapshot. "
        "Inspect Sources & verification for detail.",
        "Die aktuelle Erklärung steht im Technical-Abschnitt oben.",
    ).replace(
        "No separate limitation statement is authored here; this does not establish completeness.",
        "Die konkreten Grenzen stehen unter Soll / Ist / Grenzen oben.",
    )
    parents = sorted(
        e.target for e in atlas.relationships if e.source == identity and e.relation == "part_of"
    )
    children = sorted(
        e.source for e in atlas.relationships if e.target == identity and e.relation == "part_of"
    )
    status = (
        f"Registry-Ist: **{node.technical.implementation_status}** · "
        f"Prüfstatus: **{node.technical.verification_status}**"
        if hasattr(node, "technical")
        else "Einordnungs-/Programmdatensatz; kein ausführbarer Implementierungsstatus."
    )
    position = (
        "Technischer Elternteil: " + ", ".join(link(p) for p in parents) + "."
        if parents
        else "Systemwurzel der technischen Hierarchie."
        if node.type == "System"
        else "Außerhalb des Agenten; kein technischer Elternteil."
        if node.type == "Environment"
        else "Eigenständige typisierte Identität; Beziehungen begründen "
        "keine technische Elternschaft."
    )
    meaning = (
        "How it works"
        if node.type in {"Component", "System", "Environment"}
        else "What this record means"
    )
    lines = [
        "## Technical",
        "",
        f"`{identity}` · **{node.type}** · {status}",
        "",
        position,
        "",
        "### Kurz erklärt",
        "",
        resolve(binding.purpose),
        "",
        f"### {meaning}",
        "",
        resolve(item.how_it_works),
        "",
        "### Inputs and outputs",
        "",
        "**Eingang:** " + resolve(binding.inputs),
        "",
        "**Ergebnis und Nutzung:** " + resolve(binding.outputs),
        "",
        "### Direct relationships and why",
        "",
        "Nur erklärte Registry-Beziehungen: Quelle → Ziel bleibt erhalten. "
        "Bei `consumes` zeigt der Pfeil vom Empfänger auf die Daten. "
        "Die Begründungen erklären den Zusammenhang, nicht eine beobachtete Laufzeitspur.",
        "",
        "| Beziehung | Quelle | Ziel | Warum relevant? | Quellen |",
        "| --- | --- | --- | --- | --- |",
    ]
    if node.type == "Component":
        area = catalog.components[identity].area
        lines[6:6] = [
            f"Lesebereich: [[Research Map/Guides/System Overview#{area}|{area}]] "
            "(funktionaler Kontext, kein technischer Elternteil).",
            "",
        ]
    edges = sorted(
        (e for e in catalog.relationship_explanations if identity in {e.source, e.target}),
        key=lambda e: (e.relation, e.source, e.target),
    )
    for edge in edges:
        cells = [
            f"`{edge.relation}`",
            link(edge.source),
            link(edge.target),
            resolve(edge.why),
            catalog.links(edge.sources),
        ]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |")
    if not edges:
        lines += [
            "",
            "Keine direkte Beziehung zu einer weiteren bevorzugten Identität erklärt. "
            "Lesekontext im Text ergänzt keine Registry-Beziehung.",
        ]
    if node.type in {"System", "Component"}:
        lines += ["", "### True subcomponents", ""]
        lines += [
            "- " + link(c) + " — " + resolve(catalog.page_bindings[c].purpose) for c in children
        ] or ["Keine direkten Component-Kinder erklärt."]
    if node.type == "ResearchThread":
        lines += [
            "",
            "### Ordered reading path",
            "",
            "Registry-Lesereihenfolge; keine Ausführungs- oder Kausalkette.",
            "",
        ]
        lines += [f"{index}. {link(i)}" for index, i in enumerate(node.ordered_refs, 1)]
    lines += [
        "",
        "### Soll / Ist / Grenzen",
        "",
        "**Soll:** " + resolve(item.normative),
        "",
        "**Ist:** " + resolve(item.implementation),
        "",
        "**Grenzen / offen:** " + resolve(item.limitations),
        "",
        "### Konkretes Beispiel",
        "",
        resolve(item.example),
        "",
        "### Exact explanation sources",
        "",
        "Normative Quellen: " + catalog.links(item.sources, "normative"),
        "",
        "Code-/Darstellungsgrenze: " + catalog.links(item.sources, "implementation"),
        "",
        "Testquellen (Inspektion; Ausführung siehe PR/CI): " + catalog.links(item.sources, "test"),
        "",
        catalog.provenance(item.sources),
        "",
        f"[Package-A-Vertrag]({catalog.package_a_control_reference}).",
        "",
        "[[Research Map/Diagrams/Interaction Map#Complete linked relation ledger|"
        "47 technische Beziehungen]]"
        " · [[Research Map/Diagrams/Architecture Tree|Vollständige technische Hierarchie]]",
        "",
        "> [!info]- Previous technical presentation / inspection data",
        ">",
        *("> " + line for line in previous.splitlines()),
        "",
    ]
    return before + "\n".join(lines) + "\n## Research\n" + research


def component_technical(
    catalog: ExplanationCatalog,
    identity: str,
    atlas: Atlas,
    preferred: dict[str, PurePosixPath],
    interaction_relations: frozenset[str],
) -> str:
    item = catalog.components[identity]
    node = atlas.entities[identity]

    def link(target: str) -> str:
        entity = atlas.entities[target]
        return f"[[{preferred[target].with_suffix('')}|{entity.name}]] ({entity.type})"

    parents = sorted(
        e.target for e in atlas.relationships if e.source == identity and e.relation == "part_of"
    )
    children = sorted(
        e.source for e in atlas.relationships if e.target == identity and e.relation == "part_of"
    )
    lines = [
        "## Technical",
        "",
        f"`{identity}` · Component · "
        f"Registry implementation: **{node.technical.implementation_status}** · "
        f"verification: **{node.technical.verification_status}**",
        "",
        "Technical position: " + ", ".join(link(p) for p in parents) + ". "
        f"Reading area: [[Research Map/Guides/System Overview#{item.area}|{item.area}]] "
        "(functional context, not ancestry).",
        "",
        item.responsibility + " " + item.why,
        "",
        "### How it works",
        "",
        "**Normative target:** " + item.normative,
        "",
        catalog.links(item.sources, "normative"),
        "",
        "**Current mechanism and boundary:** " + item.mechanism,
        "",
        catalog.links(item.sources, "implementation"),
        "",
        "**Concrete example:** " + item.example,
        "",
        "### Inputs and outputs",
        "",
        "**Inputs:** " + item.inputs,
        "",
        "**Outputs:** " + item.outputs,
        "",
        "### True subcomponents",
        "",
    ]
    lines += [
        "- " + link(child) + " — " + catalog.components[child].responsibility for child in children
    ] or ["No direct Component children are declared."]
    lines += [
        "",
        "### Immediate typed interactions",
        "",
        "Exact Registry declarations below preserve source → target. "
        "`consumes` points from consumer to payload. Shared payloads imply no additional "
        "direct Component edge; these declarations are not a runtime trace.",
        "",
        "| Relation | Source | Target |",
        "| --- | --- | --- |",
    ]
    edges = sorted(
        (
            e
            for e in atlas.relationships
            if identity in {e.source, e.target} and e.relation in interaction_relations
        ),
        key=lambda e: (e.relation, e.source, e.target),
    )
    for edge in edges:
        left = link(edge.source).replace("|", "\\|")
        right = link(edge.target).replace("|", "\\|")
        lines.append(f"| `{edge.relation}` | {left} | {right} |")
    if not edges:
        lines += [
            "",
            "No immediate interaction is declared; code usage above adds no Registry edge.",
        ]
    lines += [
        "",
        "### Current implementation state",
        "",
        item.implementation,
        "",
        "### Important limitations",
        "",
        item.limitations,
        "",
        "Tests/source inspection establish bounded technical behavior, not Live capability, "
        "scientific effectiveness or phase exit.",
        "",
        "Technical test sources (inspection only): " + catalog.links(item.sources, "test"),
        "",
        "[[Research Map/Diagrams/Interaction Map#Complete linked relation ledger|"
        "Complete interaction ledger]] · "
        f"[[Research Map/Graphs/{identity}|Component Graph / full audits]]",
        "",
    ]
    return "\n".join(lines)
