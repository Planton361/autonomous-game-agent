---
name: publish-issue
description: Use when handing off a validated GitHub Issue through its branch, commit, push, Draft Pull Request, CI, and user-merge workflow.
---

# Publish issue

Never publish normal work directly to `main`.

Create the declared `codex/<issue-number>-<slug>` branch, run the required local checks, explicitly stage intended files only, review the staged diff, commit, push, and create a fully populated Draft Pull Request containing `Closes #<issue-number>`. Wait for full GitHub CI and review; only the user merges.

If push, Draft PR creation, or CI is unavailable, report `partial` or `blocked`; never fall back to a direct `main` push. Record the commit, PR, validation, scope checks, and residual risks in the Pull Request rather than a routine session report.
