# Research intake and maintenance

This is the bounded #128 operator workflow, not authorization to perform Research.
Use a separately authorized Research contract for each specialist investigation:

exact approved technical identity → question or technical-practice need →
authorized specialist research → structured private drafts → reference/type/source
validation → explicit human review where applicable → deterministic projection.

## Discover templates and authorship

| Record | Maintained copy source | Ownership/use |
| --- | --- | --- |
| ResearchQuestion | [WRQ](Wiki%20Templates/WRQ%20%E2%80%94%20Research%20Question.md) | One question identity; optional accepted 0.3 RQ-owned analysis |
| SearchRecord | [SEARCH](Wiki%20Templates/SEARCH%20%E2%80%94%20Search%20Record.md) | Actual dated search provenance; planned strategy stays draft |
| Paper | [WPAPER](Wiki%20Templates/WPAPER%20%E2%80%94%20Paper%20Identity.md) | Reusable project pointer to Zotero-primary literature |
| ReadingNote | [READ](Wiki%20Templates/READ%20%E2%80%94%20Reading%20Note.md) | Reusable processing record of an exact version actually read |
| Finding | [WFIND](Wiki%20Templates/WFIND%20%E2%80%94%20Finding.md) | Attributed proposition, separate origin and review state |
| Synthesis | [SYN](Wiki%20Templates/SYN%20%E2%80%94%20Synthesis.md) | Explicit inference over declared Findings |
| Dossier / analysis | [DOS](Wiki%20Templates/DOS%20%E2%80%94%20Dossier.md) | Existing contextual body analysis; no competing RQ master |
| DecisionDraft | [WDEC](Wiki%20Templates/WDEC%20%E2%80%94%20Decision%20Draft%20History.md) | Proposal/history; actual decision needs separate authority |

Copy required example properties into frontmatter of a separately authored private
note outside `_generated`; replace placeholders, merge only needed optional fields,
and keep the B0 provenance/revision/review body. Do not copy the whole template and
expect fenced YAML to become an active record. Allocate one durable `wiki_id`, retain
it on rename/reuse, and use a readable title. Increment `record_version` for material
changes and explicitly arrange human review. Existing valid records can stay in
any authored folder. No migration, automatic record creation or importing occurs.

Humans or authorized specialist chats author attributable drafts, selections,
source claims, author limitations, project inference, comparison and conclusions.
Start `document_maturity: draft`; Finding also starts `review_state: draft`, and
DecisionDraft starts `decision_record_state: draft`. Creation cannot attest reading,
review or acceptance. Preserve assistance provenance, source versions and locators.
Use the [accepted RQ contract](RQ%20Reader%20Contract.md) exactly: one optional
closed RQ analysis and Finding passage bindings. No new coverage counts or
technical-practice schema was accepted by #124. Contextual practice prompts remain
Dossier body text and are never consumed as generated scientific input.

Reuse a Paper and its ReadingNotes across RQs/components through exact refs and
owner-specific contexts. Do not clone records to gain a second context. Distinct
actual processing may warrant another ReadingNote, with explicit provenance;
multiple notes or versions are never automatically independent evidence.

## Read-only preflight and safe refresh

On a committed supported checkout, supply an explicit physical synthetic vault
while rehearsing; actual-vault use requires later CONTROL authorization. Keep one
writer and stable inputs. No command searches for a vault; omission uses the
existing local-only `PRIVATE_VAULT` setting.

```bash
uv run --no-sync python -m fh_agent.research_atlas.research_intake --vault-root "$INTAKE_VAULT"
uv run --no-sync fh-agent workspace apply --vault-root "$INTAKE_VAULT"
uv run --no-sync python -m fh_agent.research_atlas.research_intake --vault-root "$INTAKE_VAULT" --check-generated
uv run --no-sync fh-agent workspace check --vault-root "$INTAKE_VAULT"
```

Stop on any nonzero exit before applying; inspect warnings/notices and complete
applicable human review first. Do not treat a sequence of shell commands as
authorization to ignore a failed preflight.

The first command validates the existing closed envelopes/profiles before
inspecting exact references, source resolution and current reader eligibility.
It has no output files, writes, restore points or network calls. Exit 2 indicates
invalid structure/references or preflight failure; exit 0 may still include
warnings/notices needing human review. Missing/wrong-type internal references
produce local record ID, field, code and repair action. Source/catalog uncertainty
remains a warning with no fallback. Malformed profile failures expose field
locations without echoing private content. All output is private: do not paste
actual-corpus diagnostics, fingerprints or IDs into public GitHub.

`--check-generated` additionally runs the existing zero-write workspace check.
An empty first-use vault can pass intake while this check reports absent output;
then explicit apply is needed. Preflight does not replace ownership checks or
certify that a later apply will succeed. Apply uses the existing restore-point
harness and both projectors/checks; no second renderer/writer is introduced.
Checks create no directories, temp files, manifests or restore points, even on
failure. Review errors before retrying; never erase unknown/edited content to
force success. Preserve it outside generated ownership or restore reviewed
intact output, then use apply/check. The harness is per-file atomic, manifest-last,
not a whole-tree transaction or concurrent-editor lock. Its restore point covers
generated roots only; separately preserve authored revisions/catalog as needed.

