"""Closed original-reference data; never execute code selected by a vault manifest."""

import base64
import gzip
import io
import json
import re
import subprocess
import tarfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from . import private_projection as public
from . import private_views as views
from .final_projection import MANIFESTS, ProductTree
from .private_projection import ProjectionError, digest, git, no_symlink_boundary, read_yaml, utf8

HISTORICAL_COMMIT = "8e544d2e05180306a9580b5475c03e0bd91601ac"
HISTORICAL_TREE = "8bcc160af08583a053b06d12a3b07af9c5dd1e71"
# Pinned independently sandboxed historical code + assets, empty synthetic inputs.
REFERENCE_SHA256 = "c8cf4a6bbe318c895f2c4e68859b0599069ec4774147e990f32f0171cc3ec1af"
REFERENCE_PATH = Path(__file__).parent / "historical_references/8e544d2.json.gz"


def _same_renderer(repo: Path, revision: str) -> bool:
    """Current rendering is historical only when all code/assets are byte-identical."""
    package = Path(__file__).parent
    sources = {
        "src/fh_agent/research_atlas/" + str(p.relative_to(package)): p
        for p in package.rglob("*.py")
    }
    sources["src/fh_agent/__init__.py"] = package.parent / "__init__.py"
    for path in (
        *(PurePosixPath(public.SOURCE_PATHS[0]) / name for name in public.REGISTRY_FILES),
        public.HERO_SOURCE,
        views.PUBLIC_SOURCE,
        views.DIRECT_SOURCE,
        views.CATALOG_PATH,
    ):
        sources[str(path)] = repo / path
    for path in sources.values():
        no_symlink_boundary(path)
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), "archive", revision, *sorted(sources)],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return False
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        emitted = {}
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile() or member.name not in sources:
                return False
            stream = archive.extractfile(member)
            if stream is None:
                return False
            emitted[member.name] = stream.read()
    return emitted.keys() == sources.keys() and all(
        emitted[name] == path.read_bytes() for name, path in sources.items()
    )


def _frozen_reference(repo: Path) -> ProductTree:
    if git(repo, "rev-parse", "--verify", HISTORICAL_COMMIT + "^{tree}") != HISTORICAL_TREE:
        raise ProjectionError("Historical source tree differs from trusted original reference")
    no_symlink_boundary(REFERENCE_PATH)
    data = REFERENCE_PATH.read_bytes()
    if digest(data) != REFERENCE_SHA256:
        raise ProjectionError("Corrupt historical original reference")
    value = json.loads(gzip.decompress(data))
    if (
        set(value)
        != {"reference_schema_version", "source_commit", "source_tree", "files", "owners"}
        or value["reference_schema_version"] != "1.0"
        or value["source_commit"] != HISTORICAL_COMMIT
        or value["source_tree"] != HISTORICAL_TREE
        or value["files"].keys() != value["owners"].keys()
    ):
        raise ProjectionError("Invalid historical original reference lineage")
    files = {
        PurePosixPath(p): base64.b64decode(v, validate=True) for p, v in value["files"].items()
    }
    owners = {PurePosixPath(p): v for p, v in value["owners"].items()}
    public.validate_portable_paths(files)
    for owner, path in MANIFESTS.items():
        metadata = read_yaml(utf8(files[path]))
        if (
            metadata["product_schema_version"] != "1.0"
            or metadata["generated_by"] != owner
            or metadata["provenance"]["source_commit"] != HISTORICAL_COMMIT
        ):
            raise ProjectionError("Invalid historical original manifest")
        rows = {PurePosixPath(row["path"]): row for row in metadata["owned_files"]}
        for target in files:
            if target not in MANIFESTS.values() and owners[target] == owner:
                if target not in rows or digest(files[target]) != rows[target]["sha256"]:
                    raise ProjectionError("Corrupt historical emitted reference")
    return ProductTree(files, owners, {})


def resolve(
    repo: Path,
    vault: Path,
    revision: str,
    build: Callable[[Path, Path, str], ProductTree],
) -> ProductTree:
    """Bind original bytes to local immutable source and current admissible inputs."""
    if (
        not re.fullmatch(r"[a-f0-9]{40}", revision)
        or git(repo, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
        != revision
    ):
        raise ProjectionError("Unavailable historical source revision")
    if revision == HISTORICAL_COMMIT:
        reference = _frozen_reference(repo)
        # Current output is used ONLY to validate input provenance, never as this oracle.
        present = build(repo, vault, revision)
        for path in MANIFESTS.values():
            expected = read_yaml(utf8(reference.files[path]))["provenance"]
            actual = read_yaml(utf8(present.files[path]))["provenance"]
            if actual != expected:
                raise ProjectionError("Historical admissible inputs cannot be reproduced")
        return reference
    if not _same_renderer(repo, revision):
        raise ProjectionError("Unsupported historical renderer; no original reference")
    return build(repo, vault, revision)
