from collections.abc import Iterable

from darml.application.ports.progress_reporter import ProgressReporterPort
from darml.domain.enums import BuildStatus


class CompositeReporter(ProgressReporterPort):
    """Fan out a single report() call to many reporters."""

    def __init__(self, reporters: Iterable[ProgressReporterPort]):
        self._reporters = list(reporters)

    async def report(
        self,
        build_id: str,
        status: BuildStatus,
        message: str = "",
        progress: float = 0.0,
    ) -> None:
        for r in self._reporters:
            try:
                await r.report(build_id, status, message, progress)
            except Exception:
                # Never let a reporter failure break the build.
                pass
