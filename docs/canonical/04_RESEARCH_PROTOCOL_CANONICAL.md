# Canonical Research Protocol — No-Spoiler, Evidence, Evaluation and Reproducibility

## 1. Epistemic principle

The agent may treat as game-specific knowledge only information that an ordinary player could obtain from admissible visible interaction during the experiment or that was derived from the agent's own prior admissible runs.

Technical availability is not epistemic permission.

## 2. Allowed evidence

- screenshots/screen recordings of the game window;
- OCR text visibly present in linked frames;
- visible UI state derived from pixels;
- visible spatial/motion signals derived from pixels;
- logged primitive actions and visible after-effects;
- evidence-backed memories from prior admissible runs;
- in `bridge-assisted`, deny-by-default sanitized fields that encode information simultaneously visible on screen and are linked to screenshot evidence.

Generic game knowledge such as “movement keys may navigate” or “an unexplored path might matter” is allowed only as a hypothesis, never as a Fear & Hunger fact.

## 3. Forbidden evidence

Official or training-eligible data must not use:

- Fear & Hunger wikis, walkthroughs, maps, videos, forums or human spoiler hints;
- RPG Maker map/event IDs, names, comments, trigger conditions or source data;
- switches, variables, quest/ending flags;
- enemy/item databases, exact hidden stats/resistances/effects;
- savegame internals;
- process/RAM-derived hidden state;
- non-visible accessibility/debug/telemetry state that reveals unavailable truth;
- contaminated artifacts or descendants of contaminated data.

A forbidden-field attempt is logged as an integrity incident rather than silently normalized into an official run.

## 4. Run modes

### `screen-only`
Primary official cohort. Runtime knowledge comes from pixels, OCR, visible action outcomes and admissible prior-run memory. No bridge is active. Official runs use local inference under the network-isolation protocol.

### `bridge-assisted`
Separate official diagnostic cohort. Screenshots remain mandatory. The bridge may add only allowlisted simultaneously visible information. Results are never pooled with screen-only results.

### `debug`
Development/synthetic/offline instrumentation. Not eligible for headline results. Hidden state remains forbidden unless the artifact is immediately classified contaminated and excluded from admissible memory/training.

### `networked-api-exploratory`
A separate capability-ceiling/development mode allowing remote API Cortex inference. It is not an official offline/no-spoiler cohort under this frozen protocol and is analyzed separately.

### `contaminated`
Permanent quarantine for hidden-state/spoiler exposure, network-policy breach in an official run, mixed/uncertain provenance, or other epistemic integrity failure. It remains in accounting but is excluded from admissible memory, Body training and official metrics.

## 5. Network isolation for official runs

Before an official run:

1. stage dependencies, prompts, configs, local model artifacts and tools;
2. enforce deny-all network access or equivalent host/container isolation;
3. verify the Cortex endpoint is local and telemetry/update checks are disabled;
4. record isolation method and verification evidence;
5. hash the exact software/model/prompt/config state before the first observation.

Remote inference, web retrieval, package installation, cloud logging or telemetry during an official run terminates eligibility.

## 6. Evidence and provenance

Game-specific facts, grounded targets, verifier outcomes and memory updates carry evidence IDs.

Each research run should record at least:

- run ID and run mode;
- Git commit, branch and dirty/diff identity;
- prompt bundle hash;
- canonical configuration hash;
- model/provider identity and local model artifact/content-manifest hash when applicable;
- seed and time/action budgets;
- host/runtime identity;
- window identity/resolution;
- firewall/allowlist version/hash;
- network-isolation proof for official runs;
- before/action/after event linkage.

Missing mandatory provenance makes an official claim invalid rather than being reconstructed from memory later.

## 7. Data and corpus rules

Perception datasets and skill-training datasets must preserve provenance and run-mode eligibility.

For perception corpora:

- split at sequence level, not neighboring-frame level;
- prevent exact-content hash leakage across splits;
- preserve train/validation/test isolation;
- retain uncertain/exclude labels rather than forcing doubtful ground truth;
- freeze evaluation corpora before optimizing a detector against them.

For Body learning:

