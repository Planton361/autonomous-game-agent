# Fear & Hunger Pilot — Experiment Contract

## Status and research question

This document is the Phase 0 preregistration contract. It freezes what the pilot is intended to
measure before runtime integration or evaluation runs begin.

**Research question:** Under equal visible start states and action/time budgets, does a local
Cortex–Manager–heuristic Body hierarchy produce more evidence-grounded task progress than fixed
unplanned baselines without increasing deaths, unsafe inputs, false success, or no-spoiler
violations?

The pilot concerns Fear & Hunger only. It imposes no cross-game transfer requirement and supports
no cross-game generalization claim.

## Hypotheses

- **H1 (primary):** `cortex_manager_heuristic` has a higher contract success rate than
  `fixed_goal_heuristic` in screen-only runs.
- **H2:** It achieves greater evidence-grounded progress per 100 primitive actions than both
  baselines.
- **H3 (non-inferiority safety):** It does not materially increase death rate, focus/input safety
  violations, or false-success rate relative to `fixed_goal_heuristic`.
- **H4 (diagnostic):** Bridge-assisted visible fields improve grounding coverage or latency. This
  is reported as a separate cohort and is not evidence for screen-only H1–H3.

The small pilot is estimation-first: report effect sizes and 95% bootstrap confidence intervals.
Do not convert absence of significance into proof of equivalence.

## Conditions and baselines

| ID | Condition | Cortex | Manager | Body |
|---|---|---|---|---|
| `no_action` | Negative-control baseline | off | one fixed wait-only contract | `wait` only |
| `fixed_goal_heuristic` | Competent non-LLM baseline | off | fixed preregistered visible goals and normal contracts | same heuristic skills/safety path |
| `cortex_manager_heuristic` | Experimental condition | local LLM | full grounding/schedule/stop/replan authority | same heuristic skills/safety path |

The negative control estimates incidental progress and success-detector false positives. No
baseline grants an LLM direct primitive control. A bridge-assisted diagnostic repeats the
experimental condition only after the primary screen-only cohort and is analyzed separately.

## Experimental unit and pairing

One **run** is the experimental unit. A run begins after preflight at a preregistered, visibly
verified start-state card and ends at the first run stop condition. Conditions use the same set of
start-state cards, seeds, budgets, resolution, input timing, and model parameters where applicable.
Assignment order is randomized and recorded. Runs sharing a start-state card form a paired block.

The pilot minimum is 10 valid runs per primary condition. This number is a feasibility floor, not
a power claim. No confirmatory condition may stop early because interim results look favorable.
Replacement runs are allowed only for predeclared technical invalidation and retain their original
artifacts and exclusion record.

## Start state and budget

Start states must be established through ordinary visible game interaction or a documented manual
procedure; save internals may not be inspected. A start-state card contains a human-readable setup,
one or more reference screenshots, resolution, allowed initial UI state, and visible verification
checks. It must not encode a solution.

Default run limits are 900 seconds and 500 primitive actions. A task contract has its own smaller
step/time budget. The first reached limit wins. The exact frozen values in
`configs/experiments/pilot_fh.yaml` are authoritative for a run.

## Mandatory preflight

A run cannot start unless all of the following are recorded:

1. `run_id`, assigned condition, run mode, seed, and start-state card;
2. clean or explicitly diff-hashed working tree and full Git commit;
3. exact prompt bundle SHA-256 and canonical config SHA-256;
4. local model name and model/content-manifest SHA-256;
5. fixed window identity and resolution, focus guard, rate limit, and tested emergency stop;
6. empty/new run artifact directory and monotonic clock availability;
7. network isolation proof and local endpoint verification;
8. no-spoiler firewall/allowlist snapshot appropriate to the mode;
9. successful smoke of observation, event, and screenshot persistence.

Missing mandatory metadata prevents official classification; it is not filled in from memory after
the run.

## Procedure

1. Seal network access and perform preflight without opening spoiler-bearing material.
2. Establish and visibly verify the assigned start state.
3. Start immutable run logging before the first observation.
4. Execute exactly the assigned condition. Every primitive proposal and execution/rejection is
   linked to its contract and before/after evidence.
5. Let only the Manager declare contract success/failure, stop, or replan. A Cortex response is not
   a success label.
6. Stop on the first run stop condition and persist final screenshot, detector state, pending
   contract, and reason.
7. Validate artifacts, assign provisional run-mode/integrity labels, then conduct blinded manual
   outcome review from visible evidence only.
8. Freeze the run record before aggregate analysis.

## Stop and replan rules

Run-terminal conditions are emergency stop, focus loss during attempted input, death, no-spoiler
incident, network-isolation failure, corrupt/missing required log stream, 900 seconds, or 500
primitive actions. A terminal safety condition never triggers autonomous replanning.

Manager contract termination occurs on validated success, declared failure, timeout, no progress,
grounding loss, safety-filter deadlock, or contradiction between target and current visible state.
After closing the prior contract, the Manager may replan if the run remains valid and within budget.
Three consecutive contracts ending in `no_progress`, or a repeated identical visible-state/action
cycle above the configured loop threshold, stops the run as `stalled`.

## Outcome labeling and exclusions

Automated labels are provisional. A reviewer uses screenshots/events only and records
`success`, `failure`, or `indeterminate` plus evidence IDs. A second reviewer adjudicates every
claimed success in the pilot and a sampled set of failures. Disagreement remains reported.

A run is excluded from confirmatory analysis only for:

- contamination under `NO_SPOILER_PROTOCOL.md`;
- missing mandatory provenance or core artifacts;
- input directed at an unverified window;
- failure before the assigned condition begins;
- irrecoverably wrong start-state assignment.

Deaths, stalls, planner errors, grounding failures, timeouts, and Body failures are outcomes, not
exclusions. All exclusions remain in the run ledger with reasons. Debug and bridge-assisted runs
are never silently promoted into the primary screen-only cohort.

## Integrity gates before pilot execution

Phase 3 evaluation is blocked until Phase 2 demonstrates:

- a real measured screen-only OCR path;
- end-to-end grounding and closed-loop execution;
- executable skill/reward catalog consistency;
- one canonical reward representation;
- manually measured false-positive/false-negative rates for success detectors;
- 100% action-to-contract and action-to-evidence linkage in smoke artifacts;
- zero wrong-window inputs and zero no-spoiler violations;
- deterministic reconstruction of all mandatory hashes.

## Analysis and reporting

Use definitions from `METRICS.md`. Report per-run values, medians and interquartile ranges, means
where informative, paired differences by start-state block, and 95% bootstrap intervals. Publish
condition counts, invalid/excluded counts, contamination reasons, detector audit results, prompt/
config/model hashes, and known technical failures. Screen-only and bridge-assisted data receive
separate tables and plots.

Any post-freeze change to prompts, configuration, model bytes, start-state cards, metric formulas,
or outcome rules creates a new experiment version. It cannot be merged into the original cohort
without an explicitly labeled exploratory analysis.
