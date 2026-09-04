"""Ordering adapter that returns one already-consumed canonical observation first."""

from fh_agent.observation.schemas import Observation
from fh_agent.observation.source import ObservationSource


class PrimedObservationSource:
    """Return the supplied initial observation once before delegating to a source."""

    def __init__(
        self,
        initial_observation: Observation,
        remaining_source: ObservationSource,
    ) -> None:
        self._initial_observation = initial_observation
        self._remaining_source = remaining_source
        self._initial_available = True

    def observe(self) -> Observation:
        """Return the primed observation once, then delegate exactly one read."""

        if self._initial_available:
            self._initial_available = False
            return self._initial_observation
        return self._remaining_source.observe()
