"""Build ephemeral planning context from independently verified task outcomes."""

from collections.abc import Mapping, Sequence
from typing import Any

from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.verifier.schemas import VerifierStatus


class ReplanContextError(ValueError):
    """Raised when a completion cannot become an evidence-backed outcome note."""


def build_replan_memory_summary(
    base_memory_summary: Mapping[str, Any],
    completion_event: TaskCompletionEvent,
) -> dict[str, Any]:
    """Append one verifier-backed outcome note without mutating caller-owned context."""

    verifier_result = completion_event.verifier_result
    if verifier_result is None:
        msg = "replan context requires a verifier-backed completion"
        raise ReplanContextError(msg)

    if verifier_result.status not in {VerifierStatus.SUCCESS, VerifierStatus.FAILURE}:
        msg = "replan context requires a terminal verifier success or failure"
        raise ReplanContextError(msg)

    evidence_ids = list(verifier_result.evidence_ids)
    if not evidence_ids:
        msg = "replan context requires verifier evidence"
        raise ReplanContextError(msg)

    if verifier_result.status is VerifierStatus.SUCCESS:
        note = f"Skill {completion_event.selected_skill} completed with verifier status success."
    else:
        failure_kind = verifier_result.failure_kind
        if failure_kind is None:
            msg = "verifier failure requires a failure kind"
            raise ReplanContextError(msg)
        note = (
            f"Skill {completion_event.selected_skill} "
            f"completed with verifier failure {failure_kind.value}."
        )

    existing_outcomes = base_memory_summary.get("recent_skill_outcomes", [])
    if isinstance(existing_outcomes, str | bytes | bytearray) or not isinstance(
        existing_outcomes, Sequence
    ):
        msg = "recent_skill_outcomes must be a non-string sequence"
        raise ReplanContextError(msg)

    memory_summary = dict(base_memory_summary)
    outcomes = list(existing_outcomes)
    outcomes.append(
        {
            "status": "observed_fact",
            "note": note,
            "evidence_ids": evidence_ids,
        }
    )
    memory_summary["recent_skill_outcomes"] = outcomes
    return memory_summary
