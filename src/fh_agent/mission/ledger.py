"""Per-Mission transactional SQLite ledger (MRIC-S0, Issue #184).

Every successfully persisted state transition commits atomically in one ``BEGIN IMMEDIATE``
transaction. A failed transaction rolls back and raises ``LedgerWriteError``; nothing from it
is durable and it is never cited as evidence that a fallback event or state was written.
Only the restore transaction in ``resume_existing_mission`` turns unresolved reservations
into ``UNKNOWN`` and the Mission into ``RECOVERY_HOLD``.
"""

import hashlib
import json
import re
import secrets
import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from fh_agent.mission.manifest import (
    MISSION_RUN_ID_PATTERN,
    MissionManifestV1,
    activation_refusals,
    compare_frozen_identity,
)
from fh_agent.mission.state import (
    ActionAttemptRecord,
    ActionDisposition,
    BudgetCounter,
    BudgetExhausted,
    ContractStatus,
    EpisodeState,
    FaultPoint,
    IdentityMismatchError,
    InvalidMissionTransition,
    LedgerIntegrityError,
    LedgerWriteError,
    LifeEpisodeV1,
    MissionActivationRefused,
    MissionExistsError,
    MissionFailStopped,
    MissionPathError,
    MissionState,
    RecoveryDecision,
    RecoveryRefused,
    RunEventRecord,
    StaleWriterError,
    UnsupportedLedgerSchema,
)

LEDGER_SCHEMA_VERSION = "1"
LEDGER_FILENAME = "mission.sqlite"
GENESIS_EVENT_SHA256 = "0" * 64

GLOBAL_ACTION_BUDGET = "action_attempts"
CONTRACT_BUDGET = "contracts"
EPISODE_BUDGET = "life_episodes"

FaultHook = Callable[[FaultPoint], None]
Clock = Callable[[], float]


def episode_action_budget(episode_id: str) -> str:
    return f"episode:{episode_id}:action_attempts"


def contract_action_budget(contract_id: str) -> str:
    return f"contract:{contract_id}:action_attempts"


