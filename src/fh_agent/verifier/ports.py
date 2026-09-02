"""Generic independent visible-outcome verification port."""

from typing import Protocol

from fh_agent.observation.schemas import Observation
from fh_agent.verifier.schemas import VerifierResult


class OutcomeVerifier(Protocol):
    """Verify a visible before/after observation pair."""

    def verify(self, before: Observation, after: Observation) -> VerifierResult:
        """Return the independently verified outcome."""
