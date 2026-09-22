# Validation tiers

The required `validate` workflow is the only automatic standard validation gate. It runs
on Pull Requests and pushes to `main`. It performs the diff/whitespace check, Ruff lint,
Ruff formatting check, the CLI smoke command, and the deterministic contract/safety
tests listed in [`fast-tests.txt`](fast-tests.txt). The workflow rejects an empty or
invalid manifest, and `tests/test_validation_manifest.py` protects the required
core-contract entries.

The fast tier proves that the merge candidate satisfies the repository hygiene checks,
CLI import surface, and selected high-signal safety, no-spoiler, Manager/Cortex/Body
boundary, evidence, verifier, and project-control contracts. It does not claim that the
exhaustive fixture-heavy suite ran.

The separate `validate-full` workflow preserves exhaustive validation and runs only by
manual dispatch. Invoke it for high-risk boundaries, CI or test-infrastructure changes
that need exhaustive evidence, phase exits, global repairs, or explicit CONTROL / Program
Owner requests. It runs the complete `pytest` suite, Ruff checks, the diff check, and
CLI smoke. It retains Node setup because the complete suite includes the Node-backed
watcher tests. Locally, the full suite remains:

```bash
uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
uv run --no-sync fh-agent --help
```

The fast test selection can be run locally with:

```bash
uv run --no-sync pytest --maxfail=1 $(sed "/^[[:space:]]*#/d; /^[[:space:]]*$/d" .github/fast-tests.txt)
```

Issue #80 baseline profiling on `main` `1bd84d360a1df741bac7e32083a526156a849422`
collected 2,555 tracked tests in 0.53s and completed them in 423.94s (`real 424.31s`). The
slowest families were research-wiki views/projection/reference-index CLI and related
filesystem-heavy regeneration tests. Post-change local evidence is 898 fast-tier tests
passed in 11.41s (`real 16.31s`) and 2,557 tracked tests passed in 422.47s (`real
427.23s`).
