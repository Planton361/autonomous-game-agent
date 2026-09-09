# Research Atlas

Generated from Registry YAML; fully overwriteable. Do not edit structured claims here.

Registry = authoritative SOT. Generated notes = views. Presentation Domain != technical hierarchy: only `part_of` defines technical ancestry.

Open docs/research-atlas/ as an Obsidian vault. Enable the Bases core plugin. The Excalidraw community plugin is required only for the visual map; no personal plugin settings are committed.

[[Assets/Excalidraw/System Anatomy.excalidraw|System Anatomy]] · [[Generated/Atlas Views.base|Atlas Views]] · [[overview|Compatibility overview]]

## Read and maintain

Follow a technical note to its Evidence notes and source locators. Historical Evidence refs stay historical. New current-main claims require new records.

Properties and all generated files are overwriteable, including changes made in Bases. Keep authored commentary/proposals in separate notes (for example Review Queues/). Accepted changes go through Registry review; no reverse sync or automatic status acceptance.

Zotero/Work remain external proposal boundaries only: no API, automation, import or reverse sync is implemented. Research overlays do not change technical ancestry or accept research/architecture claims.

Regenerate from repository root with `uv run --no-sync python -m fh_agent.research_atlas.workspace docs/research-atlas`; append `--check` for drift validation. The old dossiers/ views are migrated and removed.

File-format references: [Bases syntax](https://obsidian.md/help/bases/syntax), [Excalidraw writer](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/master/src/shared/ExcalidrawData.ts) and [Drawing parser](https://github.com/zsviczian/obsidian-excalidraw-plugin/blob/master/src/shared/excalidrawMarkdownParsing.ts). The generated map uses parsed frontmatter, Text Elements, Element Links and an uncompressed JSON Drawing section. Validation is structural; it does not claim an interactive Obsidian plugin test.

## System and presentation views

- [[Home/SYS-AGA — Autonomous Game Agent Experiment System|SYS-AGA · Autonomous Game Agent Experiment System]]
- [[Architecture/Domains/DOM-ENV-ACQUISITION — Environment & Acquisition|DOM-ENV-ACQUISITION · Environment & Acquisition]]
- [[Architecture/Domains/DOM-OBS-INTEGRITY-STATE — Observation Integrity & State|DOM-OBS-INTEGRITY-STATE · Observation Integrity & State]]
- [[Architecture/Domains/DOM-EVIDENCE-MEMORY — Evidence, Memory & Retrieval|DOM-EVIDENCE-MEMORY · Evidence, Memory & Retrieval]]
- [[Architecture/Domains/DOM-COGNITION — Cognition|DOM-COGNITION · Cognition]]
- [[Architecture/Domains/DOM-EXECUTIVE — Executive Control & Contracts|DOM-EXECUTIVE · Executive Control & Contracts]]
- [[Architecture/Domains/DOM-ACTION-SAFETY — Action & Safety|DOM-ACTION-SAFETY · Action & Safety]]
- [[Architecture/Domains/DOM-VERIFY-LEARN — Verification & Learning|DOM-VERIFY-LEARN · Verification & Learning]]
- [[Architecture/Environments/ENV-GAME-INSTANCE — Game - Environment|ENV-GAME-INSTANCE · Game / Environment]]

## Research overlays

- [[Research Questions/RQ-PROGRAM-AB-001 — Program A–B working question|RQ-PROGRAM-AB-001 · Program A–B working question]]
- [[Research Threads/THREAD-EXPERIENCE-TO-ACTION-001 — Experience to Action|THREAD-EXPERIENCE-TO-ACTION-001 · Experience to Action]]

The map includes canonical target paths as well as implementation. Consult individual notes for scope and status. Verifier is independent of Cortex; reflection follows verification. Training/candidate/certification are between runs only.
