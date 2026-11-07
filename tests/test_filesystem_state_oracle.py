"""Synthetic oracle: the scandir snapshot helper equals the original pathlib helper (#180)."""

import os
import sys

import pytest
from test_research_wiki_projection import filesystem_state


def pathlib_filesystem_state(root):
    # Unchanged pre-#180 helper, kept verbatim as the equivalence oracle.
    return {
        str(p.relative_to(root)): (
            p.stat().st_ino,
            p.stat().st_mtime_ns,
            p.is_dir(),
            p.read_bytes() if p.is_file() else None,
        )
        for p in [root, *root.rglob("*")]
    }


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "root"
    (root / "nested/deeper/deepest").mkdir(parents=True)
    (root / "nested/deeper/deepest/note.md").write_text("synthetic\n", encoding="utf-8")
    (root / "nested/binary.bin").write_bytes(bytes(range(256)) + b"\x00\r\n")
    (root / "empty-dir").mkdir()
    (root / "with spaces & ümlaut").mkdir()
    (root / "with spaces & ümlaut/.hidden").write_bytes(b"")
    outside = tmp_path / "outside"
    (outside / "inner").mkdir(parents=True)
    (outside / "inner/secret.txt").write_text("not traversed\n", encoding="utf-8")
    (root / "linked-dir").symlink_to(outside)
    (root / "linked-file").symlink_to(root / "nested/binary.bin")
    return root


def assert_equivalent(root):
    state = filesystem_state(root)
    assert state == pathlib_filesystem_state(root)
    return state


def test_snapshot_matches_oracle_including_root_and_symlinks(tree):
    state = assert_equivalent(tree)
    assert state["."][2] is True
    assert state["nested/binary.bin"][3] == bytes(range(256)) + b"\x00\r\n"
    assert state["empty-dir"][2:] == (True, None)
    assert state["linked-dir"][2:] == (True, None)
    assert state["linked-file"][3] == state["nested/binary.bin"][3]
    assert not any(key.startswith("linked-dir/") for key in state)


def _replace_inode(root):
    path = root / "nested/binary.bin"
    replacement = path.with_name("replacement.tmp")
    replacement.write_bytes(path.read_bytes())
    os.utime(replacement, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns))
    os.replace(replacement, path)


def _touch_mtime(root):
    path = root / "nested/deeper/deepest/note.md"
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000_000))


MUTATIONS = {
    "bytes": lambda root: (root / "nested/deeper/deepest/note.md").write_bytes(b"synthetiC\n"),
    "mtime": _touch_mtime,
    "inode-replacement": _replace_inode,
    "create-directory": lambda root: (root / "empty-dir/created").mkdir(),
    "remove-directory": lambda root: (root / "empty-dir").rmdir(),
    "create-file": lambda root: (root / "nested/new.txt").write_bytes(b""),
    "remove-file": lambda root: (root / "with spaces & ümlaut/.hidden").unlink(),
    "retarget-symlink": lambda root: (
        (root / "linked-file").unlink(),
        (root / "linked-file").symlink_to(root / "nested/deeper/deepest/note.md"),
    ),
}


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_snapshot_detects_each_change_exactly_like_oracle(tree, mutation):
    before = assert_equivalent(tree)
    MUTATIONS[mutation](tree)
    after = assert_equivalent(tree)
    assert after != before


def test_broken_symlink_fails_like_oracle(tree):
    (tree / "dangling").symlink_to(tree / "missing")
    with pytest.raises(FileNotFoundError):
        pathlib_filesystem_state(tree)
    with pytest.raises(FileNotFoundError):
        filesystem_state(tree)


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX non-root permissions"
)
def test_unreadable_directory_contributes_no_children_like_oracle(tree):
    locked = tree / "nested/locked"
    locked.mkdir()
    (locked / "hidden.txt").write_text("x", encoding="utf-8")
    locked.chmod(0)
    try:
        state = assert_equivalent(tree)
        assert "nested/locked" in state
        assert "nested/locked/hidden.txt" not in state
    finally:
        locked.chmod(0o700)
