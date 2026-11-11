"""Execute one already-running Manager task through existing runtime boundaries."""

from dataclasses import dataclass

from fh_agent.game.authorized_input_gateway import GatewayStop
from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.action_authority import ManagerActionAuthority
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.runtime_stop import ManagerStopResult
from fh_agent.manager.scheduler import TaskSchedulerError
from fh_agent.manager.skill_catalog import SkillCatalog
from fh_agent.manager.skill_runner import SkillRunner, SkillRunResult
from fh_agent.manager.task_events import TaskCompletionEvent
from fh_agent.manager.verifier_catalog import VerifierCatalog
from fh_agent.mission.state import GatewayBlockReason
from fh_agent.observation.schemas import SkillResult
from fh_agent.observation.source import ObservationSource
from fh_agent.verifier.schemas import FailureKind


class TaskExecutionError(ValueError):
    """Raised when a task's resolved runtime binding violates its Manager contract."""


@dataclass(frozen=True, slots=True)
class TaskExecutionResult:
    """Result of one bounded attempt to execute the current Manager task."""

    task_id: str
    skill_run_result: SkillRunResult
    completion_event: TaskCompletionEvent | None


class ManagerTaskExecutor:
    """Compose existing Manager, Body, Verifier, and guarded runtime boundaries."""

    def __init__(
        self,
        *,
        skill_catalog: SkillCatalog | None = None,
        verifier_catalog: VerifierCatalog | None = None,
        skill_runner: SkillRunner | None = None,
        action_authority: ManagerActionAuthority | None = None,
    ) -> None:
        self._skill_catalog = skill_catalog or SkillCatalog.default()
        self._verifier_catalog = verifier_catalog or VerifierCatalog()
        self._skill_runner = skill_runner or SkillRunner()
        self._action_authority = action_authority

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
        """Run the current task once without changing Manager execution authority."""

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
        if self._action_authority is not None:
            return self._execute_with_authority(
                orchestrator,
                observation_source,
                input_executor,
                skill=skill,
                verifier=verifier,
                run_id=run_id,
                completion_event_id=completion_event_id,
                created_at=created_at,
            )
        skill_run_result = self._skill_runner.run(
            skill,
            observation_source,
            verifier=verifier,
            input_executor=input_executor,
        )
        completion_event = orchestrator.complete_from_skill_run(
            skill_run_result,
            task_id=task_spec.task_id,
            run_id=run_id,
            event_id=completion_event_id,
            created_at=created_at,
        )
        return TaskExecutionResult(
            task_id=task_spec.task_id,
            skill_run_result=skill_run_result,
            completion_event=completion_event,
        )

    def _execute_with_authority(
        self,
        orchestrator: ManagerOrchestrator,
        observation_source: ObservationSource,
        input_executor: InputExecutor,
        *,
        skill: object,
        verifier: object,
        run_id: str,
        completion_event_id: str,
        created_at: str | None,
    ) -> TaskExecutionResult:
        """Run the task under one durable Manager contract that never outlives this call.

        A ``GatewayStop`` becomes a genuine Manager stop that ends the bounded loop. Any other
        exception revokes the contract and its unconsumed permits before propagating; if that
        revocation cannot be persisted, the ledger handle is fail-stopped and
        ``ContractCleanupFailed`` is raised instead.
        """

        authority = self._action_authority
        assert authority is not None
        task_spec = orchestrator.scheduler.current_task.task_spec  # type: ignore[union-attr]
        contract = authority.open_contract(
            task_spec,
            skill.contract,  # type: ignore[attr-defined]
            verifier_id=type(verifier).__name__,
        )
        gateway_stop: GatewayStop | None = None
        try:
            try:
                skill_run_result = self._skill_runner.run(
                    skill,  # type: ignore[arg-type]
                    observation_source,
                    verifier=verifier,  # type: ignore[arg-type]
                    input_executor=input_executor,
                )
            except GatewayStop as stop:
                gateway_stop = stop
                skill_run_result = self._gateway_stop_result(skill, stop)
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

    def _gateway_stop_result(self, skill: object, stop: GatewayStop) -> SkillRunResult:
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
        skill_name = skill.contract.skill_name  # type: ignore[attr-defined]
        event_record = None
        event_logger = self._skill_runner.event_logger
        if event_logger is not None:
            event_record = event_logger.append_manager_stop(  # type: ignore[attr-defined]
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
