import logging

from darml.application.ports.progress_reporter import ProgressReporterPort
from darml.domain.enums import BuildStatus


class LogReporter(ProgressReporterPort):
    def __init__(self, logger: logging.Logger | None = None):
        self._log = logger or logging.getLogger("darml.build")

    async def report(
        self,
        build_id: str,
        status: BuildStatus,
        message: str = "",
        progress: float = 0.0,
    ) -> None:
        self._log.info(
            "[%s] %-10s %3.0f%% %s",
            build_id[:8],
            status.value,
            progress * 100,
            message,
        )
