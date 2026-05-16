PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    evidence_id TEXT,
    ui_state TEXT,
    observation_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_observations_run_created
ON observations (run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_observations_ui_state
ON observations (ui_state);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    primitive_action TEXT NOT NULL,
    action_json TEXT NOT NULL,
    related_observation_id TEXT,
    FOREIGN KEY (related_observation_id)
        REFERENCES observations (observation_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_actions_run_created
ON actions (run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_actions_primitive_action
ON actions (primitive_action);

CREATE TABLE IF NOT EXISTS skill_results (
    skill_result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    success INTEGER NOT NULL CHECK (success IN (0, 1)),
    reward REAL,
    steps INTEGER,
    skill_result_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skill_results_run_created
ON skill_results (run_id, created_at);

CREATE INDEX IF NOT EXISTS idx_skill_results_skill_name
ON skill_results (skill_name);

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    claim TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('hypothesis', 'observed_fact', 'validated_rule', 'contradicted')
    ),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    fact_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_facts_status
ON facts (status);

CREATE TABLE IF NOT EXISTS fact_evidence (
    fact_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (fact_id, evidence_id),
    FOREIGN KEY (fact_id)
        REFERENCES facts (fact_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_risks (
    entity_key TEXT PRIMARY KEY,
    risk_score REAL NOT NULL CHECK (risk_score >= 0.0 AND risk_score <= 1.0),
    total_outcomes INTEGER NOT NULL CHECK (total_outcomes >= 0),
    last_outcome TEXT CHECK (
        last_outcome IS NULL OR last_outcome IN (
            'death',
            'combat_started',
            'damage_taken',
            'skill_failed',
            'safe_passage',
            'no_change'
        )
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entity_risks_score
ON entity_risks (risk_score);

CREATE TABLE IF NOT EXISTS entity_risk_events (
    risk_update_id TEXT PRIMARY KEY,
    entity_key TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (
        outcome IN (
            'death',
            'combat_started',
            'damage_taken',
            'skill_failed',
            'safe_passage',
            'no_change'
        )
    ),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    risk_delta REAL NOT NULL,
    risk_score_after REAL NOT NULL CHECK (
        risk_score_after >= 0.0 AND risk_score_after <= 1.0
    ),
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_key)
        REFERENCES entity_risks (entity_key)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entity_risk_events_entity_created
ON entity_risk_events (entity_key, created_at);

CREATE TABLE IF NOT EXISTS entity_risk_event_evidence (
    risk_update_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (risk_update_id, evidence_id),
    FOREIGN KEY (risk_update_id)
        REFERENCES entity_risk_events (risk_update_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rooms (
    room_signature TEXT PRIMARY KEY,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    visit_count INTEGER NOT NULL CHECK (visit_count >= 0),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS room_evidence (
    room_signature TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (room_signature, evidence_id),
    FOREIGN KEY (room_signature)
        REFERENCES rooms (room_signature)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS room_transitions (
    transition_key TEXT PRIMARY KEY,
    from_room_signature TEXT NOT NULL,
    to_room_signature TEXT NOT NULL,
    action_id TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('screen_transition')),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    observed_count INTEGER NOT NULL CHECK (observed_count >= 0),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    metadata_json TEXT,
    FOREIGN KEY (from_room_signature)
        REFERENCES rooms (room_signature)
        ON DELETE CASCADE,
    FOREIGN KEY (to_room_signature)
        REFERENCES rooms (room_signature)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_room_transitions_from_room
ON room_transitions (from_room_signature);

CREATE INDEX IF NOT EXISTS idx_room_transitions_to_room
ON room_transitions (to_room_signature);

CREATE TABLE IF NOT EXISTS transition_evidence (
    transition_key TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    PRIMARY KEY (transition_key, evidence_id),
    FOREIGN KEY (transition_key)
        REFERENCES room_transitions (transition_key)
        ON DELETE CASCADE
);
