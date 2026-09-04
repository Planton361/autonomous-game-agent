"""Compose the local bridge-assisted ingress with the bounded hierarchy runtime."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fh_agent.bridge.evidence_sync import EventLogBridgeScreenshotEvidenceLookup
from fh_agent.bridge.jsonl_payload_source import JsonlBridgePayloadSource
from fh_agent.bridge.observation_source import BridgeObservationSource
from fh_agent.game.input_executor import InputExecutor
from fh_agent.manager.orchestrator import ManagerOrchestrator
from fh_agent.manager.replan_loop import (
    HierarchicalReplanLoopResult,
    HierarchicalReplanLoopRunner,
    ReplanLoopStepIds,
)


@dataclass(frozen=True, slots=True)
class BridgeAssistedRuntimeResult:
    """Audit paths and the exact bounded hierarchy result for one bridge-assisted run."""

    run_id: str
    feed_path: Path
    event_log_path: Path
    loop_result: HierarchicalReplanLoopResult


def run_bridge_assisted_bounded(
    loop_runner: HierarchicalReplanLoopRunner,
    orchestrator: ManagerOrchestrator,
    input_executor: InputExecutor,
    initial_memory_summary: Mapping[str, Any],
    *,
    run_id: str,
    feed_path: Path,
    event_log_path: Path,
    step_ids: Sequence[ReplanLoopStepIds],
    created_at: str | None = None,
) -> BridgeAssistedRuntimeResult:
    """Run the configured bounded hierarchy from the concrete bridge-assisted feed."""

    payload_source = JsonlBridgePayloadSource(feed_path)
    screenshot_lookup = EventLogBridgeScreenshotEvidenceLookup(event_log_path)
    observation_source = BridgeObservationSource(
        payload_source,
        run_id=run_id,
        expected_run_mode="bridge-assisted",
        screenshot_evidence_lookup=screenshot_lookup,
    )
    loop_result = loop_runner.run_bounded(
        orchestrator,
        observation_source,
        input_executor,
        initial_memory_summary,
        run_id=run_id,
        step_ids=step_ids,
        created_at=created_at,
    )
    return BridgeAssistedRuntimeResult(
        run_id=run_id,
        feed_path=feed_path,
        event_log_path=event_log_path,
        loop_result=loop_result,
    )
