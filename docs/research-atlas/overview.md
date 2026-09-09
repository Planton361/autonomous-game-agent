# Research Atlas v0.2

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

[[Home/Research Atlas|Research Atlas Home]] · [[Assets/Excalidraw/System Anatomy.excalidraw|System Anatomy]]

Domains are presentation views. Technical ancestry derives only from `part_of`. Statuses and relationships are in generated record notes, backed by Registry.

## Environment & Acquisition

[[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION · Environment & Acquisition]]

- [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]
- [[Components/CMP-SCREEN-CAPTURE — Screen Capture|CMP-SCREEN-CAPTURE · Screen Capture]]
- [[Data Artifacts/DAT-SCREEN-FRAME — ScreenFrame|DAT-SCREEN-FRAME · ScreenFrame]]
- [[Components/CMP-VISIBLE-STATE-BRIDGE — Optional Visible-State Bridge|CMP-VISIBLE-STATE-BRIDGE · Optional Visible-State Bridge]]

## Observation Integrity & State

[[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE · Observation Integrity & State]]

- [[Components/CMP-NO-SPOILER-FIREWALL — No-Spoiler Firewall|CMP-NO-SPOILER-FIREWALL · No-Spoiler Firewall]]
- [[Components/CMP-PERCEPTION — Perception|CMP-PERCEPTION · Perception]]
- [[Data Artifacts/DAT-OBSERVATION — Observation|DAT-OBSERVATION · Observation]]
- [[Components/CMP-TEMPORAL-STATE — Temporal State|CMP-TEMPORAL-STATE · Temporal State]]
- [[Components/CMP-PERCEPTION-UI-STATE — UI State Classification|CMP-PERCEPTION-UI-STATE · UI State Classification]]
- [[Components/CMP-OBSERVATION-BUILDER — Observation Builder|CMP-OBSERVATION-BUILDER · Observation Builder]]

## Evidence, Memory & Retrieval

