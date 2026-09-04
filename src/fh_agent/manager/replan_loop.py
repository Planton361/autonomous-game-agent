"""Run a finite sequence of hierarchical attempts from verified outcomes only."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.hierarchical_step import (
    HierarchicalTaskStepResult,
    HierarchicalTaskStepRunner,
)
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_context import build_replan_memory_summary
from fh_agent.observation.source import ObservationSource

ReplanLoopStopReason = Literal["budget_exhausted", "manager_stop", "nonterminal"]


class ReplanLoopError(ValueError):
    """Raised when a terminal completion lacks a recognized outcome authority."""


@dataclass(frozen=True, slots=True)
class ReplanLoopStepIds:
    """Caller-owned identity contract for one bounded task attempt."""

    task_id: str
    completion_event_id: str
    planner_output_id: str | None = None
    planner_trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class HierarchicalReplanLoopResult:
    """Records every completed attempt and the final ephemeral planning context."""

    step_results: tuple[HierarchicalTaskStepResult, ...]
    final_memory_summary: dict[str, Any]
    stop_reason: ReplanLoopStopReason


class HierarchicalReplanLoopRunner:
    """Compose a caller-bounded sequence of existing hierarchical task attempts."""

    def __init__(self, step_runner: HierarchicalTaskStepRunner) -> None:
        self._step_runner = step_runner

    def run_bounded(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        initial_memory_summary: Mapping[str, Any],
        *,
        run_id: str,
        step_ids: Sequence[ReplanLoopStepIds],
        created_at: str | None = None,
    ) -> HierarchicalReplanLoopResult:
        """Run at most the supplied attempts, continuing only from verified terminals."""

        if not step_ids:
            msg = "replan loop requires at least one step ID contract"
            raise ReplanLoopError(msg)

        current_memory_summary: Mapping[str, Any] = initial_memory_summary
        step_results: list[HierarchicalTaskStepResult] = []

        for ids in step_ids:
            step_result = self._step_runner.run_once(
                orchestrator,
                observation_source,
                input_executor,
                current_memory_summary,
                task_id=ids.task_id,
                run_id=run_id,
                completion_event_id=ids.completion_event_id,
                planner_output_id=ids.planner_output_id,
                planner_trace_id=ids.planner_trace_id,
                created_at=created_at,
            )
            step_results.append(step_result)
            completion_event = step_result.execution_result.completion_event

            if completion_event is None:
                return HierarchicalReplanLoopResult(
                    step_results=tuple(step_results),
                    final_memory_summary=dict(current_memory_summary),
                    stop_reason="nonterminal",
                )

            if completion_event.manager_stop_result is not None:
                return HierarchicalReplanLoopResult(
                    step_results=tuple(step_results),
                    final_memory_summary=dict(current_memory_summary),
                    stop_reason="manager_stop",
                )

            if completion_event.verifier_result is None:
                msg = "terminal completion requires verifier or ManagerStop authority"
                raise ReplanLoopError(msg)

            current_memory_summary = build_replan_memory_summary(
                current_memory_summary,
                completion_event,
            )

        return HierarchicalReplanLoopResult(
            step_results=tuple(step_results),
            final_memory_summary=dict(current_memory_summary),
            stop_reason="budget_exhausted",
        )
