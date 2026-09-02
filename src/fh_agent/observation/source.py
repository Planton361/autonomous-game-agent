"""Runtime source boundary for canonical observations."""

from collections.abc import Sequence
from typing import Protocol

from fh_agent.observation.schemas import Observation


class ObservationSource(Protocol):
    """Provides one fully formed canonical observation at a time."""

    def observe(self) -> Observation:
        """Return the next canonical observation."""


class ObservationSourceExhausted(RuntimeError):
    """Raised when an observation source has no observation remaining."""


class SequenceObservationSource:
    """Deterministic observation source backed by a fixed supplied sequence."""

    def __init__(self, observations: Sequence[Observation]) -> None:
        self._observations = tuple(observations)
        self._next_index = 0

    def observe(self) -> Observation:
        if self._next_index >= len(self._observations):
            raise ObservationSourceExhausted

        observation = self._observations[self._next_index]
        self._next_index += 1
        return observation
