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


def test_required_validate_timer_contains_setup_tests_hygiene_and_cli() -> None:
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
    assert sum(step.get("id") == "timer" for step in steps) == 1
    assert 'test "$elapsed_ms" -le 60000' in steps[-1]["run"]