[[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]

- [[Components/CMP-MEM-RETRIEVAL — Memory Retrieval|CMP-MEM-RETRIEVAL · Memory Retrieval]]
- [[Interfaces & Contracts/IF-MEM-CORTEX — Memory to Cortex|IF-MEM-CORTEX · Memory to Cortex]]
- [[Data Artifacts/DAT-RETRIEVAL-SNAPSHOT — Bounded retrieval snapshot (target only)|DAT-RETRIEVAL-SNAPSHOT · Bounded retrieval snapshot (target only)]]
- [[Measurements/MEAS-RETRIEVAL-DELIVERY-001 — Actual memory-evidence delivered to Cortex|MEAS-RETRIEVAL-DELIVERY-001 · Actual memory/evidence delivered to Cortex]]
- [[Components/CMP-EVIDENCE-LEDGER — Evidence Ledger|CMP-EVIDENCE-LEDGER · Evidence Ledger]]
- [[Components/CMP-MEMORY — Memory|CMP-MEMORY · Memory]]
- [[Components/CMP-MEM-EPISODIC — Episodic Memory|CMP-MEM-EPISODIC · Episodic Memory]]
- [[Components/CMP-MEM-FACTS — Semantic Facts|CMP-MEM-FACTS · Semantic Facts]]
- [[Components/CMP-MEM-HYPOTHESES — Hypotheses|CMP-MEM-HYPOTHESES · Hypotheses]]
- [[Components/CMP-MEM-TOPOLOGY — Topological Memory|CMP-MEM-TOPOLOGY · Topological Memory]]
- [[Components/CMP-MEM-STRATEGY — Strategy - Experiment Memory|CMP-MEM-STRATEGY · Strategy / Experiment Memory]]
- [[Components/CMP-SKILL-COMPETENCE — Skill Competence Registry|CMP-SKILL-COMPETENCE · Skill Competence Registry]]

## Cognition

[[Architecture/Domains/DOM-COGNITION — Cognition|DOM-COGNITION · Cognition]]

- [[Components/CMP-CORTEX — Cortex|CMP-CORTEX · Cortex]]
- [[Interfaces & Contracts/CON-CORTEX-CONTEXT — CortexContext|CON-CORTEX-CONTEXT · CortexContext]]
- [[Interfaces & Contracts/CON-PLANNER-OUTPUT — PlannerOutput|CON-PLANNER-OUTPUT · PlannerOutput]]
- [[Measurements/MEAS-CORTEX-PROPOSAL-001 — Produced PlannerOutput|MEAS-CORTEX-PROPOSAL-001 · Produced PlannerOutput]]

## Executive Control & Contracts

[[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE · Executive Control & Contracts]]

- [[Components/CMP-MANAGER — Manager|CMP-MANAGER · Manager]]
- [[Interfaces & Contracts/IF-CORTEX-MANAGER — Cortex to Manager|IF-CORTEX-MANAGER · Cortex to Manager]]
- [[Interfaces & Contracts/CON-SKILL-CONTRACT — TaskSpec - bounded Skill Contract|CON-SKILL-CONTRACT · TaskSpec / bounded Skill Contract]]
- [[Measurements/MEAS-MANAGER-DISPOSITION-001 — Manager disposition and TaskSpec|MEAS-MANAGER-DISPOSITION-001 · Manager disposition and TaskSpec]]
- [[Components/CMP-MANAGER-GROUNDING — Grounding|CMP-MANAGER-GROUNDING · Grounding]]
- [[Components/CMP-MANAGER-SCHED-COMP — Scheduling and Completion|CMP-MANAGER-SCHED-COMP · Scheduling and Completion]]

## Action & Safety

[[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]

- [[Components/CMP-BODY — Body|CMP-BODY · Body]]
- [[Components/CMP-BOUNDED-REFLEX — Bounded Reflex|CMP-BOUNDED-REFLEX · Bounded Reflex]]
- [[Interfaces & Contracts/CON-PRIMITIVE-ACTION — Primitive Action Vocabulary|CON-PRIMITIVE-ACTION · Primitive Action Vocabulary]]
- [[Components/CMP-SAFETY-FILTER — SafetyFilter|CMP-SAFETY-FILTER · SafetyFilter]]
- [[Components/CMP-INPUT-EXECUTOR — InputExecutor|CMP-INPUT-EXECUTOR · InputExecutor]]
- [[Data Artifacts/DAT-ACTION-RESULT — ActionResult|DAT-ACTION-RESULT · ActionResult]]

## Verification & Learning

[[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]

- [[Measurements/MEAS-VERIFIED-OUTCOME-001 — Independent verified outcome|MEAS-VERIFIED-OUTCOME-001 · Independent verified outcome]]
- [[Data Artifacts/DAT-VISIBLE-OUTCOME — Visible Outcome|DAT-VISIBLE-OUTCOME · Visible Outcome]]
- [[Components/CMP-INDEPENDENT-VERIFIER — Independent Verifier|CMP-INDEPENDENT-VERIFIER · Independent Verifier]]
- [[Interfaces & Contracts/CON-VERIFIER-RESULT — VerifierResult|CON-VERIFIER-RESULT · VerifierResult]]
- [[Interfaces & Contracts/CON-MEMORY-UPDATE-REQUEST — MemoryUpdateRequest|CON-MEMORY-UPDATE-REQUEST · MemoryUpdateRequest]]
- [[Interfaces & Contracts/CON-POST-MORTEM-OUTPUT — PostMortemOutput|CON-POST-MORTEM-OUTPUT · PostMortemOutput]]
- [[Components/CMP-REPLAY-BUFFER — Replay Buffer|CMP-REPLAY-BUFFER · Replay Buffer]]
- [[Data Artifacts/DAT-REPLAY-TRANSITION — ReplayTransition|DAT-REPLAY-TRANSITION · ReplayTransition]]
- [[Components/CMP-SKILL-TRAINER — SkillTrainer|CMP-SKILL-TRAINER · SkillTrainer]]
- [[Data Artifacts/DAT-CANDIDATE-BODY-VERSION — Candidate Body Version|DAT-CANDIDATE-BODY-VERSION · Candidate Body Version]]
- [[Components/CMP-BODY-CERTIFICATION — Body Validation - Certification|CMP-BODY-CERTIFICATION · Body Validation / Certification]]
