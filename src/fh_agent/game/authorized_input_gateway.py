"""Manager-bound, single-use action permits checked at the final input boundary (MRIC-S0).

S0 is offline only: the gateway accepts exactly the production ``DryRunInputBackend`` inside an
exact ``InputExecutor``. Every action is authorized and reserved (permit consumed, budgets
debited) in one committed transaction before the executor is called. Failures after a
possible dispatch fail-stop the process handle and are never retried.
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.game.input_executor import BlockedReason, DryRunInputBackend, InputExecutor
from fh_agent.mission.ledger import (
    GLOBAL_ACTION_BUDGET,
    MissionLedger,
    contract_action_budget,
    episode_action_budget,
)
from fh_agent.mission.state import (
    ActionDisposition,
    ContractStatus,
    EpisodeState,
    FaultPoint,
    GatewayBlockReason,
    LedgerWriteError,
    MissionFailStopped,
    MissionState,
    StaleWriterError,
)
from fh_agent.observation.schemas import ActionResult

S0_ALLOWED_BACKEND_TYPES: tuple[type, ...] = (DryRunInputBackend,)
REAL_BACKEND_NOT_PERMITTED = "real_backend_not_permitted_in_s0"

_PHYSICAL_BLOCK_REASONS = {
    BlockedReason.NOT_FOCUSED: GatewayBlockReason.FOCUS_LOST,
    BlockedReason.EMERGENCY_STOP: GatewayBlockReason.STOP_TRIGGERED,
    BlockedReason.RATE_LIMITED: GatewayBlockReason.RATE_LIMITED,
}


class PrimitiveActionProposalV1(BaseModel):
    """A Body/Reflex action proposal; it carries no authority of its own."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    contract_id: str = Field(min_length=1)
    attempt_ordinal: int = Field(ge=1)
    action: PrimitiveAction


