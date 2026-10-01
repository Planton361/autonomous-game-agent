"""G4 private exact source resolution. No bibliographic inference or scientific writes."""

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from .private_projection import (
    COMMIT,
    REPOSITORY,
    SHA256,
    ProjectionError,
    digest,
    no_symlink_boundary,
)
from .wiki_schema import EpistemicRecord, Paper, ReadingNote

CATALOG_INPUT = PurePosixPath(".research-source-catalog.json")
SOURCE_INDEX = PurePosixPath("indexes/source-resolution-index.yaml")
SOURCE_DETAIL = PurePosixPath("indexes/Source Details.md")
SOURCE_PAYLOADS = frozenset((SOURCE_INDEX, SOURCE_DETAIL))
SOURCE_FINGERPRINT_VERSION = "1.0"
DERIVED = PurePosixPath("_generated/derived")
Text = Annotated[str, StringConstraints(strict=True, min_length=1)]
FamilyID = Annotated[Text, StringConstraints(pattern=r"^srcf-[a-z0-9]+(?:-[a-z0-9]+)*$")]
VersionID = Annotated[Text, StringConstraints(pattern=r"^srcv-[a-z0-9]+(?:-[a-z0-9]+)*$")]
SourceID = FamilyID | VersionID
Kind = Literal[
    "preprint",
    "revised_preprint",
    "accepted_manuscript",
    "published",
    "correction",
    "erratum",
    "other",
]
RelationKind = Literal["revision_of", "published_from", "corrects", "erratum_for", "supersedes"]
Diagnostic = Literal[
    "catalog-unavailable",
    "unresolved-reference",
    "duplicate-exact-alias",
    "wrong-source-type",
    "paper-family-count",
    "reading-paper-unavailable",
    "cross-family-version",
    "preferred-version-missing",
    "preferred-version-unresolved",
    "preferred-version-conflict",
    "preferred-version-cross-family",
    "preferred-version-retracted",
    "preferred-version-withdrawn",
    "version-read-missing",
    "source-status-unknown",
    "retracted",
    "withdrawn",
    "correction",
    "erratum",
    "superseded",
    "corrected",
    "erratum-exists",
    "attachment-unavailable",
    "not-locally-available",
    "availability-unknown",
]


def safe_text(value: str) -> None:
    """Private resolver values are structured literals, never filesystem locations."""
    if (
        not value.strip()
        or value != value.strip()
        or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value)
        or value.lower().startswith("file:")
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).drive
        or "\\" in value
        or ".." in re.split(r"[/\\]", value)
    ):
        raise ValueError("Unsafe source catalog literal")


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @model_validator(mode="after")
    def literals(self) -> "Closed":
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str):
                safe_text(value)
        return self


class SourceFamily(Closed):
    source_family_id: FamilyID
    title: Text
    bibliographic_label: Text | None = None
    preferred_version_ref: Text | None = None


class VersionRelation(Closed):
    relation: RelationKind
    target_version_ref: VersionID


class SourceLocator(Closed):
    url: Text | None = None
    page: Text | None = None
    section: Text | None = None

    @model_validator(mode="after")
    def location(self) -> "SourceLocator":
        if not (self.url or self.page or self.section):
            raise ValueError("Empty source locator")
        if self.url:
            parsed = urlsplit(self.url)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "Source URL requires an explicit HTTP(S) locator without credentials"
                )
        return self


class SourceVersion(Closed):
    source_version_id: VersionID
    source_family_ref: FamilyID
    label: Text
    kind: Kind
    status: Literal["available", "unknown", "withdrawn", "retracted"] = "unknown"
    availability: Literal[
        "available", "not_locally_available", "attachment_unavailable", "unknown"
    ] = "unknown"
    locator: SourceLocator | None = None
    relations: list[VersionRelation] = Field(default_factory=list)


class ExactBinding(Closed):
    scheme: Literal["doi", "arxiv", "openreview", "url", "citation_key", "opaque"]
    value: Text
    target_ref: SourceID

    @property
    def alias(self) -> str:
        return self.value if self.scheme == "opaque" else self.scheme + ":" + self.value

    @model_validator(mode="after")
    def namespace(self) -> "ExactBinding":
        if self.scheme == "opaque" and (
            self.value.startswith(("srcf-", "srcv-", "zsrc-", "zsv-", "zatt-"))
            or self.value.partition(":")[0] in {"doi", "arxiv", "openreview", "url", "citation_key"}
        ):
            raise ValueError("Opaque alias cannot shadow a reserved namespace")
        if self.scheme == "url":
            SourceLocator(url=self.value)
        return self


