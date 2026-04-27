import asyncio

from darml.application.ports.build_repository import BuildRepositoryPort
from darml.domain.models import BuildResult


class InMemoryBuildRepository(BuildRepositoryPort):
    def __init__(self):
        self._store: dict[str, BuildResult] = {}
        self._lock = asyncio.Lock()

    async def save(self, build: BuildResult) -> None:
        async with self._lock:
            self._store[build.build_id] = build

    async def get(self, build_id: str) -> BuildResult | None:
        async with self._lock:
            return self._store.get(build_id)

    async def list(self, limit: int = 50) -> list[BuildResult]:
        async with self._lock:
            items = list(self._store.values())
        items.sort(key=lambda b: b.created_at, reverse=True)
        return items[:limit]
