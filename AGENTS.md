# AGENTS.md — Fear & Hunger Autonomous Agent

## Project identity

This repository builds a local, no-spoiler, hierarchical agent for **Fear & Hunger**. The agent must learn from its own observed evidence, not from external game guides, hidden engine state, map files, enemy databases, savegame inspection, or wiki knowledge.

The intended architecture is:

```text
GameInstance
→ Screen Capture and/or Visible-State Bridge
→ No-Spoiler Firewall
→ Observation Router
→ Memory: Evidence, RoomGraph, EntityRisk, SkillRegistry, StrategyGraph
→ Cortex: local LLM planner
→ Manager: task, reward, timeout, success/failure contracts
→ Body: primitive key actions, heuristics, later goal-conditioned RL
→ InputExecutor
→ GameInstance
```

## Hard rules

1. **No hidden-state usage in official runs.** Do not read or expose RPG Maker map JSON, event names, event comments, trigger conditions, `$gameSwitches`, `$gameVariables`, enemy HP, enemy database entries, item database effects, ending flags, savegame internals, or RAM-derived hidden game state.
2. **Use only visible evidence.** Game-specific claims require evidence IDs from screenshots, visible text, sanitized bridge observations, or observed outcomes.
3. **The LLM is not the joystick.** The planner may choose goals, skills, constraints, and hypotheses. It must not directly output low-level key sequences as its main control mechanism.
4. **The Body is universal.** Do not create hardcoded skills like `kill_guard_x`, `solve_room_y`, or `use_item_for_ending_z`. Skills must be reusable: `safe_reach_target`, `interact_visible_object`, `continue_dialogue`, `retreat_from_hazard`, `wait_for_safe_gap`, `menu_select_visible_option`.
5. **Every action must be logged.** Observations, actions, skill results, rewards, screenshots, and evidence links must be persisted.
6. **Do not add large architectural dependencies without documenting why.** Prefer small modules, typed schemas, tests, and clear boundaries.
7. **Never run automation against the wrong window.** Input code must include focus checks, rate limits, and an emergency stop.

## Development environment

Preferred stack:

```text
Python 3.12
uv for dependency/project management
VS Code or Cursor with the Codex IDE extension
Git + GitHub
pytest + ruff
pydantic for schemas
SQLite + JSONL for storage
mss/OpenCV/PaddleOCR/PyAutoGUI for MVP perception/control
llama.cpp/Ollama for local gpt-oss-20b later
Gymnasium + Stable-Baselines3 later for RL skills
```

Basic commands should eventually work:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run python -m fh_agent --help
```

## Code style

- Use typed Python.
- Prefer Pydantic models for every cross-module data object.
- Keep pure logic testable without launching the game.
- Keep side effects isolated in `game/`, `bridge/`, `perception/`, and `control/`.
- Do not mix planner logic with input execution.
- Do not let Memory depend on the LLM.
- Do not let Body depend on raw RPG Maker internals.

## Module boundaries

### `game/`
Launch, focus, and window lifecycle. No strategy logic.

### `bridge/`
Visible-State Bridge integration and firewall. Must enforce allowlist. Any hidden-state field must be blocked and logged as a violation if attempted.

### `perception/`
Screen capture, OCR, visual hashes, UI-state classification, optional entity/frontier detection. Perception may produce uncertain observations with confidence scores.

### `observation/`
Canonical observation schemas and event routing.

### `memory/`
SQLite schema, evidence store, room graph, entity risk, strategy graph, skill history. Game claims need evidence IDs.

### `planner/`
Local LLM client and prompts. Planner outputs structured JSON only.

### `manager/`
Converts planner goals into task specs, reward profiles, stop conditions, and skill contracts.

### `body/`
Primitive actions, deterministic skills, safety filter, learned policies. Body outputs only primitive game inputs.

### `rl/`
Gymnasium wrappers, replay buffers, behavior cloning, PPO/DQN experiments, HER relabeling.

## No-spoiler firewall policy

Allowed bridge fields:

```yaml
allowed:
  message_window_visible: true
  visible_message_text: true
  menu_open: true
  visible_menu_items: true
  combat_ui_visible: true
  death_screen_visible: true
  player_screen_position: true
  visible_sprite_screen_positions: true
  visible_sprite_visual_hashes: true
  screenshot_id: true
```

Forbidden fields:

```yaml
forbidden:
  map_id: true
  event_id: true
  event_name: true
  event_comments: true
  event_trigger_conditions: true
  game_switches: true
  game_variables: true
  enemy_database: true
  enemy_hp: true
  item_database_effects: true
  ending_flags: true
  savegame_variables: true
```

## Planner output contract

The planner must output JSON similar to:

```json
{
  "current_belief_state": [],
  "open_questions": [],
  "next_goal": "Reach the visible unexplored exit while avoiding high-risk entities.",
  "selected_skill": "safe_reach_target",
  "success_condition": ["screen_transition"],
  "risk_limit": {"avoid_known_dangers": true, "max_danger_score": 0.4},
  "memory_updates_requested": []
}
```

## Body rules

Primitive action set:

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

The Body may learn goal-conditioned policies. It must not learn game-specific quest actions. Rewards must come from Manager/RewardComputer using allowed reward terms.

## Testing expectations

For every task, add or update tests where possible. Minimum early tests:

```text
test_observation_schema.py
test_firewall_allowlist.py
test_event_log.py
test_reward_computer.py
test_skill_contracts.py
test_input_executor_safety.py
```

## Codex workflow

When working as a coding agent:

1. Inspect relevant files first.
2. State a concise implementation plan.
3. Make the smallest coherent change.
4. Add tests or smoke tests.
5. Run `uv run pytest` and `uv run ruff check .` if available.
6. Summarize changed files, validation results, and next recommended task.
7. Do not perform broad rewrites without explicit instruction.
8. Do not run the game or send inputs unless the user explicitly asks.

## Current milestone discipline

Only work on the active Roadmap milestone unless explicitly told otherwise. If a task reveals that the architecture needs to change, stop and ask for an architectural review rather than silently changing the design.
