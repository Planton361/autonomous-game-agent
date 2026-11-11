from pathlib import Path

import pytest
from mission_fixtures import (
    FaultHook,
    SimulatedCrash,
    dry_run_executor,
    gateway_for,
    new_ledger,
    open_contract,
    resume,
    table_snapshot,
)

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.authorized_input_gateway import (
    ActionPermitRef,
    AuthorizedInputGateway,
    ContractBoundPrimitiveActionExecutor,
    GatewayStop,
)
from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.action_authority import ManagerActionAuthority
from fh_agent.mission.ledger import (
    GLOBAL_ACTION_BUDGET,
    MissionLedger,
    contract_action_budget,
    episode_action_budget,
)
from fh_agent.mission.state import (
    ActionDisposition,
    FaultPoint,
    GatewayBlockReason,
    MissionState,
    RecoveryDecision,
    RecoveryRefused,
)


def setup(
    tmp_path: Path,
    *,
    hook: FaultHook | None = None,
    executor: InputExecutor | None = None,
    **overrides: object,
) -> tuple[MissionLedger, ManagerActionAuthority, AuthorizedInputGateway, InputExecutor]:
    ledger = new_ledger(tmp_path, fault_hook=hook, **overrides)
    authority = ManagerActionAuthority(ledger)
    open_contract(authority)
    input_executor = executor or dry_run_executor()
    return ledger, authority, AuthorizedInputGateway(ledger, input_executor), input_executor


def sent(executor: InputExecutor) -> list[str]:
    return [action.value for action in executor.backend.actions]  # type: ignore[attr-defined]


def permitted(authority: ManagerActionAuthority, action: PrimitiveAction = PrimitiveAction.CONFIRM):
    proposal = authority.next_proposal(action)
    return proposal, authority.issue_permit(proposal)


