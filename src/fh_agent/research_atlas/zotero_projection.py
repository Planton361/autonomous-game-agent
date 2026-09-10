"""Offline synthetic Zotero JSON source projections; never authored research records."""

import argparse
import json
import re
import string
import sys
import unicodedata
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from .private_projection import (
    COMMIT,
    REPOSITORY,
    SHA256,
    ProjectionError,
    atomic_write,
    digest,
    git,
    inspect_owned,
    markdown_parts,
    no_symlink_boundary,
    read_yaml,
    target_path,
    utf8,
    yaml_text,
)

OWNER = "zotero-source-projection"
OWNED_ROOT = PurePosixPath("_generated/zotero")
MANIFEST = PurePosixPath("manifest/projection.yaml")
INDEX = PurePosixPath("indexes/zotero-source-index.yaml")
HOME = PurePosixPath("indexes/Zotero Source Index.md")
SOURCE_PATHS = (
    "src/fh_agent/research_atlas",
    "docs/research-atlas/Zotero Source Projection Contract.md",
)
WARNING = (
    "Generated Zotero source projection only. Current/retained describes projection presence, "
    "not reading, review, scientific validity, preferred version, Finding support, "
    "candidate status or Decision acceptance."
)
SourceID = Annotated[str, StringConstraints(pattern=r"^zsrc-[a-f0-9]{64}$")]
VersionID = Annotated[str, StringConstraints(pattern=r"^zsv-[a-f0-9]{64}$")]
AttachmentID = Annotated[str, StringConstraints(pattern=r"^zatt-[a-f0-9]{64}$")]
AnnotationID = Annotated[str, StringConstraints(pattern=r"^zann-[a-f0-9]{64}$")]


def safe_text(value: str) -> str:
    # Values are opaque text, never filesystem inputs or link destinations.
    if (
        not value.strip()
        or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value)
        or value.startswith(("/", "\\", "~/"))
        or PureWindowsPath(value).drive
        or "\\" in value
        or "file:" in value.lower()
        or ".." in re.split(r"[/\\]", value)
        or re.search(r"(?:^|\s)(?:/[^\s]+|[A-Za-z]:[/\\]|~[/\\])", value)
        or re.search(r"(?:^|[/\s])storage[/\\]", value, re.I)
    ):
        raise ValueError("Unsafe source text or locator")
    return value


Text = Annotated[str, AfterValidator(safe_text)]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PersistentID(Closed):
    kind: Literal["doi", "arxiv", "isbn", "other"]
    value: Text


class Metadata(Closed):
    item_type: Text
    title: Text
    creators: list[Text]
    publication_year: int | None = Field(gt=0)
    container_title: Text | None
    citation_key: Text | None = None
    url: Text | None


class Attachment(Closed):
    zotero_attachment_key: Text
    sha256: SHA256 | None = None


class Predecessor(Closed):
    source_version: Text
    zotero_attachment_key: Text
    attachment_digest: SHA256 | None


class RelativeLocator(Closed):
    kind: Literal["pdf-page"]
    value: Text


class Location(Closed):
    page: Text | None = None
    section: Text | None = None
    attachment_relative: RelativeLocator | None = None


class Annotation(Closed):
    annotation_key: Text
    text: Text
    locator: Location


class Item(Closed):
    zotero_item_key: Text
    persistent_ids: list[PersistentID]
    source_version: Text
    primary_attachment: Attachment
    predecessor: Predecessor | None
    metadata: Metadata
    annotations: list[Annotation]


class Fixture(Closed):
    fixture_schema_version: Literal["1.0"]
    export_revision: Text
    library_context: Text
    items: list[Item]


class SourceLocator(Closed):
    adapter: Literal["zotero-fixture-json"] = "zotero-fixture-json"
    library_context: Text
    zotero_item_key: Text
    source_version_id: VersionID
    attachment_identity: AttachmentID


class AnnotationLocator(Location):
    source_version_id: VersionID
    attachment_identity: AttachmentID
    annotation_key: Text


class ProjectedAnnotation(Closed):
    annotation_key: Text
    annotation_id: AnnotationID
    text: Text
    locator: AnnotationLocator


