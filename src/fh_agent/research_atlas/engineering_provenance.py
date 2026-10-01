"""Explicit public presentation bindings; no Registry or implementation authority."""

from datetime import date
from pathlib import PurePosixPath
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, StringConstraints, ValidationError, model_validator

from .private_projection import COMMIT, REPOSITORY, ProjectionError, read_yaml, utf8
from .schema import Evidence, Record, Text
from .validator import Atlas

CATALOG_PATH = PurePosixPath("docs/research-atlas/presentation/engineering-provenance.yaml")
PUBLIC_REF = Annotated[
    str,
    StringConstraints(
        pattern=r"^https://github\.com/Planton361/autonomous-game-agent/(issues/[1-9][0-9]*(#issuecomment-[1-9][0-9]*)?|pull/[1-9][0-9]*)$"
    ),
]
SUBJECT_TYPES = frozenset(
    {
        "System",
        "Component",
        "Interface",
        "Contract",
        "DataArtifact",
        "MeasurementPoint",
        "Environment",
        "Function",
    }
)


class Binding(Record):
    subject_id: Text
    role: Literal[
        "implementation", "introduced", "modified", "documented", "decision", "verification"
    ]
    evidence_id: Text
    repository: Literal["Planton361/autonomous-game-agent"]
    inspected_revision: COMMIT
    checked_date: date
    path: Text
    locator: Text
    reference: PUBLIC_REF | None = None
    # Explicit acceptance is independently authored; PR merge status cannot supply it.
    accepted_reference: PUBLIC_REF | None = None
    inspected_pr_status: Literal["open", "closed", "merged"] | None = None

    @model_validator(mode="after")
    def public_role_contract(self) -> "Binding":
        path = PurePosixPath(self.path)
        if (
            len(path.parts) < 2
            or path.is_absolute()
            or ".." in path.parts
            or any(character in self.path for character in "\r\n\t<>`[]|#")
            or "\\" in self.path
            or str(path) != self.path
            or path.parts[0] not in {"src", "tests", "docs", ".github"}
        ):
            raise ValueError("Engineering locator must be a public repository-relative path")
        if self.role in {"introduced", "modified"} and (
            self.reference is None or "/pull/" not in self.reference
        ):
            raise ValueError("Change provenance requires an explicit PR reference")
        if self.inspected_pr_status is not None and (
            self.reference is None or "/pull/" not in self.reference
        ):
            raise ValueError("Inspected PR status requires a PR reference")
        if self.role == "decision":
            if self.accepted_reference is None or "/issues/" not in self.accepted_reference:
                raise ValueError("Decision provenance requires an explicit accepted Issue record")
        elif self.accepted_reference is not None:
            raise ValueError("Acceptance is reserved for explicit Decision provenance")
        return self

    @property
    def source_url(self) -> str:
        return f"https://github.com/{REPOSITORY}/blob/{self.inspected_revision}/{quote(self.path)}"


class Catalog(Record):
    presentation_binding_version: Literal["1.0"]
    bindings: tuple[Binding, ...] = Field(default=())


def validated_bindings(catalog: Catalog, atlas: Atlas) -> tuple[Binding, ...]:
    """Require exact direct Evidence support; never use ancestry or Function proximity."""
    supports = {
        (edge.source, edge.target) for edge in atlas.relationships if edge.relation == "supports"
    }
    seen = set()
    for binding in catalog.bindings:
        subject = atlas.entities.get(binding.subject_id)
        evidence = atlas.entities.get(binding.evidence_id)
        if subject is None or subject.type not in SUBJECT_TYPES:
            raise ProjectionError("Missing or unsupported engineering subject reference")
        if not isinstance(evidence, Evidence):
            raise ProjectionError("Missing engineering Evidence reference")
        if evidence.provenance_kind not in {
            "github_implementation",
            "canonical_project_source",
            "project_decision",
        }:
            raise ProjectionError("Scientific/private sources cannot become engineering provenance")
        if (binding.evidence_id, binding.subject_id) not in supports:
            raise ProjectionError("Wrong-subject engineering Evidence reference")
        if binding.role == "implementation" and (
            evidence.provenance_kind != "github_implementation" or binding.path != evidence.path
        ):
            raise ProjectionError(
                "Implementation binding must reinspect the exact Evidence locator"
            )
        key = (binding.subject_id, binding.role, binding.reference, binding.path, binding.locator)
        if key in seen:
            raise ProjectionError("Duplicate engineering provenance binding")
        seen.add(key)
    return tuple(
        sorted(
            catalog.bindings,
            key=lambda item: (
                item.subject_id,
                item.role,
                item.reference or "",
                item.path,
                item.locator,
                item.evidence_id,
                item.inspected_revision,
                item.checked_date.isoformat(),
            ),
        )
    )


