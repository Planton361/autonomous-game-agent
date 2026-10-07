# Bounded original schema-1.0 reference

`8e544d2.json.gz` is public original emitted data, not executable code or an
actual-vault snapshot. It was generated independently of the current renderer
from immutable source `8e544d2e05180306a9580b5475c03e0bd91601ac`, tree
`8bcc160af08583a053b06d12a3b07af9c5dd1e71`.

The actual historical `product_migration.build` and all its code/assets were
loaded from a Git archive with an isolated historical Git index/HEAD. Inputs
were a newly created, empty, marked synthetic vault: no authored records,
private catalog or Zotero projection. Generation ran as a non-root user with
macOS sandbox network access denied and filesystem writes restricted to the
external private temporary workspace (plus `/dev/null`); bytecode was disabled.
Neither the actual private vault nor prior private diagnostic files were read.

The complete original build emitted 520 files. This bundle retains only the
12 managed Base/Canvas/Excalidraw files, both original owner manifests, the empty
source-history index and the generated SVG: 16 files. The manifests retain all
518 original payload hashes and complete original provenance. JSON encodes
exact file bytes as Base64; gzip uses `mtime=0`. Compressed SHA-256:

`c8cf4a6bbe318c895f2c4e68859b0599069ec4774147e990f32f0171cc3ec1af`

The independent Agent Anatomy original emitted SHA-256 is
`2947d718331e317698a9da0c268411a37d3d1f1658364bf7543b742bad0ca39c`;
the Domain scene is
`9cd981871b48616c1ca2f6b02b6b106a785b4ae8ea4cdd8668a68bc89ddf4ce9`.
Cross-revision tests pin the artifact/original bytes rather than generating their
oracle with the current renderer and downgrading its schema.

Runtime never executes archived code, fetches a revision or writes a replay
workspace. It requires this exact local Git commit/tree, the pinned bundle,
matching original manifest provenance and reproducible admissible inputs.
The current build may certify input provenance, but its file bytes are never
the original-reference oracle for this revision. Other source revisions are
supported only if local Git proves every current renderer module and relevant
public asset/input byte identical to that recorded revision. Otherwise they
fail closed; additional historical families require a separate reviewed oracle.

This data does not permit Canvas endpoint-side additions, abbreviated image
cache routes, Excalidraw height changes or text whitespace changes. The existing
canonicalizers and recovery rules remain the authority for those comparisons.
