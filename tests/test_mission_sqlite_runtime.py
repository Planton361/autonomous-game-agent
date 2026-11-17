"""Record the SQLite library actually linked at test time (Issue #184 Test/CI evidence).

The version is emitted as a pytest warning so it appears in the default warnings summary of
every local and CI run that collects this module; it is real runtime output, not an estimate.
"""

import platform
import sqlite3
import warnings
from pathlib import Path

from mission_fixtures import new_ledger

# Partial unique indexes (3.8.0) are the newest SQLite feature the Mission ledger relies on.
MINIMUM_SQLITE = (3, 8, 0)


def test_sqlite_runtime_is_reported_and_supports_the_ledger(tmp_path: Path) -> None:
    # A built-in category keeps the warning serializable across pytest-xdist workers.
    warnings.warn(
        f"MRIC-S0 runtime report: sqlite3.sqlite_version={sqlite3.sqlite_version} "
        f"python={platform.python_version()}",
        UserWarning,
        stacklevel=1,
    )
    ledger = new_ledger(tmp_path)

    assert sqlite3.sqlite_version_info >= MINIMUM_SQLITE
    assert ledger.fetch_one("SELECT sqlite_version()") == (sqlite3.sqlite_version,)
