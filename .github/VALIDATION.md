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
watcher tests.

The exhaustive job has a 45-minute timeout. Issue #152's restored serial suite
passed locally but reached the Zotero lifecycle module at approximately 73% on
GitHub before the former 30-minute job timeout canceled it. This timeout gives
the complete serial suite time to finish; it does not change test selection or
the required `validate` workflow's enforced `<= 60000 ms` budget.

Locally, the full suite remains:

```bash
uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
uv run --no-sync fh-agent --help
```

## Required static file shards

[`fast-tests.txt`](fast-tests.txt) remains the authoritative required-module set.
[`fast-test-shards.txt`](fast-test-shards.txt) is a complete, disjoint static
whole-file partition of that manifest. Before pytest starts, the workflow validates
that both shards are non-empty, manifest entries and assignments are unique, the
assigned set exactly equals the manifest, and every assigned path is an existing
`tests/test_*.py` file.

Exactly two concurrent pytest processes are launched. Each shard runs serial
pytest with `--maxfail=1`; no test file is split between processes. This preserves
module-scoped fixtures and in-process reuse without sharing reuse dictionaries
or introducing a persistent cache. Both subprocess statuses are collected and
both logs are printed. Any non-zero shard exit makes the required test step fail.

`pytest-xdist` remains installed and locked, but it is no longer the scheduler
used by required `validate`. The complete suite and `validate-full` remain serial.
The validation timer start/end and enforced `<= 60000 ms` gate remain unchanged.

From the repository root, reproduce the current required test step by executing
its committed workflow script. This uses the same manifest validation, static
mapping, concurrent serial processes and combined failure propagation as CI:

```bash
uv sync --locked
uv run --no-sync python - <<'PY'
from pathlib import Path
import subprocess
import yaml

workflow = yaml.safe_load(Path(".github/workflows/validate.yml").read_text())
step = next(
    step for step in workflow["jobs"]["validate"]["steps"]
    if step["name"] == "Fast contract tests"
)
raise SystemExit(subprocess.run(["bash", "-c", step["run"]]).returncode)
PY
```

This reproduces the required test step locally; hosted setup and the enforced
job timer remain in GitHub Actions. The static checks and CLI smoke remain
separate required workflow steps.

Issue #80 baseline profiling on `main` `1bd84d360a1df741bac7e32083a526156a849422`
collected 2,555 tracked tests in 0.53s and completed them in 423.94s (`real 424.31s`). The
slowest families were research-wiki views/projection/reference-index CLI and related
filesystem-heavy regeneration tests. Post-change local evidence is 898 fast-tier tests
passed in 11.41s (`real 16.31s`) and 2,557 tracked tests passed in 422.47s (`real
427.23s`).

## Bounded reuse in projection acceptance tests

Issue #150 retains the required manifest, timing scope and 60,000 ms gate.
The module-scoped `cached_full_projections` fixture also reuses identical pure
YAML parsing/serialization within that module. `tests/yaml_test_cache.py` keys
parsing by complete text/bytes, input type, supported loader identity and its
constructor/resolver configuration. Serialization keys include typed values,
order/alias structure, every option and the SafeDumper configuration. Parsed
containers are deep-copied, while serialized text is immutable. Unsupported
loaders, streams and unkeyable inputs run the original implementation; failures
are never stored. Production code has no test-cache branch.

Filesystem reads, existing Registry validation coverage, workspace stages,
edited/unowned rejection and zero-write comparisons remain live. Reordered and mutated inputs
miss the reuse key. Independent real-parser oracles and eight required cases
verify these properties. Reuse dictionaries expire at module teardown. They store pure YAML inputs and
results, never filesystem inspections or Vault state.

The RQ lifecycle constructs its historical direct-view fixture on the already
projected technical setup, avoiding an unchanged preparatory workspace apply.
The migration still uses real workspace apply and verifies its restore point
and completed stages. It also avoids a standalone check immediately after apply,
which already executes both real projector checks. It asserts the returned
completed stages and retains a later real standalone check after a body-only
edit, now with whole-Vault byte equality and exact source/stage assertions.
Migration, authored preservation and all rejection cases remain required.

For repeatable diagnosis, set `PYTEST_ADDOPTS=--durations=50` when running the
reproduction procedure above so both shards report durations, then run the
lifecycle-heavy modules separately:

```bash
uv run pytest tests/test_rq_reader.py tests/test_research_steering.py tests/test_knowledge_graph.py --durations=50
```

Compare setup/call/teardown and collection costs separately. Instrumentation such
as `cProfile` is useful for invocation counts and attribution, but its inflated
runtime is not an acceptance timing measurement. Host variance does not excuse
a red timing gate or authorize moving coverage out of the required tier.

## Projection path-safety phases

Projection readers inspect the physical owned root and all existing descendants
before reading generated content. During the subsequent read-only phase, each
untrusted relative path still passes lexical normalization/traversal validation,
without repeating ancestor symlink scans and resolution for every read. Manifest
entry, UTF-8, ownership, history, drift and output-parent collision checks remain
live. Standalone prior-manifest validation performs its own tree inspection.

No symlink/resolve result is cached across a mutation. Deletes, including failed
temporary-file cleanup, use live target validation immediately before unlink.
Atomic writes retain live validation before
creating their temporary output and again immediately before replace. The required
fast tier includes adversarial parent/target symlink changes after preflight and
after the temporary write; the full serial suite retains the technical projection,
direct-view and workspace-harness safety families. Timer, tier and dependency
semantics are unchanged.
