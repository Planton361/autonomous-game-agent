# ALIGN-2026-09-19-v1.0 — project control and Mission Run semantics

## Release record

- **Release:** `ALIGN-2026-09-19-v1.0`
- **Change:** GitHub Issue [#62](https://github.com/Planton361/autonomous-game-agent/issues/62)
- **Base commit:** `a2b5def3e59c0b01d27b1415259a822ec2ffa34f`
- **Status:** accepted active control overlay; repository delivery remains subject to the normal review and merge workflow
- **Scope:** documentation and control-contract alignment only
- **Machine-readable contract:** [`projectctl-status.schema.json`](projectctl-status.schema.json)

This release records the Program Owner decision of 2026-09-18. It is a versioned
control supplement to `ALIGN-2026-09-06-v1.0`; it does not rewrite that release or
claim that the current implementation has been changed. It is the accepted active
control overlay for the semantics and workflow defined below.

This release does not authorize a game launch, native input, gameplay, model
training, model download, networked experimentation, or execution of Issue #38.
It does not implement `projectctl`.

## Precedence and historical preservation

The source files and registration record for `ALIGN-2026-09-06-v1.0` remain
unchanged historical evidence. On activation, this release supersedes only the
following operational interpretations from that package:

- the death/restart boundary described in `07_RESEARCH_PROGRAM_SOT.md` §2;
- the permanent two-orchestrator operating model and chat handoff process in
  `08_ORCHESTRATION_PROTOCOL.md` §§1–3, §5 and §8;
- the TECH-ORCH/SCI-ORCH start choreography and corresponding operating duties in
  `10_ORCHESTRATOR_MANDATES.md`.

The old wording remains identifiable as the historical `ALIGN-2026-09-06-v1.0`
source text; it must not be read as if it had always used the terminology below.
Historical milestone/session reports, the legacy archive, and the existing
manuscript are not rewritten by this release. A later manuscript correction is a
separate bounded issue.

### Explicit precedence mapping to canonical architecture and protocol

`02_ARCHITECTURE_CANONICAL.md` remains authoritative for the component hierarchy,
Cortex/Manager/Body/Reflex/Verifier authority boundaries, contract execution,
between-Mission-Run learning lifecycle, and input safety. `04_RESEARCH_PROTOCOL_CANONICAL.md`
remains authoritative for admissible evidence, provenance, run modes, network
isolation, contamination, evaluation, and live-authorization requirements. This
overlay does not rewrite either canonical file.

Under this overlay, the narrow operational reading is:

- historical/canonical `run` references concerning experimental identity, run mode,
  frozen configuration, parameter training/certification, or the primary outer
  experimental unit are read as **Mission Run**;
- death/restart ends a **Life Episode**, not the Mission Run, unless an independently
  declared Mission Run terminal condition is reached;
- admissible evidence and memory from earlier Life Episodes of the same Mission Run
  may persist with provenance;
- independent new Mission Runs begin with the protocol-defined fresh experimental
  state; cross-Mission-Run inherited memory is not enabled by default merely because
  older canonical text mentions “prior runs”;
- all unrelated no-spoiler, provenance, Manager/Body/Verifier, input-safety,
  run-mode, and live-authorization rules remain unchanged.

## Nested experimental units

The nesting is:

```text
Mission Run
└── Life Episode (one or more)
    └── Grounded Skill Contract (zero or more at a time, one active contract at most)
        └── primitive action (proposed/executed only through the safety boundary)
```

### Mission Run

A Mission Run is the outer bounded experimental unit. It starts from the
protocol-defined fresh experimental state, receives a new mission identity and
manifest, and continues across permitted deaths, game restarts, and application
or process restarts. A Mission Run ends only at a declared terminal condition.

Death or a death-driven game restart does **not** create a new Mission Run. It
closes the current Life Episode and may open the next one under the same frozen
identities. A new independent scientific repetition is a new Mission Run with
fresh experimental memory; it is not a descendant of the previous Mission Run
unless a future, explicitly approved protocol says otherwise.

### Life Episode

A Life Episode is the bounded interval from a life start/restart to visible death,
episode stop, or Mission Run termination. It owns its transient runtime state and
records observations, contracts, actions, outcomes, and visible death evidence.

The permitted persistent state is not discarded merely because an episode ends.
Evidence, episodic memory, hypotheses, topology, strategies, and plans may grow or
be revised across Life Episodes, provided each update keeps provenance and does not
turn an inference into an observation. A death is an outcome, not proof of its
cause and not by itself a terminal Mission Run condition.

### Grounded Skill Contract

A Grounded Skill Contract is a Manager-issued, bounded execution contract inside a
Mission Run/Life Episode. It binds a visible evidence-linked target, an available
universal skill, allowed action set, budget, risk limit, verifier, timeout,
termination conditions, and evidence/logging requirements.

The Manager alone validates Cortex output, grounds the target, and opens,
suspends, closes, or replans the contract. The Body and bounded Reflex may act
only inside the active contract. A contract is more concrete than a high-level
mission goal and more abstract than a key sequence; it never contains a
game-specific solution shortcut.

### Primitive action

A primitive action is one contract-allowed proposal or execution step. Cortex does
not issue primitive keys or timings. Body/Reflex proposals reach the game only
through the SafetyFilter/InputExecutor after valid-contract, target-focus,
allowlist, rate-limit, emergency-stop, evidence, and logging checks succeed. The
Independent Verifier determines visible outcome; a screenshot or perceptual-hash
change alone is not success.

## Mission Run identity and mutable state

The Mission Run manifest freezes the identities that define the experiment before
the first observation. At minimum, the following remain fixed until the Mission
Run terminates:

| Frozen identity or boundary | Required treatment |
| --- | --- |
| Mission Run ID, run mode, protocol/configuration and frozen budgets | No silent replacement, mode switch, or budget increase |
| Cortex model/provider identity, prompt bundle and configuration hashes | No prompt/configuration swap or LLM parameter update |
| Body/controller version and weights | No controller replacement, weight update, or generational refresh between Life Episodes |
| Declared harness and executable component identities | No unlogged harness or safety-boundary change |
| Evidence/no-spoiler, Manager, Verifier, SafetyFilter and InputExecutor contract | No authority or integrity relaxation during the Mission Run |

The following may mutate during a Mission Run when the mutation is admissible,
logged, and evidence-linked:

- the append-only evidence ledger and episode/action/outcome records;
- episodic memory, evidence-backed facts, hypotheses, contradictions, topology,
  strategies, plans, open questions, and bounded retrieval snapshots;
- Manager contract state, observed progress, consumed budget, failure category,
  and replan decisions;
- visible temporal state and other episode-local runtime observations;
- post-mortem and memory-consolidation records after death or episode stop.

Mutable knowledge does not grant new execution authority. A memory update cannot
open a contract, expand a budget, bypass a safety check, or authorize hidden state.
Training and certification remain between Mission Runs under the canonical
collect → validate on held-out scenarios → certify/reject → activate lifecycle.

## Restart and terminal semantics

An application/process restart is an operational restart of the runtime. It does
not create a new Mission Run when the manifest, frozen identities, provenance, and
integrity checks are preserved. It may recreate process handles and other
transient state, but it must not silently reset experimental memory or switch the
controller. If continuity cannot be established, the run is stopped or quarantined
for review; it is never relabeled as a clean new run after the fact.

After visible death, the current Life Episode is closed with evidence and a
post-mortem that separates observation from inferred cause. If the Mission Run has
not reached a terminal condition, a new Life Episode may begin with the same frozen
identities. The same rule applies to an authorized game restart after death.

A Mission Run terminates on one of these declared conditions:

- independently verified mission ending or other protocol-defined success;
- exhaustion of the frozen time/action/cost/life budget;
- explicit manual stop by the Program Owner or an authorized safety operator;
- unrecoverable safety or integrity stop, including wrong-window input,
  no-spoiler/hidden-state violation, provenance loss, or network-policy breach;
- unrecoverable environment or harness failure that prevents trustworthy
  continuation.

Contract failure, timeout, target loss, no-progress, ordinary death, and a
replan-triggering contradiction close or suspend the relevant contract/episode;
they do not silently change the Mission Run identity and do not automatically
prove Mission Run success or failure.

## Single project-control workflow

The active control loop is:

```text
Question/Need → Decision or Ready Issue → Codex → focused checks → Draft PR
→ GitHub CI → review → Anton merge → next eligible Issue
```

The loop has one technical Issue in progress by default. A Ready Issue defines one
bounded outcome, scope, non-goals, acceptance criteria, authority constraints, and
focused validation. A Draft PR is a handoff for review, not a merge or Issue
completion. GitHub CI and review remain required before Anton decides whether to
merge.

Scientific reasoning, architecture review, implementation evidence, and user
decisions remain distinct records even though they no longer require separate
persistent orchestrator chats:

| Concern | Required record/authority |
| --- | --- |
| Scientific reasoning and literature synthesis | Obsidian knowledge graph plus versioned claim/evidence work; Zotero is the source/PDF authority |
| Architecture, protocol, run-mode, or phase-gate change | A bounded GitHub Issue/ADR and explicit Program Owner decision; canonical sources change only through that gate |
| Implementation and validation evidence | Codex worktree, changed files, focused commands, Draft PR, GitHub CI and review records |
| User intent, scope, merge, live authorization, scientific freeze | Explicit Program Owner decision recorded in the relevant Issue/ADR/project artifact |

Operational roles are non-overlapping:

| System or role | Sole operational role in this workflow |
| --- | --- |
| GitHub | Issues, Pull Requests, Actions, milestones, project state, and durable implementation decisions |
| ChatGPT Project | Primary planning/review interface and bounded handoff preparation; not a competing implementation or research source of truth |
| Codex | Executes exactly one authorized Ready technical Issue and reports evidence; it does not decide architecture, merge, or live authorization |
| Obsidian | Private research knowledge graph for notes, hypotheses, and synthesis; not the operational status authority |
| Zotero | Source/PDF authority for literature records; not an execution or project-status system |
| Notion | Dashboard/projection only; it must not become a competing source of truth |
| Program Owner (Anton) | Explicit decisions for canonical/protocol changes, scientific freeze/preregistration, live input/gameplay, merge, and scope expansion |

The former TECH-ORCH/SCI-ORCH split may remain useful as a human review lens,
but it is no longer a permanent operating dependency or a requirement for
separate chats. No role may create an unrecorded parallel queue or silently
delegate a new Issue.

## Task classes and gates

Every future automation status identifies one task class. The minimum classes and
their gates are:

| Class | Entry gate | Required evidence/gates | Exit state |
| --- | --- | --- | --- |
| `research` | Question/Need with source set and claim scope | Source/provenance record; claim class; explicit separation of hypothesis, literature finding, implementation fact, and result; no live action | Reviewed research handoff or a bounded Decision/Ready Issue |
| `decision` | A concrete choice with alternatives and impact | Issue/ADR; affected files/claims; explicit Program Owner approval for canonical, protocol, run-mode, architecture, phase-gate, or scope changes | Recorded decision with owner, release/version impact, and one eligible next step |
| `implementation` | Ready GitHub Issue and one active technical WIP slot | Codex branch; narrow diff; no live authorization inferred; focused checks; Draft PR; GitHub CI and review before merge | `ready_for_review`, `merged`, `partial`, or `blocked`; never “done” from a Draft PR alone |
| `verification` | Frozen target and acceptance criteria | Independent or separately identified verifier; actual commands/evidence; failures and limitations recorded; no claim based on a plan or stale output | Verified result, partial result, or blocked handoff with one next step |
| `live` | Exact run scope plus explicit Program Owner live authorization | Run manifest; mode/network/no-spoiler checks; active Manager contract; focus identity; emergency stop; finite budgets; before/action/after evidence; independent Verifier; complete audit trail | Verified terminal result or safety/integrity stop; Issue #38 is not entered by this release |

Canonical/protocol changes, merge, live input/gameplay, and scientific
freeze/preregistration are human gates. Routine automation may prepare evidence or
stop at a gate; it may not infer approval from an Issue label, CI result, Draft PR,
or chat message.

## Future `projectctl` handoff/status contract

`projectctl` is intentionally not implemented here. Future automation may consume
the JSON Schema at [`projectctl-status.schema.json`](projectctl-status.schema.json),
but it must not broaden the authority rules above.

Each status object must make these facts machine-readable:

- the active task: ID, class, Issue, scope, non-goals, and state;
- dependencies: each dependency, its state, and any blocking reference;
- gate state: scope, canonical/protocol decision, scientific freeze, live
  authorization, focused validation, CI, review, and merge;
- validation: aggregate result plus each actually executed check and evidence
  reference;
- status: current handoff state, including `ready_for_review`, `partial`, or
  `blocked` where applicable;
- limitations: explicit known gaps/conflicts, including an empty list when none
  are known;
- exactly one `next_step` object with owner, action, and gate/Issue context.

The schema deliberately represents `next_step` as one object, not an array. A
handoff with multiple alternatives must first record a Decision task; it must not
hide several recommendations inside one status update. The contract records
provenance and release identity, but it does not make an unmerged status a merged
implementation or a live authorization.

## Alignment delta

`ALIGN-2026-09-19-v1.0` makes this explicit delta from
`ALIGN-2026-09-06-v1.0`:

1. **Run boundary:** introduce `Mission Run > Life Episode > Grounded Skill
   Contract > primitive action`; death/restart creates a Life Episode, not a new
   Mission Run.
2. **Identity freeze:** freeze the Cortex identity/configuration, Body/controller
   version and weights, declared harness, protocol/mode, and safety/verification
   boundaries throughout one Mission Run; permit only provenance-preserving
   experience/state evolution.
3. **Project control:** replace permanent two-orchestrator choreography with the
   GitHub + ChatGPT Project + Codex + CI + review + Anton merge loop.
4. **Operational roles:** assign one non-overlapping role to GitHub, ChatGPT,
   Obsidian, Zotero, Notion, Codex, and the Program Owner.
5. **Automation contract:** define task classes, human gates, structured status
   fields, validation evidence, limitations, and exactly one next step for future
   `projectctl` work.
6. **Preserved boundaries:** no change to no-spoiler evidence eligibility,
   Cortex/Manager/Body/Reflex authority, Independent Verifier independence,
   between-run learning, input safety, or explicit live authorization.

The release is the accepted active control overlay, while the repository delivery
remains ready for review on the stated base commit. Any future canonical or
protocol-source edit remains an explicit human decision. Issue #38 remains open
and is not executed by this change.

## Source set and validation scope

This release was prepared against:

- `AGENTS.md`;
- `docs/canonical/00_ACTIVE_SOURCE_INDEX.md`;
- `docs/canonical/07_RESEARCH_PROGRAM_SOT.md`;
- `docs/canonical/08_ORCHESTRATION_PROTOCOL.md`;
- `docs/canonical/09_ARTIFACT_CONTRACTS.md`;
- `docs/canonical/10_ORCHESTRATOR_MANDATES.md`;
- `docs/canonical/02_ARCHITECTURE_CANONICAL.md`;
- `docs/canonical/04_RESEARCH_PROTOCOL_CANONICAL.md`;
- open Issue #38 as the explicitly unauthorized live-smoke reference.

This document is a control contract and release delta, not evidence that any live
run, model training, or new runtime capability has occurred.
