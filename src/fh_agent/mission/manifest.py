"""Immutable, versioned Mission Run manifest with frozen identities (MRIC-S0, Issue #184)."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

MANIFEST_SCHEMA_VERSION: Literal["1"] = "1"
MANIFEST_HASH_DOMAIN = b"fh-agent/mission-manifest/v1\n"
MISSION_RUN_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"

RunMode = Literal["screen-only", "bridge-assisted", "debug", "networked-api-exploratory"]
ExecutionClass = Literal["dry-run", "debug-replay", "live"]

OFFICIAL_ELIGIBLE_RUN_MODES = frozenset({"screen-only", "bridge-assisted"})
S0_NOT_APPLICABLE_BUDGETS = ("cost", "model_calls", "snapshots", "tokens", "wall_time")

LIVE_EXECUTION_NOT_SUPPORTED = "live_execution_not_supported_in_s0"
NETWORK_ISOLATION_UNPROVEN = "network_isolation_unproven"
DIRTY_SOURCE_NOT_ALLOWED = "dirty_source_not_allowed_for_official_execution"

Sha256Hex = str


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceIdentity(_Frozen):
    commit: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    dirty: bool
    diff_sha256: Sha256Hex | None = Field(default=None, pattern=SHA256_HEX_PATTERN)


class CortexIdentity(_Frozen):
    provider: str = Field(min_length=1)
    endpoint_identity: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    model_digest: str | None = None
    prompt_bundle_sha256: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)
    inference_params_sha256: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)


class BodyIdentity(_Frozen):
    controller_version: str = Field(min_length=1)
    weights_digest: str | None = None
    skill_registry_sha256: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)


class PolicyHashes(_Frozen):
    manager: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)
    verifier: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)
    safety_filter: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)
    input_executor: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)
    no_spoiler: Sha256Hex = Field(pattern=SHA256_HEX_PATTERN)


class MissionBudgets(_Frozen):
    """Frozen Mission ceilings; dimensions S0 does not meter are declared, never omitted."""

    max_action_attempts: PositiveInt
    max_action_attempts_per_episode: PositiveInt
    max_contracts: PositiveInt
    max_life_episodes: PositiveInt
    not_applicable_in_s0: tuple[str, ...]

    @field_validator("not_applicable_in_s0")
    @classmethod
    def must_declare_every_unmetered_dimension(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(value)) != S0_NOT_APPLICABLE_BUDGETS or len(set(value)) != len(value):
            msg = f"not_applicable_in_s0 must declare exactly {list(S0_NOT_APPLICABLE_BUDGETS)}"
            raise ValueError(msg)
        return tuple(sorted(value))


class MissionManifestV1(_Frozen):
    """Write-once Mission Run manifest; frozen until the Mission Run terminates."""

    schema_version: Literal["1"]
    mission_run_id: str = Field(pattern=MISSION_RUN_ID_PATTERN)
    created_at: str = Field(min_length=1)
    run_mode: RunMode
    execution_class: ExecutionClass
    source: SourceIdentity
    cortex: CortexIdentity
    body: BodyIdentity
    policy_hashes: PolicyHashes
    budgets: MissionBudgets
    network_isolation_proof_ref: str | None = None
    restart_policy_id: str = Field(min_length=1)
    termination_criteria_id: str = Field(min_length=1)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    @property
    def manifest_sha256(self) -> str:
        return hashlib.sha256(MANIFEST_HASH_DOMAIN + self.canonical_json().encode()).hexdigest()

    def frozen_identity(self) -> dict[str, Any]:
        """The manifest minus ``created_at``; every field here must match on resume."""

        identity = self.model_dump(mode="json")
        identity.pop("created_at")
        return identity


@dataclass(frozen=True, slots=True)
class IdentityMismatch:
    field: str
    stored: Any
    candidate: Any


def compare_frozen_identity(
    stored: MissionManifestV1, candidate: MissionManifestV1
) -> list[IdentityMismatch]:
    """Return field-level frozen-identity mismatches, sorted by dotted field path."""

    stored_fields = _flatten(stored.frozen_identity())
    candidate_fields = _flatten(candidate.frozen_identity())
    return [
        IdentityMismatch(name, stored_fields.get(name), candidate_fields.get(name))
        for name in sorted(stored_fields.keys() | candidate_fields.keys())
        if stored_fields.get(name) != candidate_fields.get(name)
    ]


def activation_refusals(manifest: MissionManifestV1) -> list[str]:
    """Return every S0 activation refusal; an empty list means activation may proceed.

    A loopback endpoint is never accepted as network-isolation proof: only an explicit
    ``network_isolation_proof_ref`` counts, and S0 refuses live execution regardless.
    """

    reasons: list[str] = []
    official_eligible = (
        manifest.execution_class == "live" and manifest.run_mode in OFFICIAL_ELIGIBLE_RUN_MODES
    )
    if manifest.execution_class == "live":
        reasons.append(LIVE_EXECUTION_NOT_SUPPORTED)
    if official_eligible and manifest.network_isolation_proof_ref is None:
        reasons.append(NETWORK_ISOLATION_UNPROVEN)
    if manifest.source.dirty and manifest.execution_class not in {"dry-run", "debug-replay"}:
        reasons.append(DIRTY_SOURCE_NOT_ALLOWED)
    return reasons


def hash_prompt_bundle(paths: Sequence[Path], *, root: Path) -> str:
    """Hash a prompt bundle stably over sorted root-relative POSIX paths and file bytes."""

    resolved_root = root.resolve()
    entries = sorted(
        (path.resolve().relative_to(resolved_root).as_posix(), path.read_bytes()) for path in paths
    )
    digest = hashlib.sha256(b"fh-agent/prompt-bundle/v1\n")
    for relative, payload in entries:
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(str(len(payload)).encode())
        digest.update(b"\0")
        digest.update(payload)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}{key}."))
        return flat
    return {prefix.removesuffix("."): value}
