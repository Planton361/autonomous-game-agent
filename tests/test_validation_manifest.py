import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "fast-tests.txt"
RESEARCH_MAP_SHARDS = ROOT / ".github" / "research-map-shards.txt"
MODULE = "tests/test_final_research_map.py"
SHARD_IDS = ["0", "1", "2", "3"]
REQUIRED_FAST_TESTS = {
    "tests/test_bridge_sanitizer.py",
    "tests/test_emergency_stop.py",
    "tests/test_firewall_allowlist.py",
    "tests/test_import.py",
    "tests/test_input_executor_safety.py",
    "tests/test_planner_output.py",
    "tests/test_project_control_contract.py",
    "tests/test_run_mode_manifest_alignment.py",
    "tests/test_safety_filter.py",
    "tests/test_task_manager.py",
    "tests/test_task_spec.py",
    "tests/test_validation_manifest.py",
    "tests/test_verifier_schemas.py",
}


def _manifest_paths() -> list[str]:
    return [
        line.strip()
        for line in MANIFEST.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_fast_manifest_is_non_empty_unique_and_points_to_tests() -> None:
    paths = _manifest_paths()

    assert paths
    assert len(paths) == len(set(paths))
    assert all(path.startswith("tests/test_") and path.endswith(".py") for path in paths)
    assert all((ROOT / path).is_file() for path in paths)


def test_fast_manifest_protects_critical_contract_coverage() -> None:
    assert REQUIRED_FAST_TESTS <= set(_manifest_paths())


def test_required_shards_are_a_complete_disjoint_two_way_partition() -> None:
    shards = {"0": [], "1": []}
    for line in (ROOT / ".github/fast-test-shards.txt").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        shard, path = line.split()
        assert shard in shards
        shards[shard].append(path)
    assigned = shards["0"] + shards["1"]
    assert all(shards.values())
    assert len(assigned) == len(set(assigned))
    assert set(assigned) == set(_manifest_paths())


def test_required_workflow_timers_contain_setup_tests_hygiene_and_cli() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text())
    job = workflow["jobs"]["validate"]
    assert job["name"] == "validate"
    assert "needs" not in job and "strategy" not in job
    steps = job["steps"]
    names = [step["name"] for step in steps]
    assert names[0] == "Start validation timer"
    assert names[-1] == "Report validation duration"
    required = [
        "Sync locked dependencies",
        "Check pull request diff whitespace",
        "Lint",
        "Check formatting",
        "Fast contract tests",
        "CLI smoke",
    ]
    positions = [names.index(name) for name in required]
    assert positions == sorted(positions)
    assert all(0 < position < len(steps) - 1 for position in positions)
    shard_job = workflow["jobs"]["research-map-migration-shard"]
    assert "needs" not in shard_job
    assert shard_job["strategy"]["fail-fast"] is False
    assert shard_job["strategy"]["matrix"] == {"shard": SHARD_IDS}
    shard_steps = shard_job["steps"]
    shard_names = [step["name"] for step in shard_steps]
    assert shard_names[0] == "Start migration validation timer"
    assert shard_names[-1] == "Report migration validation duration"
    sync = shard_names.index("Sync locked dependencies")
    coverage = shard_names.index("Verify Research Map shard coverage")
    acceptance = shard_names.index("Final Research Map migration acceptance")
    assert 0 < sync < coverage < acceptance < len(shard_steps) - 1
    assert shard_steps[coverage]["env"]["SHARD"] == "${{ matrix.shard }}"
    assert shard_steps[coverage]["env"]["SHARD_TOTAL"] == "${{ strategy.job-total }}"
    assert (
        'mapfile -t node_ids < "$RUNNER_TEMP/research-map-shard-node-ids.txt"'
        in (shard_steps[acceptance]["run"])
    )
    assert (
        'uv run --no-sync pytest -n 2 --durations=20 "${node_ids[@]}"'
        in (shard_steps[acceptance]["run"])
    )
    assert "env" not in shard_steps[acceptance]
    for timed_job in (job, shard_job):
        assert timed_job["timeout-minutes"] == 5
        assert not timed_job.get("continue-on-error", False)
        timed_steps = timed_job["steps"]
        assert sum(step.get("id") == "timer" for step in timed_steps) == 1
        assert "started_ns=$(date +%s%N)" in timed_steps[0]["run"]
        report = timed_steps[-1]
        assert report["env"]["STARTED_NS"] == "${{ steps.timer.outputs.started_ns }}"
        assert "set -euo pipefail" in report["run"]
        assert "elapsed_ms=$(( (finished_ns - STARTED_NS) / 1000000 ))" in report["run"]
        assert "- Budget: `<= 120000 ms`" in report["run"]
        assert 'test "$elapsed_ms" -le 120000' in report["run"]
        assert not report.get("continue-on-error", False)
    aggregator = workflow["jobs"]["research-map-migration"]
    assert aggregator["name"] == "research-map-migration"
    assert aggregator["needs"] == "research-map-migration-shard"
    assert aggregator["if"] == "${{ always() }}"
    assert not aggregator.get("continue-on-error", False)
    (gate,) = aggregator["steps"]
    assert gate["env"]["SHARD_RESULT"] == "${{ needs.research-map-migration-shard.result }}"
    assert 'test "$SHARD_RESULT" = "success"' in gate["run"]


