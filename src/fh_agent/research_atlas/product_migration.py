"""Global, fail-closed migration with two explicit logical owners and no adoption."""

import errno
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath

from . import obsidian_semantics as semantics
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
            prior[full] = dict(
                sha256=item.sha256, owner=module.OWNER, ownership=semantics.Ownership.STRICT.value
            )
            if path.suffix == ".base" and getattr(item, "semantic_sha256", None):
                prior[full]["semantic_sha256"] = item.semantic_sha256
                prior[full]["ownership"] = semantics.Ownership.BASE.value
        manifest = root / module.MANIFEST
        if manifest.exists():
            full = module.OWNED_ROOT / module.MANIFEST
            prior[full] = dict(
                sha256=digest(manifest.read_bytes()),
                owner=module.OWNER,
                ownership=semantics.Ownership.STRICT.value,
            )
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
            or metadata["product_schema_version"] not in ("1.0", "1.1")
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
            legacy = metadata["product_schema_version"] == "1.0"
            fields = (
                set(row) - ({"ownership"} if not legacy else set())
                if isinstance(row, dict)
                else set()
            )
            if not isinstance(row, dict) or fields not in (
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
            kind = semantics.classification(full)
            if legacy:
                kind = (
                    semantics.Ownership.BASE
                    if full.suffix == ".base"
                    else semantics.Ownership.STRICT
                )
            elif row.get("ownership") != kind.value:
                raise ProjectionError("Invalid final ownership classification")
            if (kind != semantics.Ownership.STRICT) != ("semantic_sha256" in row):
                raise ProjectionError("Invalid final semantic ownership classification")
            if "semantic_sha256" in row and not re.fullmatch(
                r"[a-f0-9]{64}", str(row["semantic_sha256"])
            ):
                raise ProjectionError("Invalid final semantic digest")
            prior[full] = dict(row, owner=owner, ownership=kind.value)
            if legacy and semantics.classification(full) in {
                semantics.Ownership.CANVAS,
                semantics.Ownership.EXCALIDRAW,
            }:
                prior[full]["legacy_source_commit"] = provenance["source_commit"]
        prior[path] = dict(
            sha256=digest(source.read_bytes()),
            owner=owner,
            ownership=semantics.Ownership.STRICT.value,
        )
    return prior


def prove_ownership(
    repo: Path, source_vault: Path, storage: Path, prior: dict[PurePosixPath, dict]
) -> dict[PurePosixPath, dict]:
    """Promote only reproducible 1.0 surfaces whose reference matches the old byte hash."""
    references = {}
    proven = {}
    for path, original in prior.items():
        row = dict(original)
        target = target_path(storage, path)
        if not target.exists():
            continue
        data = target.read_bytes()
        if row.get("legacy_source_commit") and digest(data) != row["sha256"]:
            revision = row["legacy_source_commit"]
            if revision not in references:
                references[revision] = build(repo, source_vault, revision)
            reference = references[revision]
            emitted = reference.files.get(path)
            if (
                emitted is None
                or reference.owners[path] != row["owner"]
                or digest(emitted) != row["sha256"]
            ):
                raise ProjectionError(
                    "Cannot prove historical semantic ownership from emitted digest"
                )
            row.update(
                ownership=semantics.classification(path).value,
                semantic_sha256=semantics.semantic_digest(emitted, path, row["owner"]),
            )
        if row["ownership"] == semantics.Ownership.STRICT.value:
            if not _owner(data, path, row["owner"]):
                raise ProjectionError("Owned content lost its owner marker")
            valid = digest(data) == row["sha256"]
        else:
            valid = intact(data, path, row)
        if not valid:
            raise ProjectionError("Owned content was edited; restore or preserve it")
        proven[path] = row
    return proven


def intact(data: bytes, path: PurePosixPath, row: dict) -> bool:
    kind = semantics.Ownership(row["ownership"])
    if kind == semantics.Ownership.STRICT:
        return _owner(data, path, row["owner"]) and digest(data) == row["sha256"]
    return semantics.semantic_digest(data, path, row["owner"]) == row["semantic_sha256"]


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
    intended: dict[Path, dict[str, str]] = {}
    for relative in tree.files:
        parent = vault
        for name in relative.parts:
            key = unicodedata.normalize("NFD", name).casefold()
            names = intended.setdefault(parent, {})
            if key in names and names[key] != name:
                raise ProjectionError("Destination case/Unicode collision")
            names[key] = name
            parent /= name
    # Read every parent live once against ALL intended child names. This retains
    # the exhaustive alias check without a directory scan per destination name.
    # No filesystem results survive this preflight; target_path stays live.
    for parent, names in intended.items():
        if parent.is_dir():
            for sibling in parent.iterdir():
                name = names.get(unicodedata.normalize("NFD", sibling.name).casefold())
                if name is not None and sibling.name != name:
                    raise ProjectionError("Destination case/Unicode collision")
    for path in tree.files.keys() | prior.keys():
        destination = target_path(vault, path)
        if destination.exists() and not destination.is_file():
            raise ProjectionError("Destination collision with directory")
        for parent in destination.parents:
            if parent == vault:
                break
            if parent.exists() and not parent.is_dir():
                raise ProjectionError("Destination parent collision")
    prove_ownership(repo, vault, vault, prior)
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
        if semantics.classification(path) != semantics.Ownership.STRICT:
            owner = tree.owners[path]
            equal = semantics.semantic_digest(actual, path, owner) == semantics.semantic_digest(
                expected, path, owner
            )
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
