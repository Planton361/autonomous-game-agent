# CODEX_FIRST_TICKETS.md

## Ticket 1 – Repo-Grundstruktur

Prompt für Codex:

```text
Lies AGENTS.md und ROADMAP.md. Implementiere Phase 0: Lege ein uv-basiertes Python-Projekt an, erstelle src/fh_agent mit Unterpaketen game, perception, observation, memory, manager, body, planner, rl, evals. Füge pyproject.toml mit pytest, ruff und pydantic hinzu. Erstelle einen Smoke-Test, der importiert, dass das Paket existiert. Keine Spielautomation implementieren.
```

Akzeptanz:

```bash
uv sync
uv run pytest
uv run ruff check
uv run ruff format --check
```

## Ticket 2 – Basisschemas

```text
Implementiere Pydantic-Schemas für Observation, Event, ActionRecord, SkillTask, SkillResult, KnowledgeFact. Tests: Fact ohne evidence_id muss invalid sein; Observation muss in JSON serialisierbar sein.
```

## Ticket 3 – Eventlog

```text
Implementiere JSONL EventLogger. Jede Observation, Action und SkillResult kann geschrieben und wieder gelesen werden. Tests mit temporärem Run-Ordner.
```

## Ticket 4 – InputExecutor-Interface

```text
Implementiere ein InputExecutor-Interface und eine DryRunInputExecutor-Implementierung. Noch keine echten Tastendrücke. Primitive Aktionen: move_up_short, move_down_short, move_left_short, move_right_short, confirm, cancel, open_menu, wait.
```

## Ticket 5 – Capture-Interface

```text
Implementiere ein ScreenCapture-Interface und eine DummyCapture-Implementierung für Tests. Echte MSS-Implementierung nur als optionaler Adapter, der noch nicht in Tests benötigt wird.
```
