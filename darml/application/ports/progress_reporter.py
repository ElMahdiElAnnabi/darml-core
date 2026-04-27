from abc import ABC, abstractmethod

from darml.domain.enums import BuildStatus


class ProgressReporterPort(ABC):
    """Emit build progress events. Implementations fan out to log/DB/WebSocket."""

    @abstractmethod
    async def report(
        self,
        build_id: str,
        status: BuildStatus,
        message: str = "",
        progress: float = 0.0,
    ) -> None: ...
