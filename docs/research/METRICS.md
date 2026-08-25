# Pilot Metrics and Baselines

## Measurement principles

The run is the unit of analysis; contracts and primitive actions are nested observations. Metrics
are computed only from durable events and visible evidence. Undefined denominators produce `null`,
not zero. Report numerator, denominator, estimate, and run-mode cohort. Do not pool screen-only,
bridge-assisted, debug, or contaminated data.

## Primary metrics

### Contract success rate

```text
review-confirmed successful contracts / all closed contracts
```

Timeout, grounding failure, safety deadlock, cancellation due to death, and indeterminate outcomes
remain in the denominator. Automated and manually confirmed rates are both reported; H1 uses the
manual label.

### Evidence-grounded progress per 100 actions

```text
100 * confirmed progress events / executed primitive actions
```

A progress event is a preregistered visible outcome: reaching a grounded visible target, obtaining
new visible dialogue/menu information, completing a visible interaction, or a visually confirmed
screen transition relevant to the active goal. Merely writing a screenshot/evidence record,
changing a perceptual hash, or repeating known text is not progress.

### Safety composite

Report each component separately; never hide it behind a single score:

- death runs / valid runs;
- wrong-window executed inputs / all executed inputs;
- focus-guard rejections / all primitive proposals;
- emergency stops / valid runs;
- safety-filter rejections / all primitive proposals;
- no-spoiler violations / all attempted runs.

Zero no-spoiler violations and zero wrong-window inputs are hard gates, not optimization targets.

### False-success rate

```text
automated successes rejected by manual visible-evidence review / automated successes reviewed
```

Also report false-negative rate from the preregistered audited sample of automated failures.

## Cortex metrics

- **Schema validity:** valid structured responses / Cortex responses.
- **Evidence grounding precision:** factual claims whose evidence supports the claim / reviewed
  factual claims.
- **Unsupported-claim rate:** factual claims without valid supporting evidence / factual claims.
- **Direct-control rejection count:** responses containing primitive controls or key sequences.
- **Planning latency:** monotonic milliseconds from frozen context to validated output.
- **Replan yield:** replans followed by confirmed progress before the next replan / replans.

A rejected Cortex response does not authorize a Body action.

## Manager metrics

- **Grounding coverage:** Cortex goals resolved to one typed, visible, evidence-linked target /
  validated goals submitted for grounding.
- **Contract validity:** contracts passing schema, catalog, reward, safety, and target checks /
  proposed contracts.
- **Stop latency:** primitive actions executed after the first visible evidence satisfying a
  terminal detector; target is zero for hard stops.
- **Replan count:** number of closed-contract-to-new-plan transitions per run.
- **Loop rate:** repeated identical state/action windows / evaluated windows, using the frozen
  perceptual equivalence and window length in configuration.
- **Budget compliance:** contracts ending at or before their step/time budget / closed contracts.

## Body and Reflex metrics

- **Skill success rate:** review-confirmed successes / invocations, stratified by skill.
- **Action efficiency:** executed primitives / confirmed successful contract.
- **No-progress action rate:** actions with no preregistered visible progress within the attribution
  window / executed actions.
- **Body decision latency:** milliseconds from grounded observation to primitive proposal.
- **Reflex trigger precision:** reviewed appropriate triggers / Reflex activations.
- **Reflex containment:** Reflex actions allowed by the active contract / Reflex actions; must be
  100%.
- **Hazard outcome rate:** deaths or combat entries within the configured attribution window after
  a hazard-handling decision / such decisions.

Reflex metrics are `null` until a Reflex condition is explicitly introduced in Phase 4.

## Perception and operational metrics

- OCR character error rate and exact-span accuracy on a held-out visible screenshot fixture set;
- UI-state classification macro F1 on labeled visible screenshots;
- visible-target precision/recall and grounding confidence calibration;
- observation coverage: actionable frames producing a valid observation / actionable frames;
- evidence linkage: records requiring evidence that contain resolvable evidence IDs / such records;
- artifact completeness: required artifact files present and valid / required files;
- closed-loop coverage: executed actions with before observation, contract, action result, and after
  observation / executed actions.

## Run-level secondary outcomes

- time and actions to first confirmed progress;
- confirmed unique visible room signatures (collision-audited, not interpreted as internal maps);
- new evidence-backed visible facts per hour;
- survival time and time to death;
- stalls, timeouts, grounding failures, and planner failures per run;
- repeated observed death-cause rate, using only visible outcome categories.

## Baseline interpretation

`no_action` measures environmental/UI drift and exposes loose success detectors. It should not
produce goal progress. `fixed_goal_heuristic` measures what the same Manager/Body safety and skill
stack achieves without an LLM planner. `cortex_manager_heuristic` differs by Cortex-driven goal and
skill selection while preserving Manager authority and the heuristic Body.

The bridge-assisted diagnostic is not a performance baseline. It estimates the perception/
grounding cost of screen-only operation and must retain its separate run-mode label.

## Aggregation rules

- Preserve raw counts and per-run data; macro-average across runs for headline rates.
- Use paired start-state blocks for condition contrasts.
- Bootstrap whole runs, not individual actions, for 95% intervals.
- Report median, IQR, and tail values for latency and action counts.
- Do not impute contaminated, excluded, aborted, or indeterminate runs.
- Correct no metrics retrospectively without versioning the metric specification and recomputing
  all conditions.
