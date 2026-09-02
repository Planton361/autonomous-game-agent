# Project Charter — Evidence-Grounded Hierarchical Agent for Long-Horizon RPGs

## 1. Research vision

The project investigates how an autonomous agent can enter a previously unseen long-horizon role-playing game with no game-specific solution knowledge, learn from its own visible experience, construct and revise useful beliefs, and progressively produce strategies that advance toward a terminal game outcome.

Fear & Hunger is the first pilot environment. It is chosen as a demanding naturalistic RPG setting in which long-horizon decisions, exploration, visible resource pressure, failure, death/restart, menus/dialogue, and time-sensitive movement can coexist. The pilot is not itself a claim of cross-game generalization.

The long-term research interest is broader: whether reusable embodied skills, hierarchical planning interfaces, memory structures, and learned low-level control can transfer to unseen interactive environments.

## 2. Central scientific thesis

A monolithic controller is not assumed to be the best solution. The project studies a hierarchy in which complementary capabilities operate at different timescales:

- an **LLM Cortex** performs slow semantic reasoning, exploration planning, hypothesis formation, long-horizon goal management, and evidence-backed memory use;
- a **Manager/Executive** converts validated intent into grounded, bounded executable contracts;
- a **Body** performs fast reusable physical control and eventually learns goal-/skill-conditioned policies;
- a **Reflex** handles immediate visible hazards under the authority of an active contract;
- an independent **Verifier** determines success, failure, progress, and outcome evidence;
- external **Memory** preserves evidence, episodes, hypotheses, topology, strategy history, and skill competence across runs;
- a between-run **SkillTrainer** improves Body versions from accumulated admissible experience.

The scientific interest lies especially in the interfaces between these layers: how abstract language-level intent becomes executable without reducing the Cortex to a joystick, how success is verified without self-confirmation, how reusable skill abstractions are learned, and how experience changes later planning.

## 3. Human-first-play analogy

The motivating analogy is operational, not cognitive. A human first-time player typically brings generic priors—movement, exploration, interaction, risk avoidance—but must discover game-specific mechanics and long-term consequences through observation and trial-and-error.

The agent should similarly be able to:

- explore without external solution knowledge;
- form hypotheses rather than assume hidden truth;
- test hypotheses through bounded actions;
- remember evidence and outcomes;
- learn from deaths and failed strategies;
- distinguish known facts from uncertain beliefs;
- reuse general skills while acquiring game-specific knowledge only through admissible experience.

The project does not claim human-like consciousness, intuition, or thought.

## 4. Immediate objective: Fear & Hunger pilot

The first major objective is a reproducible architecture that can conduct autonomous Fear & Hunger experiments under strict no-spoiler conditions. The minimum successful system must close the loop:

```text
visible observation
→ memory retrieval
→ Cortex decision
→ Manager grounding/contract
→ Body/Reflex action
→ guarded input
→ visible outcome
→ independent verification
→ memory/replay
→ replan or continue
```

The pilot should support longer repeated runs, death-triggered post-mortems, persistent evidence-backed memory, and measurable progress. Reaching an ending is an important later capability test, but scientific progress is also measured at the contract, exploration, memory, safety, and learning levels.

## 5. Later research program

Only after the Fear & Hunger closed loop and skill competence are reliable should the project test:

1. learned goal-conditioned Body skills against heuristic equivalents;
2. autonomous curriculum/skill-deficiency detection;
3. retention and improvement across repeated runs;
4. skill abstraction and interference in a shared policy;
5. cross-start-state robustness inside Fear & Hunger;
6. cross-environment/cross-game transfer;
7. language-based skill routing versus non-language routing.

A candidate long-term research question is:

> How can autonomous agents acquire, abstract, and transfer reusable skills across unseen long-horizon interactive environments, and what role can language-model-based hierarchical planning play in selecting and adapting them?

## 6. Core research questions for the pilot

- Does an evidence-grounded Cortex improve verified task progress over fixed-goal control when the same Manager and Body are held constant?
- Does persistent evidence-backed memory reduce repeated failures and improve later-run decisions?
- Which failures arise from perception, grounding, planning, execution, verification, or memory rather than being collapsed into one reward signal?
- What task abstraction is sufficiently concrete for reliable low-level execution while remaining reusable?
- When does a learned goal-conditioned Body outperform heuristics without increasing false success or safety violations?
- How much benefit comes from a stronger Cortex model versus a better harness, verifier, memory, and Body?

## 7. Stable design commitments

The project commits to the following unless a later explicit research review overturns them:

- the LLM never directly controls keys;
- game-specific facts require admissible evidence;
- the Manager owns the language-to-action authority boundary;
- the Body uses universal skill contracts, not quest-specific shortcuts;
- the default learned Body is shared and goal-/skill-conditioned, with specialization only when measured interference justifies it;
- Cortex and Verifier are separated;
- arbitrary LLM scalar reward is not trusted as ground truth;
- Body weights are frozen within a run and updated between runs through a versioned validation/certification loop;
- no RL training begins before success/failure detectors are sufficiently stable to produce meaningful targets;
- official results preserve strict run-mode, evidence, provenance, and no-spoiler separation.

## 8. Non-goals for the first pilot

The first pilot does not require:

- training a foundation LLM or VLM from scratch;
- perfect semantic object recognition;
- end-to-end pixel-to-action RL as the only controller;
- one neural network per skill;
- unrestricted online weight updates during gameplay;
- cross-game transfer claims;
- hidden engine state as a shortcut;
- game-specific hardcoded solutions;
- maximizing completion at the expense of scientific auditability.

## 9. Resource assumptions

The project is designed for a single researcher/home workstation. Local small/open-weight models and financially bounded API experimentation are acceptable. Large-scale foundation-model pretraining is not assumed.

Preferred engineering basis includes Python 3.12, uv, Git/GitHub, Pydantic, pytest, ruff, SQLite/JSONL/screenshots, lightweight CV/OCR tooling, provider-agnostic LLM inference, and later Gymnasium/PyTorch/Stable-Baselines3 or justified alternatives for Body learning.

## 10. Meaning of success

The architecture succeeds scientifically before it succeeds as a speedrunner. A strong result is a system in which:

- each game-specific belief is auditable;
- the Cortex proposes meaningful experiments and goals without key-level control;
- the Manager reliably grounds and constrains them;
- the Body executes with low latency;
- the Verifier distinguishes actual outcomes from incidental screen changes;
- deaths produce evidence-backed revisions rather than repeated blind behavior;
- reusable skills improve through controlled experience;
- later experiments can isolate which layer caused improvement or failure.
