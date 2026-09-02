from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType

from fh_agent.body.skills.basic_reach_target import BasicReachTargetSkill
from fh_agent.body.skills.continue_dialogue import ContinueDialogueSkill
from fh_agent.body.skills.interact_visible import InteractVisibleObjectSkill
from fh_agent.manager.skill_contracts import is_dialogue_observation
from fh_agent.manager.skill_runner import RunnableSkill
from fh_agent.manager.target_ref import VisibleObjectTarget, VisibleScreenPointTarget
from fh_agent.observation.schemas import Observation
from fh_agent.skill_capabilities import DEFAULT_RUNTIME_SKILLS, UniversalSkillName

SkillFactory = Callable[[object | None], RunnableSkill]


DEFAULT_SKILL_FACTORIES: MappingProxyType[UniversalSkillName, SkillFactory] = MappingProxyType(
    {
        "continue_dialogue": lambda task=None: ContinueDialogueSkill(),
        "interact_visible_object": lambda task=None: InteractVisibleObjectSkill(
            target=task if isinstance(task, VisibleObjectTarget) else None
        ),
        "basic_reach_target": lambda task=None: BasicReachTargetSkill(
            target=task if isinstance(task, VisibleScreenPointTarget) else None
        ),
    }
)


class SkillCatalogError(LookupError):
    """Raised when a skill cannot be found or selected deterministically."""


@dataclass(slots=True)
class SkillCatalog:
    """Small in-memory catalog for available universal body skills."""

    _factories: dict[UniversalSkillName, SkillFactory] = field(default_factory=dict)

    @classmethod
    def default(cls) -> SkillCatalog:
        factory_skills = tuple(sorted(DEFAULT_SKILL_FACTORIES))
        if factory_skills != DEFAULT_RUNTIME_SKILLS:
            msg = "default SkillCatalog factories do not match the runtime capability contract"
            raise RuntimeError(msg)
        return cls(_factories=dict(DEFAULT_SKILL_FACTORIES))

    def register(self, skill_name: UniversalSkillName, factory: SkillFactory) -> None:
        if not skill_name:
            msg = "skill_name must not be empty"
            raise ValueError(msg)
        self._factories[skill_name] = factory

    def get(self, skill_name: UniversalSkillName, *, task: object | None = None) -> RunnableSkill:
        try:
            factory = self._factories[skill_name]
        except KeyError as exc:
            msg = f"unknown skill: {skill_name}"
            raise SkillCatalogError(msg) from exc
        return factory(task)

    def list(self) -> list[UniversalSkillName]:
        return sorted(self._factories)

    def select(
        self,
        *,
        observation: Observation,
        task: object | None = None,
        skill_name: UniversalSkillName | None = None,
    ) -> RunnableSkill:
        if skill_name is not None:
            return self.get(skill_name, task=task)

        if is_dialogue_observation(observation):
            return self.get("continue_dialogue")
        if isinstance(task, VisibleObjectTarget):
            return self.get("interact_visible_object", task=task)
        if isinstance(task, VisibleScreenPointTarget):
            return self.get("basic_reach_target", task=task)

        msg = "no skill could be selected from visible observation and task"
        raise SkillCatalogError(msg)
