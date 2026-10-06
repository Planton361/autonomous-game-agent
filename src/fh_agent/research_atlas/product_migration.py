"""Global, fail-closed migration with two explicit logical owners and no adoption."""

import errno
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath

from . import private_projection as public
from . import private_views as views
from .final_projection import LEDGER, MANIFESTS, ProductTree, package
from .preferred_paths import HOME, INTERNAL, PRODUCT
from .private_projection import (
    ProjectionError,
    atomic_write,
    digest,
    inspect_owned,
    markdown_parts,
    no_symlink_boundary,
    read_yaml,
    relative_target_path,
    target_path,
    utf8,
    validate_portable_paths,
)
from .source_resolution import SourceIndex, validate_read_provenance, validate_source_history
from .validator import load_registry

ROOTS = (public.OWNED_ROOT, views.OWNED_ROOT, PRODUCT, INTERNAL)


def _owner(data: bytes, path: PurePosixPath, expected: str) -> bool:
    if path.suffix == ".svg":
        return expected == public.OWNER
    if path.suffix == ".base":
        return data.startswith(views.BASE_OWNER.encode())
    text = utf8(data)
    if path.suffix == ".canvas":
        canvas = json.loads(text)
        return isinstance(canvas, dict) and canvas.get("generated_by") == expected
    if path.suffix == ".yaml":
        return read_yaml(text).get("generated_by") == expected
    if markdown_parts(text)[0].get("generated_by") == expected:
        return True
    for marker in (
        views.IDENTITY_PAGE_METADATA_MARKER,
        views.RQ_METADATA_MARKER,
        views.STEERING_METADATA_MARKER,
        views.OBSERVE_SCOPE_METADATA_MARKER,
    ):
        if text.count(marker) == 1:
            header = text.split(marker, 1)[1].split("-->", 1)[0]
            if read_yaml(header).get("generated_by") == expected:
                return True
    return False


def _actual(vault: Path) -> set[PurePosixPath]:
    paths = {root / path for root in ROOTS for path in inspect_owned(vault / root)}
    no_symlink_boundary(vault / HOME)
    if (vault / HOME).exists():
        if not (vault / HOME).is_file():
            raise ProjectionError("Home destination is not a regular file")
        paths.add(HOME)
    validate_portable_paths(paths)
    return paths


def _legacy(vault: Path) -> dict[PurePosixPath, dict]:
    prior = {}
    for module in (public, views):
        root = vault / module.OWNED_ROOT
        inventory = module.validate_prior(root)
        actual = inspect_owned(root)
        if actual - inventory.keys() - {module.MANIFEST}:
            raise ProjectionError("Unknown/unowned legacy content")
        for path, item in inventory.items():
            full = module.OWNED_ROOT / path
            prior[full] = dict(sha256=item.sha256, owner=module.OWNER)
            if path.suffix == ".base" and getattr(item, "semantic_sha256", None):
                prior[full]["semantic_sha256"] = item.semantic_sha256
        manifest = root / module.MANIFEST
        if manifest.exists():
            full = module.OWNED_ROOT / module.MANIFEST
            prior[full] = dict(sha256=digest(manifest.read_bytes()), owner=module.OWNER)
    return prior


