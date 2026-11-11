"""Typed MRIC-S0 Mission Run states, dispositions and ledger errors (Issue #184)."""

from dataclasses import dataclass
from enum import StrEnum


class MissionState(StrEnum):
    """Outer Mission Run state; terminal states are irreversible."""

    PREPARED = "PREPARED"
    ACTIVE = "ACTIVE"
    RECOVERY_HOLD = "RECOVERY_HOLD"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_BUDGET = "TERMINAL_BUDGET"
    TERMINAL_STOPPED = "TERMINAL_STOPPED"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    TERMINAL_INTEGRITY_STOP = "TERMINAL_INTEGRITY_STOP"
    TERMINAL_CONTAMINATED = "TERMINAL_CONTAMINATED"

    @property
    def is_terminal(self) -> bool:
        return self.value.startswith("TERMINAL_")


class EpisodeState(StrEnum):
    """Life Episode state; death transitions are declared but deferred beyond S0."""

    OPEN = "OPEN"
    RECOVERY_HOLD = "RECOVERY_HOLD"
    CLOSED_STOP = "CLOSED_STOP"
    DEATH_OBSERVED = "DEATH_OBSERVED"
    CLOSED_DEATH = "CLOSED_DEATH"


class ContractStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    REVOKED = "REVOKED"


class ActionDisposition(StrEnum):
    """Durable disposition of one reserved primitive action attempt."""

    RESERVED = "RESERVED"
    SENT = "SENT"
    NOT_SENT = "NOT_SENT"
    UNKNOWN = "UNKNOWN"


class RecoveryDecision(StrEnum):
    resume_same_run = "resume_same_run"
    require_observation_and_review = "require_observation_and_review"
    terminal_integrity_stop = "terminal_integrity_stop"
    quarantine = "quarantine"


class GatewayBlockReason(StrEnum):
    """Typed reasons why the final input boundary refused or could not settle an action."""

    MISSING_AUTHORITY = "missing_authority"
    WRONG_RUN = "wrong_run"
    WRONG_EPISODE = "wrong_episode"
    WRONG_TASK = "wrong_task"
    STALE_CONTRACT = "stale_contract"
    REVOKED = "revoked"
    EXPIRED = "expired"
    REPLAYED = "replayed"
    ACTION_NOT_ALLOWED = "action_not_allowed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    FOCUS_LOST = "focus_lost"
    STOP_TRIGGERED = "stop_triggered"
    RATE_LIMITED = "rate_limited"
    AUDIT_UNAVAILABLE = "audit_unavailable"
    IDENTITY_MISMATCH = "identity_mismatch"
    STALE_WRITER = "stale_writer"
    MISSION_NOT_ACTIVE = "mission_not_active"
    UNKNOWN_DISPATCH = "unknown_dispatch"


class FaultPoint(StrEnum):
    """Closed set of test-only fault-injection points at ledger/gateway operation boundaries.

    A fault hook receives only one of these values. It never receives an input backend,
    executor or ledger handle, so it has no way to send input.
    """

    MISSION_WRITE = "mission_write"
    EPISODE_WRITE = "episode_write"
    CONTRACT_WRITE = "contract_write"
    PERMIT_WRITE = "permit_write"
    REJECTION_WRITE = "rejection_write"
    RESERVATION_WRITE = "reservation_write"
    AFTER_RESERVATION_COMMIT = "after_reservation_commit"
    DISPOSITION_WRITE = "disposition_write"
    UNKNOWN_WRITE = "unknown_write"
    RECOVERY_WRITE = "recovery_write"


@dataclass(frozen=True, slots=True)
class LifeEpisodeV1:
    episode_id: str
    run_id: str
    ordinal: int
    state: EpisodeState


@dataclass(frozen=True, slots=True)
class ActionAttemptRecord:
    action_id: str
    run_id: str
    episode_id: str
    task_id: str
    contract_id: str
    attempt_ordinal: int
    action: str
    disposition: ActionDisposition
    block_reason: str | None
    reconciliation_ref: str | None


@dataclass(frozen=True, slots=True)
class RunEventRecord:
    seq: int
    event_id: str
    run_id: str
    kind: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class BudgetCounter:
    name: str
    limit: int
    used: int

    @property
    def remaining(self) -> int:
        return self.limit - self.used


class MissionLedgerError(RuntimeError):
    """Base class for fail-closed Mission ledger refusals."""


class MissionActivationRefused(MissionLedgerError):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = list(reasons)
        super().__init__("mission activation refused: " + ", ".join(self.reasons))


class MissionExistsError(MissionLedgerError):
    pass


class MissionPathError(MissionLedgerError):
    pass


class IdentityMismatchError(MissionLedgerError):
    def __init__(self, fields: list[str]) -> None:
        self.fields = list(fields)
        super().__init__("frozen identity mismatch: " + ", ".join(self.fields))


class UnsupportedLedgerSchema(MissionLedgerError):
    pass


class LedgerIntegrityError(MissionLedgerError):
    pass


class StaleWriterError(MissionLedgerError):
    pass


class LedgerWriteError(MissionLedgerError):
    """A ledger write transaction failed and was rolled back; nothing from it is durable."""


class MissionFailStopped(MissionLedgerError):
    """This process handle is fail-stopped; no further dispatch or task is allowed."""


class BudgetExhausted(MissionLedgerError):
    pass


class InvalidMissionTransition(MissionLedgerError):
    pass


class RecoveryRefused(MissionLedgerError):
    pass
