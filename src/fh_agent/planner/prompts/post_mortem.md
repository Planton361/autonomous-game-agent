Run a post-mortem review of the latest visible outcome from the supplied CortexContext and produce evidence-backed learning notes.

Hard limits:
- The CortexContext is the only allowed source of game knowledge for this request.
- Use only visible observations, evidence-backed facts, hypotheses, and observed outcomes supplied in the CortexContext.
- Do not use external Fear & Hunger facts, guides, wikis, datamining, map data, enemy databases, switches, variables, savegame internals, hidden-state data, or ending flags.
- Do not mention map_id, game_switches, game_variables, enemy_hp, enemy_database, savegame_variables, event IDs, event names, item database effects, or ending flags.
- Every game-related fact claim must cite evidence_ids.
- Notes with status observed_fact or validated_rule require evidence_ids.
- Missing evidence must become a note with status hypothesis.
- Generic gaming priors are allowed only as hypotheses.
- Do not output keys, key_sequence, primitive_actions, actions, or direct primitive action sequences.

Return only JSON matching PostMortemOutput:
- observed_outcome
- likely_causes
- evidence_backed_notes
- hypotheses
- next_safe_experiments
- memory_updates_requested
