"""Reviewed presentation inputs, never Registry, runtime or scientific authority."""

import ast
import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, ValidationError, model_validator

from .private_projection import (
    COMMIT,
    REPOSITORY,
    ProjectionError,
    no_symlink_boundary,
    read_yaml,
    utf8,
)
from .schema import Record, Text
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
TOKEN = re.compile(r"\[\[(id|guide):([^\]]+)\]\]")


class SourceLocator(Record):
    kind: Literal["normative", "implementation", "test"]
    path: Text
    locator: Text
    line: int = Field(gt=0, strict=True)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

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
    dependencies: dict[Text, Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]]

    def links(self, keys: tuple[str, ...], kind: str | None = None) -> str:
        return " · ".join(
            f"[{s.locator}](https://github.com/{REPOSITORY}/blob/{self.source_revision}/"
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
            rows.append(f"> - {s.kind}: {self.links((key,))}; file SHA-256 `{s.sha256}`.")
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
    for item in (*catalog.components.values(), *catalog.guides.values()):
        if (
            len(set(item.sources)) != len(item.sources)
            or set(item.sources) - catalog.sources.keys()
        ):
            raise ProjectionError("Missing or duplicate explanation source reference")
        kinds = {catalog.sources[key].kind for key in item.sources}
        required = (
            {"normative", "implementation", "test"}
            if isinstance(item, Explanation)
            else {"normative"}
        )
        if not required <= kinds:
            raise ProjectionError("Explanation lacks normative, code or test boundary locators")
        for value in item.model_dump().values():
            for kind, identity in TOKEN.findall(str(value)):
                if (kind == "id" and identity not in atlas.entities) or (
                    kind == "guide" and identity not in GUIDES
                ):
                    raise ProjectionError("Dangling explanation navigation token")
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
    for title in GUIDES:
        guide = catalog.guides[title]
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
