---
name: publish-milestone
description: Use when handing off a validated milestone through the required A2 branch, commit, push, and Draft PR workflow.
---

# Publish milestone

Never publish a normal milestone directly to `main`.

For A2: create the declared branch, validate, stage explicit intended files only, review staged diff, commit, push the branch, create a Draft PR, and do not merge. If Draft PR creation fails because of authentication or tooling, report `partial` or `blocked`; never fall back to a direct `main` push.

Record commit, PR, validation, scope checks, and residual risks in the Session Report.
