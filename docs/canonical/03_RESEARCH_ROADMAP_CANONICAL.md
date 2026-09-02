# Canonical Research Roadmap — Capability Sequence

## Status rule

This roadmap defines the **stable capability order**, not the current implementation status. It deliberately contains no active-milestone marker, current test count, or commit-specific progress table. Determine actual progress from GitHub HEAD and the current working chat.

The sequence is designed so each later research claim rests on measured prerequisites rather than architectural assumptions.

---

## Phase A — Scientific and contract foundations

### Goal
Make epistemic rules, authority boundaries, evidence, run modes, schemas, safety and evaluation explicit before relying on autonomy claims.

### Required capabilities
- no-spoiler/firewall policy;
- typed observations/events/facts/actions/skills;
- evidence/provenance linkage;
- Cortex capability constraints;
- grounded target contracts;
- Manager revalidation;
- deterministic identity/versioning for tasks/artifacts;
- offline perception benchmark and corpus tooling;
- safe InputExecutor primitives and audit logging.

### Exit gate
Architecture contracts can be tested without launching the game, and all official-run inputs/knowledge sources have explicit authority rules.

---

## Phase B — Canonical outcome, verifier and failure model

### Goal
Create one authoritative representation of progress, success, failure, stop and reward-relevant outcomes.

### Required capabilities
- unified failure taxonomy;
- `VerifierResult`-like typed output with evidence;
- clear separation of perception/grounding/planning/skill/safety/death failures;
- canonical reward terms derived from verified outcomes;
- no success based solely on a new screenshot/hash change;
- verifier false-positive/false-negative audit support.

### Exit gate
A Skill Contract can be closed for a specific audited reason, and reward signals cannot bypass verification.

---

## Phase C — Runtime ports and guarded online SkillRunner

### Goal
Replace offline precomputed observation-sequence execution with a real bounded online control loop while preserving existing contracts.

### Required capabilities
- capture/observation port;
- Body primitive-proposal port;
- InputExecutor integration;
- before/action/after evidence linkage;
- focus/rate-limit/emergency-stop enforcement;
- contract budget/timeout/no-progress handling;
- dry-run backend for reproducible tests.

### Exit gate
A bounded task can run observe → act → observe → verify entirely through typed ports without an LLM or live game requirement.

---

## Phase D — Bridge-assisted vertical slice

### Goal
Close the full Cortex→Manager→Body→Verifier loop with the easiest admissible visible-state path before demanding robust screen-only perception.

### Required capabilities
- production visible-only bridge transport or equivalent structured visible feed;
- firewall synchronization with screenshot evidence;
- Cortex planning from evidence-backed context;
- Manager grounding and contracts;
- Body execution through guarded input;
- outcome verification and replanning;
- explicit `bridge-assisted` run classification.

### Exit gate
A manually authorized bounded live smoke completes the full hierarchy with 100% action-to-contract/evidence linkage and no hidden-state leakage.

---

## Phase E — Minimum viable screen-only perception

### Goal
Replace structured assistance with measured pixel-derived observation sufficient for the first closed-loop pilot.

### Required capabilities
- real screen capture path;
- player/visible-target spatial producer measured on a frozen real corpus;
- OCR measured on held-out visible text fixtures;
- minimal UI-state detection;
- confidence/evidence propagation;
- screen-only observation coverage metrics.

### Exit gate
Perception accuracy and coverage are measured on held-out data, and the same downstream contracts operate without the bridge.

### Not required
Perfect semantic detection, full object taxonomy, or foundation-VLM training.

---

## Phase F — Temporal State, deadlock detection and Reflex

### Goal
Support movement continuity, robust success detection and immediate visible threats without per-frame Cortex calls.

### Required capabilities
- short frame history;
- motion/progress estimates;
- target persistence/loss;
- repeated-state/action loop detection;
- temporal success/failure detectors;
- bounded Reflex triggers/action masks/cooldowns;
- reflex logging and precision audit.

### Exit gate
Fast hazards can be handled within Manager authority and no-progress/deadlock can be distinguished from ordinary slow progress.

---

## Phase G — Cortex providers, Context Service and decision trace

### Goal
Make strategic reasoning reproducible, swappable and measurable.

### Required capabilities
- provider-neutral Cortex client;
- local OpenAI-compatible runtime;
- optional networked API exploratory provider;
- deterministic context assembly/retrieval policy;
- structured CortexDecision with evidence claims and open questions;
- prompt/config/model identity and latency/cost trace;
- direct-key output rejection.

### Exit gate
The same frozen task/context can be evaluated across Cortex providers without changing Manager/Body contracts.

