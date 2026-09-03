# Operational Implementation Map

Normative target architecture: [`canonical/02_ARCHITECTURE_CANONICAL.md`](canonical/02_ARCHITECTURE_CANONICAL.md).

This document maps current repository components to that architecture. It does not replace or rewrite the canonical architecture.

| Concern | Repository path |
| --- | --- |
| Perception / capture | `src/fh_agent/perception/` |
| Observation contracts/source | `src/fh_agent/observation/` |
| No-spoiler bridge/firewall | `src/fh_agent/bridge/` |
| Cortex/providers/context | `src/fh_agent/planner/` |
| Manager/executive/contracts | `src/fh_agent/manager/` |
| Body/actions/heuristic skills | `src/fh_agent/body/` |
| Input safety/execution | `src/fh_agent/game/` |
| Independent verification | `src/fh_agent/verifier/` |
| Evidence/memory/persistence | `src/fh_agent/memory/` |
| Evaluation/audit/smoke tooling | `src/fh_agent/evals/` |
| Learning scaffolding | `src/fh_agent/rl/` |

## Retrofit-baseline runtime spine

At the M-000R retrofit baseline, the implemented Phase-C spine is:

```text
ObservationSource
→ SkillRunner
→ SkillStep
→ contract action mask
→ InputExecutor
→ canonical ActionResult
→ durable action_result event
→ post-action Observation
→ OutcomeVerifier
→ verifier_result
→ VerifiedReward
```

`ManagerStopResult` exists as a separate Manager/runtime control-plane stop. At the retrofit baseline it is not yet propagated to `TaskCompletion`.

## Future / not fully integrated

- Temporal State
- bounded Reflex
- complete production live Observation/Input ports
- full Cortex → Manager → Body → Verifier vertical slice
- learned/certified Body
- cross-environment transfer

This map makes no architectural refactor.
