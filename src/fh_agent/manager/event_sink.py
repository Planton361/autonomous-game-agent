from typing import Protocol

from fh_agent.manager.task_events import TaskCompletionEvent


class ManagerEventSink(Protocol):
    """Port for recording manager events without choosing a persistence backend."""

    def record_task_completion(self, event: TaskCompletionEvent) -> None:
        """Record a completed task event."""


class InMemoryManagerEventSink:
    """In-memory event sink for tests and dry-run workflows."""

    def __init__(self) -> None:
        self._task_completions: list[TaskCompletionEvent] = []

    def record_task_completion(self, event: TaskCompletionEvent) -> None:
        self._task_completions.append(event)

    def list_task_completions(self) -> list[TaskCompletionEvent]:
        return list(self._task_completions)

    def clear(self) -> None:
        self._task_completions.clear()
