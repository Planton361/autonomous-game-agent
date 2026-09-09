# Direct View Capability Matrix

RA-3A capability gate — a technical view-capability statement, not a research result.
These are the 15 RA-003 §19.4 Required Views, each listed once. Dispositions are
closed: `direct-ready`, `direct-partial`, `requires-derived-index`,
`requires-structured-contract/review`. Direct means declared flat Properties,
not scientific validation. Partial does not claim the missing portion is implemented.

| Required view | Disposition | Available direct Properties | Missing lookup/structure | Why no inference from prose/counts | Later stage / boundary |
| --- | --- | --- | --- | --- | --- |
| Literature by Component — with role | direct-partial | Five research-role lists; atlas_refs | Resolve source identity and Component type, then role-preserving multi-hop links | A raw Component link does not show evaluation of our implementation | RA-3B after an explicit lookup contract |
| Literature by Process | direct-partial | research-role lists; process_refs on applicable profiles | Paper → ReadingNote/Finding → RQ → Process lookup and type resolution | Association does not imply a study investigates a Process | RA-3B |
| Literature by RQ | direct-partial | rq_refs on applicable profiles; research-role lists | Source identity and linked ReadingNote/Finding resolution | A question link is not direct supporting evidence | RA-3B |
| Methods/Baselines | direct-partial | research_method_or_baseline_refs; Topic synonyms | Distinguish method from baseline and contextual use from evaluated comparator | The combined role does not prove method use or comparison | Structured review; RA-3B only for accepted lookup needs |
| Environment/Outcome | requires-structured-contract/review | research_measurement_relevance_refs only; raw references can be shown | Environment/outcome/estimand and conditions are in the Body | No prose parsing or guessing measurements from nearby links | Separate structured contract/review before any later index |
| Findings by Conditions | requires-structured-contract/review | Finding claim_origin/review_state/source_refs, not conditions | Conditions and applicability are RA-2 Body sections | No NLP or condition normalization from prose | Separate structured contract/review; not RA-3A |
| Contradictions/Heterogeneity | requires-structured-contract/review | contradicts_refs; qualifies_refs as declarations only | Comparable claim revisions/conditions and scientific relation assessment | A contradicts_refs link alone does not establish genuine contradiction; differences may be heterogeneity | Human scientific review; no classifier in RA-3A/RA-3B |
| Open Questions | direct-ready | ResearchQuestion question_stage and decision_state; decision_refs | None for current declared-state inventory; stage history remains outside this view | Current state is not novelty, acceptance evidence or historical closure | RA-3A current-state inventory only |
| Candidate History | requires-derived-index | Current question_stage/decision_state; decision_refs and record_version | Multi-record, versioned transitions; Body stage history needs structured review first | A current status row is not candidate history | RA-3B after explicit history-source contract |
| Search Coverage | direct-partial | SearchRecord target_refs/search_date/result_refs/supersedes_refs | Executed query space, screening depth and coverage limits remain in the Body | Inventory/counts cannot establish coverage or exhaustion | RA-3A inventory only; structured review before later coverage aggregation |
| Source Verification Queue | direct-ready | ReadingNote reading_depth/checked_sections/version_read/read_date | None for declared reading-state inventory; actual source checking remains human review | Depth is not a monotonic ladder and a declaration is not proof of reading | RA-3A |
| Decision Lineage | requires-derived-index | decision_record_state/decision_scope; subject_refs/supersedes_refs/overrules_refs | Multi-record lineage, exact subject revisions and authority evidence | A reference/current state alone is not a historical decision chain | RA-3B after explicit lineage-source contract |
| Evidence Profiles | requires-structured-contract/review | Finding origin/review state and source refs only | Structured scientific evidence dimensions and review | No evidence quality profile or score from counts or review labels | RA-6, not RA-3A or RA-3B |
| Atlas Mapping Incomplete | direct-ready | Public atlas_type == Component; research_mapping == unmapped | None for this technical mapping filter | Unmapped Atlas content says nothing about literature absence, gaps or novelty | RA-3A public label only; filter unchanged |
| Synthesis comparison view | requires-structured-contract/review | Synthesis finding_refs and document_maturity only | Agreement/differences/genuine contradictions/moderators/dependencies are in the Body | No majority vote, independent evidence or comparison result from Finding/Paper counts | Human review; separate structured contract before later comparison view |

## Direct dataset and interpretation boundary

The [source Base](Research%20Wiki%20Direct%20Views.base) contains 17 table views:
12 class/status inventories and five separate research-role-presence views.
Its global filter selects Markdown with the RA-1 and RA-2 version declarations,
a non-empty wiki_id, privacy private and export_policy deny, outside _generated.
Template and Process-seed sources have YAML examples, not operative frontmatter;
ordinary Markdown and the public technical projection do not enter this dataset.
A copied note becomes eligible only when deliberately authored with the envelope.
Bases do not replace the projector's structural validation or human Body review.

Raw role references retain their explicitly named role only. They imply neither
each other nor supports, part_of, implementation evidence or demonstrated transfer.
The legacy public view labelled Findings with contradictions displays declared
public relation links; it is not a scientific contradiction assessment. Public
Decisions / History is an inventory, not the deferred private lineage index.

No research-exhaustion, saturation, gap-confidence, novelty-confidence, evidence
or maturity scoring is computed. A SearchRecord inventory is not Search Coverage.
An empty view means no matching declared records, not that no literature exists.
Document maturity, reading verification, candidate state and technical verification
remain independent; views never promote any state.

## Concrete deferred lookup needs, not RA-3B implementation

Paper → ReadingNote/Finding → RQ → Process → Component requires explicit identity
resolution, type/role disambiguation and version/dependency handling. Candidate
history and Decision lineage require multiple records and authoritative transition
inputs; Body histories cannot be silently parsed. No such index is emitted here.
A later RA-3B leaf must define its contracts and safety tests separately; this
matrix is evidence of limitations, not authorization or a fabricated workaround.
Evidence Profiles remain RA-6.

## Review and use

TECH-ORCH reviews code/path safety; bounded SCI review checks this matrix, labels
and absence/gap/exhaustion interpretation without reopening RA-2. TECH-ORCH then
performs final review; Anton alone decides merge. Interactive Obsidian rendering
has not been certified by YAML/fixture checks alone.

Syntax follows the official [Bases syntax](https://help.obsidian.md/bases/syntax)
and [Functions](https://help.obsidian.md/bases/functions) documentation: global
filters and view filters intersect; no formulas, summaries or link traversal are used.