def test_authorized_action_is_reserved_before_send_and_settled_sent(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    proposal, permit = permitted(authority)

    result = gateway.execute(proposal, permit)

    assert result.disposition is ActionDisposition.SENT
    assert sent(executor) == ["confirm"]
    [attempt] = ledger.attempts()
    assert attempt.disposition is ActionDisposition.SENT
    assert attempt.contract_id == proposal.contract_id
    reserve_index = hook.reached.index(FaultPoint.RESERVATION_WRITE)
    assert hook.reached.index(FaultPoint.AFTER_RESERVATION_COMMIT) == reserve_index + 1
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 1
    assert [e.kind for e in ledger.events()][-2:] == ["action_reserved", "action_disposition"]


def test_ac3_budget_exhaustion_survives_crash_and_restore(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path, budgets__max_action_attempts=1)
    gateway.execute(*permitted(authority))
    assert sent(executor) == ["confirm"]

    with pytest.raises(GatewayStop) as raised:
        authority.issue_permit(authority.next_proposal(PrimitiveAction.CONFIRM))
    assert raised.value.reason is GatewayBlockReason.BUDGET_EXHAUSTED
    ledger.close()

    restored = resume(tmp_path, budgets__max_action_attempts=1)
    restored.resolve_recovery(RecoveryDecision.resume_same_run, operator_ref="op")
    restored_authority = ManagerActionAuthority(restored)
    open_contract(restored_authority, "task-2")
    restored_executor = dry_run_executor()
    with pytest.raises(GatewayStop) as again:
        ContractBoundPrimitiveActionExecutor(
            restored_authority, AuthorizedInputGateway(restored, restored_executor)
        ).execute(PrimitiveAction.CONFIRM)

    assert again.value.reason is GatewayBlockReason.BUDGET_EXHAUSTED
    assert sent(restored_executor) == []
    budget = restored.budget(GLOBAL_ACTION_BUDGET)
    assert (budget.limit, budget.used) == (1, 1)


@pytest.mark.parametrize("scope", ["episode", "contract"])
def test_ac3_episode_and_contract_budgets_are_enforced_at_the_gateway(
    tmp_path: Path, scope: str
) -> None:
    overrides = {"budgets__max_action_attempts_per_episode": 1} if scope == "episode" else {}
    ledger, authority, gateway, executor = setup(tmp_path, **overrides)
    for _ in range(1 if scope == "episode" else 2):
        gateway.execute(*permitted(authority))

    with pytest.raises(GatewayStop) as raised:
        authority.issue_permit(authority.next_proposal(PrimitiveAction.CONFIRM))

    assert raised.value.reason is GatewayBlockReason.BUDGET_EXHAUSTED
    contract = authority.current_contract
    assert contract is not None
    name = (
        episode_action_budget(contract.episode_id)
        if scope == "episode"
        else contract_action_budget(contract.contract_id)
    )
    assert ledger.budget(name).remaining == 0
    assert len(sent(executor)) == ledger.budget(GLOBAL_ACTION_BUDGET).used


def test_ac4_crash_after_reservation_leaves_reserved_then_unknown_on_restore(
    tmp_path: Path,
) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    proposal, permit = permitted(authority)
    hook.crash(FaultPoint.AFTER_RESERVATION_COMMIT)

    with pytest.raises(SimulatedCrash):
        gateway.execute(proposal, permit)

    assert sent(executor) == []
    rows = table_snapshot(ledger.db_path, ["action_attempts"])["action_attempts"]
    assert [row[8] for row in rows] == ["RESERVED"]
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 1
    ledger.close()

    restored = resume(tmp_path)
    [attempt] = restored.attempts()
    assert attempt.disposition is ActionDisposition.UNKNOWN
    assert restored.mission_state() is MissionState.RECOVERY_HOLD
    assert restored.budget(GLOBAL_ACTION_BUDGET).used == 1
    with pytest.raises(RecoveryRefused):
        restored.resolve_recovery(RecoveryDecision.resume_same_run, operator_ref="op")
    replay = AuthorizedInputGateway(restored, dry_run_executor()).execute(proposal, permit)
    assert replay.block_reason is GatewayBlockReason.MISSION_NOT_ACTIVE
    restored.reconcile_unknown(attempt.action_id, operator_ref="op", finding="not observed")
    assert (
        restored.resolve_recovery(RecoveryDecision.resume_same_run, operator_ref="op")
        is MissionState.ACTIVE
    )
    assert [a.disposition for a in restored.attempts()] == [ActionDisposition.UNKNOWN]


def test_ac5a_failed_reservation_write_sends_nothing_and_claims_nothing(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    proposal, permit = permitted(authority)
    before = table_snapshot(ledger.db_path)
    hook.fail(FaultPoint.RESERVATION_WRITE)

    result = gateway.execute(proposal, permit)

    assert result.block_reason is GatewayBlockReason.AUDIT_UNAVAILABLE
    assert result.durable is False
    assert result.fail_stop is True
    assert sent(executor) == []
    assert table_snapshot(ledger.db_path) == before
    hook.clear()
    assert gateway.execute(proposal, permit).block_reason is GatewayBlockReason.UNKNOWN_DISPATCH
    assert sent(executor) == []


def test_ac5b_failed_disposition_write_relies_only_on_restore(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    proposal, permit = permitted(authority)
    hook.fail(FaultPoint.DISPOSITION_WRITE)
    hook.fail(FaultPoint.UNKNOWN_WRITE)

    result = gateway.execute(proposal, permit)

    assert sent(executor) == ["confirm"]
    assert result.block_reason is GatewayBlockReason.UNKNOWN_DISPATCH
    assert result.durable is False
    assert result.disposition is None
    rows = table_snapshot(ledger.db_path, ["action_attempts", "mission"])
    assert [row[8] for row in rows["action_attempts"]] == ["RESERVED"]
    assert rows["mission"][0][5] == MissionState.ACTIVE
    with pytest.raises(GatewayStop):
        ContractBoundPrimitiveActionExecutor(authority, gateway).execute(PrimitiveAction.CONFIRM)
    assert sent(executor) == ["confirm"]
    ledger.close()

    restored = resume(tmp_path)
    [attempt] = restored.attempts()
    assert attempt.disposition is ActionDisposition.UNKNOWN
    assert restored.mission_state() is MissionState.RECOVERY_HOLD
    assert restored.budget(GLOBAL_ACTION_BUDGET).used == 1
    with pytest.raises(RecoveryRefused):
        restored.resolve_recovery(RecoveryDecision.resume_same_run, operator_ref="op")


def test_ac5b_best_effort_unknown_write_may_succeed_but_is_still_a_fail_stop(
    tmp_path: Path,
) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    hook.fail(FaultPoint.DISPOSITION_WRITE)

    result = gateway.execute(*permitted(authority))

    assert result.durable is True
    assert result.disposition is ActionDisposition.UNKNOWN
    assert ledger.mission_state() is MissionState.RECOVERY_HOLD
    assert ledger.fail_stop_reason is not None
    assert sent(executor) == ["confirm"]


def forged(permit: ActionPermitRef, **changes: str) -> ActionPermitRef:
    return permit.model_copy(update=changes)


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda p, k: (p.model_copy(update={"run_id": "other-run-0001"}), k), "wrong_run"),
        (lambda p, k: (p, forged(k, run_id="other-run-0001")), "wrong_run"),
        (lambda p, k: (p.model_copy(update={"episode_id": "e-x"}), k), "wrong_episode"),
        (lambda p, k: (p.model_copy(update={"task_id": "task-x"}), k), "wrong_task"),
        (lambda p, k: (p.model_copy(update={"contract_id": "c-x"}), k), "stale_contract"),
        (lambda p, k: (p, None), "missing_authority"),
        (lambda p, k: (p, forged(k, nonce="0" * 32)), "missing_authority"),
        (lambda p, k: (p.model_copy(update={"action_id": "other"}), k), "missing_authority"),
        (
            lambda p, k: (p.model_copy(update={"action": PrimitiveAction.WAIT}), k),
            "action_not_allowed",
        ),
        (
            lambda p, k: (p.model_copy(update={"action": PrimitiveAction.MOVE_UP_SHORT}), k),
            "action_not_allowed",
        ),
    ],
)
def test_ac7_every_scope_violation_is_typed_durable_and_sends_nothing(
    tmp_path: Path, mutate: object, reason: str
) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)
    proposal, permit = mutate(*permitted(authority))  # type: ignore[operator]

    result = gateway.execute(proposal, permit)

    assert result.block_reason == reason
    assert result.durable is True
    assert sent(executor) == []
    assert ledger.attempts() == []
    assert [e.payload["reason"] for e in ledger.events("action_rejected")] == [reason]