## Finite maintenance checklist

| Change or diagnostic | Required operator action |
| --- | --- |
| Newly approved technical child/sibling | Verify its independent Registry/architecture gate. Preflight compares the current Registry to the intact prior generated technical ID index and reports `new-technical-subject`. Author only explicit bindings; inspect refresh. No automatic relevance, inheritance or production identity creation. |
| Renamed technical display name | `renamed-technical-subject` compares labels by durable ID against that same index. Retain IDs/authored folders; refresh generated routes and inspect links/collisions. Labels never resolve identity. |
| New multi-component question | `multi-subject-question` reports explicit multi-target RQs. Review each exact target/type and why-matters context; reuse source identities. |
| Changed source version | Preserve catalog history and the actual `version_read`. The G4 resolver reports unresolved/conflicting/cross-family bindings and status/lineage warnings; `different-navigation-version` reports an explicit preference different from the read version. Changed consumed source inputs change the existing source fingerprint. Alias retarget/history loss fails the existing workspace preflight. Authorize a new reading separately; no automatic read-version rewrite. |
| Superseded analysis | `historical-analysis` reports superseded/archived records. Explain explicit lineage/direction and preserve old revisions. Existing reader reports stale pinned review/dependencies; no automatic successor choice. |
| Missing reference | `missing-reference` identifies record/field; supply the intended exact record or explicitly revise the selection. No title matching/substitute. |
| Wrong-type reference | `wrong-type-reference` identifies the field and expected type; repair against the validated snapshot. An unavailable reader block is never scientific approval. |
| Checked-at context expiry | Apply only an accepted explicit validity policy, citing its authority, exact checked revision/date, as-of and expiry rule. **No such expiry policy currently exists in RA-2/G4/#124**; date alone cannot expire a source/review. Do not invent a TTL or claim that this preflight checks expiry. A later accepted policy requires its own bounded implementation before automated expiry diagnostics. |
| Owner-marker loss / edited/unowned output | Run `--check-generated` or workspace check. Existing owner/manifest checks fail closed before generated writes. Preserve/restore reviewed output; do not adopt files, overwrite authored content or bypass the marker. |

New/renamed notices require a prior intact generated technical index. On first
use there is no comparison baseline; after refresh the old baseline is replaced.
There is no background monitor, change database or automatic historical delta.
Scientific reviewed-input staleness uses exact pins, not age or inferred adequacy.
Missing/invalid nested selections retain the renderer's accepted unavailable
behavior; intake adds diagnostics without altering projection semantics.

## Authority and ownership

Public Registry and accepted project sources govern technical identity/architecture;
a separately accepted decision governs scientific authority. Private authored
frontmatter/body and source catalog are the scientific masters, private/export-deny.
Zotero owns full bibliography/PDFs. Validators inspect structure and explicit
bindings; renderers copy only allowlisted literal inputs and generate navigation,
views, indexes and fingerprints. They never author, infer or assess conclusions,
novelty, gaps, Findings or priorities. Validation success certifies no scientific
truth, reading adequacy, acceptance, experiment permission or publication claim.

Existing owners retain `_generated/technical-atlas` and `_generated/derived` with
finite manifested paths. Nothing adds generated ownership. Authored notes/catalog
and `.obsidian` state are never overwritten. Existing reference 1.0, presentation
1.1 and source-resolution 1.0 fingerprint domains remain unchanged; body-only
edits do not author generated science. No actual Research population/import,
Registry/canonical edit, private export, Live, Experiment or publication follows.

## Proposed bounded human G6 — later authorization only

CONTROL exact-head source/CI review must precede any actual-vault G6. Do not execute
that G6 as part of #128 implementation. After a separate CONTROL authorization:

1. Find these eight templates from this page; read author/generated authority and
   validate-success limitations without source-code inspection.
2. In a separate disposable physical empty vault with the established private
   marker, create one synthetic draft RQ from WRQ (no conclusion), run intake,
   apply and check, and inspect the empty and draft-only states.
3. Deliberately use one missing then wrong-type synthetic reference. Confirm local
   ID/field/action diagnostics and unchanged vault bytes; repair explicitly.
4. Run refresh/check twice. Inspect readable titles, stable identities, warnings,
   and deterministic output; retain exact version read despite a newer preference.
5. Preserve a synthetic authored note; edit/remove an owned output marker. Confirm
   check/apply rejection with no unsafe overwrite. Restore the reviewed output.
6. Only if separately authorized, use supported apply/check on the actual vault;
   inspect truthful empty/sparse state, no fixture contamination and authored-byte
   protection. Human usability acceptance and merge remain separate decisions.
