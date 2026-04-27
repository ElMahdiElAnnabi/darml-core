from darml.application.use_cases.parse_model import ParseModel
from darml.domain.enums import BuildStatus

from ..context import BuildContext
from ..step import PipelineStep


class ParseStep(PipelineStep):
    def __init__(self, parse_model: ParseModel):
        self._parse = parse_model

    @property
    def name(self) -> str:
        return "parse"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.PARSING

    async def run(self, ctx: BuildContext) -> BuildContext:
        ctx.model_info = self._parse.execute(ctx.current_model_path)
        ctx.result.model_info = ctx.model_info
        return ctx
