import sqlite3
from pathlib import Path

import pytest
from mission_fixtures import (
    RUN_ID,
    FakeClock,
    FaultHook,
    digest,
    make_manifest,
    new_ledger,
    raw_connection,
    resume,
    table_snapshot,
)

from fh_agent.mission.ledger import (
    EPISODE_BUDGET,
    GLOBAL_ACTION_BUDGET,
    LEDGER_FILENAME,
    MissionLedger,
)
from fh_agent.mission.state import (
    EpisodeState,
    FaultPoint,
    IdentityMismatchError,
    InvalidMissionTransition,
    LedgerIntegrityError,
    LedgerWriteError,
    MissionExistsError,
    MissionPathError,
    MissionState,
    RecoveryDecision,
    StaleWriterError,
    UnsupportedLedgerSchema,
)


def test_create_new_mission_is_exclusive_and_active(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path, open_episode=False)

    assert ledger.db_path == (tmp_path / RUN_ID / LEDGER_FILENAME).resolve()
    assert ledger.mission_state() is MissionState.ACTIVE
    assert ledger.generation == 1
    assert [event.kind for event in ledger.events()] == ["mission_created"]
    with pytest.raises(MissionExistsError):
        MissionLedger.create_new_mission(tmp_path, make_manifest())


def test_sqlite_connection_uses_wal_and_full_sync(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)

    assert ledger.fetch_one("PRAGMA journal_mode") == ("wal",)
    assert ledger.fetch_one("PRAGMA synchronous") == (2,)
    assert ledger.fetch_one("PRAGMA foreign_keys") == (1,)


def test_ac1_clean_reopen_restores_same_mission_under_recovery_hold(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    episode = ledger.active_episode()
    assert episode is not None
    before_budget = ledger.budget(EPISODE_BUDGET)
    ledger.close()

    restored = resume(tmp_path, created_at="2027-02-02T00:00:00+00:00")

    assert restored.run_id == RUN_ID
    assert restored.manifest.manifest_sha256 == make_manifest().manifest_sha256
    assert restored.generation == 2
    assert restored.mission_state() is MissionState.RECOVERY_HOLD
    assert restored.budget(EPISODE_BUDGET) == before_budget
    assert sorted(path.name for path in tmp_path.iterdir()) == [RUN_ID]
    assert (
        restored.resolve_recovery(RecoveryDecision.resume_same_run, operator_ref="operator-1")
        is MissionState.ACTIVE
    )
    resumed_episode = restored.active_episode()
    assert resumed_episode is not None
    assert resumed_episode.episode_id == episode.episode_id
    assert resumed_episode.state is EpisodeState.OPEN


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"cortex__model_revision": "fake-2"}, "cortex.model_revision"),
        ({"cortex__prompt_bundle_sha256": digest("other prompts")}, "cortex.prompt_bundle_sha256"),
        ({"body__controller_version": "heuristic-2"}, "body.controller_version"),
        ({"policy_hashes__verifier": digest("other verifier")}, "policy_hashes.verifier"),
        ({"run_mode": "debug"}, "run_mode"),
        ({"source__dirty": True}, "source.dirty"),
        ({"source__diff_sha256": digest("diff")}, "source.diff_sha256"),
    ],
)
def test_ac2_identity_mismatch_refuses_without_lease_or_row_mutation(
    tmp_path: Path, override: dict[str, object], field: str
) -> None:
    ledger = new_ledger(tmp_path)
    db_path = ledger.db_path
    ledger.close()
    before = table_snapshot(db_path)

    with pytest.raises(IdentityMismatchError) as raised:
        resume(tmp_path, **override)

    assert raised.value.fields == [field]
    assert table_snapshot(db_path) == before