def _current(vault: Path) -> dict[PurePosixPath, dict]:
    prior = {}
    for owner, path in MANIFESTS.items():
        source = target_path(vault, path)
        if not source.exists():
            continue
        metadata = read_yaml(utf8(source.read_bytes()))
        if (
            set(metadata) != {"product_schema_version", "generated_by", "provenance", "owned_files"}
            or metadata["product_schema_version"] != "1.0"
            or metadata["generated_by"] != owner
        ):
            raise ProjectionError("Invalid final owner manifest")
        # Retain strict typed source-provenance contracts, without changing fingerprints.
        if not isinstance(metadata["provenance"], dict) or not isinstance(
            metadata["owned_files"], list
        ):
            raise ProjectionError("Invalid final manifest field types")
        provenance = dict(metadata["provenance"])
        provenance["owned_files"] = []
        try:
            (public.Manifest if owner == public.OWNER else views.ManifestV217).model_validate(
                provenance
            )
        except ValueError as exc:
            raise ProjectionError("Corrupt final source provenance") from exc
        for row in metadata["owned_files"]:
            if not isinstance(row, dict) or set(row) not in (
                {"path", "sha256"},
                {"path", "sha256", "semantic_sha256"},
            ):
                raise ProjectionError("Invalid final owned file")
            relative_target_path(vault, row["path"])
            full = PurePosixPath(row["path"])
            if full in prior or full in MANIFESTS.values():
                raise ProjectionError("Duplicate/self-owned final manifest path")
            if not (full == HOME or full.is_relative_to(PRODUCT) or full.is_relative_to(INTERNAL)):
                raise ProjectionError("Final manifest escapes generated namespaces")
            if not isinstance(row["sha256"], str) or not re.fullmatch(
                r"[a-f0-9]{64}", row["sha256"]
            ):
                raise ProjectionError("Invalid owned digest")
            if (full.suffix == ".base") != ("semantic_sha256" in row):
                raise ProjectionError("Invalid final Base ownership classification")
            if "semantic_sha256" in row and not re.fullmatch(
                r"[a-f0-9]{64}", str(row["semantic_sha256"])
            ):
                raise ProjectionError("Invalid final Base semantic digest")
            prior[full] = dict(row, owner=owner)
        prior[path] = dict(sha256=digest(source.read_bytes()), owner=owner)
    return prior


def build(repo: Path, vault: Path, commit: str) -> ProductTree:
    for source in public.SOURCE_PATHS:
        no_symlink_boundary(repo / source)
    no_symlink_boundary(repo / public.HERO_SOURCE)
    if (repo / public.HERO_SOURCE).read_bytes() != public.anatomy_hero_svg().encode():
        raise ProjectionError("Illustration source differs from the checked-out renderer")
    for filename in public.REGISTRY_FILES:
        no_symlink_boundary(repo / public.SOURCE_PATHS[0] / filename)
    atlas = load_registry(repo / "docs/research-atlas")
    snapshot, locators, records = views.authored_snapshot(vault, atlas)
    reference = views.build_index(atlas, snapshot, commit)
    technical = public.projection_tree(
        atlas,
        commit,
        {
            name: digest((repo / public.SOURCE_PATHS[0] / name).read_bytes())
            for name in public.REGISTRY_FILES
        },
    )
    derived = views.reference_views_tree(
        commit,
        views.source_bytes(repo, views.PUBLIC_SOURCE),
        views.source_bytes(repo, views.DIRECT_SOURCE),
        reference,
        atlas,
        locators,
        snapshot,
        (vault / "_generated/zotero/manifest/projection.yaml").is_file(),
        records,
        engineering_bindings=views.parse_catalog(
            views.source_bytes(repo, views.CATALOG_PATH), atlas
        ),
        source_catalog=views.load_catalog(vault),
    )
    return package(atlas, technical, derived)


