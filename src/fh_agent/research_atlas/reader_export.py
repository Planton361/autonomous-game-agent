"""Read-only private reader projection for generic Markdown/PDF renderers."""

import argparse
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .preferred_paths import PRODUCT
from .private_projection import ProjectionError, digest, no_symlink_boundary, validate_private_vault
from .private_views import OWNED_ROOT, _identity_page_generated_metadata, reader_export
from .product_migration import _current
from .rq_presentation import rq_metadata


def reader_derivative(payload: bytes, page: PurePosixPath, output: PurePosixPath) -> bytes:
    """Preserve private note destinations when the derivative changes folders."""

    def rebase(match: re.Match[str]) -> str:
        locator = match.group(1)
        parsed = urlsplit(locator)
        if parsed.scheme or parsed.netloc or locator.startswith(("/", "#")):
            return match.group(0)
        original = posixpath.normpath(str(page.parent / parsed.path))
        relative = posixpath.relpath(original, start=str(output.parent))
        suffix = ("?" + parsed.query if parsed.query else "") + (
            "#" + parsed.fragment if parsed.fragment else ""
        )
        return "](" + relative + suffix + ")"

    text = (
        reader_export(payload)
        .decode()
        .replace("[[#Sources & audit|", f"[[{page.with_suffix('')}#Sources & audit|")
    )
    return re.sub(r"\]\(([^)\s]+)\)", rebase, text).encode()


def export_reader(repo: Path, vault: Path, page: PurePosixPath, output: PurePosixPath) -> None:
    """Explicit private-to-private derivative; never overwrite a master or write outside vault."""
    root = validate_private_vault(vault, repo.resolve())
    for relative in (page, output):
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
            raise ProjectionError("Reader paths must be vault-relative")
        no_symlink_boundary(root / relative)
    if not (page.is_relative_to(OWNED_ROOT) or page.is_relative_to(PRODUCT)):
        raise ProjectionError("Reader source must be a generated preferred page")
    if not output.is_relative_to(PurePosixPath("reader-exports")) or output.suffix != ".md":
        raise ProjectionError("Reader output must be private reader-exports/*.md")
    source = root / page
    payload = source.read_bytes()
    if page.is_relative_to(PRODUCT):
        row = _current(root).get(page)
        if (
            row is None
            or row["owner"] != "research-wiki-derived"
            or digest(payload) != row["sha256"]
        ):
            raise ProjectionError("Reader source must have intact manifested ownership")
        text = payload.decode()
        if not ("identity_page_path: " + str(page) in text or "rq_page_path: " + str(page) in text):
            raise ProjectionError("Reader source must be a technical preferred page or RQ Reader")
    else:
        relative = page.relative_to(OWNED_ROOT)
        if not (
            _identity_page_generated_metadata(payload.decode(), relative)
            or rq_metadata(payload.decode(), relative)
        ):
            raise ProjectionError("Reader source must have valid generated Identity Page ownership")
    destination = root / output
    if destination.exists():
        raise ProjectionError("Reader output already exists; select a new derivative filename")
    projected = reader_derivative(payload, page, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(projected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--vault-root", type=Path, required=True)
    parser.add_argument("--page", type=PurePosixPath, required=True)
    parser.add_argument("--output", type=PurePosixPath, required=True)
    args = parser.parse_args()
    try:
        export_reader(args.repo_root, args.vault_root, args.page, args.output)
    except (OSError, UnicodeError, ProjectionError) as exc:
        print(f"Reader export refused: {exc}", file=sys.stderr)
        return 1
    print("Private reader projection created; complete audit remains on the original page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
