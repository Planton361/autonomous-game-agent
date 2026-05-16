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
