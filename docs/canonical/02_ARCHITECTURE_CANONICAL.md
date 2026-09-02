# Canonical Architecture — Cortex, Manager, Body, Verifier and Learning Loop

## 1. Normative architecture

```text
GameInstance
    ↓
Screen Capture ───────────────┐
optional Visible-State Bridge │
    ↓                         │
No-Spoiler Firewall           │
    ↓                         │
Perception / Observation      │
    ↓                         │
Temporal State                │
    ↓                         │
Evidence + Memory Retrieval   │
    ↓                         │
LLM Cortex (slow/event-driven)│
    ↓                         │
CortexDecision / GoalSpec     │
    ↓                         │
Manager / Executive           │
    ↓                         │
Grounded Skill Contract       │
    ↓                         │
Body ─────── Reflex           │
    ↓            ↓            │
Primitive Action Proposal     │
    ↓                         │
SafetyFilter / InputExecutor  │
    ↓                         │
GameInstance                  │
    ↓                         │
Visible Outcome ──────────────┘
    ↓
Independent Verifier
    ↓
Outcome + Evidence
    ├──→ Memory / Post-Mortem
    └──→ Replay Buffer
             ↓ between runs
         SkillTrainer
             ↓
      Candidate Body Version
             ↓
     Validation / Certification
             ↓
       Next eligible run
```

Every module boundary should use typed, logged, evidence-aware data. Hidden game state is never an official runtime authority.

## 2. Multi-timescale control

### Cortex timescale
The Cortex is expensive and slow. It is invoked by meaningful events rather than every frame: new evidence, contract completion/failure, contradiction, death, deadlock, resource/risk alarm, or strategically relevant uncertainty.

### Body timescale
The Body operates fast enough for normal movement/interactions, using the current visual/temporal state and an active Skill Contract. It proposes primitives one step at a time.

### Reflex timescale
The Reflex is the fastest path. It responds only to predeclared immediate visible conditions and only with actions permitted by the active Manager contract.

The architecture must not wait for LLM reasoning in situations that require immediate control.

## 3. Perception and Observation

The primary research path is screen-only. Perception may include:

- screenshots/frame sequences;
- OCR of visible text;
- UI-state signals;
- player position;
- non-semantic visible target/sprite candidates;
- perceptual signatures;
- confidence and evidence references.

Perception reports what is visible; it does not decide goals, success, quest meaning, or hidden semantics.

A visible-only RPG-Maker bridge may exist as a separate `bridge-assisted` cohort and development reference. It must pass a deny-by-default firewall and may expose only information simultaneously visible to an ordinary player.

## 4. Temporal State

Temporal State stabilizes frame-level perception into short-horizon control signals. It may contain:

- recent positions and motion estimates;
- visible appearance/disappearance events;
- stable UI transitions;
- progress/no-progress windows;
- repeated-state/action loop evidence;
- target visibility continuity;
- immediate hazard cues.

Persistent semantic identity and game-specific classification should not be assumed unless supported by visible evidence and a later explicit contract.

## 5. Memory architecture

### Evidence Ledger
Immutable links to screenshots, visible text, action/outcome records, bridge receipts, timestamps, hashes, and run provenance.

### Episodic Memory
What happened in a trajectory: state summaries, goals, skills, actions, outcomes, death/stall events.

### Semantic Facts
Evidence-backed propositions accepted as observed knowledge. Facts retain provenance.

### Hypotheses
Uncertain propositions with confidence, supporting evidence, contradicting evidence, status, and possible test actions. Hypotheses never silently become facts.

### Topological Memory
Observed connectivity/transition relationships between visually characterized locations or states. It is not an internal game map.

### Strategy / Experiment Memory
Attempted approaches, rationale, result, failure mode, and whether a future run should retry, modify, or avoid them.

### Skill Competence Registry
Skill version, applicable goal schema, controller, validation metrics, known failure modes, confidence/competence estimate, and activation state.

### Retrieval
The Cortex receives a bounded retrieval snapshot, not the entire database. Retrieval should favor current-goal relevance, recency when appropriate, evidence quality, contradiction, novelty, and prior failure context.

### Death / run-end consolidation
Death triggers a post-mortem that distinguishes observation from inferred cause. The system records what visibly preceded the outcome, what hypotheses were affected, what strategy should change, and what skill deficiency may need training.

## 6. Cortex contract

The Cortex receives a bounded `CortexContext` containing, conceptually:

- current Observation/Temporal summary;
- relevant screenshot(s) when useful;
- visible text/UI;
- evidence IDs;
- retrieved facts/hypotheses/episodes/topology/skill competence;
- current high-level objective;
- available skill capabilities;
- current budgets/risk constraints;
- previous contract outcome and open questions.

The Cortex emits a typed decision, conceptually:

- evidence-grounded belief updates/hypotheses;
- open questions/information needs;
- one next goal;
- one requested universal skill/capability;
- constraints/risk limit;
- testable success criteria proposal;
- requested memory updates linked to evidence.

