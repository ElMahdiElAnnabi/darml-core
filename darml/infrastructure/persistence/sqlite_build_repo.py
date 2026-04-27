from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from darml.application.ports.build_repository import BuildRepositoryPort
from darml.domain.enums import BuildStatus
from darml.domain.models import BuildResult


class SQLiteBuildRepository(BuildRepositoryPort):
    """Minimal SQLite-backed build repository.

    Stores a handful of indexable columns and the full serialized record in a JSON blob.
    Good enough for the v1 scope (metadata only, no large binaries).
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS builds (
        build_id    TEXT PRIMARY KEY,
        target_id   TEXT NOT NULL,
        status      TEXT NOT NULL,
        error       TEXT,
        created_at  TEXT NOT NULL,
        completed_at TEXT,
        payload     TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_builds_created_at ON builds(created_at DESC);
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(self._SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def save(self, build: BuildResult) -> None:
        async with self._lock:
            await asyncio.to_thread(self._save_sync, build)

    def _save_sync(self, build: BuildResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO builds (build_id, target_id, status, error,
                                    created_at, completed_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(build_id) DO UPDATE SET
                    status=excluded.status,
                    error=excluded.error,
                    completed_at=excluded.completed_at,
                    payload=excluded.payload
                """,
                (
                    build.build_id,
                    build.target_id,
                    build.status.value,
                    build.error,
                    build.created_at.isoformat(),
                    build.completed_at.isoformat() if build.completed_at else None,
                    json.dumps(_serialize(build)),
                ),
            )

    async def get(self, build_id: str) -> BuildResult | None:
        async with self._lock:
            return await asyncio.to_thread(self._get_sync, build_id)

    def _get_sync(self, build_id: str) -> BuildResult | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM builds WHERE build_id = ?", (build_id,)
            ).fetchone()
        if row is None:
            return None
        return _deserialize(json.loads(row["payload"]))

    async def list(self, limit: int = 50) -> list[BuildResult]:
        async with self._lock:
            return await asyncio.to_thread(self._list_sync, limit)

    def _list_sync(self, limit: int) -> list[BuildResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM builds ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_deserialize(json.loads(r["payload"])) for r in rows]


def _serialize(build: BuildResult) -> dict:
    return {
        "build_id": build.build_id,
        "target_id": build.target_id,
        "status": build.status.value,
        "error": build.error,
        "warnings": build.warnings,
        "build_log": build.build_log,
        "firmware_path": str(build.firmware_path) if build.firmware_path else None,
        "library_path": str(build.library_path) if build.library_path else None,
        "artifact_zip_path": (
            str(build.artifact_zip_path) if build.artifact_zip_path else None
        ),
        "created_at": build.created_at.isoformat(),
        "completed_at": (
            build.completed_at.isoformat() if build.completed_at else None
        ),
    }


def _deserialize(data: dict) -> BuildResult:
    return BuildResult(
        build_id=data["build_id"],
        target_id=data["target_id"],
        status=BuildStatus(data["status"]),
        error=data.get("error"),
        warnings=list(data.get("warnings", [])),
        build_log=data.get("build_log", ""),
        firmware_path=Path(data["firmware_path"]) if data.get("firmware_path") else None,
        library_path=Path(data["library_path"]) if data.get("library_path") else None,
        artifact_zip_path=(
            Path(data["artifact_zip_path"]) if data.get("artifact_zip_path") else None
        ),
        created_at=datetime.fromisoformat(data["created_at"]),
        completed_at=(
            datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None
        ),
    )
