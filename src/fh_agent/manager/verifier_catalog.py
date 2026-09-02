"""Manager-side selection of independent visible-outcome verifiers."""

from dataclasses import dataclass
from math import isfinite

from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.manager.task_spec import TaskSpec
from fh_agent.skill_capabilities import DEFAULT_RUNTIME_SKILLS, UniversalSkillName
from fh_agent.verifier.dialogue import ContinueDialogueVerifier
from fh_agent.verifier.interaction import InteractVisibleObjectVerifier
from fh_agent.verifier.ports import OutcomeVerifier
from fh_agent.verifier.reach_target import ReachTargetVerifier

_REGISTERED_VERIFIER_SKILLS: tuple[UniversalSkillName, ...] = (
    "basic_reach_target",
    "continue_dialogue",
    "interact_visible_object",
)


class VerifierSelectionError(ValueError):
    """Raised when a TaskSpec cannot select an independent verifier safely."""


@dataclass(frozen=True, slots=True)
class VerifierCatalog:
    """Bind a Manager-validated task contract to its independent outcome verifier."""

    reach_target_tolerance_px: float = 4.0

    def __post_init__(self) -> None:
        if not isfinite(self.reach_target_tolerance_px) or self.reach_target_tolerance_px < 0:
            msg = "reach_target_tolerance_px must be finite and non-negative"
            raise ValueError(msg)
        if _REGISTERED_VERIFIER_SKILLS != DEFAULT_RUNTIME_SKILLS:
            msg = "default verifier catalog does not match the runtime capability contract"
            raise RuntimeError(msg)

    @property
    def registered_skills(self) -> tuple[UniversalSkillName, ...]:
        """Return the deterministic set of independently verifiable runtime skills."""

        return _REGISTERED_VERIFIER_SKILLS

    def for_task(self, task_spec: TaskSpec) -> OutcomeVerifier:
        """Return the verifier bound only to the already validated Manager contract."""

        if task_spec.selected_skill == "continue_dialogue":
            if task_spec.target is not None:
                raise VerifierSelectionError("continue_dialogue must not have a target")
            return ContinueDialogueVerifier()

        if task_spec.selected_skill == "basic_reach_target":
            if not isinstance(task_spec.target, VisibleScreenPointTarget):
                msg = "basic_reach_target requires a visible screen-point target"
                raise VerifierSelectionError(msg)
            return ReachTargetVerifier(
                target=task_spec.target,
                tolerance_px=self.reach_target_tolerance_px,
            )

        if task_spec.selected_skill == "interact_visible_object":
            if not isinstance(task_spec.target, VisibleObjectTarget):
                msg = "interact_visible_object requires a visible object target"
                raise VerifierSelectionError(msg)
            return InteractVisibleObjectVerifier(target=task_spec.target)

        raise VerifierSelectionError(
            f"no independent verifier registered for skill: {task_spec.selected_skill}"
        )