class SourceCatalog(Closed):
    source_catalog_schema_version: Literal["1.0"]
    privacy: Literal["private"]
    export_policy: Literal["deny"]
    families: list[SourceFamily]
    versions: list[SourceVersion]
    bindings: list[ExactBinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def declarations(self) -> "SourceCatalog":
        families = {f.source_family_id: f for f in self.families}
        versions = {v.source_version_id: v for v in self.versions}
        if len(families) != len(self.families) or len(versions) != len(self.versions):
            raise ValueError("Duplicate project source identity")
        for version in self.versions:
            if version.source_family_ref not in families:
                raise ValueError("Version requires one existing explicitly declared family")
            relations = [(r.relation, r.target_version_ref) for r in version.relations]
            if len(set(relations)) != len(relations):
                raise ValueError("Duplicate version relation")
            for relation in version.relations:
                target = versions.get(relation.target_version_ref)
                if (
                    target is None
                    or target.source_version_id == version.source_version_id
                    or target.source_family_ref != version.source_family_ref
                ):
                    raise ValueError(
                        "Version relation requires a distinct exact same-family version"
                    )
        for binding in self.bindings:
            if binding.target_ref not in families and binding.target_ref not in versions:
                raise ValueError("Exact binding requires an existing project source identity")
        return self


def canonical_catalog(catalog: SourceCatalog) -> dict:
    data = catalog.model_dump(mode="json")
    data["families"].sort(key=lambda f: f["source_family_id"])
    data["versions"].sort(key=lambda v: v["source_version_id"])
    for version in data["versions"]:
        version["relations"].sort(key=lambda r: (r["relation"], r["target_version_ref"]))
    data["bindings"].sort(key=lambda b: (b["scheme"], b["value"], b["target_ref"]))
    return data


def load_catalog(vault: Path) -> SourceCatalog | None:
    """Read only the single optional private input, never attachments or adapters."""
    path = vault / CATALOG_INPUT
    no_symlink_boundary(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise ProjectionError("Private source catalog must be a regular file")

    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ValueError("Nonfinite source value")

    try:
        data = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=nonfinite
        )
        return SourceCatalog.model_validate(data)
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        raise ProjectionError(
            "Invalid private source catalog; restore its closed structured contract"
        ) from exc


class Resolution(Closed):
    reference: Text | None
    status: Literal["resolved", "unresolved", "conflict", "rejected"]
    target_ref: SourceID | None = None
    candidate_refs: list[SourceID] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class RecordBinding(Closed):
    wiki_id: Text
    doc_type: Literal["paper", "reading_note"]
    family: Resolution
    related_versions: list[Resolution] = Field(default_factory=list)
    version_read: Resolution | None = None


class FamilyPreference(Closed):
    source_family_ref: FamilyID
    preferred: Resolution


class SourceIndex(Closed):
    source_resolution_schema_version: Literal["1.0"] = "1.0"
    generated_by: Literal["research-wiki-derived"] = "research-wiki-derived"
    source_repository: Literal["Planton361/autonomous-game-agent"] = REPOSITORY
    source_commit: COMMIT
    source_resolution_fingerprint_version: Literal["1.0"] = "1.0"
    source_resolution_input_fingerprint: SHA256
    catalog: SourceCatalog | None
    record_bindings: list[RecordBinding]
    family_preferences: list[FamilyPreference]
    alias_resolutions: list[Resolution]


def source_fingerprint(catalog: SourceCatalog | None, records: tuple[EpistemicRecord, ...]) -> str:
    inputs = []
    for record in sorted(records, key=lambda r: r.wiki_id):
        if isinstance(record, Paper):
            inputs.append(
                dict(
                    wiki_id=record.wiki_id,
                    doc_type="paper",
                    source_refs=sorted(set(record.source_refs)),
                    related_version_refs=sorted(set(record.related_version_refs)),
                )
            )
        elif isinstance(record, ReadingNote):
            inputs.append(
                dict(
                    wiki_id=record.wiki_id,
                    doc_type="reading_note",
                    paper_refs=sorted(set(record.paper_refs)),
                    source_refs=sorted(set(record.source_refs)),
                    version_read=record.version_read,
                )
            )
    encoded = json.dumps(
        dict(
            source_resolution_fingerprint_version=SOURCE_FINGERPRINT_VERSION,
            catalog=canonical_catalog(catalog) if catalog is not None else None,
            records=inputs,
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return digest(encoded.encode())


@dataclass(frozen=True)
class SourceResolver:
    catalog: SourceCatalog | None
    families: Mapping[str, SourceFamily] = field(init=False, repr=False)
    versions: Mapping[str, SourceVersion] = field(init=False, repr=False)
    matches: Mapping[str, tuple[str, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        catalog = (
            SourceCatalog.model_validate(canonical_catalog(self.catalog))
            if self.catalog is not None
            else None
        )
        object.__setattr__(self, "catalog", catalog)
        families = {f.source_family_id: f for f in catalog.families} if catalog else {}
        versions = {v.source_version_id: v for v in catalog.versions} if catalog else {}
        matches = {identity: [identity] for identity in families.keys() | versions.keys()}
        for binding in catalog.bindings if catalog else ():
            matches.setdefault(binding.alias, []).append(binding.target_ref)
        object.__setattr__(self, "families", MappingProxyType(families))
        object.__setattr__(self, "versions", MappingProxyType(versions))
        object.__setattr__(
            self, "matches", MappingProxyType({k: tuple(v) for k, v in matches.items()})
        )

    def resolve(
        self, reference: str | None, expected: Literal["family", "version"] | None = None
    ) -> Resolution:
        if reference is None:
            return Resolution(
                reference=None, status="unresolved", diagnostics=["unresolved-reference"]
            )
        try:
            safe_text(reference)
        except ValueError as exc:
            raise ProjectionError("Unsafe private source reference") from exc
        if self.catalog is None:
            return Resolution(
                reference=reference,
                status="unresolved",
                diagnostics=["catalog-unavailable", "unresolved-reference"],
            )
        matches = self.matches.get(reference, ())
        if not matches:
            return Resolution(
                reference=reference, status="unresolved", diagnostics=["unresolved-reference"]
            )
        if len(matches) > 1:
            return Resolution(
                reference=reference,
                status="conflict",
                candidate_refs=sorted(matches),
                diagnostics=["duplicate-exact-alias"],
            )
        target = matches[0]
        if expected is not None and not target.startswith(
            "srcf-" if expected == "family" else "srcv-"
        ):
            return Resolution(
                reference=reference, status="rejected", diagnostics=["wrong-source-type"]
            )
        return Resolution(reference=reference, status="resolved", target_ref=target)

    def family(self, identifier: str) -> SourceFamily:
        return self.families[identifier]

    def version(self, identifier: str) -> SourceVersion:
        return self.versions[identifier]

    def preferred(self, family: SourceFamily) -> Resolution:
        result = self.resolve(family.preferred_version_ref, "version")
        if family.preferred_version_ref is None:
            return result.model_copy(update={"diagnostics": ["preferred-version-missing"]})
        if result.status != "resolved":
            code = (
                "preferred-version-conflict"
                if result.status == "conflict"
                else "preferred-version-unresolved"
            )
            return result.model_copy(update={"diagnostics": [*result.diagnostics, code]})
        version = self.version(result.target_ref)
        if version.source_family_ref != family.source_family_id:
            return result.model_copy(
                update={
                    "status": "rejected",
                    "target_ref": None,
                    "diagnostics": ["preferred-version-cross-family"],
                }
            )
        if version.status in {"retracted", "withdrawn"}:
            return result.model_copy(
                update={"diagnostics": ["preferred-version-" + version.status]}
            )
        return result

    def in_family(self, result: Resolution, family: Resolution) -> Resolution:
        if result.status != "resolved":
            return result
        if family.status != "resolved":
            return result.model_copy(
                update={
                    "status": "rejected",
                    "target_ref": None,
                    "diagnostics": ["cross-family-version"],
                }
            )
        if self.version(result.target_ref).source_family_ref != family.target_ref:
            return result.model_copy(
                update={
                    "status": "rejected",
                    "target_ref": None,
                    "diagnostics": ["cross-family-version"],
                }
            )
        return result

    def paper(self, paper: Paper) -> RecordBinding:
        if len(set(paper.source_refs)) != 1:
            family = Resolution(
                reference=None, status="rejected", diagnostics=["paper-family-count"]
            )
        else:
            family = self.resolve(paper.source_refs[0], "family")
        return RecordBinding(
            wiki_id=paper.wiki_id,
            doc_type="paper",
            family=family,
            related_versions=[
                self.in_family(self.resolve(ref, "version"), family)
                for ref in sorted(set(paper.related_version_refs))
            ],
        )

    def reading(self, reading: ReadingNote, records: tuple[EpistemicRecord, ...]) -> RecordBinding:
        reference = (reading.paper_refs or reading.source_refs)[0]
        papers = [r for r in records if isinstance(r, Paper) and r.wiki_id == reference]
        if reading.paper_refs or papers:
            family = (
                self.paper(papers[0]).family
                if len(papers) == 1
                else Resolution(
                    reference=reference,
                    status="unresolved",
                    diagnostics=["reading-paper-unavailable"],
                )
            )
        else:
            family = self.resolve(reading.source_refs[0], "family")
        read = self.in_family(self.resolve(reading.version_read, "version"), family)
        if reading.version_read is None:
            read = read.model_copy(update={"diagnostics": ["version-read-missing"]})
        return RecordBinding(
            wiki_id=reading.wiki_id, doc_type="reading_note", family=family, version_read=read
        )

    def version_diagnostics(self, version: SourceVersion) -> list[str]:
        codes = []
        if version.status in {"unknown", "retracted", "withdrawn"}:
            codes.append("source-status-unknown" if version.status == "unknown" else version.status)
        if version.kind in {"correction", "erratum"}:
            codes.append(version.kind)
        if version.availability != "available":
            codes.append(
                {
                    "unknown": "availability-unknown",
                    "attachment_unavailable": "attachment-unavailable",
                    "not_locally_available": "not-locally-available",
                }[version.availability]
            )
        for other in self.catalog.versions:
            for relation in other.relations:
                if (
                    relation.target_version_ref == version.source_version_id
                    and relation.relation in {"supersedes", "corrects", "erratum_for"}
                ):
                    codes.append(
                        {
                            "supersedes": "superseded",
                            "corrects": "corrected",
                            "erratum_for": "erratum-exists",
                        }[relation.relation]
                    )
        return sorted(set(codes))

    def index(self, commit: str, records: tuple[EpistemicRecord, ...]) -> SourceIndex:
        bindings = []
        for record in sorted(records, key=lambda r: r.wiki_id):
            if isinstance(record, Paper):
                bindings.append(self.paper(record))
            elif isinstance(record, ReadingNote):
                bindings.append(self.reading(record, records))
        catalog = (
            SourceCatalog.model_validate(canonical_catalog(self.catalog))
            if self.catalog is not None
            else None
        )
        aliases = sorted({b.alias for b in catalog.bindings}) if catalog else []
        return SourceIndex(
            source_commit=commit,
            source_resolution_input_fingerprint=source_fingerprint(catalog, records),
            catalog=catalog,
            record_bindings=bindings,
            family_preferences=[
                FamilyPreference(source_family_ref=f.source_family_id, preferred=self.preferred(f))
                for f in catalog.families
            ]
            if catalog
            else [],
            alias_resolutions=[self.resolve(alias) for alias in aliases],
        )


def validate_source_history(previous: SourceCatalog | None, current: SourceCatalog | None) -> None:
    """Never silently prune catalog history or move an exact version to another family."""
    if previous is None:
        return
    old = SourceResolver(previous)
    new = SourceResolver(current)
    if (
        not old.families.keys() <= new.families.keys()
        or not old.versions.keys() <= new.versions.keys()
    ):
        raise ProjectionError("Known project source history must remain explicitly catalogued")
    if any(
        new.version(identity).source_family_ref != version.source_family_ref
        for identity, version in old.versions.items()
    ):
        raise ProjectionError("An exact source version cannot silently change family membership")


def validate_read_provenance(previous: SourceIndex, current: SourceIndex) -> None:
    """An unchanged authored read reference cannot acquire a different exact version."""
    prior_reads = {
        binding.wiki_id: binding.version_read
        for binding in previous.record_bindings
        if binding.version_read is not None
    }
    for binding in current.record_bindings:
        old = prior_reads.get(binding.wiki_id)
        new = binding.version_read
        if (
            old is not None
            and new is not None
            and old.reference == new.reference
            and old.status == "resolved"
            and (new.status != "resolved" or old.target_ref != new.target_ref)
        ):
            raise ProjectionError("Exact version-read binding cannot silently retarget")