class SourceContent(Closed):
    zotero_source_schema_version: Literal["1.0"] = "1.0"
    generated_by: Literal["zotero-source-projection"] = OWNER
    source_id: SourceID
    source_version_id: VersionID
    library_context: Text
    zotero_item_key: Text
    persistent_ids: list[PersistentID]
    source_version: Text
    attachment_identity: AttachmentID
    attachment_digest: SHA256 | None
    annotation_set_digest: SHA256
    import_schema_version: Literal["1.0"] = "1.0"
    fixture_schema_version: Literal["1.0"] = "1.0"
    fixture_export_revision: Text
    source_locator: SourceLocator
    source_metadata: Metadata
    predecessor_source_version_id: VersionID | None
    annotations: list[ProjectedAnnotation]


class SourceRecord(SourceContent):
    source_record_digest: SHA256


class OwnedFile(Closed):
    path: str
    kind: Literal["source_version", "source_index", "source_index_markdown"]
    source_id: SourceID | None
    source_version_id: VersionID | None
    sha256: SHA256


class VersionRef(Closed):
    source_id: SourceID
    source_version_id: VersionID


class Manifest(Closed):
    projection_schema_version: Literal["1.0"] = "1.0"
    generated_by: Literal["zotero-source-projection"] = OWNER
    source_repository: Literal["Planton361/autonomous-game-agent"] = REPOSITORY
    generator_source_commit: COMMIT
    import_schema_version: Literal["1.0"] = "1.0"
    fixture_schema_version: Literal["1.0"] = "1.0"
    fixture_export_revision: Text
    fixture_semantic_sha256: SHA256
    current_source_versions: list[VersionRef]
    retained_source_versions: list[VersionRef]
    owned_files: list[OwnedFile]


class IndexVersion(Closed):
    source_version_id: VersionID
    projection_presence: Literal["current", "retained"]
    path: str
    source_version: Text
    attachment_identity: AttachmentID
    attachment_digest: SHA256 | None
    predecessor_source_version_id: VersionID | None
    persistent_ids: list[PersistentID]
    source_file_sha256: SHA256


class IndexFamily(Closed):
    source_id: SourceID
    current_source_version_id: VersionID | None
    versions: list[IndexVersion]


class SourceIndex(Closed):
    index_schema_version: Literal["1.0"] = "1.0"
    generated_by: Literal["zotero-source-projection"] = OWNER
    generator_source_commit: COMMIT
    fixture_export_revision: Text
    fixture_semantic_sha256: SHA256
    sources: list[IndexFamily]


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def identity(prefix: str, **values: object) -> str:
    return prefix + digest(canonical(values))


def source_id(library: str, key: str) -> str:
    return identity("zsrc-", library_context=library, zotero_item_key=key)


def attachment_id(library: str, key: str) -> str:
    return identity("zatt-", library_context=library, zotero_attachment_key=key)


def version_id(source: str, version: str, attachment: str, content_digest: str | None) -> str:
    return identity(
        "zsv-",
        source_id=source,
        source_version=version,
        attachment_identity=attachment,
        attachment_digest=content_digest,
    )


def annotation_id(version: str, attachment: str, key: str) -> str:
    return identity(
        "zann-", source_version_id=version, attachment_identity=attachment, annotation_key=key
    )


def unique(values: list[str]) -> None:
    if len(set(values)) != len(values):
        raise ProjectionError("Duplicate fixture or projection identity")


def json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    unique([key for key, _ in pairs])
    return dict(pairs)


def invalid_constant(_: str) -> None:
    raise ProjectionError("Non-standard JSON constant")


def validate[Model: Closed](model: type[Model], value: object) -> Model:
    try:
        return model.model_validate(value)
    except ValueError as exc:
        raise ProjectionError("Invalid closed source projection schema or unsafe text") from exc


