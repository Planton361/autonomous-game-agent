import sqlite3
from pathlib import Path

import pytest
from mission_fixtures import (
    FakeClock,
    FaultHook,
    gateway_for,
    new_ledger,
    open_contract,
    raw_connection,
    skill_contract,
    task_spec,
)

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.authorized_input_gateway import GatewayStop, PrimitiveActionProposalV1
from fh_agent.manager.action_authority import ContractCleanupFailed, ManagerActionAuthority
from fh_agent.mission.ledger import contract_action_budget
from fh_agent.mission.state import (
    ContractStatus,
    FaultPoint,
    GatewayBlockReason,
    InvalidMissionTransition,
    MissionFailStopped,
)


def contract_status(authority: ManagerActionAuthority, contract_id: str) -> str:
    row = authority.ledger.fetch_one(
        "SELECT status FROM manager_contracts WHERE contract_id = ?", (contract_id,)
    )
    assert row is not None
    return row[0]


def test_contract_binds_mission_episode_task_and_skill_mask(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    authority = ManagerActionAuthority(ledger)

    contract = open_contract(authority)

    episode = ledger.active_episode()
    assert episode is not None
    assert contract.run_id == ledger.run_id
    assert contract.episode_id == episode.episode_id
    assert contract.task_id == "task-1"
    assert contract.allowed_actions == (PrimitiveAction.CONFIRM, PrimitiveAction.WAIT)
    assert contract.max_action_attempts == min(skill_contract().max_steps, 4)
    assert ledger.budget(contract_action_budget(contract.contract_id)).limit == 2
    assert contract_status(authority, contract.contract_id) == ContractStatus.ACTIVE


def test_contract_requires_open_episode_and_active_mission(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path, open_episode=False)
    authority = ManagerActionAuthority(ledger)

    with pytest.raises(InvalidMissionTransition):
        open_contract(authority)


def test_ac6_at_most_one_active_contract_per_episode(tmp_path: Path) -> None:
    authority = ManagerActionAuthority(new_ledger(tmp_path))
    open_contract(authority, "task-1")

    with pytest.raises(sqlite3.IntegrityError):
        conn = raw_connection(authority.ledger.db_path)
        try:
            conn.execute(
                "INSERT INTO manager_contracts SELECT 'dup', run_id, episode_id, 'task-2', "
                "task_spec_sha256, skill_name, allowed_actions_json, max_action_attempts, "
                "verifier_id, 'ACTIVE', generation, opened_seq, NULL FROM manager_contracts"
            )
        finally:
            conn.close()
    with pytest.raises(InvalidMissionTransition, match="still active"):
        open_contract(authority, "task-2")


def test_ac6_closing_a_contract_revokes_its_outstanding_permits(tmp_path: Path) -> None:
    authority = ManagerActionAuthority(new_ledger(tmp_path))
    first = open_contract(authority, "task-1")
    proposal = authority.next_proposal(PrimitiveAction.CONFIRM)
    permit = authority.issue_permit(proposal)

    authority.close_contract(first.contract_id, "replan")
    open_contract(authority, "task-2")

    result = gateway_for(authority.ledger).execute(proposal, permit)
    assert result.block_reason is GatewayBlockReason.REVOKED
    assert result.durable is True
    assert contract_status(authority, first.contract_id) == ContractStatus.CLOSED


def test_permit_refusal_is_typed_and_durable(tmp_path: Path) -> None:
    authority = ManagerActionAuthority(new_ledger(tmp_path))
    open_contract(authority)

    with pytest.raises(GatewayStop) as raised:
        authority.issue_permit(authority.next_proposal(PrimitiveAction.MOVE_UP_SHORT))

    assert raised.value.reason is GatewayBlockReason.ACTION_NOT_ALLOWED
    assert raised.value.durable is True
    assert [e.payload["reason"] for e in authority.ledger.events("permit_refused")] == [
        "action_not_allowed"
    ]


def test_no_proposal_without_an_active_contract(tmp_path: Path) -> None:
    authority = ManagerActionAuthority(new_ledger(tmp_path))

    with pytest.raises(GatewayStop) as raised:
        authority.next_proposal(PrimitiveAction.WAIT)

    assert raised.value.reason is GatewayBlockReason.MISSING_AUTHORITY


def test_permits_expire_by_clock(tmp_path: Path) -> None:
    clock = FakeClock()
    authority = ManagerActionAuthority(new_ledger(tmp_path, clock=clock), permit_ttl_seconds=1.0)
    open_contract(authority)
    proposal = authority.next_proposal(PrimitiveAction.CONFIRM)
    permit = authority.issue_permit(proposal)
    clock.advance(1.5)

    result = gateway_for(authority.ledger).execute(proposal, permit)

    assert result.block_reason is GatewayBlockReason.EXPIRED


def test_ac6_failed_cleanup_fail_stops_the_handle(tmp_path: Path) -> None:
    hook = FaultHook()
    ledger = new_ledger(tmp_path, fault_hook=hook)
    authority = ManagerActionAuthority(ledger)
    contract = open_contract(authority)
    hook.fail(FaultPoint.CONTRACT_WRITE)

    with pytest.raises(ContractCleanupFailed):
        authority.close_contract(contract.contract_id, "done")

    assert ledger.fail_stop_reason is not None
    assert authority.current_contract is None
    hook.clear()
    with pytest.raises(MissionFailStopped):
        open_contract(authority, "task-2")
    with pytest.raises(GatewayStop) as raised:
        authority.issue_permit(
            _orphan_proposal(contract.contract_id, contract.episode_id, ledger.run_id)
        )
    assert raised.value.fail_stop is True


def test_task_spec_digest_is_bound_into_the_contract(tmp_path: Path) -> None:
    authority = ManagerActionAuthority(new_ledger(tmp_path))
    contract = authority.open_contract(
        task_spec("task-9", timeout_steps=1), skill_contract(), verifier_id="V"
    )

    assert contract.max_action_attempts == 1
    assert len(contract.task_spec_sha256) == 64


def _orphan_proposal(contract_id: str, episode_id: str, run_id: str) -> PrimitiveActionProposalV1:
    return PrimitiveActionProposalV1(
        action_id=f"{contract_id}-a001",
        run_id=run_id,
        episode_id=episode_id,
        task_id="task-1",
        contract_id=contract_id,
        attempt_ordinal=1,
        action=PrimitiveAction.CONFIRM,
    )
