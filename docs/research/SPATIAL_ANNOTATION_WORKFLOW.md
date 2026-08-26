# Spatial-Corpus Assembly and Annotation Workflow

## Scope

This workflow prepares an externally stored, offline PPM corpus for the existing spatial-perception
benchmark. It does not inspect live game windows, interpret image content, define semantic classes,
or implement a detector.

## Assembly

Provide an explicit `SpatialCorpusSequenceSource` for each source directory. The source carries the
whole sequence's `train`, `validation`, or `test` assignment; individual frames have no split field.
The assembler reads only direct `.ppm` files, sorts names lexicographically, assigns consecutive
`frame_index` values, and derives frame/evidence IDs from sequence ID, relative path, and file
SHA-256. It creates canonical `uncertain` annotations as placeholders, which are retained but not
scored by the existing benchmark.

Frame paths remain relative to the supplied corpus root. The workflow never copies frames into the
repository; a real corpus may remain local or external. Run the existing corpus integrity validator
against that root before freezing.

## Annotation and review

`record_spatial_annotation` accepts only `SpatialPerceptionFrameAnnotation`: status, optional player
point, and visible sprite points. It rejects all existing annotation replacements unless
`overwrite=True` explicitly records a revision. Annotation JSON is canonical and its SHA-256 covers
the complete point-only annotation, independent of sprite-point ordering.

`create_annotation_review` records a reviewer decision (`passed` or `needs_revision`) against that
exact fingerprint. `review_is_current` must be checked before treating a review as valid: any later
annotation revision leaves its old review record auditable but invalid for the current corpus.

## Freeze gate

`freeze_spatial_corpus` requires a successful, matching file-integrity result. Its freeze record
contains corpus ID/version/schema, the canonical corpus fingerprint, a separate split fingerprint,
and a timestamp. A frozen workflow rejects annotation mutation. Future annotation changes require a
new corpus version and a new freeze record; they must not rewrite the frozen version.

Freeze readiness also requires at least one `usable` annotation with a current `passed` review in
each `train`, `validation`, and `test` split. Every `usable` annotation must have such a review, and
any obsolete review blocks the gate. Additional `uncertain` or `exclude` frames remain legitimate
and do not themselves block a corpus with this reviewed usable coverage.

No record in this workflow may add enemy, door, NPC, item, exit, hazard, room, map, event, or other
hidden-state fields.
