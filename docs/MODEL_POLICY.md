# Model policy

| Profile | Use |
| --- | --- |
| `economy` | Narrow mechanical/read-only task with simple objective verification |
| `standard` | Clearly specified normal implementation/debugging milestone |
| `critical` | Architecture ambiguity, workflow/bootstrap, security/data integrity, difficult migration, scientific result logic, adversarial review |

The actually available model is selected at session start; model availability is not project semantics. A model change never changes Scope, Autonomy, or Definition of Done.

Use one executing agent by default. Use subagents only for independent work; writing parallelism requires separate worktrees and disjoint paths. A reviewer is recommended for medium risk and required for high risk; the reviewer remains read-only.

M-000R profile: `critical`. M-001 is recommended as `standard`, risk `medium`, with independent review recommended.