def test_ac7_consumed_permit_cannot_be_replayed(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)
    proposal, permit = permitted(authority)
    gateway.execute(proposal, permit)

    result = gateway.execute(proposal, permit)

    assert result.block_reason is GatewayBlockReason.REPLAYED
    assert sent(executor) == ["confirm"]
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 1


def test_ac7_unwritable_audit_never_claims_a_durable_rejection(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger, authority, gateway, executor = setup(tmp_path, hook=hook)
    proposal, _ = permitted(authority)
    before = table_snapshot(ledger.db_path)
    hook.fail(FaultPoint.REJECTION_WRITE)

    result = gateway.execute(proposal, None)

    assert result.block_reason is GatewayBlockReason.AUDIT_UNAVAILABLE
    assert result.durable is False
    assert result.fail_stop is True
    assert sent(executor) == []
    assert table_snapshot(ledger.db_path) == before
    with pytest.raises(GatewayStop) as raised:
        ContractBoundPrimitiveActionExecutor(authority, gateway).execute(PrimitiveAction.CONFIRM)
    assert raised.value.fail_stop is True


def test_ac7_stale_writer_handle_cannot_reserve(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)
    proposal, permit = permitted(authority)
    newer = resume(tmp_path)
    before = table_snapshot(newer.db_path)

    result = gateway.execute(proposal, permit)

    assert result.block_reason is GatewayBlockReason.STALE_WRITER
    assert result.durable is False
    assert sent(executor) == []
    assert table_snapshot(newer.db_path) == before


@pytest.mark.parametrize(
    ("configure", "reason"),
    [
        (lambda executor, stop: setattr(executor.focus_guard, "focused", False), "focus_lost"),
        (lambda executor, stop: stop.write_text("stop"), "stop_triggered"),
    ],
)
def test_ac8_post_reservation_physical_blocks_are_not_sent_and_charged(
    tmp_path: Path, configure: object, reason: str
) -> None:
    stop_file = tmp_path / "STOP"
    executor = dry_run_executor(stop_file=stop_file)
    ledger, authority, gateway, _ = setup(tmp_path / "runs", executor=executor)
    configure(executor, stop_file)  # type: ignore[operator]

    result = ContractBoundPrimitiveActionExecutor(authority, gateway).execute(
        PrimitiveAction.CONFIRM
    )

    assert result.executed is False
    assert result.blocked_reason in {"not_focused", "emergency_stop"}
    assert sent(executor) == []
    [attempt] = ledger.attempts()
    assert attempt.disposition is ActionDisposition.NOT_SENT
    assert attempt.block_reason == reason
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 1


def test_ac8_stop_check_exception_and_rate_limit_block_without_sending(tmp_path: Path) -> None:
    class BrokenStop:
        def is_triggered(self) -> bool:
            raise OSError("stop check unavailable")

    executor = dry_run_executor()
    executor.emergency_stop_check = BrokenStop()
    ledger, authority, gateway, _ = setup(tmp_path, executor=executor)
    adapter = ContractBoundPrimitiveActionExecutor(authority, gateway)

    assert adapter.execute(PrimitiveAction.CONFIRM).blocked_reason == "emergency_stop"
    executor.emergency_stop_check = None
    executor.min_interval_seconds = 3600.0
    assert adapter.execute(PrimitiveAction.CONFIRM).executed is True
    with pytest.raises(GatewayStop):
        adapter.execute(PrimitiveAction.CONFIRM)

    assert sent(executor) == ["confirm"]
    assert [a.disposition for a in ledger.attempts()] == [
        ActionDisposition.NOT_SENT,
        ActionDisposition.SENT,
    ]


def test_ac8_rate_limited_attempt_is_not_sent_and_charged(tmp_path: Path) -> None:
    executor = dry_run_executor()
    executor.min_interval_seconds = 3600.0
    ledger, authority, gateway, _ = setup(tmp_path, executor=executor, budgets__max_contracts=5)
    gateway.execute(*permitted(authority))
    authority.close_contract(authority.current_contract.contract_id, "next")  # type: ignore[union-attr]
    open_contract(authority, "task-2")

    result = gateway.execute(*permitted(authority))

    assert result.block_reason is GatewayBlockReason.RATE_LIMITED
    assert result.disposition is ActionDisposition.NOT_SENT
    assert sent(executor) == ["confirm"]
    assert ledger.budget(GLOBAL_ACTION_BUDGET).used == 2


def test_ac8_wait_takes_the_same_authority_path(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)
    proposal = authority.next_proposal(PrimitiveAction.WAIT)

    unauthorized = gateway.execute(proposal, None)
    assert unauthorized.block_reason is GatewayBlockReason.MISSING_AUTHORITY
    assert sent(executor) == []

    authorized = ContractBoundPrimitiveActionExecutor(authority, gateway).execute(
        PrimitiveAction.WAIT
    )
    assert authorized.executed is True
    assert [a.action for a in ledger.attempts()] == ["wait"]


def test_ac8_action_outside_mask_is_refused_through_the_adapter(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)

    with pytest.raises(GatewayStop) as raised:
        ContractBoundPrimitiveActionExecutor(authority, gateway).execute(
            PrimitiveAction.MOVE_UP_SHORT
        )

    assert raised.value.reason is GatewayBlockReason.ACTION_NOT_ALLOWED
    assert sent(executor) == []
    assert ledger.attempts() == []


def test_ac9_permits_never_cross_missions(tmp_path: Path) -> None:
    ledger_a, authority_a, _, _ = setup(tmp_path)
    ledger_b = new_ledger(tmp_path, run_id="mission-s0-test-0002")
    authority_b = ManagerActionAuthority(ledger_b)
    open_contract(authority_b)
    executor_b = dry_run_executor()
    gateway_b = AuthorizedInputGateway(ledger_b, executor_b)
    proposal_a, permit_a = permitted(authority_a)
    proposal_b = authority_b.next_proposal(PrimitiveAction.CONFIRM)

    assert gateway_b.execute(proposal_a, permit_a).block_reason is GatewayBlockReason.WRONG_RUN
    assert gateway_b.execute(proposal_b, permit_a).block_reason is GatewayBlockReason.WRONG_RUN
    assert (
        gateway_b.execute(
            proposal_b, permit_a.model_copy(update={"run_id": ledger_b.run_id})
        ).block_reason
        is GatewayBlockReason.MISSING_AUTHORITY
    )
    assert sent(executor_b) == []
    assert ledger_b.attempts() == []
    b_rows = table_snapshot(ledger_b.db_path)
    assert all(ledger_a.run_id not in repr(row) for row in b_rows["action_permits"])
    assert ledger_a.db_path != ledger_b.db_path


def test_mission_not_active_rejects_before_backend(tmp_path: Path) -> None:
    ledger, authority, gateway, executor = setup(tmp_path)
    proposal, permit = permitted(authority)
    ledger.terminate(MissionState.TERMINAL_STOPPED, "owner stop")

    result = gateway.execute(proposal, permit)

    assert result.block_reason is GatewayBlockReason.MISSION_NOT_ACTIVE
    assert sent(executor) == []


def test_gateway_fixture_uses_exact_dry_run_backend(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    assert type(gateway_for(ledger)) is AuthorizedInputGateway
