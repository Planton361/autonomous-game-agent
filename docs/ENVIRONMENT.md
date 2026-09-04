# Environment

`last_verified`: Historical pre-cutover M-000R evidence is retained below. Current validation
evidence is recorded in Pull Requests and GitHub Actions.

| Item | Repository state |
| --- | --- |
| Python | >=3.12 |
| Dependency manager | uv |
| Lockfile | `uv.lock` |
| Build backend | hatchling |
| Tests | pytest |
| Lint / format | Ruff |
| Typechecker | not currently configured |
| CI | `validate` on Pull Requests and pushes to `main` |
| Containerization | not currently configured |

## Setup

```bash
uv sync --locked
```

## CLI smoke

```bash
uv run fh-agent --help
```

## Full local validation exceptions

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Use focused tests and static checks locally for ordinary GitHub Issue work. GitHub Actions owns
the full standard suite. Run the full local validation above only for a high-risk boundary, CI
unavailability, global repair, CI-workflow change, phase exit, or explicit user request.
`.env` is ignored; generated `runs/`, `screenshots/`, database, and log artifacts follow the
existing `.gitignore`.

Do not launch a game or send input without explicit user authorization. Live runtime has platform-specific components; do not claim broad platform portability that has not been tested.