- replay entries retain originating run, mode, evidence, contract and verifier outcome;
- contaminated/debug data are excluded by default from research-eligible training unless a clearly separate engineering experiment says otherwise;
- evaluation scenarios are held out from policy optimization.

## 8. Success, failure and reward

The Manager/Verifier—not the Cortex—owns final outcome labels.

Preference order:

1. deterministic visible success/failure detector;
2. deterministic progress signal;
3. calibrated learned detector;
4. optional separately evaluated VLM/LLM judge for genuinely semantic outcomes;
5. manual review for audit/ground truth.

A screenshot change, new evidence ID or perceptual-hash change alone is not task success.

Failure categories must remain separable so that a Body is not punished for a grounding failure and a Cortex is not blamed for a focus-loss safety event.

## 9. Learning protocol

The philosophical goal is continual trial-and-error, but experimental weight updates are generational:

- collect experience with frozen Body/model versions;
- verify and store outcomes;
- train candidates between runs;
- validate on held-out scenarios;
- certify or reject;
- activate only certified versions for later runs.

This supports learning from natural gameplay while retaining reproducibility, rollback and causal attribution.

No learned Body training should begin before the associated success/failure/progress detectors are sufficiently accurate to produce meaningful labels.

## 10. Core baselines

The first hierarchical pilot should include at least:

- **no-action**: estimates incidental UI/environment change and false success;
- **fixed-goal heuristic**: same Manager/Body/Safety stack without Cortex-driven strategic selection;
- **Cortex + Manager + heuristic Body + memory**: main hierarchy condition.

Useful later ablations include:

- no persistent memory;
- frequent Cortex replanning while still forbidding primitive key control;
- local Cortex versus separately classified API capability ceiling;
- screen-only versus bridge-assisted as separate cohorts;
- heuristic versus learned Body under identical Manager/Verifier/Safety contracts.

## 11. Measurement principles

Use the run as the primary experimental unit; contracts and primitive actions are nested observations.

Important metrics include:

### Whole system
- verified contract success rate;
- evidence-grounded progress per 100 primitive actions;
- time/actions to first verified progress;
- survival/death/stall outcomes;
- repeated-failure rate across runs.

### Cortex
- schema validity;
- unsupported-claim/evidence-grounding rate;
- direct-control rejection count;
- planning latency and LLM/API cost;
- replan yield.

### Manager/Grounding
- grounding coverage/precision;
- contract validity;
- stop latency;
- budget compliance;
- loop/no-progress detection.

### Body/Reflex
- skill success rate;
- action efficiency;
- no-progress action rate;
- Body latency;
- Reflex trigger precision/containment;
- safety outcomes.

### Perception/Verifier
- spatial precision/recall/F1 and position error;
- OCR CER/exact-span accuracy;
- UI-state F1;
- verifier false-positive and false-negative rates;
- confidence calibration where applicable.

### Safety/integrity hard gates
- wrong-window executed inputs = 0;
- no-spoiler violations in official runs = 0;
- Reflex containment = 100%;
- evidence linkage for required records = 100% target.

## 12. Statistical/reporting principles

- Preserve raw per-run values and counts.
- Do not pool different run modes.
- Pair conditions by common visible start-state blocks where practical.
- Bootstrap whole runs rather than individual actions for confidence intervals.
- Report exclusions/contamination transparently.
- Death, stalls, planner errors, grounding failures and Body failures are outcomes, not convenient exclusions.
- Freeze prompts/configs/model versions/metrics for confirmatory batches; material changes create a new experiment version.

## 13. Manual review

Automated success labels remain auditable. Research pilots should include blinded visible-evidence review of claimed successes and sampled failures. Reviewer disagreement is reported rather than erased.

## 14. API provider rule

The software architecture should support manual switching between local and API Cortex providers. However, under this frozen protocol:

- local, network-isolated inference is required for official `screen-only`/`bridge-assisted` cohorts;
- API Cortex experiments use `networked-api-exploratory` classification;
- API results may be used as a capability ceiling or engineering comparison but are not pooled with official cohorts.

Changing this rule requires an explicit future protocol revision, not an implementation shortcut.
