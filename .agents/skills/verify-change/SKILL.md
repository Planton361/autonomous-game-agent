---
name: verify-change
description: Use when selecting, running, and recording focused and standard validation for a GitHub Issue.
---

# Verify change

Use focused tests and static checks during ordinary Issue work. GitHub Actions owns the full standard suite. Run the full local suite only for a high-risk boundary, CI unavailability, global repair, CI-workflow change, phase exit, or explicit user request:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Also run Issue-specific targeted checks. Record commands and actual results in the Pull Request and handoff; do not make claims based on stale output. Classify any unchanged-baseline failure as `PRE-EXISTING BASELINE ISSUE`.
