# Architecture V2 — Contract-Bounded Cortex and Body

## Purpose

Architecture V2 defines authority, information flow, and timing for the Fear & Hunger pilot. It is
the target architecture, not a claim that the current prototype already closes the loop.

```text
Game pixels / allowlisted visible bridge fields
                    |
             No-Spoiler Firewall
                    |
       Observation + evidence provenance
                    |
          Memory snapshot / retrieval
                    |
             Cortex (slow path)
                    |
       goal + skill + constraints + claims
                    |
     Manager: validate, ground, schedule, contract
                    |
       +------------+-------------+
       |                          |
 Body skill (normal path)   Reflex (fast Body path)
       |                          |
       +----- primitive proposal--+
                    |
        SafetyFilter + InputExecutor
                    |
                  Game
                    |
      visible outcome, reward, stop/replan
```

Every arrow crossing a module boundary carries typed, logged data. No component receives hidden
engine state in an official run.

## Authority matrix

| Component | May decide | Must not decide |
|---|---|---|
| Perception/Observation | What visible signals were detected, with confidence and evidence IDs | Goals, success, strategy, or hidden-state interpretation |
| Memory | Persist/retrieve evidence, observed outcomes, hypotheses, and aggregate history | LLM-dependent truth or action selection |
| Cortex | Evidence-grounded belief/hypothesis, next goal, requested universal skill, risk limit | Keys, primitive sequences, focus/input behavior, final success |
| Manager | Grounded target, executable skill, scheduling, reward profile, budgets, stop/failure/success, replan | Raw key injection or unbounded strategy invention |
| Body | Primitive proposal under one active contract using a universal heuristic or learned skill | Quest-specific goals, contract changes, unsupported memory writes |
| Reflex | Low-latency primitive proposal for immediate visible hazards under the current contract | New goals, new permissions, budget extension, stop suppression |
| Safety/Input | Whether an allowed primitive may safely reach the focused game window | Strategy, success claims, or reward assignment |

## Cortex contract

The Cortex is a local LLM planner on the slow path. Its input is a bounded structured context made
from sanitized observations and evidence-backed Memory. Its output is validated structured JSON
containing beliefs/hypotheses, open questions, one next goal, one universal skill request, success
criteria, a risk limit, and requested evidence-linked memory updates.

The Cortex is never the joystick. Primitive action fields and key sequences are invalid output.
The Cortex cannot invoke `InputExecutor`, cannot decide that a task actually succeeded, and cannot
write Memory directly. A timeout, contradiction, failed grounding, or completed contract returns
control to the Manager, which decides whether another Cortex call is warranted.

## Manager contract

The Manager is the control-plane authority between language and action. It must:

1. validate Cortex schema and no-spoiler constraints;
2. ground the textual goal and skill request to visible, evidence-linked targets;
3. reject ungrounded or unavailable targets and skills;
4. create a versioned contract containing allowed skill/actions, risk limit, reward terms,
   step/time budget, success/failure detectors, and evidence provenance;
5. schedule the Body and optionally enable an eligible Reflex;
6. evaluate post-action observations, including detector confidence and contradictions;
7. stop on success, failure, safety trip, focus loss, timeout, contamination, or emergency stop;
8. request replanning only after closing or suspending the prior contract and logging why.

Grounding is not string copying. A Cortex phrase such as “the visible exit” must resolve to a typed
visible target with evidence IDs and confidence. Failure to resolve is `grounding_failed`, not
permission for the Body to guess.

## Body and Reflex contracts

The Body implements reusable, game-agnostic-in-form skills such as `safe_reach_target`,
`interact_visible_object`, `continue_dialogue`, `retreat_from_hazard`, `wait_for_safe_gap`, and
`menu_select_visible_option`. “Universal” means independent of a named room, enemy, quest, item,
or ending; it does not create a cross-game transfer claim.

A skill receives only its grounded target, current visible observation, history allowed by the
contract, and safety/risk parameters. It proposes one primitive at a time. Later learned policies
must use the same interface and cannot expand their observation or action authority.

The Reflex is an execution path inside the Body for conditions whose response latency cannot wait
for a Cortex call, for example an immediately approaching visible hazard. Reflex eligibility,
trigger, allowed actions, cooldown, and termination are declared by the Manager contract. Each
reflex action is filtered and logged exactly like a normal Body action. If evidence falls outside
the declared trigger, the safe behavior is `wait` plus a Manager stop/replan signal.

## Closed-loop state machine

```text
OBSERVE → PLAN → GROUND → CONTRACT → ACT → OBSERVE_AFTER → EVALUATE
             ^                                           |
             |             continue contract <-----------+
             +---- stop/fail/timeout/replan --------------+
```

Terminal safety states (`emergency_stop`, `focus_lost`, `contaminated`) do not automatically
replan. They end the run or require explicit operator authorization. No action is valid without an
active contract, matching target-window focus, rate-limit capacity, and a durable event record.

## Evidence and provenance

Game-specific facts require evidence IDs. Hypotheses must be labeled as hypotheses. An observation
record links its source screenshot or sanitized bridge receipt; action, reward, detector, stop, and
replan records link the relevant before/after evidence.

Every run manifest must capture at least:

- full Git commit and dirty-state indicator/diff hash;
- SHA-256 of the exact ordered prompt bundle;
- SHA-256 of the canonical experiment configuration;
- model name and SHA-256 of the local model artifact or immutable content manifest;
- run mode, run ID, seed, start/end time, hardware/software identity, and network-isolation proof.

The prompt and config hashes identify bytes used for the run, not merely filenames.

## Current implementation gap

The repository contains validated schemas, a local LLM boundary, Manager task/scheduler pieces,
heuristic skills, safety/input guards, memory stores, and extensive offline/audit tests. It does
not yet implement Architecture V2 end to end. The normative gap list is the technical-debt register
in `ROADMAP.md`; notably OCR, grounding, reward unification, strict success detection, catalog
alignment, an online skill runner, and the closed loop remain future work.
