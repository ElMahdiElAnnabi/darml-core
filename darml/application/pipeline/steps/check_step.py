from darml.application.use_cases.check_size import CheckSize
from darml.domain.enums import BuildStatus
from darml.domain.exceptions import ModelTooLarge

from ..context import BuildContext
from ..step import PipelineStep


class CheckStep(PipelineStep):
    def __init__(self, check_size: CheckSize, strict: bool = True):
        self._check = check_size
        self._strict = strict

    @property
    def name(self) -> str:
        return "check"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.CHECKING

    async def run(self, ctx: BuildContext) -> BuildContext:
        assert ctx.model_info is not None, "check step requires parsed ModelInfo"
        result = self._check.execute(ctx.model_info, ctx.request.target_id)
        ctx.result.size_check = result
        if result.warning:
            ctx.result.warnings.append(result.warning)
        if not result.fits and self._strict and not ctx.request.quantize:
            raise ModelTooLarge(result.warning or "Model too large for target.")
        return ctx