class ActionPermitRef(BaseModel):
    """Opaque reference to a single-use permit stored in the Mission ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    action_id: str
    nonce: str = Field(repr=False)


class RealBackendNotPermitted(RuntimeError):
    pass


class GatewayStop(RuntimeError):
    """Typed fail-closed authority/integrity stop raised toward the Manager task executor.

    ``durable`` is true only when the rejection was committed to the ledger. ``fail_stop``
    marks conditions after which the process handle must not dispatch anything else.
    """

    def __init__(
        self,
        reason: GatewayBlockReason,
        *,
        durable: bool,
        fail_stop: bool = False,
        action_id: str | None = None,
        detail: str = "",
    ) -> None:
        self.reason = reason
        self.durable = durable
        self.fail_stop = fail_stop
        self.action_id = action_id
        super().__init__(f"{reason.value}: {detail}" if detail else reason.value)


@dataclass(frozen=True, slots=True)
class GatewayResult:
    action_id: str
    disposition: ActionDisposition | None
    action_result: ActionResult | None
    block_reason: GatewayBlockReason | None = None
    durable: bool = True
    fail_stop: bool = False


class _Rejected(Exception):
    def __init__(self, reason: GatewayBlockReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason.value)


class AuthorizedInputGateway:
    """The only S0 path from a permitted proposal to ``InputExecutor.execute``."""

    def __init__(self, ledger: MissionLedger, input_executor: InputExecutor) -> None:
        _require_exact_dry_run(input_executor)
        self._ledger = ledger
        self._input_executor = input_executor

    @property
    def ledger(self) -> MissionLedger:
        return self._ledger

    def execute(
        self, proposal: PrimitiveActionProposalV1, permit: ActionPermitRef | None
    ) -> GatewayResult:
        ledger = self._ledger
        if ledger.fail_stop_reason is not None:
            return self._in_process(proposal, GatewayBlockReason.UNKNOWN_DISPATCH, fail_stop=True)
        _require_exact_dry_run(self._input_executor)

        try:
            with ledger.write_transaction(FaultPoint.RESERVATION_WRITE) as conn:
                self._authorize_and_reserve(conn, proposal, permit)
        except _Rejected as rejection:
            return self._record_rejection(proposal, rejection)
        except StaleWriterError:
            return self._in_process(proposal, GatewayBlockReason.STALE_WRITER)
        except (LedgerWriteError, MissionFailStopped):
            ledger.enter_fail_stop("reservation_write_failed")
            return self._in_process(proposal, GatewayBlockReason.AUDIT_UNAVAILABLE, fail_stop=True)

        # The reservation is durable from here on: the attempt is charged and never refunded.
        ledger.fire_fault_point(FaultPoint.AFTER_RESERVATION_COMMIT)
        try:
            action_result = self._input_executor.execute(proposal.action)
        except Exception:
            return self._unknown(proposal, "backend_raised")

        physical_block = _PHYSICAL_BLOCK_REASONS.get(action_result.blocked_reason)
        if not action_result.executed and physical_block is None:
            return self._unknown(proposal, f"unrecognized_block:{action_result.blocked_reason}")
        disposition = (
            ActionDisposition.SENT if action_result.executed else ActionDisposition.NOT_SENT
        )
        try:
            with ledger.write_transaction(FaultPoint.DISPOSITION_WRITE) as conn:
                _settle(conn, proposal.action_id, disposition, physical_block)
                ledger.append_event(
                    conn,
                    "action_disposition",
                    {
                        "action_id": proposal.action_id,
                        "disposition": disposition.value,
                        "block_reason": None if physical_block is None else physical_block.value,
                    },
                )
        except (LedgerWriteError, StaleWriterError, MissionFailStopped):
            return self._unknown(proposal, "disposition_write_failed", action_result=action_result)
        return GatewayResult(proposal.action_id, disposition, action_result, physical_block)

    # ----------------------------------------------------------------- internals

    def _authorize_and_reserve(
        self,
        conn: sqlite3.Connection,
        proposal: PrimitiveActionProposalV1,
        permit: ActionPermitRef | None,
    ) -> None:
        ledger = self._ledger
        (state,) = conn.execute("SELECT state FROM mission").fetchone()
        if state != MissionState.ACTIVE.value:
            raise _Rejected(GatewayBlockReason.MISSION_NOT_ACTIVE, state)
        if proposal.run_id != ledger.run_id:
            raise _Rejected(GatewayBlockReason.WRONG_RUN)
        if permit is None:
            raise _Rejected(GatewayBlockReason.MISSING_AUTHORITY)
        if permit.run_id != ledger.run_id:
            raise _Rejected(GatewayBlockReason.WRONG_RUN, "foreign permit")
        row = conn.execute(
            "SELECT action_id, run_id, episode_id, task_id, contract_id, attempt_ordinal, action, "
            "issued_generation, expires_at, consumed_at, revoked_reason "
            "FROM action_permits WHERE permit_nonce = ?",
            (permit.nonce,),
        ).fetchone()
        if row is None:
            raise _Rejected(GatewayBlockReason.MISSING_AUTHORITY, "unknown permit")
        (
            p_action_id,
            p_run,
            p_episode,
            p_task,
            p_contract,
            p_ordinal,
            p_action,
            p_generation,
            p_expires,
            p_consumed,
            p_revoked,
        ) = row
        if p_consumed is not None:
            raise _Rejected(GatewayBlockReason.REPLAYED)
        if p_revoked is not None:
            raise _Rejected(GatewayBlockReason.REVOKED, p_revoked)
        if p_generation != ledger.generation or ledger.clock() > p_expires:
            raise _Rejected(GatewayBlockReason.EXPIRED)
        if p_action_id != proposal.action_id or permit.action_id != proposal.action_id:
            raise _Rejected(GatewayBlockReason.MISSING_AUTHORITY, "permit scoped to other action")
        if p_run != proposal.run_id:
            raise _Rejected(GatewayBlockReason.WRONG_RUN)

        episode = conn.execute(
            "SELECT episode_id FROM life_episodes WHERE state = ?", (EpisodeState.OPEN.value,)
        ).fetchone()
        if episode is None or proposal.episode_id != episode[0] or p_episode != episode[0]:
            raise _Rejected(GatewayBlockReason.WRONG_EPISODE)

        contract = conn.execute(
            "SELECT episode_id, task_id, allowed_actions_json, status FROM manager_contracts "
            "WHERE contract_id = ?",
            (proposal.contract_id,),
        ).fetchone()
        if contract is None or p_contract != proposal.contract_id:
            raise _Rejected(GatewayBlockReason.STALE_CONTRACT, "permit bound to other contract")
        c_episode, c_task, allowed_json, c_status = contract
        if c_status == ContractStatus.REVOKED.value:
            raise _Rejected(GatewayBlockReason.REVOKED, "contract revoked")
        if c_status != ContractStatus.ACTIVE.value or c_episode != episode[0]:
            raise _Rejected(GatewayBlockReason.STALE_CONTRACT)
        if proposal.task_id != c_task or p_task != c_task:
            raise _Rejected(GatewayBlockReason.WRONG_TASK)
        if proposal.action.value not in _json_list(allowed_json) or p_action != proposal.action:
            raise _Rejected(GatewayBlockReason.ACTION_NOT_ALLOWED)
        if p_ordinal != proposal.attempt_ordinal:
            raise _Rejected(GatewayBlockReason.MISSING_AUTHORITY, "attempt ordinal mismatch")

        budgets = (
            GLOBAL_ACTION_BUDGET,
            episode_action_budget(episode[0]),
            contract_action_budget(proposal.contract_id),
        )
        for name in budgets:
            if ledger.remaining(conn, name) <= 0:
                raise _Rejected(GatewayBlockReason.BUDGET_EXHAUSTED, name)

        conn.execute(
            "UPDATE action_permits SET consumed_at = ? WHERE permit_nonce = ?",
            (ledger.now_iso(), permit.nonce),
        )
        for name in budgets:
            ledger.debit(conn, name)
        event = ledger.append_event(
            conn,
            "action_reserved",
            {
                "action_id": proposal.action_id,
                "contract_id": proposal.contract_id,
                "episode_id": proposal.episode_id,
                "task_id": proposal.task_id,
                "action": proposal.action.value,
                "attempt_ordinal": proposal.attempt_ordinal,
            },
        )
        conn.execute(
            "INSERT INTO action_attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL)",
            (
                proposal.action_id,
                proposal.run_id,
                proposal.episode_id,
                proposal.task_id,
                proposal.contract_id,
                permit.nonce,
                proposal.attempt_ordinal,
                proposal.action.value,
                ActionDisposition.RESERVED.value,
                event.seq,
            ),
        )

    def _record_rejection(
        self, proposal: PrimitiveActionProposalV1, rejection: _Rejected
    ) -> GatewayResult:
        ledger = self._ledger
        try:
            with ledger.write_transaction(FaultPoint.REJECTION_WRITE) as conn:
                ledger.append_event(
                    conn,
                    "action_rejected",
                    {
                        "action_id": proposal.action_id,
                        "contract_id": proposal.contract_id,
                        "reason": rejection.reason.value,
                        "detail": rejection.detail,
                    },
                )
        except StaleWriterError:
            return self._in_process(proposal, GatewayBlockReason.STALE_WRITER)
        except (LedgerWriteError, MissionFailStopped):
            # The authority reason is kept in-process only; no durable rejection is claimed.
            ledger.enter_fail_stop("rejection_write_failed")
            return GatewayResult(
                proposal.action_id,
                None,
                None,
                GatewayBlockReason.AUDIT_UNAVAILABLE,
                durable=False,
                fail_stop=True,
            )
        return GatewayResult(proposal.action_id, None, None, rejection.reason, durable=True)

    def _in_process(
        self,
        proposal: PrimitiveActionProposalV1,
        reason: GatewayBlockReason,
        *,
        fail_stop: bool = False,
    ) -> GatewayResult:
        return GatewayResult(
            proposal.action_id, None, None, reason, durable=False, fail_stop=fail_stop
        )

    def _unknown(
        self,
        proposal: PrimitiveActionProposalV1,
        cause: str,
        *,
        action_result: ActionResult | None = None,
    ) -> GatewayResult:
        """Fail-stop after a possible dispatch; persist UNKNOWN/hold only if a fresh write works.

        The best-effort write is never relied on: if it fails, the durable row stays RESERVED
        and the next verified restore converts it to UNKNOWN and RECOVERY_HOLD.
        """

        ledger = self._ledger
        ledger.enter_fail_stop(f"unknown_dispatch:{cause}")
        durable = False
        try:
            with ledger.write_transaction(
                FaultPoint.UNKNOWN_WRITE, allow_in_fail_stop=True
            ) as conn:
                _settle(conn, proposal.action_id, ActionDisposition.UNKNOWN, None, cause)
                ledger.revoke_open_authority(conn, f"unknown_dispatch:{cause}")
                conn.execute("UPDATE mission SET state = ?", (MissionState.RECOVERY_HOLD.value,))
                ledger.append_event(
                    conn, "action_unknown", {"action_id": proposal.action_id, "cause": cause}
                )
            durable = True
        except (LedgerWriteError, StaleWriterError):
            durable = False
        return GatewayResult(
            proposal.action_id,
            ActionDisposition.UNKNOWN if durable else None,
            action_result,
            GatewayBlockReason.UNKNOWN_DISPATCH,
            durable=durable,
            fail_stop=True,
        )


class PermitIssuer(Protocol):
    """Manager-side authority that owns the active contract and mints permits."""

    def next_proposal(self, action: PrimitiveAction) -> PrimitiveActionProposalV1:
        """Derive a proposal from the actual active Manager contract."""

    def issue_permit(self, proposal: PrimitiveActionProposalV1) -> ActionPermitRef:
        """Mint one single-use permit or raise ``GatewayStop``."""


class ContractBoundPrimitiveActionExecutor:
    """Duck-typed ``execute(action) -> ActionResult`` seam for the existing ``SkillRunner``.

    Genuine focus/stop/rate blocks keep their legacy blocked results; every authority,
    integrity or audit failure raises ``GatewayStop`` for the Manager task executor.
    """

    def __init__(self, issuer: PermitIssuer, gateway: AuthorizedInputGateway) -> None:
        self._issuer = issuer
        self._gateway = gateway

    def execute(self, action: PrimitiveAction) -> ActionResult:
        proposal = self._issuer.next_proposal(action)
        permit = self._issuer.issue_permit(proposal)
        result = self._gateway.execute(proposal, permit)
        if result.block_reason is None and result.action_result is not None:
            return result.action_result
        if result.block_reason in _PHYSICAL_BLOCK_REASONS.values() and not result.fail_stop:
            assert result.action_result is not None
            return result.action_result
        assert result.block_reason is not None
        raise GatewayStop(
            result.block_reason,
            durable=result.durable,
            fail_stop=result.fail_stop,
            action_id=result.action_id,
        )


def _require_exact_dry_run(input_executor: object) -> None:
    """Closed allowlist: exact classes only, no subclass, wrapper or per-instance override."""

    if type(input_executor) is not InputExecutor:
        raise RealBackendNotPermitted(REAL_BACKEND_NOT_PERMITTED)
    backend = input_executor.backend
    if type(backend) not in S0_ALLOWED_BACKEND_TYPES:
        raise RealBackendNotPermitted(REAL_BACKEND_NOT_PERMITTED)
    if "send" in vars(backend) or "execute" in vars(input_executor):
        raise RealBackendNotPermitted(REAL_BACKEND_NOT_PERMITTED)


def _settle(
    conn: sqlite3.Connection,
    action_id: str,
    disposition: ActionDisposition,
    block_reason: GatewayBlockReason | None,
    detail: str | None = None,
) -> None:
    reason = detail if block_reason is None else block_reason.value
    cursor = conn.execute(
        "UPDATE action_attempts SET disposition = ?, block_reason = ? "
        "WHERE action_id = ? AND disposition = ?",
        (disposition.value, reason, action_id, ActionDisposition.RESERVED.value),
    )
    if cursor.rowcount != 1:
        raise LedgerWriteError(f"attempt {action_id} is not RESERVED")


def _json_list(raw: str) -> list[str]:
    value = json.loads(raw)
    return [str(item) for item in value]
