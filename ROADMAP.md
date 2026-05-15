# ROADMAP.md — Fear & Hunger Autonomous Agent

This roadmap is designed for work with Codex as the coding agent and ChatGPT as architecture/review advisor.

## Session handoff rule

Start a new ChatGPT session at the end of every milestone or whenever the work changes type:

```text
architecture → implementation
implementation → debugging
debugging → review
review → next milestone
```

Every new session starts with this handoff:

```text
Milestone:
Current repo state:
Changed files:
Tests run:
Known failures:
Open architectural questions:
Next Codex ticket desired:
```

---

## Milestone 0 — Workspace and repository skeleton

**Goal:** create a clean Python project that Codex can work in safely.

Deliverables:

```text
pyproject.toml
AGENTS.md
ROADMAP.md
configs/default.yaml
src/fh_agent/__init__.py
src/fh_agent/cli.py
tests/test_import.py
```

Acceptance criteria:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -m fh_agent --help
```

Switch session when:
- project skeleton exists
- tests pass
- Codex can explain repo structure

Suggested Codex ticket:

```text
Create a Python 3.12 uv project skeleton for fh-agent with src layout, pytest, ruff, typer CLI, and a passing import test. Do not implement game automation yet.
```

---

## Milestone 1 — Game window, focus guard, and input executor

**Goal:** safely send primitive inputs only to the correct window.

Deliverables:

```text
src/fh_agent/game/window.py
src/fh_agent/game/focus_guard.py
src/fh_agent/game/input_executor.py
src/fh_agent/body/primitive_actions.py
tests/test_input_executor_safety.py
```

Primitive actions:

```text
move_up_short
move_down_short
move_left_short
move_right_short
confirm
cancel
open_menu
wait
```

Acceptance criteria:
- input calls are blocked if target window is not focused
- emergency stop flag exists
- primitive actions are rate-limited
- tests pass without launching the game

Switch session when:
- safe action executor is implemented and tested

---

## Milestone 2 — Screenshot capture and evidence logging

**Goal:** capture frames and store evidence without interpretation.

Deliverables:

```text
src/fh_agent/perception/screen_capture.py
src/fh_agent/memory/event_log.py
src/fh_agent/memory/evidence.py
configs/capture.yaml
runs/.gitkeep
screenshots/.gitkeep
```

Acceptance criteria:
- capture test saves N screenshots with timestamps and hashes
- JSONL event log records observations and actions
- no game logic or LLM is involved

Switch session when:
- screenshots and events can be captured/logged reproducibly

---

## Milestone 3 — Observation schema and No-Spoiler Firewall

**Goal:** define what the agent is allowed to know.

Deliverables:

```text
src/fh_agent/observation/schemas.py
src/fh_agent/bridge/firewall.py
configs/bridge_allowlist.yaml
tests/test_firewall_allowlist.py
tests/test_observation_schema.py
```

Required schemas:

```text
Observation
VisibleTextSpan
VisibleSprite
ActionResult
Event
SkillResult
KnowledgeFact
```

Acceptance criteria:
- forbidden fields are rejected
- allowed fields produce sanitized Observation objects
- every game-specific fact has evidence_id support

Switch session when:
- firewall tests pass

---

## Milestone 4 — MVP perception without LLM

**Goal:** translate screen/bridge data into Observation JSON.

Deliverables:

```text
src/fh_agent/perception/ui_state.py
src/fh_agent/perception/ocr.py
src/fh_agent/perception/visual_hash.py
src/fh_agent/observation/observation_builder.py
configs/crops.yaml
```

MVP fields:

```text
ui_state: field/dialogue/menu/combat/death/unknown
visible_text
screen_signature
last_action_result
```

Acceptance criteria:
- known screenshots are classified into UI states
- OCR results include confidence and evidence_id
- observation builder produces valid JSON

Switch session when:
- parser can process saved screenshots offline

---

## Milestone 5 — Body MVP without RL

**Goal:** execute simple universal skills with heuristics.

Deliverables:

```text
src/fh_agent/body/skills/continue_dialogue.py
src/fh_agent/body/skills/basic_reach_target.py
src/fh_agent/body/skills/interact_visible.py
src/fh_agent/manager/skill_contracts.py
src/fh_agent/manager/reward_computer.py
```

Acceptance criteria:
- skills have preconditions, timeout, success detector, failure detector
- skill results are logged
- no LLM and no RL yet

Switch session when:
- at least one skill can run against mock observations and pass tests

---

## Milestone 6 — SQLite memory core

**Goal:** store experience as reusable evidence.

Deliverables:

```text
src/fh_agent/memory/schema.sql
src/fh_agent/memory/db.py
src/fh_agent/memory/facts.py
src/fh_agent/memory/room_graph.py
src/fh_agent/memory/entity_risk.py
src/fh_agent/memory/skill_registry.py
src/fh_agent/memory/strategy_graph.py
```

Acceptance criteria:
- observations/actions/skill_results/facts are stored
- facts require evidence IDs
- entity risk can be updated from observed outcomes
- skill registry tracks success rates

Switch session when:
- DB schema and CRUD tests pass

---

## Milestone 7 — Visible-State Bridge prototype

**Goal:** optionally extract only visible RPG Maker MV metadata.

Deliverables:

```text
bridge/rmmv_visible_bridge.js
src/fh_agent/bridge/bridge_server.py
src/fh_agent/bridge/sanitizer.py
```

Allowed output only:

```text
visible_message_text
visible_menu_items
ui_state
player_screen_position
visible_sprite_screen_positions
visible_sprite_visual_hashes
screenshot_id
```

Acceptance criteria:
- forbidden fields cannot pass firewall
- bridge runs can be marked debug/official
- screenshot evidence is still stored

Switch session when:
- bridge produces sanitized Observation or is explicitly deferred

---

## Milestone 8 — Local LLM Cortex

**Goal:** planner chooses local goals and universal skills.

Deliverables:

```text
src/fh_agent/planner/llm_client.py
src/fh_agent/planner/cortex.py
src/fh_agent/planner/prompts/system_no_spoiler.md
src/fh_agent/planner/prompts/plan_next_goal.md
src/fh_agent/planner/prompts/post_mortem.md
```

Acceptance criteria:
- local model can be called through an OpenAI-compatible local endpoint
- planner outputs valid structured JSON
- planner never outputs direct key sequences as control plan
- planner cites evidence IDs for game-specific claims

Switch session when:
- planner can select a skill from mock memory and observations

---

## Milestone 9 — Manager and task scheduler

**Goal:** convert planner goals into executable Body tasks.

Deliverables:

```text
src/fh_agent/manager/task_manager.py
src/fh_agent/manager/scheduler.py
src/fh_agent/manager/task_spec.py
src/fh_agent/manager/reward_profiles.py
```

Acceptance criteria:
- task specs include target, constraints, rewards, timeout, stop conditions
- reward terms come from allowed library
- skill completion triggers Memory update

Switch session when:
- mock planner output can trigger mock skill execution and logging

---

## Milestone 10 — Safe navigation heuristic

**Goal:** implement `safe_reach_target` before RL.

Deliverables:

```text
src/fh_agent/body/skills/safe_reach_target.py
src/fh_agent/body/safety_filter.py
```

Acceptance criteria:
- target attraction + hazard repulsion works in synthetic tests
- high-risk actions are blocked by safety filter
- Body can report `blocked_by_high_risk_entity`

Switch session when:
- heuristic is testable and produces sensible paths in toy states

---

## Milestone 11 — RL wrapper and replay data

**Goal:** prepare learning but do not depend on it yet.

Deliverables:

```text
src/fh_agent/rl/gym_env.py
src/fh_agent/rl/replay_buffer.py
src/fh_agent/rl/her_relabel.py
src/fh_agent/rl/behavior_cloning.py
```

Acceptance criteria:
- Gymnasium wrapper exposes reset/step
- replay buffer stores obs/action/reward/next_obs/done/task
- HER relabeling can turn accidental goals into training data

Switch session when:
- RL wrapper works on synthetic/proxy tasks

---

## Milestone 12 — First controlled live run

**Goal:** run the system for a short controlled session.

Acceptance criteria:
- fixed resolution and window focus
- emergency stop verified
- actions and observations logged
- screenshots/evidence stored
- no hidden-state violation
- post-run report generated

Switch session when:
- first run report exists
- next architecture adjustment is needed

---

## Milestone 13 — Longer autonomous sessions

**Goal:** 30–60 minute exploration with memory reuse.

Metrics:

```text
unique room signatures
new visible texts/facts per hour
skill success rate
loop rate
time to death
repeated death cause reduction
no-spoiler violations
```

Switch session when:
- one complete long-run report is ready for review