def test_ac2_unknown_ledger_schema_version_is_refused_read_only(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    db_path = ledger.db_path
    ledger.close()
    conn = raw_connection(db_path)
    conn.execute("UPDATE mission SET ledger_schema_version = '99'")
    conn.close()
    before = table_snapshot(db_path)

    with pytest.raises(UnsupportedLedgerSchema):
        resume(tmp_path)

    assert table_snapshot(db_path) == before


def test_ac3_budget_counters_are_monotone_and_ceilings_frozen(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    conn = raw_connection(ledger.db_path)
    conn.execute("UPDATE budget_counters SET used = 2 WHERE name = ?", (GLOBAL_ACTION_BUDGET,))

    with pytest.raises(sqlite3.IntegrityError, match="monotone"):
        conn.execute("UPDATE budget_counters SET used = 1 WHERE name = ?", (GLOBAL_ACTION_BUDGET,))
    with pytest.raises(sqlite3.IntegrityError, match="frozen"):
        conn.execute(
            'UPDATE budget_counters SET "limit" = 99 WHERE name = ?', (GLOBAL_ACTION_BUDGET,)
        )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute("UPDATE budget_counters SET used = 11 WHERE name = ?", (GLOBAL_ACTION_BUDGET,))
    conn.close()
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 2


def test_ac3_restore_never_resets_counters(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    ledger.close_episode("stop")
    ledger.open_episode()
    used = ledger.budget(EPISODE_BUDGET).used
    ledger.close()

    restored = resume(tmp_path)

    assert restored.budget(EPISODE_BUDGET).used == used == 2


def test_episode_budget_is_enforced(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path, budgets__max_life_episodes=1)
    ledger.close_episode("stop")

    with pytest.raises(Exception, match="life_episodes"):
        ledger.open_episode()


def test_at_most_one_open_episode(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)

    with pytest.raises(InvalidMissionTransition):
        ledger.open_episode()
    conn = raw_connection(ledger.db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO life_episodes VALUES ('x-e999', ?, 999, 'OPEN', 1, NULL)", (RUN_ID,)
        )
    conn.close()


def test_ac10_older_handle_is_fenced_and_writes_nothing(tmp_path: Path) -> None:
    old = new_ledger(tmp_path)
    new = resume(tmp_path)
    before = table_snapshot(new.db_path)

    with pytest.raises(StaleWriterError):
        old.close_episode("stale")
    with pytest.raises(StaleWriterError):
        old.verify_writer()

    assert table_snapshot(new.db_path) == before
    assert new.generation == old.generation + 1


def test_ac10_event_ids_are_unique_and_sequence_contiguous(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    conn = raw_connection(ledger.db_path)
    first = conn.execute("SELECT * FROM run_events WHERE seq = 1").fetchone()
    (last_seq,) = conn.execute("SELECT MAX(seq) FROM run_events").fetchone()

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        conn.execute(
            "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (last_seq + 1, first[1], *first[2:]),
        )
    with pytest.raises(sqlite3.IntegrityError, match="contiguous"):
        conn.execute(
            "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (last_seq + 5, "fresh-event-id", *first[2:]),
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE run_events SET kind = 'x' WHERE seq = 1")
    conn.close()


def test_ac10_tampered_event_payload_blocks_restore_before_activity(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    db_path = ledger.db_path
    ledger.close()
    conn = raw_connection(db_path)
    conn.execute("DROP TRIGGER run_events_append_only_update")
    conn.execute("UPDATE run_events SET payload_json = '{\"forged\":true}' WHERE seq = 2")
    conn.close()
    before = table_snapshot(db_path)

    with pytest.raises(LedgerIntegrityError, match="seq 2"):
        resume(tmp_path)

    assert table_snapshot(db_path) == before


def test_resume_path_must_stay_inside_runs_root(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    new_ledger(runs_root).close()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "mission-elsewhere-01").symlink_to(runs_root / RUN_ID)

    with pytest.raises(MissionPathError):
        MissionLedger.resume_existing_mission(runs_root, "../" + RUN_ID, make_manifest())
    with pytest.raises(MissionPathError):
        MissionLedger.resume_existing_mission(
            outside, "mission-elsewhere-01", make_manifest("mission-elsewhere-01")
        )


def test_restore_transaction_failure_returns_no_handle(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    db_path = ledger.db_path
    ledger.close()
    before = table_snapshot(db_path)
    hook = FaultHook()
    hook.fail(FaultPoint.RECOVERY_WRITE)

    with pytest.raises(LedgerWriteError):
        resume(tmp_path, fault_hook=hook)

    assert table_snapshot(db_path) == before


def test_terminal_states_are_irreversible(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path, clock=FakeClock())
    ledger.terminate(MissionState.TERMINAL_STOPPED, "owner stop")

    with pytest.raises(InvalidMissionTransition):
        ledger.terminate(MissionState.TERMINAL_FAILURE, "again")
    with pytest.raises(InvalidMissionTransition):
        ledger.open_episode()
    conn = raw_connection(ledger.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="irreversible"):
        conn.execute("UPDATE mission SET state = 'ACTIVE'")
    conn.close()
    restored = resume(tmp_path)
    assert restored.mission_state() is MissionState.TERMINAL_STOPPED
