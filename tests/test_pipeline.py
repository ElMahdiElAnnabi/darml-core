import asyncio
from pathlib import Path

from darml.application.factories.parser_factory import ParserFactory
from darml.application.factories.quantizer_factory import QuantizerFactory
from darml.application.pipeline.pipeline import BuildPipeline
from darml.application.pipeline.steps.check_step import CheckStep
from darml.application.pipeline.steps.parse_step import ParseStep
from darml.application.pipeline.steps.quantize_step import QuantizeStep
from darml.application.ports.progress_reporter import ProgressReporterPort
from darml.application.pipeline.context import BuildContext
from darml.application.use_cases.check_size import CheckSize
from darml.application.use_cases.parse_model import ParseModel
from darml.domain.enums import BuildStatus
from darml.domain.models import BuildRequest, BuildResult


class RecordingReporter(ProgressReporterPort):
    def __init__(self):
        self.events = []

    async def report(self, build_id, status, message="", progress=0.0):
        self.events.append((status, message, progress))


def test_pipeline_runs_all_steps_and_marks_completed(tmp_path, fake_tflite_parser):
    model = tmp_path / "model.tflite"
    model.write_bytes(b"dummy model bytes")

    reporter = RecordingReporter()
    pipeline = BuildPipeline(
        steps=[
            ParseStep(ParseModel(ParserFactory([fake_tflite_parser]))),
            CheckStep(CheckSize(), strict=False),
            QuantizeStep(QuantizerFactory([])),
        ],
        reporter=reporter,
    )
    ctx = BuildContext(
        request=BuildRequest(model_path=model, target_id="esp32-s3"),
        result=BuildResult.new(target_id="esp32-s3"),
        workspace=tmp_path,
        current_model_path=model,
    )

    asyncio.run(pipeline.run(ctx))

    assert ctx.result.status == BuildStatus.COMPLETED
    assert ctx.model_info is not None
    assert ctx.result.size_check is not None
    # Reporter saw parse + check + quantize + completion = 4 events
    assert any(status == BuildStatus.PARSING for status, *_ in reporter.events)
    assert any(status == BuildStatus.COMPLETED for status, *_ in reporter.events)
