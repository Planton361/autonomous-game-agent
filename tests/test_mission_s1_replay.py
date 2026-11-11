"""MRIC-S0 bounded-loop stop propagation, exception cleanup and the opt-in S1 replay hook."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mission_fixtures import (
    SKILL,
    FaultHook,
    dry_run_executor,
    new_ledger,
    raw_connection,
    resume,
    skill_contract,
    table_snapshot,
    task_spec,
)

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.authorized_input_gateway import (
    ActionPermitRef,
    AuthorizedInputGateway,
    ContractBoundPrimitiveActionExecutor,
    PrimitiveActionProposalV1,
)
from fh_agent.manager.action_authority import (
    AuthorizedManagerTaskExecutor,
    ContractCleanupFailed,
    ManagerActionAuthority,
)
from fh_agent.manager.hierarchical_step import HierarchicalTaskStepRunner
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import HierarchicalReplanLoopRunner, ReplanLoopStepIds
from fh_agent.manager.skill_contracts import SkillStep
from fh_agent.manager.skill_runner import SkillRunner
from fh_agent.manager.task_executor import ManagerTaskExecutor
from fh_agent.mission.ledger import MissionLedger
from fh_agent.mission.state import (
    ActionDisposition,
    ContractStatus,
    FaultPoint,
    GatewayBlockReason,
    MissionFailStopped,
    MissionState,
)
from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSourceExhausted
from fh_agent.pilot_step import (
    PilotStepMissionPreflightError,
    build_pilot_step_report,
    load_pilot_step_scenario,
    run_pilot_step,
    semantic_report,
)
from fh_agent.verifier.schemas import VerifierResult, VerifierStatus

SCENARIO_PATH = (
    Path(__file__).resolve().parents[1] / "configs/replay/pilot_step_visible_object_v1.json"
)
REPLAY_RUN_ID = "pilot-step-replay-0001"


# --------------------------------------------------------------------------- loop harness


class ConfirmSkill:
    contract = skill_contract()

    def __init__(self, *, fail_on_step: int | None = None) -> None:
        self._fail_on_step = fail_on_step

    def can_start(self, observation: Observation) -> bool:
        return True

    def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
        if step_index == self._fail_on_step:
            raise RuntimeError("injected skill failure")
        return SkillStep(
            skill_name=SKILL, action=PrimitiveAction.CONFIRM, step_index=step_index, reason="t"
        )


class StubSkillCatalog:
    def __init__(self, skill: ConfirmSkill) -> None:
        self._skill = skill

    def get(self, skill_name: str, *, task: object | None = None) -> ConfirmSkill:
        return self._skill


class SuccessVerifier:
    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        return VerifierResult(status=VerifierStatus.SUCCESS, evidence_ids=after.evidence_ids)


class StubVerifierCatalog:
    def for_task(self, task: object) -> SuccessVerifier:
        return SuccessVerifier()


class DirectSubmitter:
    def __init__(self) -> None:
        self.calls = 0

    def plan_ground_and_submit(
        self, orchestrator: ManagerOrchestrator, observation: Observation, memory: Any, **ids: Any
    ) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(
            scheduled_task=orchestrator.scheduler.enqueue(task_spec(ids["task_id"]))
        )


class Observations:
    def __init__(self, count: int) -> None:
        self._remaining = [
            Observation(run_id="loop", ui_state="field", evidence_ids=[f"shot-{i}"])
            for i in range(count)
        ]

    def observe(self) -> Observation:
        if not self._remaining:
            raise ObservationSourceExhausted
        return self._remaining.pop(0)


class ForgingIssuer:
    """Delegates to the real Manager authority but hands the gateway a forged permit."""

    def __init__(self, authority: ManagerActionAuthority) -> None:
        self._authority = authority

    def next_proposal(self, action: PrimitiveAction) -> PrimitiveActionProposalV1:
        return self._authority.next_proposal(action)

    def issue_permit(self, proposal: PrimitiveActionProposalV1) -> ActionPermitRef:
        real = self._authority.issue_permit(proposal)
        return real.model_copy(update={"nonce": "f" * 32})


def run_loop(
    ledger: MissionLedger,
    *,
    tasks: int = 2,
    issuer: Any = None,
    skill: ConfirmSkill | None = None,
) -> tuple[Any, DirectSubmitter, Any, ManagerActionAuthority]:
    authority = ManagerActionAuthority(ledger)
    executor = dry_run_executor()
    adapter = ContractBoundPrimitiveActionExecutor(
        issuer(authority) if issuer else authority, AuthorizedInputGateway(ledger, executor)
    )
    submitter = DirectSubmitter()
    task_executor = AuthorizedManagerTaskExecutor(
        action_authority=authority,
        skill_catalog=StubSkillCatalog(skill or ConfirmSkill()),  # type: ignore[arg-type]
        verifier_catalog=StubVerifierCatalog(),  # type: ignore[arg-type]
        skill_runner=SkillRunner(),
    )
    loop = HierarchicalReplanLoopRunner(
        HierarchicalTaskStepRunner(submitter, task_executor=task_executor)  # type: ignore[arg-type]
    )
    result = loop.run_bounded(
        ManagerOrchestrator(),
        Observations(6),
        adapter,  # type: ignore[arg-type]
        {},
        run_id=ledger.run_id,
        step_ids=tuple(
            ReplanLoopStepIds(task_id=f"task-{i}", completion_event_id=f"done-{i}")
            for i in range(1, tasks + 1)
        ),
    )
    return result, submitter, executor, authority


def contract_rows(ledger: MissionLedger) -> list[tuple[Any, ...]]:
    return table_snapshot(ledger.db_path, ["manager_contracts"])["manager_contracts"]


def test_positive_control_two_authorized_tasks_both_run(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)

    result, submitter, executor, _ = run_loop(ledger)

    assert result.stop_reason == "budget_exhausted"
    assert submitter.calls == 2
    assert [a.value for a in executor.backend.actions] == ["confirm", "confirm"]
    assert [a.disposition for a in ledger.attempts()] == [ActionDisposition.SENT] * 2
    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.CLOSED] * 2


def test_ac7_ac8_gateway_authorization_failure_is_a_manager_stop_and_ends_the_loop(
    tmp_path: Path,
) -> None:
    ledger = new_ledger(tmp_path)

    result, submitter, executor, _ = run_loop(ledger, issuer=ForgingIssuer)

    assert result.stop_reason == "manager_stop"
    assert len(result.step_results) == 1
    assert submitter.calls == 1
    assert executor.backend.actions == []
    completion = result.step_results[0].execution_result.completion_event
    assert completion.manager_stop_result.failure_kind == "capability_rejected"
    assert completion.manager_stop_result.reason == "gateway_missing_authority"
    assert completion.manager_stop_result.reason not in {
        "emergency_stop",
        "not_focused",
        "rate_limited",
    }
    assert [e.payload["reason"] for e in ledger.events("action_rejected")] == ["missing_authority"]
    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.REVOKED]


def test_ac7_unwritable_audit_in_the_loop_fail_stops_without_a_next_task(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger = new_ledger(tmp_path, fault_hook=hook)
    hook.fail(FaultPoint.REJECTION_WRITE)

    result, submitter, executor, authority = run_loop(ledger, issuer=ForgingIssuer)

    assert result.stop_reason == "manager_stop"
    assert submitter.calls == 1
    assert executor.backend.actions == []
    stop = result.step_results[0].execution_result.completion_event.manager_stop_result
    assert stop.failure_kind == "safety_intervention"
    assert stop.reason == "gateway_audit_unavailable"
    assert ledger.events("action_rejected") == []
    assert ledger.fail_stop_reason is not None
    with pytest.raises(MissionFailStopped):
        authority.open_contract(task_spec("task-3"), skill_contract(), verifier_id="V")


def test_ac8_mission_budget_exhaustion_in_the_loop_stops_instead_of_continuing(
    tmp_path: Path,
) -> None:
    ledger = new_ledger(tmp_path, budgets__max_action_attempts=1)

    result, submitter, executor, _ = run_loop(ledger)

    assert result.stop_reason == "manager_stop"
    assert submitter.calls == 2
    assert [a.value for a in executor.backend.actions] == ["confirm"]
    stop = result.step_results[1].execution_result.completion_event.manager_stop_result
    assert stop.reason == "gateway_budget_exhausted"


def test_ac6_exception_in_skill_execution_revokes_contract_and_open_permits(
    tmp_path: Path,
) -> None:
    ledger = new_ledger(tmp_path)

    with pytest.raises(RuntimeError, match="injected skill failure"):
        run_loop(ledger, skill=ConfirmSkill(fail_on_step=0))

    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.REVOKED]
    assert ledger.attempts() == []
    assert ledger.fetch_one(
        "SELECT COUNT(*) FROM action_permits WHERE consumed_at IS NULL AND revoked_reason IS NULL"
    ) == (0,)


def test_ac6_exception_between_permit_and_gateway_leaves_no_usable_permit(
    tmp_path: Path,
) -> None:
    ledger = new_ledger(tmp_path)
    captured: list[tuple[PrimitiveActionProposalV1, ActionPermitRef]] = []

    class IssueThenCrash(ForgingIssuer):
        def issue_permit(self, proposal: PrimitiveActionProposalV1) -> ActionPermitRef:
            permit = self._authority.issue_permit(proposal)
            captured.append((proposal, permit))
            raise RuntimeError("crash after permit issuance")

    with pytest.raises(RuntimeError, match="after permit issuance"):
        run_loop(ledger, issuer=IssueThenCrash)

    [(proposal, permit)] = captured
    executor = dry_run_executor()
    replay = AuthorizedInputGateway(ledger, executor).execute(proposal, permit)
    assert replay.block_reason is GatewayBlockReason.REVOKED
    assert executor.backend.actions == []
    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.REVOKED]


def test_ac6_exception_in_task_completion_revokes_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = new_ledger(tmp_path)

    def broken_completion(self: object, *args: object, **kwargs: object) -> None:
        raise ValueError("completion failed")

    monkeypatch.setattr(ManagerOrchestrator, "complete_from_skill_run", broken_completion)

    with pytest.raises(ValueError, match="completion failed"):
        run_loop(ledger)

    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.REVOKED]


def test_ac6_unpersistable_cleanup_fail_stops_and_runs_no_next_task(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger = new_ledger(tmp_path, fault_hook=hook)

    class CrashAfterCleanupArmed(ConfirmSkill):
        def next_action(self, observation: Observation, *, step_index: int) -> SkillStep:
            hook.fail(FaultPoint.CONTRACT_WRITE)
            raise RuntimeError("skill failure with unwritable ledger")

    with pytest.raises(ContractCleanupFailed) as raised:
        run_loop(ledger, skill=CrashAfterCleanupArmed())

    assert isinstance(raised.value.__context__, RuntimeError)
    assert ledger.fail_stop_reason is not None
    assert [row[9] for row in contract_rows(ledger)] == [ContractStatus.ACTIVE]
    ledger.close()
    restored = resume(tmp_path)
    assert [row[9] for row in contract_rows(restored)] == [ContractStatus.REVOKED]
    assert restored.mission_state() is MissionState.RECOVERY_HOLD


# --------------------------------------------------------------------------- S1 replay hook


def replay_ledger(runs_root: Path, **overrides: Any) -> MissionLedger:
    return new_ledger(runs_root, run_id=REPLAY_RUN_ID, **overrides)


def run_replay(tmp_path: Path, run_dir: Path, ledger: MissionLedger | None) -> Any:
    scenario, sha = load_pilot_step_scenario(SCENARIO_PATH)
    return run_pilot_step(
        scenario,
        scenario_sha256=sha,
        run_dir=run_dir,
        stop_file=tmp_path / "STOP",
        mission_ledger=ledger,
    )


def test_ac13_opt_in_replay_matches_legacy_and_binds_every_action(tmp_path: Path) -> None:
    legacy = run_replay(tmp_path, tmp_path / "legacy", None)
    runs_root = tmp_path / "runs"
    ledger = replay_ledger(runs_root)

    mission = run_replay(tmp_path, runs_root / REPLAY_RUN_ID, ledger)

    legacy_report = build_pilot_step_report(legacy)
    mission_report = build_pilot_step_report(mission)
    assert mission.error is None
    assert semantic_report(mission_report) == semantic_report(legacy_report)
    assert mission_report["result_classification"] == "debug-replay"
    assert mission_report["live_gameplay_verified"] is False
    assert mission_report["official_evidence"] is False
    assert {o["transition"] for o in mission_report["observations"][1:]} == {"replayed_transition"}
    used = mission_report["budgets"]["used"]
    assert used["task_attempts"] == 1
    assert used["primitive_action_attempts"] <= 2
    assert used["observations"] <= 4
    attempts = ledger.attempts()
    assert [a.action for a in attempts] == [a.value for a in mission.backend.actions]
    assert all(a.disposition is ActionDisposition.SENT for a in attempts)
    [contract] = contract_rows(ledger)
    assert {a.contract_id for a in attempts} == {contract[0]}
    assert contract[3] == mission_report["task"]["task_id"]
    assert contract[9] == ContractStatus.CLOSED
    events_path = runs_root / REPLAY_RUN_ID / "events.jsonl"
    run_ids = {json.loads(line)["run_id"] for line in events_path.read_text().splitlines()}
    assert run_ids == {REPLAY_RUN_ID}
    assert ledger.manifest.execution_class != "live"


def test_authorized_executor_is_injected_only_with_a_mission_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import inspect

    import fh_agent.pilot_step as pilot_step_module

    injected: list[type] = []
    real_runner = pilot_step_module.HierarchicalTaskStepRunner

    def recording_runner(submitter: Any, *, task_executor: Any) -> Any:
        injected.append(type(task_executor))
        return real_runner(submitter, task_executor=task_executor)

    monkeypatch.setattr(pilot_step_module, "HierarchicalTaskStepRunner", recording_runner)
    runs_root = tmp_path / "runs"
    run_replay(tmp_path, tmp_path / "legacy", None)
    run_replay(tmp_path, runs_root / REPLAY_RUN_ID, replay_ledger(runs_root))

    assert injected == [ManagerTaskExecutor, AuthorizedManagerTaskExecutor]
    assert issubclass(AuthorizedManagerTaskExecutor, ManagerTaskExecutor)
    assert "action_authority" not in inspect.signature(ManagerTaskExecutor).parameters


def _symlinked_run_dir(tmp_path: Path, runs_root: Path) -> Path:
    link = tmp_path / "elsewhere"
    link.mkdir()
    target = link / REPLAY_RUN_ID
    target.symlink_to(runs_root / REPLAY_RUN_ID)
    return target


def _other_dir(tmp_path: Path, runs_root: Path) -> Path:
    other = tmp_path / "other" / REPLAY_RUN_ID
    other.mkdir(parents=True)
    return other


@pytest.mark.parametrize(
    "case",
    [
        "scenario_run_id",
        "other_dir",
        "symlink_dir",
        "wrong_name_dir",
        "execution_class",
        "run_mode",
        "stale_handle",
        "no_episode",
        "not_active",
        "budget",
    ],
)
def test_ac9_ac13_replay_identity_mismatch_fails_before_any_write(
    tmp_path: Path, case: str
) -> None:
    runs_root = tmp_path / "runs"
    overrides: dict[str, Any] = {}
    if case == "execution_class":
        overrides["execution_class"] = "dry-run"
    if case == "run_mode":
        overrides["run_mode"] = "debug"
    if case == "budget":
        overrides["budgets__max_contracts"] = 1
    run_id = "pilot-step-replay-9999" if case == "scenario_run_id" else REPLAY_RUN_ID
    ledger = new_ledger(runs_root, run_id=run_id, open_episode=case != "no_episode", **overrides)
    run_dir = runs_root / run_id
    if case == "other_dir":
        run_dir = _other_dir(tmp_path, runs_root)
    if case == "symlink_dir":
        run_dir = _symlinked_run_dir(tmp_path, runs_root)
    if case == "wrong_name_dir":
        run_dir = runs_root / "not-the-mission-dir"
        run_dir.mkdir()
    if case == "stale_handle":
        resume(runs_root, run_id=run_id).close()
    if case == "not_active":
        ledger.terminate(MissionState.TERMINAL_STOPPED, "stop")
    if case == "budget":
        conn = raw_connection(ledger.db_path)
        conn.execute("UPDATE budget_counters SET used = 1 WHERE name = 'contracts'")
        conn.close()
    before = table_snapshot(ledger.db_path)
    files_before = sorted(p.name for p in (runs_root / run_id).iterdir())

    with pytest.raises(PilotStepMissionPreflightError):
        run_replay(tmp_path, run_dir, ledger)

    assert table_snapshot(ledger.db_path) == before
    assert sorted(p.name for p in (runs_root / run_id).iterdir()) == files_before
    for directory in {run_dir, runs_root / run_id}:
        assert not (directory / "events.jsonl").exists()
        assert not (directory / "feed.jsonl").exists()
