from abc import ABC, abstractmethod

from darml.domain.enums import BuildStatus

from .context import BuildContext


class PipelineStep(ABC):
    """One stage of the build pipeline. Reads and mutates a BuildContext."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def status(self) -> BuildStatus: ...

    @abstractmethod
    async def run(self, ctx: BuildContext) -> BuildContext: ...
