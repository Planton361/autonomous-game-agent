from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowTarget:
    """Configured identity of the window that may receive inputs."""

    title: str
    process_name: str | None = None
    window_id: str | None = None
    class_name: str | None = None


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """Observed window identity, supplied by future OS-specific adapters."""

    title: str
    process_name: str | None = None
    handle: str | None = None
    window_id: str | None = None
    class_name: str | None = None
