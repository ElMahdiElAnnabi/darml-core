from dataclasses import dataclass
from datetime import datetime, timezone

from darml.application.ports.progress_reporter import ProgressReporterPort
from darml.domain.enums import BuildStatus

from .context import BuildContext
from .step import PipelineStep


@dataclass
class BuildPipeline:
    """Run an ordered sequence of PipelineSteps, emitting progress events."""

    steps: list[PipelineStep]
    reporter: ProgressReporterPort

    async def run(self, ctx: BuildContext) -> BuildContext:
        total = max(1, len(self.steps))
        try:
            for idx, step in enumerate(self.steps):
                ctx.result.status = step.status
                await self.reporter.report(
                    ctx.result.build_id,
                    step.status,
                    f"Running {step.name}",
                    progress=idx / total,
                )
                ctx = await step.run(ctx)
            ctx.result.status = BuildStatus.COMPLETED
            ctx.result.completed_at = datetime.now(timezone.utc)
            await self.reporter.report(
                ctx.result.build_id, BuildStatus.COMPLETED, "Build complete", 1.0
            )
        except Exception as e:
            ctx.result.status = BuildStatus.FAILED
            ctx.result.error = str(e)
            ctx.result.completed_at = datetime.now(timezone.utc)
            await self.reporter.report(
                ctx.result.build_id, BuildStatus.FAILED, str(e), 1.0
            )
            raise
        return ctx