def preflight(repo: Path, vault: Path, commit: str) -> tuple[ProductTree, set[PurePosixPath]]:
    actual = _actual(vault)
    legacy = _legacy(vault)
    current = _current(vault)
    if legacy.keys() & current.keys():
        raise ProjectionError("Ambiguous ownership")
    prior = legacy | current
    tree = build(repo, vault, commit)
    if actual - prior.keys():
        raise ProjectionError("Unknown/unowned product destination; no adoption")
    # Exact current inventory is the finite ownership allowlist, not a namespace wildcard.
    for path, row in current.items():
        if path not in tree.files or tree.owners[path] != row["owner"]:
            raise ProjectionError("Ambiguous or invalid final ownership path")
    validate_portable_paths(tree.files.keys() | actual)
    # Also reject case/Unicode aliases in existing directory entries, including
    # unowned sibling namespaces on case-sensitive Linux filesystems.
    checked = set()
    for relative in tree.files:
        parent = vault
        for name in relative.parts:
            key = unicodedata.normalize("NFD", name).casefold()
            if parent.is_dir() and (parent, name) not in checked:
                for sibling in parent.iterdir():
                    if (
                        unicodedata.normalize("NFD", sibling.name).casefold() == key
                        and sibling.name != name
                    ):
                        raise ProjectionError("Destination case/Unicode collision")
                checked.add((parent, name))
            parent /= name
    for path in tree.files.keys() | prior.keys():
        destination = target_path(vault, path)
        if destination.exists() and not destination.is_file():
            raise ProjectionError("Destination collision with directory")
        for parent in destination.parents:
            if parent == vault:
                break
            if parent.exists() and not parent.is_dir():
                raise ProjectionError("Destination parent collision")
    for path in actual:
        row = prior[path]
        data = target_path(vault, path).read_bytes()
        semantic_base = path.suffix == ".base" and row.get("semantic_sha256")
        if not semantic_base and not _owner(data, path, row["owner"]):
            raise ProjectionError("Owned content lost its owner marker")
        if path.suffix == ".base" and row.get("semantic_sha256"):
            intact = views._base_semantic_digest(data) == row["semantic_sha256"]
        else:
            intact = digest(data) == row["sha256"]
        if not intact:
            raise ProjectionError("Owned content was edited; restore or preserve it")
    source = INTERNAL / "Indexes/source-resolution-index.yaml"
    old_source = views.OWNED_ROOT / views.SOURCE_INDEX
    for path in (old_source, source):
        if path not in prior:
            continue
        if path not in actual:
            raise ProjectionError("Missing source history index; restore its manifested bytes")
        previous = SourceIndex.model_validate(
            read_yaml(utf8(target_path(vault, path).read_bytes()))
        )
        present = SourceIndex.model_validate(read_yaml(utf8(tree.files[source])))
        validate_source_history(previous.catalog, present.catalog)
        validate_read_provenance(previous, present)
    # Ledger contains every historical owned file, including supported older versions.
    ledger = read_yaml(utf8(tree.files[LEDGER]))
    for path in sorted(legacy):
        if str(path) not in ledger["routes"]:
            raise ProjectionError("Legacy route absent from bounded migration inventory")
    return tree, actual


def verify(vault: Path, tree: ProductTree) -> None:
    if _actual(vault) != tree.files.keys():
        raise ProjectionError("Final inventory drift")
    for path, expected in tree.files.items():
        actual = target_path(vault, path).read_bytes()
        if path.suffix == ".base":
            equal = views._base_semantically_matches(actual, expected)
        else:
            equal = actual == expected
        if not equal:
            raise ProjectionError(f"Final generated drift: {path}")


def apply(vault: Path, tree: ProductTree, actual: set[PurePosixPath]) -> None:
    manifests = set(MANIFESTS.values())
    for path, data in sorted(tree.files.items()):
        if path not in manifests:
            atomic_write(vault, path, data)
    # Replacements must read back exactly before any retirement.
    for path, data in tree.files.items():
        if path not in manifests and target_path(vault, path).read_bytes() != data:
            raise ProjectionError("Replacement verification failed; legacy files retained")
    for path in sorted(actual - tree.files.keys()):
        target_path(vault, path).unlink()
    # Prune only empty directories that were ancestors of retired owned files,
    # stopping at each old root; independently owned _generated siblings survive.
    directories = set()
    for path in actual - tree.files.keys():
        for root in (public.OWNED_ROOT, views.OWNED_ROOT):
            if path.is_relative_to(root):
                directories.update(parent for parent in path.parents if parent.is_relative_to(root))
    for relative in sorted(directories, key=lambda p: (-len(p.parts), str(p))):
        directory = target_path(vault, relative)
        try:
            directory.rmdir()
        except OSError as exc:
            if exc.errno not in {errno.ENOTEMPTY, errno.ENOENT}:
                raise
    for path in sorted(manifests):
        atomic_write(vault, path, tree.files[path])
    verify(vault, tree)
