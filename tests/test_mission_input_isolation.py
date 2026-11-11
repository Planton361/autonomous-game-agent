"""AC12: S0 modules cannot reach a real input sender (static audit + runtime allowlist)."""

import ast
import inspect
from pathlib import Path

import pytest
from mission_fixtures import FaultHook, dry_run_executor, new_ledger

import fh_agent.game.authorized_input_gateway as gateway_module
from fh_agent.game.authorized_input_gateway import (
    REAL_BACKEND_NOT_PERMITTED,
    S0_ALLOWED_BACKEND_TYPES,
    AuthorizedInputGateway,
    RealBackendNotPermitted,
)
from fh_agent.game.input_executor import DryRunInputBackend, InputExecutor
from fh_agent.mission.state import FaultPoint

SRC = Path(__file__).resolve().parents[1] / "src" / "fh_agent"
S0_MODULES = [
    *sorted((SRC / "mission").glob("*.py")),
    SRC / "manager" / "action_authority.py",
    SRC / "game" / "authorized_input_gateway.py",
]
FORBIDDEN_IMPORTS = {"subprocess", "fh_agent.game.xdotool_adapters", "os", "ctypes", "pty"}
FORBIDDEN_NAMES = {"XdotoolInputBackend", "XdotoolFocusGuard", "_send_single_directional_tap"}


@pytest.mark.parametrize("path", S0_MODULES, ids=lambda path: path.name)
def test_s0_modules_import_no_os_input_capability(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)

    assert not imported & FORBIDDEN_IMPORTS
    assert not names & FORBIDDEN_NAMES
    assert "xdotool" not in path.read_text(encoding="utf-8").lower()


def test_allowlist_is_closed_to_the_exact_production_dry_run_backend() -> None:
    assert S0_ALLOWED_BACKEND_TYPES == (DryRunInputBackend,)


def test_exact_dry_run_backend_is_accepted(tmp_path: Path) -> None:
    gateway = AuthorizedInputGateway(new_ledger(tmp_path), dry_run_executor())

    assert type(gateway) is AuthorizedInputGateway


def test_dry_run_subclass_with_side_effect_sender_is_rejected(tmp_path: Path) -> None:
    class SideEffectBackend(DryRunInputBackend):
        def send(self, action: object) -> None:  # pragma: no cover - never reached
            raise AssertionError("must never be called")

    executor = dry_run_executor()
    executor.backend = SideEffectBackend()

    with pytest.raises(RealBackendNotPermitted, match=REAL_BACKEND_NOT_PERMITTED):
        AuthorizedInputGateway(new_ledger(tmp_path), executor)


def test_wrapper_and_instance_override_and_executor_subclass_are_rejected(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)

    class Wrapper:
        def __init__(self) -> None:
            self.actions: list[object] = []

        def send(self, action: object) -> None:  # pragma: no cover - never reached
            self.actions.append(action)

    wrapped = dry_run_executor()
    wrapped.backend = Wrapper()  # type: ignore[assignment]
    patched = dry_run_executor()
    patched.backend.send = lambda action: None  # type: ignore[method-assign]

    class LoggingExecutor(InputExecutor):
        pass

    base = dry_run_executor()
    subclassed = LoggingExecutor(
        base.target, base.focus_guard, DryRunInputBackend(), min_interval_seconds=0.0
    )

    for executor in (wrapped, patched, subclassed):
        with pytest.raises(RealBackendNotPermitted):
            AuthorizedInputGateway(ledger, executor)


def test_backend_swapped_after_construction_is_rejected_before_send(tmp_path: Path) -> None:
    ledger = new_ledger(tmp_path)
    executor = dry_run_executor()
    gateway = AuthorizedInputGateway(ledger, executor)

    class Swapped(DryRunInputBackend):
        pass

    executor.backend = Swapped()

    from mission_fixtures import open_contract

    from fh_agent.body.primitive_actions import PrimitiveAction
    from fh_agent.manager.action_authority import ManagerActionAuthority

    authority = ManagerActionAuthority(ledger)
    open_contract(authority)
    proposal = authority.next_proposal(PrimitiveAction.CONFIRM)
    with pytest.raises(RealBackendNotPermitted):
        gateway.execute(proposal, authority.issue_permit(proposal))
    assert executor.backend.actions == []
    assert ledger.attempts() == []


def test_fault_hook_receives_only_a_fault_point(tmp_path: Path) -> None:
    hook = FaultHook()
    new_ledger(tmp_path, fault_hook=hook)

    assert hook.reached
    assert all(type(point) is FaultPoint for point in hook.reached)
    call_sites = [
        line for line in inspect.getsource(gateway_module).splitlines() if "fault" in line.lower()
    ]
    assert all("backend" not in line and "_input_executor" not in line for line in call_sites)
