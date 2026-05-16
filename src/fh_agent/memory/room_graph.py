import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fh_agent.memory.db import MemoryDB

TransitionOutcome = Literal["screen_transition"]

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "map_id",
        "event_id",
        "event_name",
        "event_comments",
        "event_trigger_conditions",
        "tile_coordinates",
        "rpg_maker_tile_coordinates",
        "game_switches",
        "game_variables",
        "enemy_database",
        "enemy_hp",
        "item_database_effects",
        "savegame_variables",
        "ending_flags",
    }
)


class RoomRecord(BaseModel):
    """A room-like visible-state cluster learned from observed screen signatures."""

    model_config = ConfigDict(frozen=True)

    room_signature: str
    confidence: float = Field(ge=0.0, le=1.0)
    visit_count: int = Field(ge=0)
    first_seen_at: datetime
    last_seen_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoomTransitionRecord(BaseModel):
    """A visible transition observed between two learned room signatures."""

    model_config = ConfigDict(frozen=True)

    transition_key: str
    from_room_signature: str
    to_room_signature: str
    action_id: str | None = None
    outcome: TransitionOutcome = "screen_transition"
    confidence: float = Field(ge=0.0, le=1.0)
    observed_count: int = Field(ge=0)
    first_seen_at: datetime
    last_seen_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoomGraphStore:
    """Persistence for an experience graph built only from visible signatures."""

    def __init__(self, db: MemoryDB) -> None:
        self.db = db

    def upsert_room(
        self,
        room_signature: str,
        evidence_ids: list[str],
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> RoomRecord:
        self._validate_signature(room_signature)
        self._validate_evidence(evidence_ids)
        self._validate_confidence(confidence)
        clean_metadata = _validated_metadata(metadata)
        now = _utc_now_iso()

        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO rooms (
                    room_signature,
                    confidence,
                    visit_count,
                    first_seen_at,
                    last_seen_at,
                    metadata_json
                )
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(room_signature) DO UPDATE SET
                    confidence = MAX(rooms.confidence, excluded.confidence),
                    visit_count = rooms.visit_count + 1,
                    last_seen_at = excluded.last_seen_at,
                    metadata_json = COALESCE(excluded.metadata_json, rooms.metadata_json)
                """,
                (
                    room_signature,
                    confidence,
                    now,
                    now,
                    _metadata_json(clean_metadata),
                ),
            )
            self.db.conn.executemany(
                """
                INSERT OR IGNORE INTO room_evidence (room_signature, evidence_id)
                VALUES (?, ?)
                """,
                [(room_signature, evidence_id) for evidence_id in evidence_ids],
            )

        room = self.get_room(room_signature)
        if room is None:
            msg = f"room could not be read after upsert: {room_signature}"
            raise RuntimeError(msg)
        return room

    def get_room(self, room_signature: str) -> RoomRecord | None:
        row = self.db.conn.execute(
            """
            SELECT
                room_signature,
                confidence,
                visit_count,
                first_seen_at,
                last_seen_at,
                metadata_json
            FROM rooms
            WHERE room_signature = ?
            """,
            (room_signature,),
        ).fetchone()
        if row is None:
            return None
        return self._room_from_row(dict(row))

    def list_rooms(self) -> list[RoomRecord]:
        rows = self.db.conn.execute(
            """
            SELECT
                room_signature,
                confidence,
                visit_count,
                first_seen_at,
                last_seen_at,
                metadata_json
            FROM rooms
            ORDER BY room_signature
            """,
        ).fetchall()
        return [self._room_from_row(dict(row)) for row in rows]

    def record_transition(
        self,
        from_room_signature: str,
        to_room_signature: str,
        evidence_ids: list[str],
        action_id: str | None = None,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> RoomTransitionRecord:
        self._validate_signature(from_room_signature)
        self._validate_signature(to_room_signature)
        self._validate_evidence(evidence_ids)
        self._validate_confidence(confidence)
        clean_metadata = _validated_metadata(metadata)

        self.upsert_room(from_room_signature, evidence_ids, confidence=confidence)
        self.upsert_room(to_room_signature, evidence_ids, confidence=confidence)

        transition_key = _transition_key(from_room_signature, to_room_signature, action_id)
        now = _utc_now_iso()
        with self.db.conn:
            self.db.conn.execute(
                """
                INSERT INTO room_transitions (
                    transition_key,
                    from_room_signature,
                    to_room_signature,
                    action_id,
                    outcome,
                    confidence,
                    observed_count,
                    first_seen_at,
                    last_seen_at,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, 'screen_transition', ?, 1, ?, ?, ?)
                ON CONFLICT(transition_key) DO UPDATE SET
                    confidence = MAX(room_transitions.confidence, excluded.confidence),
                    observed_count = room_transitions.observed_count + 1,
                    last_seen_at = excluded.last_seen_at,
                    metadata_json = COALESCE(excluded.metadata_json, room_transitions.metadata_json)
                """,
                (
                    transition_key,
                    from_room_signature,
                    to_room_signature,
                    action_id,
                    confidence,
                    now,
                    now,
                    _metadata_json(clean_metadata),
                ),
            )
            self.db.conn.executemany(
                """
                INSERT OR IGNORE INTO transition_evidence (transition_key, evidence_id)
                VALUES (?, ?)
                """,
                [(transition_key, evidence_id) for evidence_id in evidence_ids],
            )

        transition = self._get_transition(transition_key)
        if transition is None:
            msg = f"transition could not be read after upsert: {transition_key}"
            raise RuntimeError(msg)
        return transition

    def get_neighbors(self, room_signature: str) -> list[RoomTransitionRecord]:
        rows = self.db.conn.execute(
            """
            SELECT transition_key
            FROM room_transitions
            WHERE from_room_signature = ?
            ORDER BY to_room_signature, action_id, transition_key
            """,
            (room_signature,),
        ).fetchall()
        return [
            transition
            for row in rows
            if (transition := self._get_transition(row["transition_key"])) is not None
        ]

    def list_transitions(self) -> list[RoomTransitionRecord]:
        rows = self.db.conn.execute(
            """
            SELECT transition_key
            FROM room_transitions
            ORDER BY from_room_signature, to_room_signature, action_id, transition_key
            """,
        ).fetchall()
        return [
            transition
            for row in rows
            if (transition := self._get_transition(row["transition_key"])) is not None
        ]

    def _get_transition(self, transition_key: str) -> RoomTransitionRecord | None:
        row = self.db.conn.execute(
            """
            SELECT
                transition_key,
                from_room_signature,
                to_room_signature,
                action_id,
                outcome,
                confidence,
                observed_count,
                first_seen_at,
                last_seen_at,
                metadata_json
            FROM room_transitions
            WHERE transition_key = ?
            """,
            (transition_key,),
        ).fetchone()
        if row is None:
            return None
        return self._transition_from_row(dict(row))

    def _room_from_row(self, row: dict[str, Any]) -> RoomRecord:
        return RoomRecord(
            room_signature=row["room_signature"],
            confidence=row["confidence"],
            visit_count=row["visit_count"],
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            evidence_ids=self._room_evidence_ids(row["room_signature"]),
            metadata=_metadata_from_json(row["metadata_json"]),
        )

    def _transition_from_row(self, row: dict[str, Any]) -> RoomTransitionRecord:
        return RoomTransitionRecord(
            transition_key=row["transition_key"],
            from_room_signature=row["from_room_signature"],
            to_room_signature=row["to_room_signature"],
            action_id=row["action_id"],
            outcome=row["outcome"],
            confidence=row["confidence"],
            observed_count=row["observed_count"],
            first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
            last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
            evidence_ids=self._transition_evidence_ids(row["transition_key"]),
            metadata=_metadata_from_json(row["metadata_json"]),
        )

    def _room_evidence_ids(self, room_signature: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT evidence_id
            FROM room_evidence
            WHERE room_signature = ?
            ORDER BY evidence_id
            """,
            (room_signature,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    def _transition_evidence_ids(self, transition_key: str) -> list[str]:
        rows = self.db.conn.execute(
            """
            SELECT evidence_id
            FROM transition_evidence
            WHERE transition_key = ?
            ORDER BY evidence_id
            """,
            (transition_key,),
        ).fetchall()
        return [row["evidence_id"] for row in rows]

    @staticmethod
    def _validate_signature(room_signature: str) -> None:
        if not room_signature:
            msg = "room_signature must not be empty"
            raise ValueError(msg)

    @staticmethod
    def _validate_evidence(evidence_ids: list[str]) -> None:
        if not evidence_ids:
            msg = "room graph updates require at least one evidence_id"
            raise ValueError(msg)

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        if not 0.0 <= confidence <= 1.0:
            msg = "confidence must be between 0.0 and 1.0"
            raise ValueError(msg)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _transition_key(
    from_room_signature: str,
    to_room_signature: str,
    action_id: str | None,
) -> str:
    raw_key = "\x1f".join([from_room_signature, to_room_signature, action_id or ""])
    return f"transition-{sha256(raw_key.encode('utf-8')).hexdigest()}"


def _validated_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    _reject_forbidden_metadata_keys(metadata)
    return metadata


def _reject_forbidden_metadata_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_METADATA_KEYS:
                msg = f"metadata contains forbidden hidden-state key: {key}"
                raise ValueError(msg)
            _reject_forbidden_metadata_keys(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_metadata_keys(item)


def _metadata_json(metadata: dict[str, Any]) -> str | None:
    if not metadata:
        return None
    return json.dumps(metadata, sort_keys=True, separators=(",", ":"))


def _metadata_from_json(payload: str | None) -> dict[str, Any]:
    if payload is None:
        return {}
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        return {}
    return loaded
