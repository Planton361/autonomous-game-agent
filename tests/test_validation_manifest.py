from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "fast-tests.txt"
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
    migration = workflow["jobs"]["research-map-migration"]
    assert migration["name"] == "research-map-migration"
    assert "needs" not in migration and "strategy" not in migration
    migration_steps = migration["steps"]
    migration_names = [step["name"] for step in migration_steps]
    assert migration_names[0] == "Start migration validation timer"
    assert migration_names[-1] == "Report migration validation duration"
    sync = migration_names.index("Sync locked dependencies")
    acceptance = migration_names.index("Final Research Map migration acceptance")
    assert 0 < sync < acceptance < len(migration_steps) - 1
    assert migration_steps[acceptance]["run"] == (
        "uv run --no-sync pytest -n 2 tests/test_final_research_map.py"
    )
    for timed_job in (job, migration):
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
