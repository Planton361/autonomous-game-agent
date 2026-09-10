"""Private declared-reference navigation and direct Bases; no scientific adjudication."""

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import quote

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

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
    unreadable_tree,
    utf8,
    yaml_text,
)
from .private_projection import (
    project as technical_projection,
)
from .private_reference_index import (
    NAVIGATION,
    REFERENCE_INDEX,
    ReferenceIndex,
    Snapshot,
    build_index,
    make_snapshot,
    render_index,
    render_navigation,
)
from .validator import Atlas, UniqueKeyLoader, load_registry

OWNER = "research-wiki-derived"
OWNED_ROOT = PurePosixPath("_generated/derived")
MANIFEST = PurePosixPath("manifest/direct-views.yaml")
TECHNICAL_BASE = PurePosixPath("bases/Technical Atlas Views.base")
DIRECT_BASE = PurePosixPath("bases/Research Wiki Direct Views.base")
INDEX = PurePosixPath("indexes/Direct Views Index.md")
PUBLIC_SOURCE = PurePosixPath("docs/research-atlas/Generated/Atlas Views.base")
DIRECT_SOURCE = PurePosixPath("docs/research-atlas/Wiki Views/Research Wiki Direct Views.base")
SOURCE_PATHS = (
    str(PUBLIC_SOURCE),
    "docs/research-atlas/Wiki Views",
    "docs/research-atlas/Process Seeds",
)
BASE_OWNER = f"# generated_by: {OWNER}\n"


class OwnedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    sha256: SHA256