---

## Phase H — First complete heuristic Cortex–Body closed loop

### Goal
Demonstrate autonomous hierarchical operation before introducing learned Body policies.

### Required capabilities
- screen-only observation;
- evidence-backed memory retrieval;
- Cortex goal/skill selection;
- Manager grounding/contracting;
- heuristic Body execution;
- independent verification;
- stop/replan loop;
- durable run artifacts.

### Exit gate
Multiple bounded autonomous smokes show Observation→Cortex→Manager→Body→Input→Observation→Verifier→replan with no wrong-window/no-spoiler violations and audited false-success behavior.

---

## Phase I — Persistent memory, death post-mortem and cross-run adaptation

### Goal
Make repeated runs informationally cumulative without allowing unsupported self-confirmation.

### Required capabilities
- evidence/episode/fact/hypothesis/topology/strategy stores;
- bounded retrieval;
- contradiction handling;
- death/run-end post-mortem;
- repeated-failure detection;
- measurable change in later-run hypotheses/experiments;
- contamination-aware memory filtering.

### Exit gate
Paired repeat runs demonstrate that admissible prior experience changes later reasoning in auditable ways, while unsupported hypotheses remain labeled as such.

---

## Phase J — Heuristic scientific pilot

### Goal
Evaluate the hierarchy itself before learned low-level control confounds the result.

### Core conditions
- no-action negative control;
- fixed-goal + same Manager/heuristic Body;
- Cortex + Manager + same heuristic Body + memory;
- selected ablations such as no-memory or frequent-replanning while preserving the no-direct-key rule.

### Exit gate
Frozen run dataset, artifact audit, manual outcome review, effect sizes/confidence intervals, limitations, and contamination ledger exist.

---

## Phase K — Shared goal-conditioned Body V1

### Goal
Test whether learned reusable physical skills improve execution efficiency under the exact same Manager/Verifier/Safety authority.

### Default approach
- shared visual/temporal backbone;
- goal/skill conditioning;
- grounded target input;
- allowed-action mask;
- Behavior Cloning bootstrap where useful;
- RL fine-tuning only after verifier validity;
- versioned replay and holdout validation.

### Exit gate
At least one learned skill version improves preregistered skill success/action efficiency over the heuristic baseline without increased false-success, safety, or no-spoiler violations.

---

## Phase L — Learned Reflex, broader skillset and autonomous curriculum

### Goal
Expand beyond the first learned skill while measuring interference, retention and skill-deficiency-driven training.

### Required capabilities
- skill competence registry;
- automatic identification of recurring execution deficits;
- curriculum/task generation constrained by admissible observed states;
- certification/rollback per Body version;
- negative-transfer/interference tests;
- learned Reflex only when bounded deterministic triggers exist.

### Exit gate
The system can add or improve reusable capabilities without silently degrading previously certified skills.

---

## Phase M — Long-horizon Fear & Hunger robustness and completion challenge

### Goal
Evaluate persistent autonomous play across held-out visible start states, repeated deaths/restarts and long horizons.

### Required capabilities
- stable full hierarchy;
- persistent memory and post-mortems;
- certified Body versions;
- frozen run budgets/stopping rules;
- reproducible local model condition;
- explicit completion/ending observation protocol based only on visible evidence.

### Exit gate
The agent demonstrates sustained autonomous progress across repeated runs and can be evaluated on whether it reaches a visibly verifiable ending/completion condition without external game knowledge.

---

## Phase N — Post-pilot transfer research

### Goal
Only after Fear & Hunger is stable, test which skills and abstractions transfer to unseen environments.

### Candidate experiments
- frozen shared Body transferred to a second RPG;
- skill-library transfer versus training from scratch;
- language-based skill router versus non-language router;
- shared backbone versus separate skill policies;
- retained generic movement/menu/navigation skills versus environment-specific relearning;
- positive/negative transfer and catastrophic interference.

### Scientific caution
Cross-game transfer requires a new protocol, threat model, environment selection procedure and preregistered metrics. Fear & Hunger performance alone does not establish generality.

---

## What should not be built prematurely

Until earlier gates justify them, avoid:

- end-to-end pixel-to-action RL for the whole game;
- a distinct neural network for every skill by default;
- unrestricted online weight updates during a run;
- LLM self-assigned scalar reward as ground truth;
- complex world models before sufficient replay and stable baselines;
- broad semantic object ontologies before required by measured failures;
- cross-game infrastructure before Fear & Hunger skill competence is measurable;
- game-specific shortcuts that damage later transfer claims.
