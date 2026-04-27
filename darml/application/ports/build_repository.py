from abc import ABC, abstractmethod

from darml.domain.models import BuildResult


class BuildRepositoryPort(ABC):
    """Persist build records."""

    @abstractmethod
    async def save(self, build: BuildResult) -> None: ...

    @abstractmethod
    async def get(self, build_id: str) -> BuildResult | None: ...

    @abstractmethod
    async def list(self, limit: int = 50) -> list[BuildResult]: ...
