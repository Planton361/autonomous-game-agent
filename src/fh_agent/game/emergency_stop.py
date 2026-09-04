"""Fail-closed emergency-stop sources for guarded primitive input."""

from pathlib import Path
from typing import Protocol


class EmergencyStopCheck(Protocol):
    """Reports whether external emergency input must stop immediately."""

    def is_triggered(self) -> bool:
        """Return whether primitive input must be blocked."""


class StopFileEmergencyStopCheck:
    """Treat the presence of a caller-owned stop file as an emergency stop."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def is_triggered(self) -> bool:
        try:
            self._path.stat()
        except FileNotFoundError:
            return False
        except OSError:
            return True

        return True
