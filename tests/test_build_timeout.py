"""Build timeout: a slow pipeline gets killed and reports a clear error."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from darml.application.pipeline.context import BuildContext
from darml.application.pipeline.pipeline import BuildPipeline
from darml.application.pipeline.step import PipelineStep
from darml.application.ports.progress_reporter import ProgressReporterPort
from darml.application.use_cases.build_firmware import BuildFirmware
from darml.domain.enums import BuildStatus, OutputKind, ReportMode
from darml.domain.models import BuildRequest, BuildResult
from darml.infrastructure.persistence.in_memory_build_repo import InMemoryBuildRepository
from darml.infrastructure.storage.filesystem_storage import FileSystemStorage


class SlowStep(PipelineStep):
    @property
    def name(self) -> str: return "sleep"
    @property
    def status(self): return BuildStatus.COMPILING

    async def run(self, ctx: BuildContext) -> BuildContext:
        await asyncio.sleep(10)
        return ctx


class NullReporter(ProgressReporterPort):
    async def report(self, *a, **kw): return None


def test_build_timeout_kills_slow_pipeline(tmp_path):
    model = tmp_path / "m.tflite"
    model.write_bytes(b"x" * 16)

    use_case = BuildFirmware(
        pipeline=BuildPipeline(steps=[SlowStep()], reporter=NullReporter()),
        repo=InMemoryBuildRepository(),
        storage=FileSystemStorage(tmp_path / "data"),
        cache=None,
        timeout_s=1,
    )
    request = BuildRequest(
        model_path=model,
        target_id="esp32-s3",
        output_kind=OutputKind.FIRMWARE,
        report_mode=ReportMode.SERIAL,
    )
    result = asyncio.run(use_case.execute(request))
    assert result.status == BuildStatus.FAILED
    assert result.error is not None
    assert "DARML_BUILD_TIMEOUT" in result.error
    assert "1s" in result.error
