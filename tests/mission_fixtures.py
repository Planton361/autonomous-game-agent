"""Shared offline MRIC-S0 fixtures (Issue #184): manifests, ledgers, contracts, fault hooks.

Everything here uses the exact production ``DryRunInputBackend``. Fault hooks only raise
at named ``FaultPoint`` values and never receive an input backend or executor.
"""

import hashlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fh_agent.game.authorized_input_gateway import AuthorizedInputGateway
from fh_agent.game.focus_guard import FakeFocusGuard
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.game.window import WindowTarget
from fh_agent.manager.action_authority import ManagerActionAuthority, ManagerContractV1
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_contracts import SkillContract
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.mission.ledger import MissionLedger
from fh_agent.mission.manifest import S0_NOT_APPLICABLE_BUDGETS, MissionManifestV1
from fh_agent.mission.state import FaultPoint

RUN_ID = "mission-s0-test-0001"
SKILL = "interact_visible_object"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def manifest_data(run_id: str = RUN_ID, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": "1",
        "mission_run_id": run_id,
        "created_at": "2026-11-11T00:00:00+00:00",
        "run_mode": "bridge-assisted",
        "execution_class": "debug-replay",
        "source": {"commit": "d32904a", "branch": "test", "dirty": False, "diff_sha256": None},
        "cortex": {
            "provider": "fake",
            "endpoint_identity": "http://127.0.0.1:8080",
            "model_revision": "fake-1",
            "model_digest": None,
            "prompt_bundle_sha256": digest("prompts"),
            "inference_params_sha256": digest("inference"),
        },
        "body": {
            "controller_version": "heuristic-1",
            "weights_digest": None,
            "skill_registry_sha256": digest("skills"),
        },
        "policy_hashes": {
            name: digest(name)
            for name in ("manager", "verifier", "safety_filter", "input_executor", "no_spoiler")
        },
        "budgets": {
            "max_action_attempts": 10,
            "max_action_attempts_per_episode": 6,
            "max_contracts": 5,
            "max_life_episodes": 3,
            "not_applicable_in_s0": list(S0_NOT_APPLICABLE_BUDGETS),
        },
        "network_isolation_proof_ref": None,
        "restart_policy_id": "restart-policy-s0",
        "termination_criteria_id": "termination-s0",
    }
    for dotted, value in overrides.items():
        target = data
        *parents, leaf = dotted.split("__")
        for parent in parents:
            target = target[parent]
        target[leaf] = value
    return data


def make_manifest(run_id: str = RUN_ID, **overrides: Any) -> MissionManifestV1:
    return MissionManifestV1.model_validate(manifest_data(run_id, **overrides))


class FakeClock:
    def __init__(self, start: float = 1_800_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SimulatedCrash(BaseException):
    """Stands in for process death; deliberately not an ``Exception``."""


class FaultHook:
    """Raise at selected fault points; record every point reached. Has no input capability."""

    def __init__(self) -> None:
        self.reached: list[FaultPoint] = []
        self._faults: dict[FaultPoint, BaseException] = {}

    def fail(self, point: FaultPoint, error: BaseException | None = None) -> None:
        self._faults[point] = error or sqlite3.OperationalError("disk I/O error (injected)")

    def crash(self, point: FaultPoint) -> None:
        self._faults[point] = SimulatedCrash(point.value)

    def clear(self) -> None:
        self._faults.clear()

    def __call__(self, point: FaultPoint) -> None:
        self.reached.append(point)
        error = self._faults.get(point)
        if error is not None:
            raise error


def new_ledger(
    runs_root: Path,
    *,
    run_id: str = RUN_ID,
    clock: FakeClock | None = None,
    fault_hook: FaultHook | None = None,
    open_episode: bool = True,
    **overrides: Any,
) -> MissionLedger:
    ledger = MissionLedger.create_new_mission(
        runs_root,
        make_manifest(run_id, **overrides),
        clock=clock or FakeClock(),
        fault_hook=fault_hook,
    )
    if open_episode:
        ledger.open_episode()
    return ledger


def resume(
    runs_root: Path,
    *,
    run_id: str = RUN_ID,
    clock: FakeClock | None = None,
    fault_hook: FaultHook | None = None,
    **overrides: Any,
) -> MissionLedger:
    return MissionLedger.resume_existing_mission(
        runs_root,
        run_id,
        make_manifest(run_id, **overrides),
        clock=clock or FakeClock(),
        fault_hook=fault_hook,
    )


def dry_run_executor(*, focused: bool = True, stop_file: Path | None = None) -> InputExecutor:
    from fh_agent.game.emergency_stop import StopFileEmergencyStopCheck

    return InputExecutor(
        target=WindowTarget(title="mission-s0-test (no game window)"),
        focus_guard=FakeFocusGuard(focused=focused),
        backend=DryRunInputBackend(),
        min_interval_seconds=0.0,
        emergency_stop_check=None if stop_file is None else StopFileEmergencyStopCheck(stop_file),
    )


def skill_contract(name: str = SKILL) -> SkillContract:
    return SkillCatalog.default().get(name, task=None).contract  # type: ignore[arg-type]


def task_spec(task_id: str = "task-1", *, timeout_steps: int = 4) -> TaskSpec:
    contract = skill_contract()
    return TaskSpec(
        task_id=task_id,
        selected_skill=SKILL,
        goal="interact with the visible object",
        timeout_steps=timeout_steps,
        reward_profile=contract.reward_profile,
    )


def open_contract(authority: ManagerActionAuthority, task_id: str = "task-1") -> ManagerContractV1:
    return authority.open_contract(
        task_spec(task_id), skill_contract(), verifier_id="InteractionVerifier"
    )


def gateway_for(
    ledger: MissionLedger, executor: InputExecutor | None = None
) -> AuthorizedInputGateway:
    return AuthorizedInputGateway(ledger, executor or dry_run_executor())


def table_snapshot(db_path: Path, tables: Iterable[str] | None = None) -> dict[str, list[Any]]:
    """Read every row of the ledger tables through an independent connection."""

    names = list(
        tables
        or (
            "mission",
            "writer_lease",
            "life_episodes",
            "manager_contracts",
            "action_permits",
            "action_attempts",
            "run_events",
            "budget_counters",
        )
    )
    conn = sqlite3.connect(db_path)
    try:
        return {name: conn.execute(f"SELECT * FROM {name} ORDER BY 1").fetchall() for name in names}
    finally:
        conn.close()


def raw_connection(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path, isolation_level=None)
