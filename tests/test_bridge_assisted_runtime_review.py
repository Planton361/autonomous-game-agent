from pathlib import Path
from typing import cast

import pytest

from fh_agent.body.primitive_actions import PrimitiveAction
from fh_agent.bridge_assisted_runtime import (
    BridgeAssistedRuntimeConfig,
    assemble_bridge_assisted_runtime,
)
from fh_agent.game.window import WindowTarget
from fh_agent.manager.hierarchical_step import HierarchicalTaskStepResult
from fh_agent.manager.replan_loop import HierarchicalReplanLoopResult, ReplanLoopStepIds
from fh_agent.perception.screen_capture import DummyScreenCapture
from fh_agent.planner.llm_client import FakeLLMClient


class EarlyStopLoopRunner:
    def run_bounded(self, *args: object, **kwargs: object) -> HierarchicalReplanLoopResult:
        return HierarchicalReplanLoopResult(
            step_results=(cast(HierarchicalTaskStepResult, object()),),
            final_memory_summary={},
            stop_reason="manager_stop",
        )


def config_for_review(
    tmp_path: Path,
    *,
    allow_real_input: bool = False,
    input_min_interval_seconds: float = 0.0,
) -> BridgeAssistedRuntimeConfig:
    return BridgeAssistedRuntimeConfig(
        run_id="run-1",
        exchange_directory=tmp_path / "exchange",
        feed_path=tmp_path / "feed" / "bridge.jsonl",
        event_log_path=tmp_path / "runs" / "run-1" / "events.jsonl",
        screenshots_root=tmp_path / "screenshots",
        stop_file_path=tmp_path / "runs" / "run-1" / "STOP",
        local_llm_base_url="http://127.0.0.1:8080/v1",
        local_llm_model="local-test-model",
        target_window=WindowTarget(title="Fear & Hunger"),
        key_bindings={PrimitiveAction.CONFIRM: "Return"},
        allow_real_input=allow_real_input,
        input_min_interval_seconds=input_min_interval_seconds,
    )


def test_task_attempt_accounting_reports_executed_early_stop_attempts(tmp_path: Path) -> None:
    config = config_for_review(tmp_path)
    runtime = assemble_bridge_assisted_runtime(
        config,
        capture=DummyScreenCapture(),
        llm_client=FakeLLMClient(responses=[]),
    )
    runtime.loop_runner = EarlyStopLoopRunner()  # type: ignore[assignment]
    step_ids = (
        ReplanLoopStepIds("task-1", "completion-1"),
        ReplanLoopStepIds("task-2", "completion-2"),
        ReplanLoopStepIds("task-3", "completion-3"),
    )

    result = runtime.run_bounded({}, step_ids=step_ids)

    assert len(step_ids) == config.limits.max_task_attempts == 3
    assert result.loop_result.stop_reason == "manager_stop"
    assert len(result.loop_result.step_results) == 1
    assert result.task_attempts == 1


def test_real_input_rejects_zero_rate_limit_but_dry_run_allows_it(tmp_path: Path) -> None:
    dry_run_config = config_for_review(
        tmp_path,
        allow_real_input=False,
        input_min_interval_seconds=0.0,
    )
    assert dry_run_config.input_min_interval_seconds == 0.0

    with pytest.raises(ValueError, match="positive input_min_interval_seconds"):
        config_for_review(
            tmp_path,
            allow_real_input=True,
            input_min_interval_seconds=0.0,
        )
