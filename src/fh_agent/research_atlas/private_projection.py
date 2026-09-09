"""Commit-bound public Atlas projection into an explicitly marked private vault."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from .schema import PREFIXES, Entity
from .validator import Atlas, UniqueKeyLoader, load_registry
from .wiki_schema import validate_wiki_records
from .workspace import HOME_PATH, frontmatter, note_path_for, render_map, render_record

OWNER = "public-research-atlas"
REPOSITORY = "Planton361/autonomous-game-agent"
OWNED_ROOT = PurePosixPath("_generated/technical-atlas")
MANIFEST = PurePosixPath("manifest/projection.yaml")
INDEX = PurePosixPath("indexes/atlas-id-index.yaml")
HOME = PurePosixPath("indexes/Technical Atlas Index.md")
MAP = PurePosixPath("system-map/System Anatomy.excalidraw.md")
REGISTRY_FILES = ("nodes.yaml", "relationships.yaml", "evidence.yaml")
SOURCE_PATHS = ("docs/research-atlas/registry", "src/fh_agent/research_atlas")
SHA256 = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
COMMIT = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{40}$")]


class ProjectionError(ValueError):
    """Expected configuration, validation, or generated drift failure."""


class OwnedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    kind: Literal["atlas_record", "evidence", "system_map", "id_index", "index"]
    atlas_id: str | None = None
    sha256: SHA256


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    projection_schema_version: Literal["1.0"]
    generated_by: Literal["public-research-atlas"]
    source_repository: Literal["Planton361/autonomous-game-agent"]
    source_commit: COMMIT
    source_atlas_schema: Literal["0.2"]
    source_registry_sha256: dict[str, SHA256]
    record_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    owned_files: list[OwnedFile]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def yaml_text(data: object) -> str:
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True, width=100000)


def read_yaml(text: str) -> dict:
    try:
        data = yaml.load(text, Loader=UniqueKeyLoader)
    except (ValueError, yaml.YAMLError, TypeError) as exc:
        raise ProjectionError(
            "Invalid YAML; repair the marker, manifest, or declared envelope"
        ) from exc
    if not isinstance(data, dict):
        raise ProjectionError("Expected a YAML mapping")
    return data


def utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectionError(
            "Invalid UTF-8 in marker, manifest, or owned output; restore valid content"
        ) from exc


def markdown_parts(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text[4:].split("\n---\n", 1)
    if len(parts) != 2:
        raise ProjectionError("Unclosed Markdown frontmatter")
    return read_yaml(parts[0]), parts[1]


def private_path(node: Entity) -> PurePosixPath:
    """Identity-only resolver: display names never participate in private paths."""
    if not re.fullmatch(PREFIXES[node.type] + r"-[A-Z0-9]+(?:-[A-Z0-9]+)*", node.id):
        raise ProjectionError("Invalid public Atlas identity")
    return PurePosixPath("evidence" if node.type == "Evidence" else "records") / (node.id + ".md")


def private_link(path: PurePosixPath, alias: str) -> str:
    alias = re.sub(r"[\[\]|\r\n]", " ", alias)
    return f"[[{OWNED_ROOT / path.with_suffix('')}|{alias}]]"


def projection_tree(
    atlas: Atlas, commit: str, registry_digests: dict[str, str]
) -> dict[PurePosixPath, bytes]:
    """Pure rendering; private authored content is intentionally not an input."""
    targets = {
        str(note_path_for(n.id, n.type, n.name).with_suffix("")): private_path(n)
        for n in atlas.entities.values()
    }
    targets[str(HOME_PATH.with_suffix(""))] = HOME

    def rewrite(text: str) -> str:
        def link(match: re.Match) -> str:
            target, _, alias = match[1].partition("|")
            if target not in targets:
                raise ProjectionError("Public renderer emitted an unresolved technical link")
            return private_link(targets[target], alias or target)

        return re.sub(r"\[\[([^\]]+)\]\]", link, text)

    def rewrite_properties(value: object) -> object:
        if isinstance(value, str):
            return rewrite(value)
        if isinstance(value, list):
            return [rewrite_properties(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite_properties(item) for key, item in value.items()}
        return value

    def note(text: str, source_digest: str) -> bytes:
        props, body = markdown_parts(text)
        # Parse YAML first so folded public links become complete strings before rewriting.
        props.update(
            generated_by=OWNER,
            source_repository=REPOSITORY,
            source_commit=commit,
            source_schema="0.2",
            source_record_digest=source_digest,
        )
        return ("---\n" + yaml_text(rewrite_properties(props)) + "---\n" + rewrite(body)).encode()

    tree: dict[PurePosixPath, bytes] = {}
    entries = {}
    owned = []
    for identity, node in sorted(atlas.entities.items()):
        path = private_path(node)
        source = json.dumps(
            node.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
        ).encode()
        tree[path] = note(render_record(atlas, node), digest(source))
        entries[identity] = dict(atlas_type=node.type, display_name=node.name, path=str(path))
        owned.append(
            dict(
                path=str(path),
                kind="evidence" if node.type == "Evidence" else "atlas_record",
                atlas_id=identity,
                sha256=digest(tree[path]),
            )
        )
    public_map = render_map(atlas)
    tree[MAP] = note(public_map, digest(public_map.encode()))
    tree[INDEX] = yaml_text(
        dict(index_schema_version="1.0", generated_by=OWNER, source_commit=commit, entries=entries)
    ).encode()
    # Construct navigation directly through private paths, independent of public Home content.
    home = (
        "# Technical Atlas Index\n\n"
        "Public Git/YAML Registry is authoritative. One-way generated view.\n\n"
    )
    home += private_link(MAP, "System Anatomy") + "\n\n"
    home += (
        "\n".join(
            "- " + private_link(private_path(n), n.id + " · " + n.name)
            for _, n in sorted(atlas.entities.items())
        )
        + "\n"
    )
    props = dict(
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        source_schema="0.2",
        source_record_digest=digest(yaml_text(entries).encode()),
    )
    tree[HOME] = (frontmatter(props) + home).encode()
    for path, kind in ((MAP, "system_map"), (INDEX, "id_index"), (HOME, "index")):
        owned.append(dict(path=str(path), kind=kind, sha256=digest(tree[path])))
    manifest = Manifest(
        projection_schema_version="1.0",
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        source_atlas_schema="0.2",
        source_registry_sha256=registry_digests,
        record_count=sum(n.type != "Evidence" for n in atlas.entities.values()),
        evidence_count=sum(n.type == "Evidence" for n in atlas.entities.values()),
        owned_files=sorted(owned, key=lambda item: item["path"]),
    )
    tree[MANIFEST] = yaml_text(manifest.model_dump(exclude_none=True)).encode()
    return tree


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ProjectionError("Git source check failed; verify repo-root and source-ref")
    return result.stdout.strip()


def source_state(repo: Path, source_ref: str) -> str:
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ProjectionError("repo-root must be the Git worktree root")
    commit = git(repo, "rev-parse", "--verify", "--end-of-options", source_ref + "^{commit}")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ProjectionError("source-ref must resolve to a full 40-character commit")
    if commit != git(repo, "rev-parse", "HEAD"):
        raise ProjectionError("source-ref must match checked-out HEAD")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *SOURCE_PATHS):
        raise ProjectionError(
            "Relevant source paths are dirty; commit or resolve Atlas changes first"
        )
    return commit


def no_symlink_boundary(path: Path) -> None:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ProjectionError("Symlink boundary rejected; use physical directories")


def target_path(root: Path, relative: str | PurePosixPath) -> Path:
    raw = str(relative)
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or PureWindowsPath(raw).drive
        or "\\" in raw
        or "\x00" in raw
        or ".." in path.parts
        or str(path) != raw
        or raw in {"", "."}
    ):
        raise ProjectionError("Unsafe manifest/output path; require normalized relative paths")
    target = root / path
    no_symlink_boundary(target)
    if not target.resolve().is_relative_to(root) or target.resolve() == root:
        raise ProjectionError("Output target escapes owned root")
    return target


def unreadable_tree(error: OSError) -> None:
    raise ProjectionError(
        "Cannot inspect vault tree; resolve directory access before projection"
    ) from error


def inspect_owned(root: Path) -> set[PurePosixPath]:
    no_symlink_boundary(root)
    files = set()
    if root.exists() and not root.is_dir():
        raise ProjectionError("Generated root must be a directory")
    if not root.exists():
        return files
    for parent, directories, names in os.walk(root, followlinks=False, onerror=unreadable_tree):
        for name in directories + names:
            path = Path(parent) / name
            if path.is_symlink():
                raise ProjectionError(
                    "Symlink descendant in owned subtree; remove it before projection"
                )
            if not path.is_dir():
                if not path.is_file():
                    raise ProjectionError("Owned subtree contains a non-regular file")
                files.add(PurePosixPath(path.relative_to(root).as_posix()))
    return files


def validate_prior(root: Path) -> dict[PurePosixPath, OwnedFile]:
    path = target_path(root, MANIFEST)
    if not path.exists():
        return {}
    if not path.is_file():
        raise ProjectionError("Prior manifest must be a regular file")
    try:
        manifest = Manifest.model_validate(read_yaml(utf8(path.read_bytes())))
    except ValidationError as exc:
        raise ProjectionError(
            "Invalid prior manifest owner/schema/fields; restore a valid manifest"
        ) from exc
    if set(manifest.source_registry_sha256) != set(REGISTRY_FILES):
        raise ProjectionError("Invalid prior manifest Registry digests")
    owned = {}
    for item in manifest.owned_files:
        target_path(root, item.path)
        relative = PurePosixPath(item.path)
        if relative == MANIFEST or relative in owned:
            raise ProjectionError("Invalid duplicate/self-owned manifest path")
        if item.kind in {"atlas_record", "evidence"}:
            prefix = "evidence" if item.kind == "evidence" else "records"
            if (
                not item.atlas_id
                or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", item.atlas_id)
                or relative != PurePosixPath(prefix) / (item.atlas_id + ".md")
            ):
                raise ProjectionError("Manifest record identity/path mismatch")
        elif (
            relative != {"system_map": MAP, "id_index": INDEX, "index": HOME}[item.kind]
            or item.atlas_id is not None
        ):
            raise ProjectionError("Manifest kind/path mismatch")
        owned[relative] = item
    if manifest.record_count != sum(
        i.kind == "atlas_record" for i in owned.values()
    ) or manifest.evidence_count != sum(i.kind == "evidence" for i in owned.values()):
        raise ProjectionError("Manifest record counts mismatch")
    return owned


def authored_properties(vault: Path, root: Path) -> list[dict]:
    properties = []
    for parent, directories, names in os.walk(vault, followlinks=False, onerror=unreadable_tree):
        directories[:] = [name for name in directories if Path(parent) / name != root]
        for name in names:
            path = Path(parent) / name
            if path.suffix.lower() != ".md" or path.is_symlink():
                continue
            text = path.read_text(encoding="utf-8")
            # Ordinary notes, including their non-Wiki frontmatter, remain unmodeled.
            if not text.startswith("---\n"):
                continue
            header = text[4:].split("\n---\n", 1)[0]
            try:
                props = yaml.load(header, Loader=UniqueKeyLoader)
            except (ValueError, yaml.YAMLError, TypeError) as exc:
                if re.search(r"wiki_schema_version|wiki_id", header):
                    raise ProjectionError(
                        "Invalid declared Wiki frontmatter; repair its YAML"
                    ) from exc
                continue
            if not isinstance(props, dict) or not (
                {"wiki_schema_version", "wiki_id"} & props.keys()
            ):
                continue
            props, _ = markdown_parts(text)
            properties.append(props)
    return properties


def atomic_write(root: Path, relative: PurePosixPath, data: bytes) -> None:
    target = target_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=".projection-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        target_path(root, relative)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def project(
    repo_root: Path, vault_root: Path, source_ref: str, *, check: bool = False
) -> dict[PurePosixPath, bytes]:
    repo = repo_root.resolve()
    no_symlink_boundary(vault_root.absolute())
    vault = vault_root.resolve()
    if vault.is_relative_to(repo) or repo.is_relative_to(vault):
        raise ProjectionError("Repo and vault must be physically separate, non-nested roots")
    if not vault.is_dir():
        raise ProjectionError("Vault must already exist")
    marker = vault / ".research-wiki-private"
    no_symlink_boundary(marker)
    if not marker.is_file():
        raise ProjectionError(
            "Missing .research-wiki-private marker; explicitly mark the private vault"
        )
    metadata = read_yaml(utf8(marker.read_bytes()))
    if (
        metadata.get("research_wiki_private_version") != "1.0"
        or metadata.get("project") != REPOSITORY
    ):
        raise ProjectionError("Invalid private marker version/project")
    root = vault / OWNED_ROOT
    actual = inspect_owned(root)
    commit = source_state(repo, source_ref)
    for source in SOURCE_PATHS:
        no_symlink_boundary(repo / source)
    for filename in REGISTRY_FILES:
        no_symlink_boundary(repo / SOURCE_PATHS[0] / filename)
    prior = validate_prior(root)
    try:
        atlas = load_registry(repo / "docs/research-atlas")
        validate_wiki_records(authored_properties(vault, root), atlas.entities.keys())
    except (ValueError, yaml.YAMLError, FileNotFoundError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(
            "Invalid Atlas or private Wiki envelope; check identity, atlas_refs, "
            "privacy/private and export_policy/deny"
        ) from exc
    registry_digests = {
        name: digest((repo / SOURCE_PATHS[0] / name).read_bytes()) for name in REGISTRY_FILES
    }
    tree = projection_tree(atlas, commit, registry_digests)
    unknown = actual - prior.keys() - {MANIFEST}
    if unknown:
        raise ProjectionError(
            "Unknown/unowned files in generated root; move them out before projection"
        )
    for relative in tree.keys() | prior.keys():
        target = target_path(root, relative)
        if target.exists() and not target.is_file():
            raise ProjectionError("Output path is occupied by a directory")
        for parent in target.parents:
            if parent == vault:
                break
            if parent.exists() and not parent.is_dir():
                raise ProjectionError("Output parent is not a directory")
    for relative, item in prior.items():
        if relative not in actual:
            continue
        data = target_path(root, relative).read_bytes()
        props = markdown_parts(utf8(data))[0] if relative.suffix == ".md" else read_yaml(utf8(data))
        if props.get("generated_by") != OWNER:
            raise ProjectionError(
                "Prior-owned file lost its owner marker; preserve it outside generated root"
            )
        if item.atlas_id is not None and props.get("atlas_id") != item.atlas_id:
            raise ProjectionError("Prior-owned file identity changed; restore or move it")
        if relative not in tree and digest(data) != item.sha256:
            raise ProjectionError("Obsolete owned file was edited; preserve edits before cleanup")
    if check:
        if actual != tree.keys() or any(
            target_path(root, p).read_bytes() != data for p, data in tree.items()
        ):
            raise ProjectionError("Generated projection drift; regenerate with the same source-ref")
        return tree
    for relative in sorted(prior.keys() - tree.keys()):
        target_path(root, relative).unlink(missing_ok=True)
    for relative, data in sorted(tree.items()):
        if relative != MANIFEST:
            atomic_write(root, relative, data)
    atomic_write(root, MANIFEST, tree[MANIFEST])
    return tree


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument(
        "--check", action="store_true", help="Validate exact projection without any writes"
    )
    args = parser.parse_args(argv)
    try:
        project(args.repo_root, args.vault_root, args.source_ref, check=args.check)
    except ProjectionError as exc:
        print(f"Projection: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
