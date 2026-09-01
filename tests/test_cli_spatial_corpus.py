import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from fh_agent.cli import app
from fh_agent.evals.spatial_annotation_review import SpatialAnnotationWorkflow
from fh_agent.perception.screen_capture import ScreenFrame


def write_ppm(root: Path, relative_path: str, *, rgb: bytes = b"\x01\x02\x03") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        ScreenFrame(
            width=1,
            height=1,
            rgb=rgb,
            captured_at=datetime(2026, 8, 24, tzinfo=UTC),
        ).to_ppm_bytes()
    )


def assemble_args(corpus_root: Path, output: Path, *sources: str) -> list[str]:
    args = [
        "spatial-corpus-assemble",
        "--corpus-root",
        str(corpus_root),
        "--corpus-id",
        "visible-corpus",
        "--schema-version",
        "1",
        "--corpus-version",
        "0.1.0",
        "--annotation-dataset-version",
        "0.1.0",
    ]
    for source in sources:
        args.extend(["--sequence", source])
    return [*args, "--output", str(output)]


def workflow_frame_id(path: Path) -> str:
    workflow = SpatialAnnotationWorkflow.model_validate_json(path.read_text(encoding="utf-8"))
    return workflow.manifest.annotations.sequences[0].frames[0].frame_id