class SourceDigests(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    public_atlas_base: SHA256
    research_wiki_direct_base: SHA256


class ManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    view_schema_version: Literal["1.0"]
    generated_by: Literal["research-wiki-derived"]
    source_repository: Literal["Planton361/autonomous-game-agent"]
    source_commit: COMMIT
    source_atlas_schema: Literal["0.2"]
    source_sha256: SourceDigests
    owned_files: list[OwnedFile]


class Manifest(ManifestV1):
    view_schema_version: Literal["2.0"]
    reference_index_schema_version: Literal["1.0"]
    private_input_fingerprint: SHA256


def views_tree(commit: str, public_base: bytes, direct_base: bytes) -> dict[PurePosixPath, bytes]:
    """Retained v1 renderer; v2 extends its exact Base payloads under the same owner."""
    technical = read_yaml(utf8(public_base))
    direct = read_yaml(utf8(direct_base))
    for base in (technical, direct):
        if (
            not isinstance(base.get("filters"), dict)
            or not isinstance(base.get("views"), list)
            or not base["views"]
            or any(
                not isinstance(view, dict)
                or view.get("type") != "table"
                or not isinstance(view.get("name"), str)
                for view in base["views"]
            )
        ):
            raise ProjectionError("Invalid source Base structure; restore committed table views")
    # Preserve every public view/filter; scope its dataset to the RA-1 projection.
    technical["filters"] = {
        "and": ['file.inFolder("_generated/technical-atlas")', technical["filters"]]
    }
    tree = {
        TECHNICAL_BASE: (BASE_OWNER + yaml_text(technical)).encode(),
        DIRECT_BASE: BASE_OWNER.encode() + direct_base,
    }
    props = dict(generated_by=OWNER, source_repository=REPOSITORY, source_commit=commit)
    body = "# Direct Views Index\n\nNavigation only; no scientific data index.\n\n"
    for path in (TECHNICAL_BASE, DIRECT_BASE):
        body += f"- [[{OWNED_ROOT / path}|{path.stem}]]\n"
    body += "\nPublic-safe copy sources and capability limits at this source commit:\n\n"
    for label, path in (
        ("Direct View Capability Matrix", "Wiki Views/Direct View Capability Matrix.md"),
        ("Process seed sources", "Process Seeds"),
    ):
        route = "blob" if path.endswith(".md") else "tree"
        url = f"https://github.com/{REPOSITORY}/{route}/{commit}/docs/research-atlas/{quote(path)}"
        body += f"- [{label}]({url})\n"
    body += (
        "\nViews display declared properties, not verified scientific conclusions. "
        "No automatic acceptance, private-to-public promotion or Wiki-to-Agent-Memory path.\n"
    )
    tree[INDEX] = ("---\n" + yaml_text(props) + "---\n" + body).encode()
    manifest = ManifestV1(
        view_schema_version="1.0",
        generated_by=OWNER,
        source_repository=REPOSITORY,
        source_commit=commit,
        source_atlas_schema="0.2",
        source_sha256=SourceDigests(
            public_atlas_base=digest(public_base),
            research_wiki_direct_base=digest(direct_base),
        ),
        owned_files=[
            OwnedFile(path=str(path), sha256=digest(data)) for path, data in sorted(tree.items())
        ],
    )
    tree[MANIFEST] = yaml_text(manifest.model_dump()).encode()
    return tree


def reference_views_tree(
    commit: str,
    public_base: bytes,
    direct_base: bytes,
    reference: ReferenceIndex,
    atlas: Atlas,
    locators: dict[str, PurePosixPath],
) -> dict[PurePosixPath, bytes]:
    tree = views_tree(commit, public_base, direct_base)
    old = ManifestV1.model_validate(read_yaml(utf8(tree.pop(MANIFEST))))
    tree[REFERENCE_INDEX] = render_index(reference)
    tree[NAVIGATION] = render_navigation(reference, atlas, locators)
    text = utf8(tree[INDEX]).replace(
        "Navigation only; no scientific data index.",
        "Declared structured reference index for navigation/audit; no scientific adjudication.",
    )
    tree[INDEX] = (
        text + f"\n- [[{OWNED_ROOT / NAVIGATION}|Declared Literature Navigation]]\n"
    ).encode()
    data = old.model_dump()
    data.update(
        view_schema_version="2.0",
        reference_index_schema_version="1.0",
        private_input_fingerprint=reference.private_input_fingerprint,
        owned_files=[OwnedFile(path=str(p), sha256=digest(b)) for p, b in sorted(tree.items())],
    )
    tree[MANIFEST] = yaml_text(Manifest.model_validate(data).model_dump()).encode()
    return tree


def authored_snapshot(vault: Path, atlas: Atlas) -> tuple[Snapshot, dict[str, PurePosixPath]]:
    """RA-1 discovery semantics, excluding all generated content; locators are not identity."""
    properties: list[dict] = []
    paths: list[PurePosixPath] = []
    try:
        for parent, directories, names in os.walk(
            vault, followlinks=False, onerror=unreadable_tree
        ):
            directories[:] = sorted(
                name
                for name in directories
                if Path(parent) / name != vault / "_generated"
                and not (Path(parent) / name).is_symlink()
            )
            for name in sorted(names):
                path = Path(parent) / name
                if path.suffix.lower() != ".md" or path.is_symlink():
                    continue
                if not path.is_file():
                    raise ProjectionError("Authored Markdown must be a readable regular file")
                text = path.read_text(encoding="utf-8")
                if not text.startswith("---\n"):
                    continue
                header = text[4:].split("\n---\n", 1)[0]
                try:
                    props = yaml.load(header, Loader=UniqueKeyLoader)
                except (ValueError, yaml.YAMLError, TypeError) as exc:
                    if re.search(r"wiki_schema_version|wiki_id", header):
                        raise ProjectionError("Invalid declared Wiki frontmatter") from exc
                    continue
                if not isinstance(props, dict) or not (
                    {"wiki_schema_version", "wiki_id"} & props.keys()
                ):
                    continue
                props, _ = markdown_parts(text)
                properties.append(props)
                paths.append(PurePosixPath(path.relative_to(vault).as_posix()))
    except (OSError, UnicodeError) as exc:
        raise ProjectionError("Cannot read authored Wiki snapshot") from exc
    snapshot = make_snapshot(properties, atlas)
    locators = {props["wiki_id"]: path for props, path in zip(properties, paths, strict=True)}
    return snapshot, locators


def validate_prior(root: Path) -> dict[PurePosixPath, OwnedFile]:
    path = target_path(root, MANIFEST)
    if not path.exists():
        return {}
    if not path.is_file():
        raise ProjectionError("Prior direct-views manifest must be a regular file")
    try:
        data = read_yaml(utf8(path.read_bytes()))
        if data.get("view_schema_version") == "1.0":
            manifest = ManifestV1.model_validate(data)
        elif data.get("view_schema_version") == "2.0":
            manifest = Manifest.model_validate(data)
        else:
            raise ProjectionError("Unsupported direct-views manifest version")
    except ValidationError as exc:
        raise ProjectionError("Invalid direct-views manifest; restore owner/schema/fields") from exc
    prior = {}
    for item in manifest.owned_files:
        target_path(root, item.path)
        relative = PurePosixPath(item.path)
        if relative == MANIFEST or relative in prior:
            raise ProjectionError("Duplicate/self-owned direct-views manifest path")
        # V1 cannot claim YAML; V2 adds exactly one fixed YAML payload, not a subtree.
        if not (
            len(relative.parts) == 2
            and (
                (relative.parent == PurePosixPath("bases") and relative.suffix == ".base")
                or (relative.parent == PurePosixPath("indexes") and relative.suffix == ".md")
            )
            or (manifest.view_schema_version == "2.0" and relative == REFERENCE_INDEX)
        ):
            raise ProjectionError("Invalid direct-view ownership path/type")
        prior[relative] = item
    return prior


def source_bytes(repo: Path, relative: PurePosixPath) -> bytes:
    path = repo / relative
    no_symlink_boundary(path)
    if not path.is_file():
        raise ProjectionError("Missing direct-view source; restore the committed Base")
    git(repo, "ls-files", "--error-unmatch", "--", str(relative))
    return path.read_bytes()


def project(
    repo_root: Path, vault_root: Path, source_ref: str, *, check: bool = False
) -> dict[PurePosixPath, bytes]:
    # RA-1 performs all topology/marker/Git/Atlas/RA-2 checks, strictly without writes.
    # Inspect our boundary first so symlinks never reach the authored-note scanner.
    no_symlink_boundary(vault_root.absolute())
    vault = vault_root.resolve()
    root = vault / OWNED_ROOT
    actual = inspect_owned(root)
    prior = validate_prior(root)
    for relative in actual:
        # Convert invalid owned Markdown encoding into an actionable validation error
        # before RA-1 reads this otherwise unmodeled navigation note.
        if relative.suffix.lower() == ".md":
            utf8(target_path(root, relative).read_bytes())
    try:
        technical = technical_projection(repo_root, vault_root, source_ref, check=True)
    except (OSError, UnicodeError) as exc:
        raise ProjectionError("Cannot read projection preconditions") from exc
    commit = read_yaml(utf8(technical[PurePosixPath("manifest/projection.yaml")]))["source_commit"]
    repo = repo_root.resolve()
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", *SOURCE_PATHS):
        raise ProjectionError(
            "Direct-view sources are dirty; commit or resolve source changes first"
        )
    atlas = load_registry(repo / "docs/research-atlas")
    snapshot, locators = authored_snapshot(vault, atlas)
    reference = build_index(atlas, snapshot, commit)
    tree = reference_views_tree(
        commit,
        source_bytes(repo, PUBLIC_SOURCE),
        source_bytes(repo, DIRECT_SOURCE),
        reference,
        atlas,
        locators,
    )
    if actual - prior.keys() - {MANIFEST}:
        raise ProjectionError("Unknown/unowned derived files; move them out before generation")
    # Complete preflight before any mkdir, deletion, or atomic replace.
    for relative in tree.keys() | prior.keys():
        target = target_path(root, relative)
        if target.exists() and not target.is_file():
            raise ProjectionError("Direct-view output path is occupied by a directory")
        for parent in target.parents:
            if parent == vault:
                break
            if parent.exists() and not parent.is_dir():
                raise ProjectionError("Direct-view output parent is not a directory")
    for relative, item in prior.items():
        if relative not in actual:
            continue
        data = target_path(root, relative).read_bytes()
        if relative == REFERENCE_INDEX:
            metadata = read_yaml(utf8(data))
            owned = (
                metadata.get("generated_by") == OWNER
                and metadata.get("index_schema_version") == "1.0"
            )
        elif relative.suffix == ".base":
            owned = data.startswith(BASE_OWNER.encode())
        else:
            owned = markdown_parts(utf8(data))[0].get("generated_by") == OWNER
        if not owned:
            raise ProjectionError("Prior-owned view lost its owner marker; preserve or restore it")
        if relative not in tree and digest(data) != item.sha256:
            raise ProjectionError("Obsolete owned view was edited; preserve edits before cleanup")
    if check:
        if actual != tree.keys() or any(
            target_path(root, p).read_bytes() != data for p, data in tree.items()
        ):
            raise ProjectionError("Direct-view drift; regenerate with the same source-ref")
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
        "--check", action="store_true", help="Validate exact views without any writes"
    )
    args = parser.parse_args(argv)
    try:
        project(args.repo_root, args.vault_root, args.source_ref, check=args.check)
    except ProjectionError as exc:
        print(f"Direct views: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