def _shard_coverage_script() -> str:
    workflow = yaml.safe_load((ROOT / ".github/workflows/validate.yml").read_text())
    steps = workflow["jobs"]["research-map-migration-shard"]["steps"]
    run = next(s for s in steps if s["name"] == "Verify Research Map shard coverage")["run"]
    return run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def _run_shard_coverage(
    manifest: Path, shard: str, collected: Path | None = None, total: int = len(SHARD_IDS)
):
    args = [str(manifest), shard, str(total)]
    args += [str(collected)] if collected is not None else []
    return subprocess.run(
        [sys.executable, "-", *args],
        input=_shard_coverage_script(),
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_research_map_shards_exactly_partition_collected_node_ids(tmp_path) -> None:
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", MODULE],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    node_ids = [line for line in collected.splitlines() if line.startswith(MODULE + "::")]
    collected_file = tmp_path / "collected.txt"
    collected_file.write_text("\n".join(node_ids) + "\n")
    owned = {}
    for shard in SHARD_IDS:
        result = _run_shard_coverage(RESEARCH_MAP_SHARDS, shard, collected_file)
        assert result.returncode == 0, result.stderr
        owned[shard] = result.stdout.splitlines()
        assert owned[shard]
    assigned = [node_id for ids in owned.values() for node_id in ids]
    assert len(assigned) == len(set(assigned)) == len(node_ids) == 208
    assert set(assigned) == set(node_ids)
    # The CI path collects node IDs itself; it must agree with the precomputed list.
    live = _run_shard_coverage(RESEARCH_MAP_SHARDS, SHARD_IDS[0])
    assert live.returncode == 0, live.stderr
    assert live.stdout.splitlines() == owned[SHARD_IDS[0]]


SYNTHETIC_IDS = [f"{MODULE}::test_{name}" for name in ("a", "b", "c[with space]")]
VALID_ROWS = ["0 " + SYNTHETIC_IDS[0], "1 " + SYNTHETIC_IDS[1], "1 " + SYNTHETIC_IDS[2]]


@pytest.mark.parametrize(
    ("rows", "shard", "message"),
    [
        (VALID_ROWS[:2], "0", "missing="),
        ([*VALID_ROWS, VALID_ROWS[0]], "0", "Duplicate shard node ID"),
        ([*VALID_ROWS, f"1 {MODULE}::test_unknown"], "0", "unknown="),
        (VALID_ROWS, "2", "without gaps"),
        ([VALID_ROWS[0], "2 " + SYNTHETIC_IDS[1], "2 " + SYNTHETIC_IDS[2]], "0", "without gaps"),
        ([*VALID_ROWS[:2], "3 " + SYNTHETIC_IDS[2]], "0", "without gaps"),
        ([*VALID_ROWS[:2], "x " + SYNTHETIC_IDS[2]], "0", "Invalid shard mapping"),
        ([*VALID_ROWS[:2], "1 tests/test_other.py::test_c"], "0", "Invalid shard mapping"),
    ],
    ids=[
        "missing",
        "duplicate",
        "unknown",
        "empty-shard",
        "gap",
        "beyond-matrix",
        "bad-shard",
        "foreign-module",
    ],
)
def test_research_map_shard_coverage_fails_closed(tmp_path, rows, shard, message) -> None:
    manifest = tmp_path / "shards.txt"
    manifest.write_text("# synthetic\n" + "\n".join(rows) + "\n")
    collected = tmp_path / "collected.txt"
    collected.write_text("\n".join(SYNTHETIC_IDS) + "\n")
    result = _run_shard_coverage(manifest, shard, collected, total=3)
    assert result.returncode != 0
    assert message in result.stderr
    assert result.stdout == ""


def test_research_map_shard_coverage_accepts_exact_synthetic_partition(tmp_path) -> None:
    manifest = tmp_path / "shards.txt"
    manifest.write_text("\n".join(VALID_ROWS) + "\n")
    collected = tmp_path / "collected.txt"
    collected.write_text("\n".join(SYNTHETIC_IDS) + "\n")
    result = _run_shard_coverage(manifest, "1", collected, total=2)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == SYNTHETIC_IDS[1:]
