from pathlib import Path

import pytest
from mission_fixtures import RUN_ID, make_manifest, manifest_data
from pydantic import ValidationError

from fh_agent.mission.ledger import MissionLedger
from fh_agent.mission.manifest import (
    LIVE_EXECUTION_NOT_SUPPORTED,
    NETWORK_ISOLATION_UNPROVEN,
    MissionManifestV1,
    activation_refusals,
    compare_frozen_identity,
    hash_prompt_bundle,
)
from fh_agent.mission.state import MissionActivationRefused


def test_manifest_is_frozen_and_rejects_unknown_fields() -> None:
    manifest = make_manifest()

    with pytest.raises(ValidationError):
        manifest.run_mode = "debug"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        MissionManifestV1.model_validate({**manifest_data(), "extra_field": 1})


@pytest.mark.parametrize("run_id", ["short", "../escape-run", "has space-0001", "x" * 65])
def test_mission_run_id_must_be_opaque_and_path_safe(run_id: str) -> None:
    with pytest.raises(ValidationError):
        make_manifest(run_id)


def test_unmetered_budget_dimensions_must_be_declared_not_omitted() -> None:
    with pytest.raises(ValidationError):
        make_manifest(budgets__not_applicable_in_s0=["wall_time", "tokens"])


def test_manifest_digest_is_domain_separated_and_stable() -> None:
    first = make_manifest()
    second = MissionManifestV1.model_validate_json(first.canonical_json())

    assert first.manifest_sha256 == second.manifest_sha256
    assert len(first.manifest_sha256) == 64
    assert make_manifest(cortex__model_revision="fake-2").manifest_sha256 != first.manifest_sha256


def test_frozen_identity_ignores_only_created_at() -> None:
    stored = make_manifest()

    assert compare_frozen_identity(stored, make_manifest(created_at="2027-01-01T00:00:00")) == []
    mismatches = compare_frozen_identity(stored, make_manifest(body__controller_version="v2"))
    assert [mismatch.field for mismatch in mismatches] == ["body.controller_version"]


def test_prompt_bundle_hash_is_order_independent_and_content_sensitive(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.md").write_text("beta", encoding="utf-8")
    paths = [tmp_path / "a.md", tmp_path / "b.md"]

    forward = hash_prompt_bundle(paths, root=tmp_path)
    assert hash_prompt_bundle(list(reversed(paths)), root=tmp_path) == forward
    (tmp_path / "b.md").write_text("beta!", encoding="utf-8")
    assert hash_prompt_bundle(paths, root=tmp_path) != forward


def test_ac11_live_execution_is_refused_before_any_db_is_created(tmp_path: Path) -> None:
    manifest = make_manifest(execution_class="live", network_isolation_proof_ref="proof-1")

    with pytest.raises(MissionActivationRefused) as raised:
        MissionLedger.create_new_mission(tmp_path, manifest)

    assert raised.value.reasons == [LIVE_EXECUTION_NOT_SUPPORTED]
    assert not (tmp_path / RUN_ID).exists()


def test_ac11_loopback_endpoint_is_never_network_isolation_proof(tmp_path: Path) -> None:
    manifest = make_manifest(
        execution_class="live", cortex__endpoint_identity="http://127.0.0.1:11434"
    )

    with pytest.raises(MissionActivationRefused) as raised:
        MissionLedger.create_new_mission(tmp_path, manifest)

    assert NETWORK_ISOLATION_UNPROVEN in raised.value.reasons
    assert LIVE_EXECUTION_NOT_SUPPORTED in raised.value.reasons
    assert not (tmp_path / RUN_ID).exists()


def test_ac11_s1_replay_identity_is_bridge_assisted_debug_replay_and_non_official() -> None:
    manifest = make_manifest(run_mode="bridge-assisted", execution_class="debug-replay")

    assert activation_refusals(manifest) == []
    assert manifest.network_isolation_proof_ref is None
    assert manifest.execution_class != "live"


def test_dirty_source_is_recorded_and_allowed_only_for_offline_classes() -> None:
    assert activation_refusals(make_manifest(source__dirty=True)) == []
    live_dirty = make_manifest(
        execution_class="live", source__dirty=True, network_isolation_proof_ref="proof"
    )
    assert "dirty_source_not_allowed_for_official_execution" in activation_refusals(live_dirty)
