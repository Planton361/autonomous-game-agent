-- MRIC-S0 per-Mission transactional ledger (Issue #184). One database file per Mission Run.

CREATE TABLE mission (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    run_id TEXT NOT NULL,
    ledger_schema_version TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER mission_identity_immutable
BEFORE UPDATE OF run_id, manifest_json, manifest_sha256, created_at ON mission
BEGIN
    SELECT RAISE(ABORT, 'mission identity is immutable');
END;

CREATE TRIGGER mission_terminal_irreversible
BEFORE UPDATE OF state ON mission
WHEN OLD.state LIKE 'TERMINAL_%' AND NEW.state <> OLD.state
BEGIN
    SELECT RAISE(ABORT, 'terminal mission state is irreversible');
END;

CREATE TABLE writer_lease (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    generation INTEGER NOT NULL CHECK (generation >= 1),
    holder_nonce TEXT NOT NULL,
    acquired_at TEXT NOT NULL
);

CREATE TRIGGER writer_lease_generation_monotone
BEFORE UPDATE OF generation ON writer_lease
WHEN NEW.generation <= OLD.generation
BEGIN
    SELECT RAISE(ABORT, 'writer lease generation must increase');
END;

CREATE TABLE life_episodes (
    episode_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL UNIQUE CHECK (ordinal >= 1),
    state TEXT NOT NULL,
    opened_seq INTEGER NOT NULL,
    close_reason TEXT
);

CREATE UNIQUE INDEX one_open_episode_per_mission
ON life_episodes (run_id) WHERE state IN ('OPEN', 'RECOVERY_HOLD');

CREATE TABLE manager_contracts (
    contract_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    episode_id TEXT NOT NULL REFERENCES life_episodes (episode_id),
    task_id TEXT NOT NULL,
    task_spec_sha256 TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    allowed_actions_json TEXT NOT NULL,
    max_action_attempts INTEGER NOT NULL CHECK (max_action_attempts >= 1),
    verifier_id TEXT NOT NULL,
    status TEXT NOT NULL,
    generation INTEGER NOT NULL,
    opened_seq INTEGER NOT NULL,
    close_reason TEXT
);

CREATE UNIQUE INDEX one_active_contract_per_episode
ON manager_contracts (episode_id) WHERE status = 'ACTIVE';

CREATE TABLE action_permits (
    permit_nonce TEXT PRIMARY KEY,
    action_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    contract_id TEXT NOT NULL REFERENCES manager_contracts (contract_id),
    attempt_ordinal INTEGER NOT NULL,
    action TEXT NOT NULL,
    issued_generation INTEGER NOT NULL,
    expires_at REAL NOT NULL,
    consumed_at TEXT,
    revoked_reason TEXT
);

CREATE TRIGGER permit_consumed_once
BEFORE UPDATE OF consumed_at ON action_permits
WHEN OLD.consumed_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'permit already consumed');
END;

CREATE TABLE action_attempts (
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    contract_id TEXT NOT NULL REFERENCES manager_contracts (contract_id),
    permit_nonce TEXT NOT NULL UNIQUE REFERENCES action_permits (permit_nonce),
    attempt_ordinal INTEGER NOT NULL,
    action TEXT NOT NULL,
    disposition TEXT NOT NULL,
    block_reason TEXT,
    reserved_seq INTEGER NOT NULL,
    reconciliation_ref TEXT
);

CREATE TRIGGER attempt_settled_disposition_final
BEFORE UPDATE OF disposition ON action_attempts
WHEN OLD.disposition IN ('SENT', 'NOT_SENT', 'UNKNOWN')
BEGIN
    SELECT RAISE(ABORT, 'settled action disposition is final');
END;

CREATE TABLE run_events (
    seq INTEGER PRIMARY KEY CHECK (seq >= 1),
    event_id TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    prev_event_sha256 TEXT NOT NULL,
    event_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (run_id, seq)
);

CREATE TRIGGER run_events_seq_contiguous
BEFORE INSERT ON run_events
WHEN NEW.seq <> (SELECT COALESCE(MAX(seq), 0) + 1 FROM run_events)
BEGIN
    SELECT RAISE(ABORT, 'run event sequence must be contiguous');
END;

CREATE TRIGGER run_events_append_only_update
BEFORE UPDATE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'run events are append-only');
END;

CREATE TRIGGER run_events_append_only_delete
BEFORE DELETE ON run_events
BEGIN
    SELECT RAISE(ABORT, 'run events are append-only');
END;

CREATE TABLE budget_counters (
    name TEXT PRIMARY KEY,
    "limit" INTEGER NOT NULL CHECK ("limit" >= 0),
    used INTEGER NOT NULL CHECK (used >= 0 AND used <= "limit")
);

CREATE TRIGGER budget_used_monotone
BEFORE UPDATE OF used ON budget_counters
WHEN NEW.used < OLD.used
BEGIN
    SELECT RAISE(ABORT, 'budget usage is monotone');
END;

CREATE TRIGGER budget_limit_frozen
BEFORE UPDATE OF "limit" ON budget_counters
WHEN NEW."limit" <> OLD."limit"
BEGIN
    SELECT RAISE(ABORT, 'budget ceilings are frozen');
END;

CREATE TRIGGER budget_counters_no_delete
BEFORE DELETE ON budget_counters
BEGIN
    SELECT RAISE(ABORT, 'budget counters cannot be deleted');
END;