def test_cli_assembles_annotates_reviews_summarizes_validates_and_freezes(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    write_ppm(corpus_root, "sequence-a/frame.ppm")
    initial = tmp_path / "initial.json"
    runner = CliRunner()

    assembled = runner.invoke(
        app,
        assemble_args(corpus_root, initial, "sequence-a:sequence-a:test"),
    )

    assert assembled.exit_code == 0, assembled.output
    frame_id = workflow_frame_id(initial)
    revised = tmp_path / "revised.json"
    annotated = runner.invoke(
        app,
        [
            "spatial-corpus-annotate",
            "--workflow",
            str(initial),
            "--frame-id",
            frame_id,
            "--status",
            "usable",
            "--player",
            "0,0",
            "--sprite",
            "0,0",
            "--overwrite-annotation",
            "--output",
            str(revised),
        ],
    )

    assert annotated.exit_code == 0, annotated.output
    no_silent_overwrite = runner.invoke(
        app,
        [
            "spatial-corpus-annotate",
            "--workflow",
            str(revised),
            "--frame-id",
            frame_id,
            "--status",
            "usable",
            "--output",
            str(tmp_path / "refused.json"),
        ],
    )
    assert no_silent_overwrite.exit_code == 1
    assert "overwrite=True" in no_silent_overwrite.output

    readiness = runner.invoke(
        app,
        [
            "spatial-corpus-readiness",
            "--workflow",
            str(revised),
            "--corpus-root",
            str(corpus_root),
        ],
    )
    readiness_payload = json.loads(readiness.output)

    assert readiness.exit_code == 0, readiness.output
    assert readiness_payload["test_sequence_count"] == 1
    assert readiness_payload["total_frame_count"] == 1
    assert readiness_payload["usable_annotation_count"] == 1
    assert readiness_payload["usable_annotations_lacking_review"] == 1
    assert readiness_payload["corpus_integrity_status"] == "passed"
    assert readiness_payload["freeze_status"] == "blocked"

    unreviewed_freeze = runner.invoke(
        app,
        [
            "spatial-corpus-freeze",
            "--workflow",
            str(revised),
            "--corpus-root",
            str(corpus_root),
            "--output",
            str(tmp_path / "unreviewed-freeze.json"),
        ],
    )
    assert unreviewed_freeze.exit_code == 1
    assert "usable_annotations_lack_valid_passed_review" in unreviewed_freeze.output

    reviewed = tmp_path / "reviewed.json"
    review = runner.invoke(
        app,
        [
            "spatial-corpus-review",
            "--workflow",
            str(revised),
            "--frame-id",
            frame_id,
            "--status",
            "passed",
            "--reviewer",
            "reviewer-1",
            "--output",
            str(reviewed),
        ],
    )
    validation = runner.invoke(
        app,
        [
            "spatial-corpus-validate",
            "--workflow",
            str(reviewed),
            "--corpus-root",
            str(corpus_root),
        ],
    )
    frozen = tmp_path / "frozen.json"
    freeze = runner.invoke(
        app,
        [
            "spatial-corpus-freeze",
            "--workflow",
            str(reviewed),
            "--corpus-root",
            str(corpus_root),
            "--output",
            str(frozen),
        ],
    )

    assert review.exit_code == 0, review.output
    assert validation.exit_code == 0, validation.output
    assert json.loads(validation.output)["valid"] is True
    assert freeze.exit_code == 1
    assert "train_split_has_no_reviewed_usable_annotation" in freeze.output


def test_cli_reports_obsolete_review_and_refuses_freeze(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    write_ppm(corpus_root, "sequence-a/frame.ppm")
    runner = CliRunner()
    initial = tmp_path / "initial.json"
    assert (
        runner.invoke(
            app,
            assemble_args(corpus_root, initial, "sequence-a:sequence-a:train"),
        ).exit_code
        == 0
    )
    frame_id = workflow_frame_id(initial)
    usable = tmp_path / "usable.json"
    assert (
        runner.invoke(
            app,
            [
                "spatial-corpus-annotate",
                "--workflow",
                str(initial),
                "--frame-id",
                frame_id,
                "--status",
                "usable",
                "--overwrite-annotation",
                "--output",
                str(usable),
            ],
        ).exit_code
        == 0
    )
    reviewed = tmp_path / "reviewed.json"
    assert (
        runner.invoke(
            app,
            [
                "spatial-corpus-review",
                "--workflow",
                str(usable),
                "--frame-id",
                frame_id,
                "--status",
                "passed",
                "--output",
                str(reviewed),
            ],
        ).exit_code
        == 0
    )
    revised = tmp_path / "revised.json"
    assert (
        runner.invoke(
            app,
            [
                "spatial-corpus-annotate",
                "--workflow",
                str(reviewed),
                "--frame-id",
                frame_id,
                "--status",
                "usable",
                "--sprite",
                "0,0",
                "--overwrite-annotation",
                "--output",
                str(revised),
            ],
        ).exit_code
        == 0
    )

    readiness = runner.invoke(
        app,
        [
            "spatial-corpus-readiness",
            "--workflow",
            str(revised),
            "--corpus-root",
            str(corpus_root),
        ],
    )
    freeze = runner.invoke(
        app,
        [
            "spatial-corpus-freeze",
            "--workflow",
            str(revised),
            "--corpus-root",
            str(corpus_root),
            "--output",
            str(tmp_path / "frozen.json"),
        ],
    )

    assert readiness.exit_code == 0, readiness.output
    assert json.loads(readiness.output)["obsolete_review_count"] == 1
    assert freeze.exit_code == 1
    assert "obsolete_annotation_review_present" in freeze.output


def test_cli_rejects_integrity_and_split_leakage_failures(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    write_ppm(corpus_root, "sequence-a/frame.ppm", rgb=b"\x01\x02\x03")
    write_ppm(corpus_root, "sequence-b/frame.ppm", rgb=b"\x01\x02\x03")
    runner = CliRunner()

    leaked = runner.invoke(
        app,
        assemble_args(
            corpus_root,
            tmp_path / "leaked.json",
            "sequence-a:sequence-a:train",
            "sequence-b:sequence-b:test",
        ),
    )
    assert leaked.exit_code == 1
    assert "sha256" in leaked.output

    initial = tmp_path / "initial.json"
    assert (
        runner.invoke(
            app,
            assemble_args(corpus_root, initial, "sequence-a:sequence-a:train"),
        ).exit_code
        == 0
    )
    (corpus_root / "sequence-a/frame.ppm").write_bytes(b"not a ppm")
    validation = runner.invoke(
        app,
        [
            "spatial-corpus-validate",
            "--workflow",
            str(initial),
            "--corpus-root",
            str(corpus_root),
        ],
    )

    assert validation.exit_code == 1
    assert json.loads(validation.output)["valid"] is False


def test_cli_annotation_ui_uses_a_headless_replaceable_launcher_and_existing_output_policy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    corpus_root = tmp_path / "corpus"
    write_ppm(corpus_root, "sequence-a/frame.ppm")
    initial = tmp_path / "initial.json"
    runner = CliRunner()
    assert (
        runner.invoke(
            app,
            assemble_args(corpus_root, initial, "sequence-a:sequence-a:train"),
        ).exit_code
        == 0
    )
    output = tmp_path / "annotated.json"

    def headless_launcher(session, *, corpus_root, persist) -> None:
        assert corpus_root.is_dir()
        session.set_status("usable")
        session.set_player_point((0, 0))
        session.save_current(persist)

    monkeypatch.setattr("fh_agent.cli.launch_spatial_annotation_ui", headless_launcher)
    result = runner.invoke(
        app,
        [
            "spatial-corpus-annotate-ui",
            "--workflow",
            str(initial),
            "--corpus-root",
            str(corpus_root),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    saved = SpatialAnnotationWorkflow.model_validate_json(output.read_text(encoding="utf-8"))
    annotation = saved.manifest.annotations.sequences[0].frames[0]
    assert annotation.status == "usable"
    assert annotation.player_screen_position == (0, 0)
