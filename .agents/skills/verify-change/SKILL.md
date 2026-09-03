---
name: verify-change
description: Use when selecting, running, and recording focused and standard validation for a repository milestone.
---

# Verify change

Use focused tests during development where useful. Before normal milestone publication, run fresh:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Also run milestone-specific targeted checks. Record commands and actual results in the Session Report; do not make claims based on stale output. Classify any unchanged-baseline failure as `PRE-EXISTING BASELINE ISSUE`.
