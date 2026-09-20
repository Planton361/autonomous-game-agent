---
name: scientific-python-reproducibility
description: Use when changing, executing, or evaluating scientific Python work that requires frozen contracts, reproducibility, provenance, and no-spoiler safeguards.
---

# Scientific Python reproducibility

Use uv and the committed lockfile. Keep code correctness, detector uncertainty, experiment
evidence, scientific interpretation, and accepted claims distinct. A passing unit or
integration test is not by itself a scientific result.

Before a confirmatory or otherwise inference-bearing experiment executes, use the frozen
contract named by the active Issue. Record proportional provenance as applicable:

- RQ and hypothesis;
- treatment and comparator;
- frozen model/controller/configuration identities;
- run mode, seeds and budgets;
- endpoints and decision rules;
- data/run IDs and commit identity;
- exclusions and stop conditions;
- analysis plan.

Do not silently change those elements after observing results. If a necessary change is
material, stop for the applicable decision/freeze gate or classify the run separately.

Record actual execution evidence, missingness/refusals/integrity cases, analysis outputs,
and limitations. Negative, null, or inconclusive results are legitimate outcomes; do not
rewrite the hypothesis to make them successes.

Do not admit contaminated data into eligible training. Preserve no-spoiler evidence rules,
run-mode separation, provenance, and the Mission Run identity/weight-freeze rules. Do not
begin RL work before detector targets are valid.

Evaluation consumes frozen evidence and may support, qualify, contradict, or leave a claim
unresolved. It does not automatically promote an experiment result into an accepted claim
or publication wording.
