"""Manager-owned durable contracts and single-use action permits (MRIC-S0, Issue #184).

Only the Manager opens, closes and revokes contracts and mints permits. Body/Reflex code
may build a proposal, but cannot create authority for it.
"""

import hashlib
import json
import secrets
import sqlite3

from pydantic import BaseModel, ConfigDict

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.authorized_input_gateway import (
    ActionPermitRef,
    GatewayStop,
    PrimitiveActionProposalV1,
)
from fh_agent.manager.skill_contracts import SkillContract
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.mission.ledger import (
    CONTRACT_BUDGET,
    GLOBAL_ACTION_BUDGET,
    MissionLedger,
    contract_action_budget,
    episode_action_budget,
)
from fh_agent.mission.state import (
    ContractStatus,
    EpisodeState,
    FaultPoint,
    GatewayBlockReason,
    InvalidMissionTransition,
    LedgerWriteError,
    MissionFailStopped,
    MissionLedgerError,
    MissionState,
    StaleWriterError,
)

DEFAULT_PERMIT_TTL_SECONDS = 5.0


class ManagerContractV1(BaseModel):
    """Durable Grounded Skill Contract bound to one Mission, Life Episode and Manager task."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str
    run_id: str
    episode_id: str
    task_id: str
    task_spec_sha256: str
    skill_name: str
    allowed_actions: tuple[PrimitiveAction, ...]
    max_action_attempts: int
    verifier_id: str
    status: ContractStatus
    generation: int


class ContractCleanupFailed(RuntimeError):
    """Durable close/revoke failed; the ledger handle is fail-stopped in-process."""


class ManagerActionAuthority:
    """Manager authority over the active contract and its permits in one Mission ledger."""

    def __init__(
        self,
        ledger: MissionLedger,
        *,
        permit_ttl_seconds: float = DEFAULT_PERMIT_TTL_SECONDS,
    ) -> None:
        if permit_ttl_seconds <= 0:
            raise ValueError("permit_ttl_seconds must be positive")
        self._ledger = ledger
        self._permit_ttl_seconds = permit_ttl_seconds
        self._current: ManagerContractV1 | None = None

    @property
    def ledger(self) -> MissionLedger:
        return self._ledger

    @property
    def current_contract(self) -> ManagerContractV1 | None:
        return self._current

    def open_contract(
        self,
        task_spec: TaskSpec,
        skill_contract: SkillContract,
        *,
        verifier_id: str,
    ) -> ManagerContractV1:
        ledger = self._ledger
        task_spec_sha = hashlib.sha256(task_spec.to_deterministic_json().encode()).hexdigest()
        max_attempts = min(skill_contract.max_steps, task_spec.timeout_steps)
        with ledger.write_transaction(FaultPoint.CONTRACT_WRITE) as conn:
            (state,) = conn.execute("SELECT state FROM mission").fetchone()
            if state != MissionState.ACTIVE.value:
                raise InvalidMissionTransition(f"mission is {state}")
            episode = conn.execute(
                "SELECT episode_id FROM life_episodes WHERE state = ?",
                (EpisodeState.OPEN.value,),
            ).fetchone()
            if episode is None:
                raise InvalidMissionTransition("no open Life Episode")
            active = conn.execute(
                "SELECT contract_id FROM manager_contracts WHERE episode_id = ? AND status = ?",
                (episode[0], ContractStatus.ACTIVE.value),
            ).fetchone()
            if active is not None:
                raise InvalidMissionTransition(f"contract {active[0]} is still active")
            ledger.debit(conn, CONTRACT_BUDGET)
            (count,) = conn.execute("SELECT COUNT(*) FROM manager_contracts").fetchone()
            contract = ManagerContractV1(
                contract_id=f"{ledger.run_id}-c{count + 1:04d}",
                run_id=ledger.run_id,
                episode_id=episode[0],
                task_id=task_spec.task_id,
                task_spec_sha256=task_spec_sha,
                skill_name=skill_contract.skill_name,
                allowed_actions=tuple(skill_contract.allowed_actions),
                max_action_attempts=max_attempts,
                verifier_id=verifier_id,
                status=ContractStatus.ACTIVE,
                generation=ledger.generation,
            )
            event = ledger.append_event(
                conn,
                "contract_opened",
                {
                    "contract_id": contract.contract_id,
                    "episode_id": contract.episode_id,
                    "task_id": contract.task_id,
                    "skill_name": contract.skill_name,
                    "task_spec_sha256": task_spec_sha,
                },
            )
            conn.execute(
                "INSERT INTO manager_contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                (
                    contract.contract_id,
                    contract.run_id,
                    contract.episode_id,
                    contract.task_id,
                    task_spec_sha,
                    contract.skill_name,
                    json.dumps([action.value for action in contract.allowed_actions]),
                    max_attempts,
                    verifier_id,
                    ContractStatus.ACTIVE.value,
                    contract.generation,
                    event.seq,
                ),
            )
            ledger.ensure_counter(conn, contract_action_budget(contract.contract_id), max_attempts)
        self._current = contract
        return contract

    def close_contract(self, contract_id: str, reason: str) -> None:
        self._finish_contract(contract_id, ContractStatus.CLOSED, reason)

    def revoke_contract(self, contract_id: str, reason: str) -> None:
        self._finish_contract(contract_id, ContractStatus.REVOKED, reason)

    def revoke_all(self, reason: str) -> None:
        try:
            with self._ledger.write_transaction(
                FaultPoint.CONTRACT_WRITE, allow_in_fail_stop=True
            ) as conn:
                self._ledger.revoke_open_authority(conn, reason)
                self._ledger.append_event(conn, "authority_revoked", {"reason": reason})
        except MissionLedgerError as exc:
            self._ledger.enter_fail_stop(f"revoke_all_failed:{reason}")
            raise ContractCleanupFailed(str(exc)) from exc
        finally:
            self._current = None

    def next_proposal(self, action: PrimitiveAction) -> PrimitiveActionProposalV1:
        contract = self._current
        if contract is None:
            raise GatewayStop(GatewayBlockReason.MISSING_AUTHORITY, durable=False)
        (issued,) = self._ledger.fetch_one(
            "SELECT COUNT(*) FROM action_permits WHERE contract_id = ?", (contract.contract_id,)
        ) or (0,)
        ordinal = issued + 1
        return PrimitiveActionProposalV1(
            action_id=f"{contract.contract_id}-a{ordinal:03d}",
            run_id=contract.run_id,
            episode_id=contract.episode_id,
            task_id=contract.task_id,
            contract_id=contract.contract_id,
            attempt_ordinal=ordinal,
            action=action,
        )

    def issue_permit(self, proposal: PrimitiveActionProposalV1) -> ActionPermitRef:
        """Mint one single-use permit for the active contract, or raise ``GatewayStop``."""

        ledger = self._ledger
        if ledger.fail_stop_reason is not None:
            raise GatewayStop(
                GatewayBlockReason.AUDIT_UNAVAILABLE,
                durable=False,
                fail_stop=True,
                action_id=proposal.action_id,
                detail=ledger.fail_stop_reason,
            )
        nonce = secrets.token_hex(16)
        try:
            with ledger.write_transaction(FaultPoint.PERMIT_WRITE) as conn:
                reason = self._permit_refusal(conn, proposal)
                if reason is not None:
                    ledger.append_event(
                        conn,
                        "permit_refused",
                        {"action_id": proposal.action_id, "reason": reason.value},
                    )
                else:
                    conn.execute(
                        "INSERT INTO action_permits VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
                        (
                            nonce,
                            proposal.action_id,
                            proposal.run_id,
                            proposal.episode_id,
                            proposal.task_id,
                            proposal.contract_id,
                            proposal.attempt_ordinal,
                            proposal.action.value,
                            ledger.generation,
                            ledger.clock() + self._permit_ttl_seconds,
                        ),
                    )
                    ledger.append_event(
                        conn,
                        "permit_issued",
                        {"action_id": proposal.action_id, "contract_id": proposal.contract_id},
                    )
        except StaleWriterError as exc:
            raise GatewayStop(
                GatewayBlockReason.STALE_WRITER, durable=False, action_id=proposal.action_id
            ) from exc
        except (LedgerWriteError, MissionFailStopped) as exc:
            ledger.enter_fail_stop("permit_write_failed")
            raise GatewayStop(
                GatewayBlockReason.AUDIT_UNAVAILABLE,
                durable=False,
                fail_stop=True,
                action_id=proposal.action_id,
            ) from exc
        if reason is not None:
            raise GatewayStop(reason, durable=True, action_id=proposal.action_id)
        return ActionPermitRef(run_id=proposal.run_id, action_id=proposal.action_id, nonce=nonce)

    # ----------------------------------------------------------------- internals

    def _permit_refusal(
        self, conn: sqlite3.Connection, proposal: PrimitiveActionProposalV1
    ) -> GatewayBlockReason | None:
        ledger = self._ledger
        contract = self._current
        (state,) = conn.execute("SELECT state FROM mission").fetchone()
        if state != MissionState.ACTIVE.value:
            return GatewayBlockReason.MISSION_NOT_ACTIVE
        if contract is None or proposal.contract_id != contract.contract_id:
            return GatewayBlockReason.STALE_CONTRACT
        row = conn.execute(
            "SELECT status FROM manager_contracts WHERE contract_id = ?",
            (contract.contract_id,),
        ).fetchone()
        if row is None or row[0] == ContractStatus.REVOKED.value:
            return GatewayBlockReason.REVOKED
        if row[0] != ContractStatus.ACTIVE.value:
            return GatewayBlockReason.STALE_CONTRACT
        if proposal.run_id != contract.run_id:
            return GatewayBlockReason.WRONG_RUN
        if proposal.episode_id != contract.episode_id:
            return GatewayBlockReason.WRONG_EPISODE
        if proposal.task_id != contract.task_id:
            return GatewayBlockReason.WRONG_TASK
        if proposal.action not in contract.allowed_actions:
            return GatewayBlockReason.ACTION_NOT_ALLOWED
        for name in (
            GLOBAL_ACTION_BUDGET,
            episode_action_budget(contract.episode_id),
            contract_action_budget(contract.contract_id),
        ):
            if ledger.remaining(conn, name) <= 0:
                return GatewayBlockReason.BUDGET_EXHAUSTED
        return None

    def _finish_contract(self, contract_id: str, status: ContractStatus, reason: str) -> None:
        """Close/revoke one contract and its unconsumed permits; fail-stop if not durable."""

        ledger = self._ledger
        try:
            with ledger.write_transaction(
                FaultPoint.CONTRACT_WRITE, allow_in_fail_stop=status is ContractStatus.REVOKED
            ) as conn:
                conn.execute(
                    "UPDATE action_permits SET revoked_reason = ? "
                    "WHERE contract_id = ? AND consumed_at IS NULL AND revoked_reason IS NULL",
                    (f"contract_{status.value.lower()}:{reason}", contract_id),
                )
                cursor = conn.execute(
                    "UPDATE manager_contracts SET status = ?, close_reason = ? "
                    "WHERE contract_id = ? AND status = ?",
                    (status.value, reason, contract_id, ContractStatus.ACTIVE.value),
                )
                if cursor.rowcount == 1:
                    ledger.append_event(
                        conn,
                        f"contract_{status.value.lower()}",
                        {"contract_id": contract_id, "reason": reason},
                    )
        except MissionLedgerError as exc:
            ledger.enter_fail_stop(f"contract_cleanup_failed:{contract_id}")
            raise ContractCleanupFailed(f"{contract_id}: {exc}") from exc
        finally:
            if self._current is not None and self._current.contract_id == contract_id:
                self._current = None