class MissionLedger:
    """One writer handle on one Mission's ledger, fenced by the writer-lease generation."""

    def __init__(
        self,
        *,
        connection: sqlite3.Connection,
        runs_root: Path,
        mission_dir: Path,
        manifest: MissionManifestV1,
        generation: int,
        holder_nonce: str,
        clock: Clock,
        fault_hook: FaultHook | None,
    ) -> None:
        self._conn = connection
        self.runs_root = runs_root
        self.mission_dir = mission_dir
        self.manifest = manifest
        self.generation = generation
        self._holder_nonce = holder_nonce
        self.clock = clock
        self._fault_hook = fault_hook
        self._fail_stop_reason: str | None = None

    # ----------------------------------------------------------------- construction

    @classmethod
    def create_new_mission(
        cls,
        runs_root: Path,
        manifest: MissionManifestV1,
        *,
        clock: Clock | None = None,
        fault_hook: FaultHook | None = None,
    ) -> "MissionLedger":
        """Create a new Mission exclusively; refuse activation before any file is created."""

        refusals = activation_refusals(manifest)
        if refusals:
            raise MissionActivationRefused(refusals)
        runs_root.mkdir(parents=True, exist_ok=True)
        resolved_root = runs_root.resolve(strict=True)
        mission_dir = resolved_root / manifest.mission_run_id
        try:
            mission_dir.mkdir()
        except FileExistsError as exc:
            msg = f"mission already exists: {manifest.mission_run_id}"
            raise MissionExistsError(msg) from exc

        resolved_clock = clock or time.time
        conn = _connect(mission_dir / LEDGER_FILENAME, create=True)
        conn.executescript(files("fh_agent.mission").joinpath("schema.sql").read_text())
        holder_nonce = secrets.token_hex(16)
        ledger = cls(
            connection=conn,
            runs_root=resolved_root,
            mission_dir=mission_dir,
            manifest=manifest,
            generation=1,
            holder_nonce=holder_nonce,
            clock=resolved_clock,
            fault_hook=fault_hook,
        )
        now = ledger.now_iso()
        budgets = manifest.budgets
        _begin(conn)
        try:
            conn.execute(
                "INSERT INTO mission VALUES (1, ?, ?, ?, ?, ?, ?)",
                (
                    manifest.mission_run_id,
                    LEDGER_SCHEMA_VERSION,
                    manifest.canonical_json(),
                    manifest.manifest_sha256,
                    MissionState.ACTIVE.value,
                    now,
                ),
            )
            conn.execute("INSERT INTO writer_lease VALUES (1, 1, ?, ?)", (holder_nonce, now))
            for name, limit in (
                (GLOBAL_ACTION_BUDGET, budgets.max_action_attempts),
                (CONTRACT_BUDGET, budgets.max_contracts),
                (EPISODE_BUDGET, budgets.max_life_episodes),
            ):
                conn.execute("INSERT INTO budget_counters VALUES (?, ?, 0)", (name, limit))
            ledger.append_event(
                conn,
                "mission_created",
                {"manifest_sha256": manifest.manifest_sha256, "generation": 1},
            )
            ledger._fire(FaultPoint.MISSION_WRITE)
            conn.execute("COMMIT")
        except BaseException:
            _rollback(conn)
            conn.close()
            raise
        return ledger

    @classmethod
    def resume_existing_mission(
        cls,
        runs_root: Path,
        mission_run_id: str,
        candidate_manifest: MissionManifestV1,
        *,
        clock: Clock | None = None,
        fault_hook: FaultHook | None = None,
    ) -> "MissionLedger":
        """Verify an existing Mission read-only, then fence older writers and hold.

        Any verification failure raises before the lease is touched or any row is written.
        """

        db_path = _owned_ledger_path(runs_root, mission_run_id)
        conn = _connect(db_path, create=False)
        try:
            manifest = _verify_existing(conn, mission_run_id, candidate_manifest)
        except BaseException:
            conn.close()
            raise

        resolved_clock = clock or time.time
        holder_nonce = secrets.token_hex(16)
        ledger = cls(
            connection=conn,
            runs_root=db_path.parent.parent,
            mission_dir=db_path.parent,
            manifest=manifest,
            generation=0,
            holder_nonce=holder_nonce,
            clock=resolved_clock,
            fault_hook=fault_hook,
        )
        _begin(conn)
        try:
            (generation,) = conn.execute("SELECT generation FROM writer_lease").fetchone()
            new_generation = generation + 1
            conn.execute(
                "UPDATE writer_lease SET generation = ?, holder_nonce = ?, acquired_at = ?",
                (new_generation, holder_nonce, ledger.now_iso()),
            )
            ledger.generation = new_generation
            unresolved = [
                row[0]
                for row in conn.execute(
                    "SELECT action_id FROM action_attempts WHERE disposition = ? "
                    "ORDER BY reserved_seq",
                    (ActionDisposition.RESERVED.value,),
                )
            ]
            for action_id in unresolved:
                conn.execute(
                    "UPDATE action_attempts SET disposition = ?, block_reason = ? "
                    "WHERE action_id = ?",
                    (ActionDisposition.UNKNOWN.value, "unresolved_on_restore", action_id),
                )
            ledger.revoke_open_authority(conn, "revoked_on_restore")
            state = ledger._mission_state(conn)
            if not state.is_terminal:
                ledger._set_mission_state(conn, MissionState.RECOVERY_HOLD)
                conn.execute(
                    "UPDATE life_episodes SET state = ? WHERE state = ?",
                    (EpisodeState.RECOVERY_HOLD.value, EpisodeState.OPEN.value),
                )
            ledger.append_event(
                conn,
                "mission_restored",
                {
                    "generation": new_generation,
                    "unknown_action_ids": unresolved,
                    "state": ledger._mission_state(conn).value,
                },
            )
            ledger._fire(FaultPoint.RECOVERY_WRITE)
            conn.execute("COMMIT")
        except sqlite3.Error as exc:
            _rollback(conn)
            conn.close()
            raise LedgerWriteError(f"restore transaction failed: {exc}") from exc
        except BaseException:
            _rollback(conn)
            conn.close()
            raise
        return ledger

    def close(self) -> None:
        self._conn.close()

    # ----------------------------------------------------------------- identity

    @property
    def run_id(self) -> str:
        return self.manifest.mission_run_id

    @property
    def db_path(self) -> Path:
        return self.mission_dir / LEDGER_FILENAME

    @property
    def fail_stop_reason(self) -> str | None:
        return self._fail_stop_reason

    def enter_fail_stop(self, reason: str) -> None:
        """Fail-stop this handle in-process; it never claims that anything was persisted."""

        if self._fail_stop_reason is None:
            self._fail_stop_reason = reason

    def verify_writer(self) -> None:
        """Read-only check that this handle still owns the writer lease and is not stopped."""

        if self._fail_stop_reason is not None:
            raise MissionFailStopped(self._fail_stop_reason)
        self._require_lease(self._conn)

    # ----------------------------------------------------------------- transactions

    @contextmanager
    def write_transaction(
        self, point: FaultPoint, *, allow_in_fail_stop: bool = False
    ) -> Iterator[sqlite3.Connection]:
        """One fenced ``BEGIN IMMEDIATE`` transaction.

        ``allow_in_fail_stop`` is reserved for authority-reducing writes (revocations).
        Any SQLite failure rolls back and raises ``LedgerWriteError``.
        """

        if self._fail_stop_reason is not None and not allow_in_fail_stop:
            raise MissionFailStopped(self._fail_stop_reason)
        try:
            _begin(self._conn)
        except sqlite3.Error as exc:
            raise LedgerWriteError(f"cannot begin transaction: {exc}") from exc
        try:
            self._require_lease(self._conn)
            yield self._conn
            self._fire(point)
            self._conn.execute("COMMIT")
        except sqlite3.Error as exc:
            _rollback(self._conn)
            raise LedgerWriteError(f"{point.value} failed: {exc}") from exc
        except BaseException:
            _rollback(self._conn)
            raise

    def fire_fault_point(self, point: FaultPoint) -> None:
        """Invoke the test-only fault hook at a boundary outside a transaction."""

        self._fire(point)

    def append_event(
        self, conn: sqlite3.Connection, kind: str, payload: dict[str, Any]
    ) -> RunEventRecord:
        row = conn.execute(
            "SELECT seq, event_sha256 FROM run_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        seq, prev_sha = (1, GENESIS_EVENT_SHA256) if row is None else (row[0] + 1, row[1])
        event_id = f"{self.run_id}-ev{seq:06d}"
        payload_json = _canonical_json(payload)
        payload_sha = hashlib.sha256(payload_json.encode()).hexdigest()
        created_at = self.now_iso()
        event_sha = _event_sha256(
            seq, event_id, self.run_id, kind, payload_sha, prev_sha, created_at
        )
        conn.execute(
            "INSERT INTO run_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                seq,
                event_id,
                self.run_id,
                kind,
                payload_json,
                payload_sha,
                prev_sha,
                event_sha,
                created_at,
            ),
        )
        return RunEventRecord(seq, event_id, self.run_id, kind, payload)

    def ensure_counter(self, conn: sqlite3.Connection, name: str, limit: int) -> None:
        conn.execute("INSERT OR IGNORE INTO budget_counters VALUES (?, ?, 0)", (name, limit))

    def remaining(self, conn: sqlite3.Connection, name: str) -> int:
        row = conn.execute(
            'SELECT "limit" - used FROM budget_counters WHERE name = ?', (name,)
        ).fetchone()
        if row is None:
            raise LedgerIntegrityError(f"missing budget counter: {name}")
        return int(row[0])

    def debit(self, conn: sqlite3.Connection, name: str) -> None:
        if self.remaining(conn, name) <= 0:
            raise BudgetExhausted(name)
        conn.execute("UPDATE budget_counters SET used = used + 1 WHERE name = ?", (name,))

    # ----------------------------------------------------------------- episodes & states

    def open_episode(self) -> LifeEpisodeV1:
        with self.write_transaction(FaultPoint.EPISODE_WRITE) as conn:
            self._require_state(conn, MissionState.ACTIVE)
            if self._open_episode_row(conn) is not None:
                raise InvalidMissionTransition("a Life Episode is already open")
            self.debit(conn, EPISODE_BUDGET)
            (count,) = conn.execute("SELECT COUNT(*) FROM life_episodes").fetchone()
            ordinal = count + 1
            episode_id = f"{self.run_id}-e{ordinal:03d}"
            event = self.append_event(conn, "episode_opened", {"episode_id": episode_id})
            conn.execute(
                "INSERT INTO life_episodes VALUES (?, ?, ?, ?, ?, NULL)",
                (episode_id, self.run_id, ordinal, EpisodeState.OPEN.value, event.seq),
            )
            self.ensure_counter(
                conn,
                episode_action_budget(episode_id),
                self.manifest.budgets.max_action_attempts_per_episode,
            )
        return LifeEpisodeV1(episode_id, self.run_id, ordinal, EpisodeState.OPEN)

    def close_episode(self, reason: str) -> None:
        with self.write_transaction(FaultPoint.EPISODE_WRITE, allow_in_fail_stop=True) as conn:
            row = self._open_episode_row(conn)
            if row is None:
                raise InvalidMissionTransition("no open Life Episode")
            self.revoke_open_authority(conn, f"episode_closed:{reason}")
            conn.execute(
                "UPDATE life_episodes SET state = ?, close_reason = ? WHERE episode_id = ?",
                (EpisodeState.CLOSED_STOP.value, reason, row[0]),
            )
            self.append_event(conn, "episode_closed", {"episode_id": row[0], "reason": reason})

    def terminate(self, state: MissionState, reason: str) -> None:
        if not state.is_terminal:
            raise InvalidMissionTransition(f"{state} is not a terminal state")
        with self.write_transaction(FaultPoint.MISSION_WRITE, allow_in_fail_stop=True) as conn:
            current = self._mission_state(conn)
            if current.is_terminal:
                raise InvalidMissionTransition(f"mission already terminal: {current}")
            self.revoke_open_authority(conn, f"terminated:{reason}")
            conn.execute(
                "UPDATE life_episodes SET state = ?, close_reason = ? WHERE state IN (?, ?)",
                (
                    EpisodeState.CLOSED_STOP.value,
                    reason,
                    EpisodeState.OPEN.value,
                    EpisodeState.RECOVERY_HOLD.value,
                ),
            )
            self._set_mission_state(conn, state)
            self.append_event(conn, "mission_terminated", {"state": state.value, "reason": reason})

    def reconcile_unknown(self, action_id: str, *, operator_ref: str, finding: str) -> None:
        """Record an explicit operator reconciliation of an UNKNOWN attempt; never resends."""

        with self.write_transaction(FaultPoint.RECOVERY_WRITE) as conn:
            row = conn.execute(
                "SELECT disposition, reconciliation_ref FROM action_attempts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None or row[0] != ActionDisposition.UNKNOWN.value:
                raise RecoveryRefused(f"no UNKNOWN attempt {action_id}")
            if row[1] is not None:
                raise RecoveryRefused(f"attempt {action_id} already reconciled")
            conn.execute(
                "UPDATE action_attempts SET reconciliation_ref = ? WHERE action_id = ?",
                (operator_ref, action_id),
            )
            self.append_event(
                conn,
                "unknown_reconciled",
                {"action_id": action_id, "operator_ref": operator_ref, "finding": finding},
            )

    def resolve_recovery(self, decision: RecoveryDecision, *, operator_ref: str) -> MissionState:
        with self.write_transaction(FaultPoint.RECOVERY_WRITE) as conn:
            self._require_state(conn, MissionState.RECOVERY_HOLD)
            (unreconciled,) = conn.execute(
                "SELECT COUNT(*) FROM action_attempts "
                "WHERE disposition = ? AND reconciliation_ref IS NULL",
                (ActionDisposition.UNKNOWN.value,),
            ).fetchone()
            if decision is RecoveryDecision.resume_same_run:
                if unreconciled:
                    raise RecoveryRefused(f"{unreconciled} unreconciled UNKNOWN attempt(s)")
                conn.execute(
                    "UPDATE life_episodes SET state = ? WHERE state = ?",
                    (EpisodeState.OPEN.value, EpisodeState.RECOVERY_HOLD.value),
                )
                new_state = MissionState.ACTIVE
            elif decision is RecoveryDecision.require_observation_and_review:
                new_state = MissionState.RECOVERY_HOLD
            elif decision is RecoveryDecision.terminal_integrity_stop:
                new_state = MissionState.TERMINAL_INTEGRITY_STOP
            else:
                new_state = MissionState.TERMINAL_CONTAMINATED
            if new_state.is_terminal:
                conn.execute(
                    "UPDATE life_episodes SET state = ?, close_reason = ? WHERE state = ?",
                    (
                        EpisodeState.CLOSED_STOP.value,
                        decision.value,
                        EpisodeState.RECOVERY_HOLD.value,
                    ),
                )
            self._set_mission_state(conn, new_state)
            self.append_event(
                conn,
                "recovery_resolved",
                {
                    "decision": decision.value,
                    "operator_ref": operator_ref,
                    "state": new_state.value,
                },
            )
        return new_state

    # ----------------------------------------------------------------- read accessors

    def mission_state(self) -> MissionState:
        return self._mission_state(self._conn)

    def active_episode(self) -> LifeEpisodeV1 | None:
        row = self._open_episode_row(self._conn)
        if row is None:
            return None
        return LifeEpisodeV1(row[0], self.run_id, row[1], EpisodeState(row[2]))

    def budget(self, name: str) -> BudgetCounter:
        row = self._conn.execute(
            'SELECT name, "limit", used FROM budget_counters WHERE name = ?', (name,)
        ).fetchone()
        if row is None:
            raise LedgerIntegrityError(f"missing budget counter: {name}")
        return BudgetCounter(row[0], row[1], row[2])

    def attempts(self) -> list[ActionAttemptRecord]:
        rows = self._conn.execute(
            "SELECT action_id, run_id, episode_id, task_id, contract_id, attempt_ordinal, "
            "action, disposition, block_reason, reconciliation_ref FROM action_attempts "
            "ORDER BY reserved_seq"
        ).fetchall()
        return [
            ActionAttemptRecord(*row[:7], ActionDisposition(row[7]), row[8], row[9]) for row in rows
        ]

    def events(self, kind: str | None = None) -> list[RunEventRecord]:
        rows = self._conn.execute(
            "SELECT seq, event_id, run_id, kind, payload_json FROM run_events ORDER BY seq"
        ).fetchall()
        return [
            RunEventRecord(row[0], row[1], row[2], row[3], json.loads(row[4]))
            for row in rows
            if kind is None or row[3] == kind
        ]

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
        return self._conn.execute(sql, params).fetchone()

    # ----------------------------------------------------------------- internals

    def _fire(self, point: FaultPoint) -> None:
        if self._fault_hook is not None:
            self._fault_hook(point)

    def now_iso(self) -> str:
        return datetime.fromtimestamp(self.clock(), UTC).isoformat()

    def _require_lease(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT generation, holder_nonce FROM writer_lease").fetchone()
        if row is None or row[0] != self.generation or row[1] != self._holder_nonce:
            msg = f"writer generation {self.generation} is fenced"
            raise StaleWriterError(msg)

    def _mission_state(self, conn: sqlite3.Connection) -> MissionState:
        (state,) = conn.execute("SELECT state FROM mission").fetchone()
        return MissionState(state)

    def _require_state(self, conn: sqlite3.Connection, expected: MissionState) -> None:
        current = self._mission_state(conn)
        if current is not expected:
            raise InvalidMissionTransition(f"mission is {current}, expected {expected}")

    def _set_mission_state(self, conn: sqlite3.Connection, state: MissionState) -> None:
        conn.execute("UPDATE mission SET state = ?", (state.value,))

    def _open_episode_row(self, conn: sqlite3.Connection) -> tuple[Any, ...] | None:
        return conn.execute(
            "SELECT episode_id, ordinal, state FROM life_episodes WHERE state IN (?, ?)",
            (EpisodeState.OPEN.value, EpisodeState.RECOVERY_HOLD.value),
        ).fetchone()

    def revoke_open_authority(self, conn: sqlite3.Connection, reason: str) -> None:
        conn.execute(
            "UPDATE action_permits SET revoked_reason = ? "
            "WHERE consumed_at IS NULL AND revoked_reason IS NULL",
            (reason,),
        )
        conn.execute(
            "UPDATE manager_contracts SET status = ?, close_reason = ? WHERE status = ?",
            (ContractStatus.REVOKED.value, reason, ContractStatus.ACTIVE.value),
        )


def _connect(path: Path, *, create: bool) -> sqlite3.Connection:
    mode = "rwc" if create else "rw"
    try:
        conn = sqlite3.connect(f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None)
    except sqlite3.Error as exc:
        raise MissionPathError(f"cannot open mission ledger {path}: {exc}") from exc
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _begin(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN IMMEDIATE")


def _rollback(conn: sqlite3.Connection) -> None:
    try:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _owned_ledger_path(runs_root: Path, mission_run_id: str) -> Path:
    """Resolve ``<runs_root>/<id>/mission.sqlite`` strictly inside the root, without links."""

    if re.fullmatch(MISSION_RUN_ID_PATTERN, mission_run_id) is None:
        raise MissionPathError(f"invalid mission_run_id: {mission_run_id!r}")
    try:
        resolved_root = runs_root.resolve(strict=True)
    except OSError as exc:
        raise MissionPathError(f"runs_root does not exist: {runs_root}") from exc
    mission_dir = resolved_root / mission_run_id
    db_path = mission_dir / LEDGER_FILENAME
    if mission_dir.is_symlink() or db_path.is_symlink():
        raise MissionPathError(f"mission path must not be a symlink: {mission_dir}")
    if not db_path.is_file():
        raise MissionPathError(f"no mission ledger at {db_path}")
    if db_path.resolve(strict=True).parent.parent != resolved_root:
        raise MissionPathError(f"mission ledger escapes runs_root: {db_path}")
    return db_path


def _verify_existing(
    conn: sqlite3.Connection, mission_run_id: str, candidate: MissionManifestV1
) -> MissionManifestV1:
    """Read-only verification of an existing ledger; raises on any mismatch."""

    try:
        (integrity,) = conn.execute("PRAGMA integrity_check").fetchone()
        row = conn.execute(
            "SELECT run_id, ledger_schema_version, manifest_json, manifest_sha256 FROM mission"
        ).fetchone()
    except sqlite3.Error as exc:
        raise LedgerIntegrityError(f"cannot read mission ledger: {exc}") from exc
    if integrity != "ok":
        raise LedgerIntegrityError(f"integrity_check failed: {integrity}")
    if row is None:
        raise LedgerIntegrityError("mission row missing")
    stored_run_id, schema_version, manifest_json, manifest_sha = row
    if schema_version != LEDGER_SCHEMA_VERSION:
        raise UnsupportedLedgerSchema(f"unsupported ledger schema version: {schema_version!r}")
    if stored_run_id != mission_run_id:
        raise LedgerIntegrityError(
            f"stored run id {stored_run_id!r} does not match directory {mission_run_id!r}"
        )
    try:
        stored = MissionManifestV1.model_validate_json(manifest_json)
    except ValueError as exc:
        raise UnsupportedLedgerSchema(f"stored manifest unreadable: {exc}") from exc
    if stored.manifest_sha256 != manifest_sha or stored.mission_run_id != stored_run_id:
        raise LedgerIntegrityError("stored manifest digest mismatch")
    _verify_event_chain(conn, stored_run_id)
    mismatches = compare_frozen_identity(stored, candidate)
    if mismatches:
        raise IdentityMismatchError([mismatch.field for mismatch in mismatches])
    return stored


def _verify_event_chain(conn: sqlite3.Connection, run_id: str) -> None:
    prev_sha = GENESIS_EVENT_SHA256
    expected_seq = 1
    for row in conn.execute(
        "SELECT seq, event_id, run_id, kind, payload_json, payload_sha256, prev_event_sha256, "
        "event_sha256, created_at FROM run_events ORDER BY seq"
    ):
        seq, event_id, row_run_id, kind, payload_json, payload_sha, row_prev, event_sha, created = (
            row
        )
        if seq != expected_seq or row_run_id != run_id or row_prev != prev_sha:
            raise LedgerIntegrityError(f"event chain broken at seq {seq}")
        if hashlib.sha256(payload_json.encode()).hexdigest() != payload_sha:
            raise LedgerIntegrityError(f"event payload hash mismatch at seq {seq}")
        recomputed = _event_sha256(seq, event_id, run_id, kind, payload_sha, prev_sha, created)
        if recomputed != event_sha:
            raise LedgerIntegrityError(f"event hash mismatch at seq {seq}")
        prev_sha = event_sha
        expected_seq += 1


def _event_sha256(
    seq: int,
    event_id: str,
    run_id: str,
    kind: str,
    payload_sha: str,
    prev_sha: str,
    created_at: str,
) -> str:
    material = _canonical_json(
        {
            "created_at": created_at,
            "event_id": event_id,
            "kind": kind,
            "payload_sha256": payload_sha,
            "prev_event_sha256": prev_sha,
            "run_id": run_id,
            "seq": seq,
        }
    )
    return hashlib.sha256(b"fh-agent/run-event/v1\n" + material.encode()).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
