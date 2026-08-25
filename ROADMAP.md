# ROADMAP.md — Cortex–Body Research Roadmap

This roadmap governs the Fear & Hunger pilot. It replaces the former component-by-component
implementation roadmap with an experiment-first sequence. Existing code is prototype evidence,
not proof that the corresponding capability is complete.

## Scope and invariant

The research target is one local, no-spoiler Fear & Hunger pilot. The hierarchy is fixed:

```text
visible evidence → Cortex → Manager contract → Body/Reflex → guarded input → visible outcome
```

- **Cortex** is the LLM planner. It proposes evidence-grounded goals, hypotheses, constraints, and
  universal skills. It is never a direct controller and never emits key sequences.
- **Manager** owns grounding, scheduling, budgets, reward selection, stop detection, and replanning.
- **Body** owns universal heuristic skills and, later, learned goal-conditioned skills.
- **Reflex** is a fast Body path operating inside an active Manager contract. It may react to an
  immediate visible hazard but may not invent goals, widen permissions, or bypass logging/safety.

Cross-game transfer, a general game benchmark, and claims of game-independent learned competence
are explicitly out of scope for every phase in this roadmap.

## Run modes

| Mode | Inputs | Research status |
|---|---|---|
| `screen-only` | Pixels, OCR, visible outcomes | Primary official pilot cohort. |
| `bridge-assisted` | Pixels plus strictly allowlisted visible-state fields | Separate official auxiliary cohort; never pooled with screen-only results. |
| `debug` | Development instrumentation, still no hidden-state authority | Non-official; excluded from headline metrics. |
| `contaminated` | Any run with spoiler exposure, hidden-state access, network-policy breach, missing provenance, or mode uncertainty | Quarantined and excluded from confirmatory results. |

The complete classification and quarantine rules live in
`docs/research/NO_SPOILER_PROTOCOL.md`.

## Phase 0 — Experiment contract (active)

**Goal:** freeze the scientific question, architecture boundaries, run modes, provenance,
baselines, metrics, and no-spoiler rules before runtime work resumes.

Deliverables:

```text
ROADMAP.md
AGENTS.md
docs/research/ARCHITECTURE_V2.md
docs/research/EXPERIMENT_CONTRACT.md
docs/research/METRICS.md
docs/research/NO_SPOILER_PROTOCOL.md
configs/experiments/pilot_fh.yaml
```

Acceptance criteria:

- every component has an explicit authority boundary;
- screen-only, bridge-assisted, debug, and contaminated modes are unambiguous;
- network isolation and contamination handling are reproducible;
- every run requires Git commit, prompt hash, config hash, model name, and model hash;
- pilot hypotheses, baselines, units of analysis, metrics, exclusions, and stopping rules are fixed;
- current technical debt is recorded without changing runtime behavior;
- no cross-game transfer requirement appears in the pilot.

Phase 0 makes documentation/configuration changes only. It must not change Runtime, Planner,
Memory, Body, Bridge, or input behavior and must not run the game.

## Phase 1 — Close the observable control loop

**Goal:** make one bounded screen-only contract executable end to end.

Work must address, with focused tickets and tests:

1. replace the default no-op OCR path with a measured real OCR adapter;
2. add visible-target grounding from observations to typed Manager targets;
3. reconcile planner skill names, reward profiles, and executable SkillCatalog entries;
4. consolidate the duplicate reward models into one contract-owned representation;
5. tighten success detectors so new screenshots or incidental signature changes are insufficient;
6. replace the offline observation-sequence runner with a guarded online loop;
7. retain focus checks, rate limits, emergency stop, action logs, and evidence linkage;
8. keep the visible bridge optional and out of the primary screen-only path.

Exit gate: a dry-run and then a manually authorized bounded live smoke demonstrate
Observation→Cortex→Manager→Body→InputExecutor→Observation with auditable stop/replan events. This
phase is not authorized by Phase 0 and requires its own implementation ticket.

## Phase 2 — Screen-only pilot readiness

**Goal:** validate deterministic heuristic Body skills and measurement quality before involving a
learned Body.

Required gates:

- fixed visible start-state protocol and scenario cards;
- inter-rater audit of success/failure and contamination labels;
- measured OCR and grounding coverage;
- calibrated success detectors with reported false-positive and false-negative rates;
- complete run manifest and artifact validation;
- fixed pilot seeds, budgets, baseline assignments, and analysis script.

Exit gate: all safety and integrity gates in `EXPERIMENT_CONTRACT.md` pass on non-evaluation smoke
runs.

## Phase 3 — Registered heuristic pilot

**Goal:** execute the frozen Fear & Hunger experiment comparing no-action, fixed-goal heuristic,
and Cortex–Manager–heuristic conditions.

Only runs generated after the preregistration commit and passing the no-spoiler audit enter the
confirmatory dataset. Screen-only is primary; bridge-assisted observations are analyzed only as a
separate diagnostic cohort. Report all exclusions and confidence intervals.

Exit gate: an immutable pilot dataset, analysis report, contamination ledger, and limitations
section exist. No learned Body claim is made.

## Phase 4 — Reflex and learned Body evaluation

**Goal:** test whether a contract-bounded Reflex and later goal-conditioned learned skills improve
Body efficiency without weakening safety or Manager authority.

The heuristic Body remains the control. Learned policies receive grounded targets and the same
allowed primitive-action set, safety filter, timeout, logging, and stop conditions. A Reflex may
only choose actions already permitted by the active Manager contract.

Exit gate: learned/Reflex conditions improve preregistered Body metrics without increasing safety,
false-success, or no-spoiler violations.

## Phase 5 — Fear & Hunger replication and robustness

**Goal:** replicate within the same game across held-out visible start states, run seeds, and local
model checkpoints.

This phase tests robustness inside Fear & Hunger only. Cross-game transfer remains outside this
roadmap and would require a separate protocol, threat model, and approval.

## Current technical-debt register

These are observed repository limitations as of Phase 0:

| Debt | Current evidence | Consequence |
|---|---|---|
| NoOp OCR | `ObservationBuilder` and offline processing default to `NoOpOcrEngine`. | Screen-only text perception is not live-capable. |
| Bridge skeleton | The bridge adapter sanitizes payloads but has no production transport. | Bridge-assisted runs are not operational. |
| OfflineSkillRunner | `SkillRunner` consumes a supplied observation sequence and never executes input. | It cannot close the environment loop. |
| Missing grounding | Planner goals become textual task targets; no component resolves them to visible typed targets. | Body skills cannot reliably act on Cortex intent. |
| SkillCatalog mismatch | Planner/profile names include skills absent from `SkillCatalog.default()`, while catalog aliases differ. | Valid plans may not be executable. |
| Duplicate reward model | `manager/reward_computer.py` and `manager/reward_profiles.py` define incompatible `RewardProfile` concepts. | Task rewards and skill rewards can diverge. |
| Loose success detectors | New evidence or any screen-signature change can count as success in some skills. | Incidental frame changes can create false positives. |
| Missing closed loop | Prototype modules are tested largely in isolation; no production Cortex–Manager–Body loop feeds post-action observations back. | Autonomous pilot claims are premature. |

Debt is descriptive in Phase 0. Fixes belong to Phase 1 tickets with explicit architecture review.

## Required validation for every ticket

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Do not run the game or send inputs unless a ticket explicitly authorizes a controlled live run.
