from collections.abc import Callable
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

CheckSeverity = Literal["info", "warning", "error"]


class FixedResolution(BaseModel):
    """Configured game window size for a future controlled run."""

    model_config = ConfigDict(extra="forbid")

    width: int | None = None
    height: int | None = None


class LiveRunPreflightConfig(BaseModel):
    """Static safety configuration for a controlled live-run preflight only."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    runs_dir: Path
    evidence_dir: Path
    run_id: str | None = None
    no_spoiler_mode: bool = True
    emergency_stop_required: bool = True
    focus_guard_required: bool = True
    fixed_resolution: FixedResolution | None = None
    live_inputs_enabled: bool = False
    bridge_hidden_state_enabled: bool = False
    debug_oracle_enabled: bool = False


class PreflightCheckResult(BaseModel):
    """One local preflight check result."""

    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    message: str
    severity: CheckSeverity


class LiveRunPreflightResult(BaseModel):
    """Aggregated result for a controlled live-run readiness check."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    checks: tuple[PreflightCheckResult, ...]
    run_id: str | None
    notes: tuple[str, ...] = ()

    def to_deterministic_json(self) -> str:
        return self.model_dump_json(exclude_none=False)


def run_live_preflight(
    config: LiveRunPreflightConfig,
    *,
    run_id_factory: Callable[[], str] | None = None,
) -> LiveRunPreflightResult:
    """Check static prerequisites without starting live automation or capture."""

    run_id = _resolve_run_id(config.run_id, run_id_factory)
    checks = [
        _check_run_id(run_id),
        _check_writable_directory("run_directory_writable", config.runs_dir, run_id),
        _check_writable_directory("evidence_directory_writable", config.evidence_dir, run_id),
        _boolean_required(
            "no_spoiler_mode",
            config.no_spoiler_mode,
            "no-spoiler mode is active",
            "no-spoiler mode must be active for controlled live runs",
        ),
        _boolean_required(
            "emergency_stop_required",
            config.emergency_stop_required,
            "emergency stop is required by configuration",
            "emergency stop must be required before any live run",
        ),
        _boolean_required(
            "focus_guard_required",
            config.focus_guard_required,
            "focus guard is required by configuration",
            "focus guard must be required before any live run",
        ),
        _check_fixed_resolution(config.fixed_resolution),
        _check_live_inputs_disabled(config.live_inputs_enabled),
        _check_hidden_state_sources(
            bridge_hidden_state_enabled=config.bridge_hidden_state_enabled,
            debug_oracle_enabled=config.debug_oracle_enabled,
        ),
    ]
    ok = all(check.passed or check.severity != "error" for check in checks)
    return LiveRunPreflightResult(
        ok=ok,
        checks=tuple(checks),
        run_id=run_id,
        notes=("preflight only; no game, bridge, screenshots, inputs, LLM, or RL started",),
    )


def _resolve_run_id(
    run_id: str | None,
    run_id_factory: Callable[[], str] | None,
) -> str | None:
    if run_id is not None and run_id.strip():
        return run_id
    factory = run_id_factory or (lambda: f"live-preflight-{uuid4().hex}")
    generated = factory()
    if generated.strip():
        return generated
    return None


def _check_run_id(run_id: str | None) -> PreflightCheckResult:
    if run_id:
        return PreflightCheckResult(
            name="run_id",
            passed=True,
            message=f"run_id is available: {run_id}",
            severity="info",
        )
    return PreflightCheckResult(
        name="run_id",
        passed=False,
        message="run_id is missing and could not be generated",
        severity="error",
    )


def _check_writable_directory(
    name: str,
    base_dir: Path,
    run_id: str | None,
) -> PreflightCheckResult:
    if run_id is None:
        return PreflightCheckResult(
            name=name,
            passed=False,
            message="run_id is required before checking a per-run directory",
            severity="error",
        )

    run_dir = base_dir / run_id
    probe_path = run_dir / ".preflight_write_probe"
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("preflight\n", encoding="utf-8")
        probe_path.unlink()
    except OSError as exc:
        return PreflightCheckResult(
            name=name,
            passed=False,
            message=f"{run_dir} is not writable: {exc}",
            severity="error",
        )

    return PreflightCheckResult(
        name=name,
        passed=True,
        message=f"{run_dir} is writable",
        severity="info",
    )


def _boolean_required(
    name: str,
    value: bool,
    passed_message: str,
    failed_message: str,
) -> PreflightCheckResult:
    return PreflightCheckResult(
        name=name,
        passed=value,
        message=passed_message if value else failed_message,
        severity="info" if value else "error",
    )


def _check_fixed_resolution(
    fixed_resolution: FixedResolution | None,
) -> PreflightCheckResult:
    if fixed_resolution is None:
        return PreflightCheckResult(
            name="fixed_resolution",
            passed=False,
            message="fixed_resolution is required before a controlled live run",
            severity="error",
        )
    if fixed_resolution.width is None or fixed_resolution.height is None:
        return PreflightCheckResult(
            name="fixed_resolution",
            passed=False,
            message="fixed_resolution must include width and height",
            severity="error",
        )
    if fixed_resolution.width <= 0 or fixed_resolution.height <= 0:
        return PreflightCheckResult(
            name="fixed_resolution",
            passed=False,
            message="fixed_resolution width and height must be greater than zero",
            severity="error",
        )
    return PreflightCheckResult(
        name="fixed_resolution",
        passed=True,
        message=f"fixed resolution is set: {fixed_resolution.width}x{fixed_resolution.height}",
        severity="info",
    )


def _check_live_inputs_disabled(live_inputs_enabled: bool) -> PreflightCheckResult:
    if live_inputs_enabled:
        return PreflightCheckResult(
            name="live_inputs_enabled",
            passed=False,
            message="live inputs are enabled; preflight must not execute live controls",
            severity="error",
        )
    return PreflightCheckResult(
        name="live_inputs_enabled",
        passed=True,
        message="live inputs are disabled",
        severity="info",
    )


def _check_hidden_state_sources(
    *,
    bridge_hidden_state_enabled: bool,
    debug_oracle_enabled: bool,
) -> PreflightCheckResult:
    enabled_sources = []
    if bridge_hidden_state_enabled:
        enabled_sources.append("bridge_hidden_state")
    if debug_oracle_enabled:
        enabled_sources.append("debug_oracle")

    if enabled_sources:
        return PreflightCheckResult(
            name="hidden_state_sources_disabled",
            passed=False,
            message=f"hidden-state sources must be disabled: {', '.join(enabled_sources)}",
            severity="error",
        )
    return PreflightCheckResult(
        name="hidden_state_sources_disabled",
        passed=True,
        message="bridge hidden-state and debug-oracle sources are disabled",
        severity="info",
    )
