# Environment

`last_verified`: 2026-09-03 — fresh M-000R validation passed: 1210 pytest tests, Ruff check, Ruff format check, `git diff --check`, and `uv run fh-agent --help`.

| Item | Repository state |
| --- | --- |
| Python | >=3.12 |
| Dependency manager | uv |
| Lockfile | `uv.lock` |
| Build backend | hatchling |
| Tests | pytest |
| Lint / format | Ruff |
| Typechecker | not currently configured |
| CI | not currently configured in repository |
| Containerization | not currently configured |

## Setup

```bash
uv sync --frozen
```

## CLI smoke

```bash
uv run fh-agent --help
```

## Standard publish verification

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Focused tests may run during implementation. The standard project validation above is still required before milestone publication unless a future explicit project decision changes it. `.env` is ignored; generated `runs/`, `screenshots/`, database, and log artifacts follow the existing `.gitignore`.

Do not launch a game or send input without explicit user authorization. Live runtime has platform-specific components; do not claim broad platform portability that has not been tested.
