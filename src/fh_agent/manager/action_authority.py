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
from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskSchedulerError
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_contracts import SkillContract
from fh_agent.manager.skill_runner import SkillRunner, SkillRunResult
from fh_agent.manager.task_executor import (
    ManagerTaskExecutor,
    TaskExecutionError,
    TaskExecutionResult,
)
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.manager.verifier_catalog import VerifierCatalog
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
from fh_agent.observation.schemas import SkillResult
from fh_agent.observation.source import ObservationSource
from fh_agent.verifier.schemas import FailureKind

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


class AuthorizedManagerTaskExecutor(ManagerTaskExecutor):
    """Opt-in S0 task executor: each task runs under one durable Manager contract.

    The legacy ``ManagerTaskExecutor`` is not modified; this subclass is injected through
    the existing ``HierarchicalTaskStepRunner`` executor seam only when a Mission ledger is
    supplied. The contract never outlives one ``execute_current_task`` call.
    """

    def __init__(
        self,
        *,
        action_authority: ManagerActionAuthority,
        skill_catalog: SkillCatalog | None = None,
        verifier_catalog: VerifierCatalog | None = None,
        skill_runner: SkillRunner | None = None,
    ) -> None:
        super().__init__(
            skill_catalog=skill_catalog,
            verifier_catalog=verifier_catalog,
            skill_runner=skill_runner,
        )
        self._action_authority = action_authority

    @property
    def action_authority(self) -> ManagerActionAuthority:
        return self._action_authority

    def execute_current_task(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        *,
        run_id: str,
        completion_event_id: str,
        created_at: str | None = None,
    ) -> TaskExecutionResult:
        """Run the current task once under a Manager contract that is always closed/revoked.

        A ``GatewayStop`` becomes a genuine Manager stop that ends the bounded loop. Any other
        exception revokes the contract and its unconsumed permits before propagating; if that
        revocation cannot be persisted, the ledger handle is fail-stopped and
        ``ContractCleanupFailed`` is raised instead.
        """

        current_task = orchestrator.scheduler.current_task
        if current_task is None:
            raise TaskSchedulerError("no running task")

        task_spec = current_task.task_spec
        skill = self._skill_catalog.get(task_spec.selected_skill, task=task_spec.target)
        if skill.contract.skill_name != task_spec.selected_skill:
            raise TaskExecutionError(
                "resolved skill contract does not match Manager-selected skill: "
                f"{skill.contract.skill_name} != {task_spec.selected_skill}"
            )
        verifier = self._verifier_catalog.for_task(task_spec)
        authority = self._action_authority
        contract = authority.open_contract(
            task_spec, skill.contract, verifier_id=type(verifier).__name__
        )
        gateway_stop: GatewayStop | None = None
        try:
            try:
                skill_run_result = self._skill_runner.run(
                    skill,
                    observation_source,
                    verifier=verifier,
                    input_executor=input_executor,
                )
            except GatewayStop as stop:
                gateway_stop = stop
                skill_run_result = self._gateway_stop_result(skill.contract.skill_name, stop)
            completion_event = orchestrator.complete_from_skill_run(
                skill_run_result,
                task_id=task_spec.task_id,
                run_id=run_id,
                event_id=completion_event_id,
                created_at=created_at,
            )
        except BaseException as exc:
            authority.revoke_contract(contract.contract_id, f"exception:{type(exc).__name__}")
            raise
        if gateway_stop is not None or authority.ledger.fail_stop_reason is not None:
            reason = (
                "gateway_stop" if gateway_stop is None else f"gateway_stop:{gateway_stop.reason}"
            )
            authority.revoke_contract(contract.contract_id, reason)
        else:
            authority.close_contract(contract.contract_id, "task_completed")
        return TaskExecutionResult(
            task_id=task_spec.task_id,
            skill_run_result=skill_run_result,
            completion_event=completion_event,
        )

    def _gateway_stop_result(self, skill_name: str, stop: GatewayStop) -> SkillRunResult:
        integrity = stop.reason in {
            GatewayBlockReason.AUDIT_UNAVAILABLE,
            GatewayBlockReason.UNKNOWN_DISPATCH,
            GatewayBlockReason.STALE_WRITER,
        }
        manager_stop = ManagerStopResult(
            failure_kind=(
                FailureKind.SAFETY_INTERVENTION if integrity else FailureKind.CAPABILITY_REJECTED
            ),
            reason=f"gateway_{stop.reason.value}",
        )
        event_record = None
        event_logger = self._skill_runner.event_logger
        if event_logger is not None:
            event_record = event_logger.append_manager_stop(
                manager_stop,
                skill_name=skill_name,
                steps_taken=0,
            )
        return SkillRunResult(
            skill_result=SkillResult(
                skill_name=skill_name,
                success=False,
                failure_reason=manager_stop.reason,
                evidence_ids=[],
                reward=None,
            ),
            manager_stop_result=manager_stop,
            manager_stop_event_record=event_record,
        )
