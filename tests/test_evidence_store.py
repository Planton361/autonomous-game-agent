from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fh_agent.memory.evidence import EvidenceStore, sha256_bytes, sha256_file
from fh_agent.perception.screen_capture import DummyScreenCapture


class SequenceFactory:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.count = 0

    def __call__(self) -> str:
        value = f"{self.prefix}-{self.count}"
        self.count += 1
        return value


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def test_evidence_store_saves_dummy_screenshots_with_hashes(tmp_path: Path) -> None:
    clock = ManualClock()
    capture = DummyScreenCapture(width=2, height=2, clock=clock)
    store = EvidenceStore(
        tmp_path,
        run_id="run-1",
        id_factory=SequenceFactory("evidence"),
    )

    records = [store.save_screenshot(capture.capture()) for _ in range(3)]

    assert [record.evidence_id for record in records] == [
        "evidence-0",
        "evidence-1",
        "evidence-2",
    ]
    assert [record.created_at for record in records] == [
        datetime(2026, 5, 16, 12, 0, tzinfo=UTC),
        datetime(2026, 5, 16, 12, 0, 1, tzinfo=UTC),
        datetime(2026, 5, 16, 12, 0, 2, tzinfo=UTC),
    ]
    for record in records:
        path = Path(record.path)
        assert path.is_file()
        assert record.kind == "screenshot"
        assert record.run_id == "run-1"
        assert record.width == 2
        assert record.height == 2
        assert record.sha256 == sha256_file(path)


def test_hashing_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "sample.bin"
    payload = b"visible pixels only"
    path.write_bytes(payload)

    assert sha256_file(path) == sha256_file(path)
    assert sha256_file(path) == sha256_bytes(payload)


def test_missing_screenshot_file_is_an_error(tmp_path: Path) -> None:
    store = EvidenceStore(
        tmp_path,
        run_id="run-1",
        id_factory=SequenceFactory("evidence"),
        clock=ManualClock(),
    )

    with pytest.raises(FileNotFoundError):
        store.record_existing_screenshot(tmp_path / "missing.ppm", width=1, height=1)
