# Spatial-Perception Offline Corpus Protocol

## Purpose and scope

This protocol defines the versioned, no-spoiler storage contract for real offline screen frames
used by the spatial-perception benchmark. It is a dataset and integrity contract only: it does not
define a detector, OCR, tracking, grounding, or game control.

The corpus may be stored locally or externally. Frame bytes are not required to be committed to
Git. A committed manifest remains useful because every frame has a relative path, SHA-256, visible
evidence ID, dimensions, ordered sequence position, and canonical point annotation.

## Manifest contract

`SpatialPerceptionCorpusManifest` contains `corpus_id`, `schema_version`, `corpus_version`,
explicit sequences, and the existing `SpatialPerceptionDataset` annotations. It deliberately
reuses `SpatialPerceptionFrameAnnotation`; there is no second point-annotation schema.

Every corpus-frame entry requires:

- `frame_id`, globally unique in the corpus;
- `sequence_id` and non-negative `frame_index`, which determine temporal order;
- a path relative to the supplied corpus root (absolute and root-escaping paths are rejected);
- lower-case SHA-256 of the frame bytes;
- width and height decoded from the frame file;
- one visible `evidence_id`; and
- optional timezone-aware `captured_at` metadata.

The initial integrity reader uses the repository's minimal PPM loader (`P3` or `P6`, 8-bit). This
keeps the corpus contract dependency-free. Other formats require an explicit future contract
change, not an implicit image-library addition.

## Splits and leakage prevention

Each sequence belongs to exactly one of `train`, `validation`, or `test`. A sequence identifier
may appear once only. The manifest rejects a SHA-256 that occurs in more than one split, including
when the bytes are stored under different relative paths.

Annotation references are exact: every corpus frame must have one existing annotation with the
same frame ID, sequence ID, and evidence ID; orphan annotations and unannotated corpus frames are
rejected. Existing `usable`, `uncertain`, and `exclude` statuses are preserved unchanged. The
benchmark continues to score only `usable` frames under its existing metric semantics.

## Integrity gate

`validate_spatial_perception_corpus_files(manifest, corpus_root)` returns a structured,
deterministically ordered result. It checks that every listed file exists, its SHA-256 matches, and
the decoded dimensions match the manifest. Missing, hash-mismatched, decode-failed, and
dimension-mismatched frames are explicit gate failures.

The manifest's canonical JSON orders sequences and frame indices, sorts JSON keys, and uses compact
UTF-8-safe serialization. Its SHA-256 fingerprint identifies the complete logical corpus contract
and should be recorded with later benchmark reports.

## No-spoiler boundary

The corpus records visible pixels and point locations only. It must not contain object classes,
enemy/door/NPC/item/exit/hazard labels, room names, map IDs, event IDs, save data, or hidden game
state. `evidence_id` refers only to visible evidence provenance; it is not an engine identifier.

When the Fear & Hunger pilot eventually supplies frames, collection and storage must still follow
the network-isolation, provenance, and contamination rules in `EXPERIMENT_CONTRACT.md` and
`NO_SPOILER_PROTOCOL.md`.
