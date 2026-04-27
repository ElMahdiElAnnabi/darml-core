from dataclasses import dataclass

from darml.application.ports.build_repository import BuildRepositoryPort
from darml.domain.exceptions import BuildNotFound
from darml.domain.models import BuildResult


@dataclass
class GetBuildStatus:
    repo: BuildRepositoryPort

    async def execute(self, build_id: str) -> BuildResult:
        result = await self.repo.get(build_id)
        if result is None:
            raise BuildNotFound(f"No build with id: {build_id}")
        return result
