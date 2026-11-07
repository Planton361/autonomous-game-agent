# Validation tiers

The required `validate` workflow is the only automatic standard validation gate. It runs
on Pull Requests and pushes to `main`. It performs the diff/whitespace check, Ruff lint,
Ruff formatting check, the CLI smoke command, and the deterministic contract/safety
tests listed in [`fast-tests.txt`](fast-tests.txt). The workflow rejects an empty or
invalid manifest, and `tests/test_validation_manifest.py` protects the required
core-contract entries.

The [Program Owner decision recorded in PR #160 comment 6045191818](https://github.com/Planton361/autonomous-game-agent/pull/160#issuecomment-6045191818)
supersedes the historical 60,000 ms target from #80. Both automatic jobs in
`validate.yml`, `validate` and `research-map-migration`, now enforce
`<= 120000 ms`, including setup and their complete existing validation steps.
Both fail if that measured interval exceeds the budget; their five-minute job
timeouts remain unchanged. This is an operational budget amendment, not a runtime
optimization. Timer scope, required coverage, two concurrent serial whole-file
shards and manual-only `validate-full` remain unchanged. The migration job's former
single two-worker run is superseded by the parallel shards described in
[Research Map migration shards](#research-map-migration-shards).

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
the required `validate` workflow's enforced `<= 120000 ms` budget.

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
used by required `validate`; only the Research Map migration shards use it (`-n 2`). The complete suite and `validate-full` remain serial.
The validation timer start/end remain unchanged; the enforced gate is `<= 120000 ms`.

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

## Research Map migration shards

The [Program Owner approval of option (a)](https://github.com/Planton361/autonomous-game-agent/issues/180#issuecomment-6707910045)
(Issue #180-A), based on the
[CI diagnostic](https://github.com/Planton361/autonomous-game-agent/pull/181#issuecomment-6700711640),
splits `tests/test_final_research_map.py` across parallel GitHub Actions jobs. One
runner measured ~400–440 s of worker time with a 69 s critical-path test, and
four workers on one runner did not scale. No test is removed or relaxed.

- [`research-map-shards.txt`](research-map-shards.txt) is a static partition of
  exact pytest node IDs: `<shard> <node ID>`, split at the first space because
  parametrized IDs may contain spaces. Within a shard, the longest tests come first.
  The first `2 * c` IDs (`c = max(2, n // 2 // 4)`, pytest-xdist's initial contiguous
  per-worker chunk under `-n 2`) alternate into two duration-balanced starting
  chunks. Otherwise one worker would receive every large test at once.
- `research-map-migration-shard` is a matrix job (`fail-fast: false`) with one
  runner per shard. Each shard keeps its own timer as the first step, the existing
  setup, and the unchanged `<= 120000 ms` gate as the last step, with the
  five-minute timeout.
- Before pytest, **Verify Research Map shard coverage** collects the module's
  node IDs and fails closed unless the manifest assigns every collected ID exactly
  once. The check also rejects unknown or duplicate IDs, malformed rows and IDs
  from another module, and requires the declared shards to be exactly
  `0..strategy.job-total-1`, so no shard can be left without a runner. The shard then runs only its
  own IDs with `uv run --no-sync pytest -n 2 --durations=20 "${node_ids[@]}"`;
  `--durations=20` is permanent per-shard observability for rebalancing.
- `research-map-migration` keeps the previous check name as an aggregator
  (`needs` the shard job, `if: always()`). It succeeds only when the shard job
  result is `success`, so any failed, cancelled or skipped shard turns it red.
- `tests/test_validation_manifest.py` pins this structure. It runs the
  workflow's own coverage script against the real collection (208 IDs) and
  against synthetic manifests for missing, duplicate, unknown, malformed,
  foreign-module, gap, beyond-matrix and empty-shard cases.

Rebalancing: when tests are added, removed or renamed, the coverage check fails until
the manifest is updated. Rebalance with the latest per-shard `--durations=20` CI
output. Changing the shard count requires updating the matrix, the manifest and
`SHARD_IDS` in the manifest test together. The repository ruleset, which requires
only `validate`, is unchanged.

## Bounded reuse in projection acceptance tests

Issue #150 retained the required manifest, timing scope and then-current 60,000 ms
gate; only that budget is superseded by the Program Owner decision above.
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

The shared zero-write helper `filesystem_state` in `tests/test_research_wiki_projection.py`
uses one followed `os.stat` per path over an `os.scandir` traversal instead of repeated
pathlib `stat`/`is_dir`/`is_file` calls (Issue #180). It records the same root-inclusive
relative keys, inode, `mtime_ns`, directory flag and file bytes, lists but does not enter
symlinked directories, and keeps the original broken-symlink and unreadable-directory
behaviour. It caches nothing. `tests/test_filesystem_state_oracle.py` keeps the original
pathlib helper verbatim as an oracle and requires identical snapshots and identical change
detection on synthetic trees.

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
