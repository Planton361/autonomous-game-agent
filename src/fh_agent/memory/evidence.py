from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from fh_agent.perception.screen_capture import ScreenFrame


class EvidenceRecord(BaseModel):
    """Persisted evidence metadata."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    run_id: str
    kind: str
    path: str
    sha256: str
    created_at: datetime
    width: int
    height: int


class EvidenceStore:
    """Stores screenshot evidence and returns append-safe metadata records."""

    def __init__(
        self,
        root: Path,
        *,
        run_id: str,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.root = root
        self.run_id = run_id
        self.clock = clock or (lambda: datetime.now(UTC))
        self.id_factory = id_factory or (lambda: uuid4().hex)

    def save_screenshot(self, frame: ScreenFrame) -> EvidenceRecord:
        evidence_id = self.id_factory()
        run_dir = self.root / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{evidence_id}.ppm"
        path.write_bytes(frame.to_ppm_bytes())

        return EvidenceRecord(
            evidence_id=evidence_id,
            run_id=self.run_id,
            kind="screenshot",
            path=str(path),
            sha256=sha256_file(path),
            created_at=frame.captured_at,
            width=frame.width,
            height=frame.height,
        )

    def record_existing_screenshot(
        self,
        path: Path,
        *,
        width: int,
        height: int,
    ) -> EvidenceRecord:
        if not path.is_file():
            msg = f"screenshot file does not exist: {path}"
            raise FileNotFoundError(msg)

        return EvidenceRecord(
            evidence_id=self.id_factory(),
            run_id=self.run_id,
            kind="screenshot",
            path=str(path),
            sha256=sha256_file(path),
            created_at=self.clock(),
            width=width,
            height=height,
        )


def sha256_bytes(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        msg = f"file does not exist: {path}"
        raise FileNotFoundError(msg)

    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
