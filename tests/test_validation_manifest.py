from pathlib import Path

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
