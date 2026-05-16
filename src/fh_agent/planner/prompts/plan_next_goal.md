Plan the next high-level goal from the supplied CortexContext.

The CortexContext is the only allowed source of game knowledge for this request.
Do not use free-form memory, prior game knowledge, external facts, or unstated
assumptions as factual inputs.

Output JSON fields:
- current_belief_state: list of fact or hypothesis objects. Facts require evidence_ids.
- open_questions: unresolved visible-state questions.
- next_goal: one concise high-level goal, not a key sequence.
- selected_skill: one universal reusable skill name.
- success_condition: visible outcome labels.
- risk_limit: avoid_known_dangers and max_danger_score.
- memory_updates_requested: only evidence-backed requests.

Do not add fields outside the schema. Do not output direct controls.