def parse_fixture(data: bytes) -> Fixture:
    try:
        raw = json.loads(utf8(data), object_pairs_hook=json_object, parse_constant=invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError("Invalid strict JSON fixture") from exc
    fixture = validate(Fixture, raw)
    unique([item.zotero_item_key for item in fixture.items])
    unique([item.primary_attachment.zotero_attachment_key for item in fixture.items])
    normalized = []
    for item in fixture.items:
        unique([a.annotation_key for a in item.annotations])
        for annotation in item.annotations:
            if not any(annotation.locator.model_dump().values()):
                raise ProjectionError("Annotation requires a human location")
        if item.metadata.url is not None and not re.fullmatch(
            r"https?://[^\s]+", item.metadata.url
        ):
            raise ProjectionError("Metadata URL must be opaque HTTP(S) text")
        normalized.append(
            item.model_copy(
                update={
                    "persistent_ids": sorted(item.persistent_ids, key=lambda p: (p.kind, p.value)),
                    "annotations": sorted(item.annotations, key=lambda a: a.annotation_key),
                }
            )
        )
    return fixture.model_copy(update={"items": sorted(normalized, key=lambda i: i.zotero_item_key)})


def source_path(source: str, version: str) -> PurePosixPath:
    return PurePosixPath("sources") / source / (version + ".source.md")


def record_for(fixture: Fixture, item: Item) -> SourceRecord:
    sid = source_id(fixture.library_context, item.zotero_item_key)
    aid = attachment_id(fixture.library_context, item.primary_attachment.zotero_attachment_key)
    vid = version_id(sid, item.source_version, aid, item.primary_attachment.sha256)
    predecessor = item.predecessor
    pred = (
        None
        if predecessor is None
        else version_id(
            sid,
            predecessor.source_version,
            attachment_id(fixture.library_context, predecessor.zotero_attachment_key),
            predecessor.attachment_digest,
        )
    )
    content = SourceContent(
        source_id=sid,
        source_version_id=vid,
        library_context=fixture.library_context,
        zotero_item_key=item.zotero_item_key,
        persistent_ids=item.persistent_ids,
        source_version=item.source_version,
        attachment_identity=aid,
        attachment_digest=item.primary_attachment.sha256,
        annotation_set_digest=digest(
            canonical([a.model_dump(mode="json") for a in item.annotations])
        ),
        fixture_export_revision=fixture.export_revision,
        source_locator=SourceLocator(
            library_context=fixture.library_context,
            zotero_item_key=item.zotero_item_key,
            source_version_id=vid,
            attachment_identity=aid,
        ),
        source_metadata=item.metadata,
        predecessor_source_version_id=pred,
        annotations=[
            ProjectedAnnotation(
                annotation_key=a.annotation_key,
                annotation_id=annotation_id(vid, aid, a.annotation_key),
                text=a.text,
                locator=AnnotationLocator(
                    **a.locator.model_dump(),
                    source_version_id=vid,
                    attachment_identity=aid,
                    annotation_key=a.annotation_key,
                ),
            )
            for a in item.annotations
        ],
    )
    return seal(content)


def seal(content: SourceContent) -> SourceRecord:
    fields = content.model_dump(exclude={"source_record_digest"}, mode="json")
    return SourceRecord(**fields, source_record_digest=digest(canonical(fields)))


def plain(value: object) -> str:
    return "".join(f"&#{ord(c)};" if c in string.punctuation else c for c in str(value))


def markdown(fields: dict, body: str) -> bytes:
    return ("---\n" + yaml_text(fields) + "---\n" + body).encode("utf-8")


def render_source(record: SourceRecord) -> bytes:
    body = f"# {plain(record.source_metadata.title)}\n\n{WARNING}\n\n"
    body += f"Source family: {record.source_id}\n\nExact version: {record.source_version_id}\n\n"
    body += "## Exported annotations\n\n"
    for a in record.annotations:
        body += f"- {a.annotation_id}: {plain(a.text)}\n"
        body += f"  Location: {plain(canonical(a.locator.model_dump(mode='json')).decode())}\n"
    return markdown(record.model_dump(mode="json"), body)


def read_record(data: bytes, owned: OwnedFile) -> SourceRecord:
    fields = markdown_parts(utf8(data))[0]
    if set(fields) != set(SourceRecord.model_fields):
        raise ProjectionError("Prior source lost owner/schema/fields")
    record = validate(SourceRecord, fields)
    if (record.source_id, record.source_version_id) != (owned.source_id, owned.source_version_id):
        raise ProjectionError("Prior source identity changed")
    if (
        source_id(record.library_context, record.zotero_item_key) != record.source_id
        or version_id(
            record.source_id,
            record.source_version,
            record.attachment_identity,
            record.attachment_digest,
        )
        != record.source_version_id
        or record.source_locator
        != SourceLocator(
            library_context=record.library_context,
            zotero_item_key=record.zotero_item_key,
            source_version_id=record.source_version_id,
            attachment_identity=record.attachment_identity,
        )
    ):
        raise ProjectionError("Prior source identity/locator binding changed")
    unique([a.annotation_key for a in record.annotations])
    for a in record.annotations:
        if not (a.locator.page or a.locator.section or a.locator.attachment_relative):
            raise ProjectionError("Prior annotation requires a human location")
        if (
            a.annotation_id
            != annotation_id(record.source_version_id, record.attachment_identity, a.annotation_key)
            or a.locator.source_version_id != record.source_version_id
            or a.locator.attachment_identity != record.attachment_identity
            or a.locator.annotation_key != a.annotation_key
        ):
            raise ProjectionError("Prior annotation binding changed")
    return record


def validate_prior(root: Path) -> Manifest | None:
    path = target_path(root, MANIFEST)
    if not path.exists():
        return None
    if not path.is_file():
        raise ProjectionError("Prior manifest must be a regular file")
    fields = read_yaml(utf8(path.read_bytes()))
    if set(fields) != set(Manifest.model_fields):
        raise ProjectionError("Prior manifest lost owner/schema/fields")
    manifest = validate(Manifest, fields)
    unique([o.path for o in manifest.owned_files])
    versions = set()
    for owned in manifest.owned_files:
        target_path(root, owned.path)
        if owned.kind == "source_version":
            if (
                owned.source_id is None
                or owned.source_version_id is None
                or PurePosixPath(owned.path)
                != source_path(owned.source_id, owned.source_version_id)
                or owned.source_version_id in versions
            ):
                raise ProjectionError("Invalid manifest source identity/path")
            versions.add(owned.source_version_id)
        elif (
            PurePosixPath(owned.path)
            != {"source_index": INDEX, "source_index_markdown": HOME}[owned.kind]
            or owned.source_id is not None
            or owned.source_version_id is not None
        ):
            raise ProjectionError("Invalid manifest kind/path")
    current, retained = manifest.current_source_versions, manifest.retained_source_versions
    unique([r.source_id for r in current])
    unique([r.source_version_id for r in current + retained])
    if {(r.source_id, r.source_version_id) for r in current + retained} != {
        (o.source_id, o.source_version_id)
        for o in manifest.owned_files
        if o.kind == "source_version"
    }:
        raise ProjectionError("Manifest version inventories do not match owned sources")
    return manifest


def indexes(
    fixture: Fixture,
    commit: str,
    records: dict[str, SourceRecord],
    payloads: dict[PurePosixPath, bytes],
    current: dict[str, str],
) -> dict[PurePosixPath, bytes]:
    families = []
    for sid in sorted({r.source_id for r in records.values()}):
        versions = []
        for vid, record in sorted(records.items()):
            if record.source_id != sid:
                continue
            path = source_path(sid, vid)
            versions.append(
                IndexVersion(
                    source_version_id=vid,
                    projection_presence="current" if current.get(sid) == vid else "retained",
                    path=str(path),
                    source_version=record.source_version,
                    attachment_identity=record.attachment_identity,
                    attachment_digest=record.attachment_digest,
                    predecessor_source_version_id=record.predecessor_source_version_id,
                    persistent_ids=record.persistent_ids,
                    source_file_sha256=digest(payloads[path]),
                )
            )
        families.append(
            IndexFamily(
                source_id=sid, current_source_version_id=current.get(sid), versions=versions
            )
        )
    index = SourceIndex(
        generator_source_commit=commit,
        fixture_export_revision=fixture.export_revision,
        fixture_semantic_sha256=digest(canonical(fixture.model_dump(mode="json"))),
        sources=families,
    )
    body = "# Zotero Source Index\n\n" + WARNING + "\n\n"
    body += (
        "| Source family | Version | Projection presence | Source label |\n"
        "| --- | --- | --- | --- |\n"
    )
    for family in index.sources:
        for version in family.versions:
            body += (
                f"| {family.source_id} | [{version.source_version_id}](../{version.path}) | "
                f"{version.projection_presence} | {plain(version.source_version)} |\n"
            )
    return {
        INDEX: yaml_text(index.model_dump(mode="json")).encode(),
        HOME: markdown(index.model_dump(mode="json", exclude={"sources"}), body),
    }


def expected_tree(
    fixture: Fixture,
    commit: str,
    prior: Manifest | None,
    previous: dict[PurePosixPath, bytes],
) -> dict[PurePosixPath, bytes]:
    proposed = [record_for(fixture, item) for item in fixture.items]
    unique([r.source_id for r in proposed])
    unique([r.source_version_id for r in proposed])
    current = {r.source_id: r.source_version_id for r in proposed}
    owned = {PurePosixPath(o.path): o for o in prior.owned_files} if prior else {}
    prior_current = {r.source_version_id for r in prior.current_source_versions} if prior else set()
    old_records = {}
    tree: dict[PurePosixPath, bytes] = {}
    for path, item in owned.items():
        if path not in previous:
            if item.kind == "source_version" and item.source_version_id not in current.values():
                raise ProjectionError("Missing retained source history; restore it")
            continue
        data = previous[path]
        if item.kind != "source_version":
            if (markdown_parts(utf8(data))[0] if path == HOME else read_yaml(utf8(data))).get(
                "generated_by"
            ) != OWNER:
                raise ProjectionError("Prior index lost its owner")
            continue
        record = read_record(data, item)
        old_records[record.source_version_id] = record
        if (
            record.source_version_id not in current.values()
            or record.source_version_id not in prior_current
        ):
            if digest(data) != item.sha256:
                raise ProjectionError("Edited retained source history; preserve or restore it")
            if seal(record) != record:
                raise ProjectionError("Invalid retained source payload")
            tree[path] = data
    known_families = {o.source_id for o in owned.values() if o.kind == "source_version"}
    records = dict(old_records)
    for record in proposed:
        vid, sid = record.source_version_id, record.source_id
        path = source_path(sid, vid)
        old = old_records.get(vid)
        pred = record.predecessor_source_version_id
        if old:
            # A previously recorded predecessor is immutable, even on metadata reimport.
            if pred is not None and pred != old.predecessor_source_version_id:
                raise ProjectionError("Existing version predecessor cannot change")
            record = seal(
                record.model_copy(
                    update={"predecessor_source_version_id": old.predecessor_source_version_id}
                )
            )
        elif (sid in known_families and path not in owned) or pred is not None:
            if pred not in old_records or old_records[pred].source_id != sid or pred == vid:
                raise ProjectionError("New version requires an explicit recoverable predecessor")
        if old and record.model_dump(
            exclude={"fixture_export_revision", "source_record_digest"}
        ) == old.model_dump(exclude={"fixture_export_revision", "source_record_digest"}):
            # Export revision is per-source last material projection, not global churn.
            record = seal(
                record.model_copy(update={"fixture_export_revision": old.fixture_export_revision})
            )
        data = render_source(record)
        if path in owned and path not in previous and digest(data) != owned[path].sha256:
            raise ProjectionError("Missing source cannot be reconstructed exactly; restore it")
        if vid in old_records and vid not in prior_current and previous[path] != data:
            raise ProjectionError("Retained version cannot be rewritten")
        records[vid] = record
        tree[path] = data
    # Reconstructed current sources may have predecessors in retained history.
    for record in records.values():
        pred = record.predecessor_source_version_id
        if pred is not None and (
            pred not in records
            or records[pred].source_id != record.source_id
            or pred == record.source_version_id
        ):
            raise ProjectionError("Dangling source predecessor")
    tree.update(indexes(fixture, commit, records, tree, current))
    files = []
    for path, data in sorted(tree.items()):
        if path in {INDEX, HOME}:
            files.append(
                OwnedFile(
                    path=str(path),
                    kind="source_index" if path == INDEX else "source_index_markdown",
                    source_id=None,
                    source_version_id=None,
                    sha256=digest(data),
                )
            )
        else:
            vid = path.name.removesuffix(".source.md")
            files.append(
                OwnedFile(
                    path=str(path),
                    kind="source_version",
                    source_id=records[vid].source_id,
                    source_version_id=vid,
                    sha256=digest(data),
                )
            )
    manifest = Manifest(
        generator_source_commit=commit,
        fixture_export_revision=fixture.export_revision,
        fixture_semantic_sha256=digest(canonical(fixture.model_dump(mode="json"))),
        current_source_versions=[
            VersionRef(source_id=s, source_version_id=v) for s, v in sorted(current.items())
        ],
        retained_source_versions=[
            VersionRef(source_id=r.source_id, source_version_id=v)
            for v, r in sorted(records.items())
            if current.get(r.source_id) != v
        ],
        owned_files=files,
    )
    tree[MANIFEST] = yaml_text(manifest.model_dump(mode="json")).encode()
    return tree


def cleanup_paths(
    prior: Manifest | None, tree: dict[PurePosixPath, bytes], previous: dict[PurePosixPath, bytes]
) -> list[PurePosixPath]:
    obsolete = []
    for item in prior.owned_files if prior else []:
        path = PurePosixPath(item.path)
        if path in tree:
            continue
        if item.kind == "source_version":
            raise ProjectionError("Source history cannot be cleaned up")
        if path in previous:
            data = previous[path]
            props = markdown_parts(utf8(data))[0] if path == HOME else read_yaml(utf8(data))
            if props.get("generated_by") != OWNER or digest(data) != item.sha256:
                raise ProjectionError("Edited obsolete payload; preserve it")
            obsolete.append(path)
    return sorted(obsolete)


def preconditions(
    repo_root: Path, vault_root: Path, source_ref: str, fixture_export: Path
) -> tuple[Path, Path, str, Fixture]:
    for path in (repo_root, vault_root, fixture_export):
        no_symlink_boundary(path.absolute())
    repo, vault = repo_root.resolve(), vault_root.resolve()
    if not repo.is_dir() or not vault.is_dir():
        raise ProjectionError("Repo and private vault must exist")
    if vault.is_relative_to(repo) or repo.is_relative_to(vault):
        raise ProjectionError("Repo and vault must be non-nested physical roots")
    marker = vault / ".research-wiki-private"
    no_symlink_boundary(marker)
    if not marker.is_file():
        raise ProjectionError("Missing private vault marker")
    metadata = read_yaml(utf8(marker.read_bytes()))
    if (
        metadata.get("research_wiki_private_version") != "1.0"
        or metadata.get("project") != REPOSITORY
    ):
        raise ProjectionError("Invalid private vault marker")
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ProjectionError("repo-root must be the Git worktree root")
    commit = git(repo, "rev-parse", "--verify", "--end-of-options", source_ref + "^{commit}")
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or commit != git(repo, "rev-parse", "HEAD"):
        raise ProjectionError("source-ref must match checked-out HEAD")
    for relative in SOURCE_PATHS:
        no_symlink_boundary(repo / relative)
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *SOURCE_PATHS):
        raise ProjectionError("Relevant generator source paths are dirty")
    if not fixture_export.is_file() or fixture_export.suffix != ".json":
        raise ProjectionError("Fixture export must be an explicit regular JSON file")
    if fixture_export.resolve().is_relative_to(vault / OWNED_ROOT):
        raise ProjectionError("Fixture input cannot be inside generated ownership")
    return repo, vault, commit, parse_fixture(fixture_export.read_bytes())