Primitive keys, timings, direct `InputExecutor` calls, or low-level action sequences are invalid Cortex output.

## 7. Manager / Executive contract

The Manager is the authority boundary. It must:

1. validate Cortex schema and no-spoiler policy;
2. validate requested capability against the current executable set;
3. ground intent to a typed, visible, evidence-linked target;
4. reject ambiguity or insufficient evidence rather than let the Body guess;
5. bind task, target, allowed action set, budget, risk limit, verifier, timeout and evidence provenance into a Skill Contract;
6. schedule Body/Reflex execution;
7. evaluate verified outcomes;
8. close/suspend contracts on success, failure, timeout, no-progress, target loss, safety event, contamination, death or contradiction;
9. invoke Cortex replanning only after the previous contract is audibly closed/suspended.

## 8. Skill abstraction

A good Skill Contract is more abstract than a key sequence and more concrete than a quest objective.

Preferred examples:

- `reach_visible_target(target)`
- `interact_visible_object(target)`
- `continue_dialogue()`
- `menu_select_visible_option(target)`
- `retreat_from_visible_hazard(target)`
- `wait_for_safe_gap()`
- later: `maintain_distance(target, range)` or other measured universal control goals.

Avoid game-specific skills such as named-room solutions, named-enemy tactics, quest shortcuts, or ending-specific actions.

## 9. Body design

### Baseline
Start with deterministic/heuristic skills through the same contract interface used later by learned policies.

### Learned default
The preferred learned Body is a shared goal-/skill-conditioned policy:

```text
policy(action | visual/temporal observation,
                grounded target,
                skill/goal embedding,
                action history,
                allowed-action mask)
```

A shared visual backbone enables reuse across skills. Skill-specific adapters/heads or separate policies are justified only by measured negative transfer/interference or incompatible action structure.

### Inputs
The Body may receive only information authorized by the active contract: current visual/temporal state, grounded target, goal/skill representation, short action history, risk/safety parameters and allowed-action mask.

### Output
One primitive action proposal at a time. Safety/Input remains a separate enforcement layer.

## 10. Reflex

Reflex triggers, eligibility, cooldown, action mask and termination conditions are declared by the Manager. Reflex cannot:

- invent a goal;
- select an unavailable skill;
- change memory truth;
- extend a budget;
- suppress a stop/replan;
- bypass SafetyFilter/InputExecutor/logging.

When evidence is insufficient, safe behavior is wait/stop/replan rather than extrapolating hidden state.

## 11. Independent verification and reward

The Cortex does not grade itself.

Verification priority:

1. deterministic visible success/failure detectors;
2. deterministic progress signals;
3. calibrated learned perceptual detector where necessary;
4. optional separately evaluated VLM/LLM judge for outcomes that cannot be expressed reliably otherwise;
5. manual review for benchmark auditing.

Rewards for Body learning are derived from validated progress/success/failure events rather than arbitrary free-form LLM scores.

A canonical failure taxonomy should distinguish at least:

- `perception_uncertain`
- `grounding_failed`
- `capability_rejected`
- `planning_failed`
- `skill_failed`
- `no_progress`
- `timeout`
- `target_lost`
- `safety_intervention`
- `focus_lost`
- `death`
- `replan_required`
- `contaminated`

## 12. Learning lifecycle

The project follows continual experience acquisition without uncontrolled within-run learning:

```text
frozen Body vN
→ collect admissible trajectories
→ verifier labels outcomes
→ replay / demonstrations / failure subsets
→ train candidate vN+1 between runs
→ held-out validation
→ safety + false-success checks
→ certify or reject
→ activate only certified version
```

Bootstrap order:

1. heuristic skills and stable verifiers;
2. demonstrations/Behavior Cloning when useful;
3. goal-conditioned RL fine-tuning after reward validity is demonstrated;
4. HER where goal relabeling is semantically valid;
5. model-based/world-model approaches only when data volume and baseline evidence justify the compute/complexity.

The SkillTrainer may propose training curricula from observed deficiencies, but cannot silently deploy an uncertified controller.

## 13. Cortex provider abstraction

Cortex inference uses a provider-neutral typed client. Supported classes may include:

- fake/deterministic test provider;
- local OpenAI-compatible provider via llama.cpp/Ollama or similar;
- optional API provider for exploratory/capability-ceiling experiments.

Provider/model/config/prompt identity, latency, token usage/cost where relevant, and run classification must be logged. Official offline cohorts currently require local inference; API cohorts stay separate unless the research protocol is explicitly revised.

## 14. Safety/Input

No primitive action is executed unless:

- a valid Manager contract is active;
- the intended game window is verified/focused;
- the primitive is allowed by the contract/action mask;
- rate-limit capacity is available;
- emergency stop is functional;
- the proposal/execution/rejection can be durably logged and linked to before/after evidence.

Wrong-window input and no-spoiler violations are hard failures, not optimization trade-offs.