def parse_catalog(data: bytes, atlas: Atlas) -> tuple[Binding, ...]:
    try:
        catalog = Catalog.model_validate(read_yaml(utf8(data)))
    except ValidationError as exc:
        raise ProjectionError("Invalid public engineering presentation catalog") from exc
    return validated_bindings(catalog, atlas)


def render_panel(subject_id: str, bindings: tuple[Binding, ...]) -> list[str]:
    """Native collapsed callout; exact roles remain readable with CSS disabled."""
    selected = tuple(binding for binding in bindings if binding.subject_id == subject_id)
    body = [
        "Inspected public sources; not live GitHub status or implementation certification.",
        "Scientific evidence remains in Research / scientific support; "
        "technical checks are not experiments.",
        "",
    ]
    for title, roles in (
        ("Implementation source", {"implementation"}),
        ("PR / change provenance", {"introduced", "modified"}),
        ("Documentation", {"documented"}),
        ("Accepted rationale / Decision", {"decision"}),
        ("Technical verification", {"verification"}),
    ):
        entries = [binding for binding in selected if binding.role in roles]
        if not entries and title not in {"PR / change provenance", "Accepted rationale / Decision"}:
            continue
        body.extend([f"**{title}**", ""])
        if title == "PR / change provenance" and not any(
            item.role == "introduced" for item in entries
        ):
            body.append(
                "- Introduction: **unknown / unavailable**; no verified introducing PR is bound."
            )
        if title == "PR / change provenance":
            for item in selected:
                if item.reference and "/pull/" in item.reference and item.role not in roles:
                    body.append(
                        f"- **{item.role.capitalize()} PR** — "
                        f"[PR #{item.reference.rsplit('/', 1)[-1]}]({item.reference}); "
                        f"checked {item.checked_date.isoformat()} at `{item.inspected_revision}`. "
                        "Scope and inspected status are in the corresponding category below."
                    )
        if not entries and title == "Accepted rationale / Decision":
            body.append("- Rationale: **unknown / unavailable**; no accepted Decision is bound.")
        for item in entries:
            # Locator text is authored public copy, escaped as plain Markdown, never raw HTML.
            locator = (
                item.locator.replace("\n", " ")
                .replace("`", "'")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            body.extend(
                [
                    f"- **{item.role.capitalize()}** — [{item.path}]({item.source_url}) "
                    f"· `{locator}`",
                    f"  - Evidence: `{item.evidence_id}`; "
                    f"checked **{item.checked_date.isoformat()}**; "
                    f"inspected revision `{item.inspected_revision}`.",
                ]
            )
            if item.reference:
                body.append(
                    f"  - Explicit {item.role} reference: "
                    f"[{item.reference.rsplit('/', 1)[-1]}]({item.reference})."
                )
            if item.accepted_reference:
                body.append(
                    "  - **Accepted Decision record**: "
                    f"[explicit acceptance]({item.accepted_reference})."
                )
            if item.inspected_pr_status:
                body.append(
                    f"  - PR status at inspection: **{item.inspected_pr_status}**, "
                    f"checked {item.checked_date.isoformat()} at `{item.inspected_revision}`; "
                    "not current live status."
                )
        body.append("")
    return ["> [!info]- Engineering provenance", ">", *(f"> {line}" for line in body)]