def project(
    repo_root: Path, vault_root: Path, source_ref: str, fixture_export: Path, *, check: bool = False
) -> dict[PurePosixPath, bytes]:
    try:
        _, vault, commit, fixture = preconditions(repo_root, vault_root, source_ref, fixture_export)
        root = vault / OWNED_ROOT
        actual = inspect_owned(root)
        prior = validate_prior(root)
        owned = {PurePosixPath(o.path) for o in prior.owned_files} if prior else set()
        if actual - owned - {MANIFEST}:
            raise ProjectionError(
                "Unknown/unowned Zotero projection content; preserve outside root"
            )
        previous = {p: target_path(root, p).read_bytes() for p in actual if p != MANIFEST}
        tree = expected_tree(fixture, commit, prior, previous)
        obsolete = cleanup_paths(prior, tree, previous)
        for relative in tree.keys() | owned:
            target = target_path(root, relative)
            if target.exists() and not target.is_file():
                raise ProjectionError("Output target must be a regular file")
            for parent in target.parents:
                if parent == vault:
                    break
                if parent.exists() and not parent.is_dir():
                    raise ProjectionError("Output parent must be a directory")
        if check:
            if actual != tree.keys() or any(
                target_path(root, p).read_bytes() != b for p, b in tree.items()
            ):
                raise ProjectionError("Zotero projection drift; regenerate from the same fixture")
            return tree
    except OSError as exc:
        raise ProjectionError("Cannot read source projection inputs or owned state") from exc
    for relative in obsolete:
        target_path(root, relative).unlink()
    for relative, data in sorted(tree.items()):
        if relative != MANIFEST and previous.get(relative) != data:
            atomic_write(root, relative, data)
    atomic_write(root, MANIFEST, tree[MANIFEST])
    return tree


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--fixture-export", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="Compare exact state without writes")
    args = parser.parse_args(argv)
    try:
        project(
            args.repo_root, args.vault_root, args.source_ref, args.fixture_export, check=args.check
        )
    except ProjectionError as exc:
        print(f"Zotero projection: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
