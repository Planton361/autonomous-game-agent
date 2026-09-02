# Canonical Project Source Index

**Status:** frozen project context baseline  
**Baseline date:** 2026-09-01  
**Project:** `Planton361/autonomous-game-agent`

These files are the stable, cross-chat knowledge base for the project. They are intentionally **not** a live progress tracker.

## Authority hierarchy

1. **GitHub HEAD** — authoritative for what is actually implemented, tested, removed, or renamed.
2. **Canonical Project Sources** — authoritative for enduring project vision, target architecture, research protocol, planned capability sequence, and literature baseline.
3. **Current working chat** — authoritative for the temporary milestone, latest local/uncommitted changes, validation results, blocker, and next Codex ticket.

A roadmap statement is never proof of implementation. A current-chat claim should be verified against GitHub when material.

## Canonical files

### `01_PROJECT_CHARTER.md`
Stable research vision, scope, scientific thesis, objectives, terminology, and explicit non-goals.

### `02_ARCHITECTURE_CANONICAL.md`
Normative target architecture and component authority: Perception, Temporal State, Memory, Cortex, Manager, Body, Reflex, Verifier, Input safety, Replay, and SkillTrainer.

### `03_RESEARCH_ROADMAP_CANONICAL.md`
Capability sequence from research foundations to a reproducible Fear & Hunger pilot, learned Body, long-horizon evaluation, and later transfer research. It contains no active-milestone marker.

### `04_RESEARCH_PROTOCOL_CANONICAL.md`
No-spoiler policy, run modes, evidence/provenance requirements, learning/evaluation separation, baseline methodology, and reproducibility rules.

### `05_LITERATURE_BASELINE_2026-09-01.md`
Frozen state-of-the-art synthesis and project-transfer analysis as of the baseline date. It is a literature baseline, not a promise that no later work exists.

### `06_REFERENCES_AUTONOMOUS_GAME_AGENTS.bib`
BibTeX database corresponding to the literature baseline.

## What is deliberately NOT a canonical source

Do not upload dynamic snapshots such as:

- current test count;
- current active milestone;
- latest changed-file list;
- temporary blockers;
- session handoffs;
- old Codex tickets;
- implementation-state tables tied to one commit;
- generated smoke-corpus artifacts;
- historical roadmap versions.

These belong in GitHub and the current working chat.

## Frozen-source rule

The canonical source set remains unchanged across ordinary milestone completion. A milestone does not trigger edits here. Revise this baseline only after the user explicitly requests a new architecture/research review and decides to create a new canonical version.
