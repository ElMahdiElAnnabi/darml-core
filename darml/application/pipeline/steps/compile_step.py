from darml.application.factories.builder_factory import BuilderFactory
from darml.domain.enums import BuildStatus

from ..context import BuildContext
from ..step import PipelineStep


class CompileStep(PipelineStep):
    def __init__(self, factory: BuilderFactory):
        self._factory = factory

    @property
    def name(self) -> str:
        return "compile"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.COMPILING

    async def run(self, ctx: BuildContext) -> BuildContext:
        assert ctx.model_info is not None
        builder = self._factory.for_target(ctx.request.target_id)
        build_result = await builder.build(
            request=ctx.request,
            model_info=ctx.model_info,
            model_path=ctx.current_model_path,
            workspace=ctx.workspace,
        )
        ctx.result.firmware_path = build_result.firmware_path
        ctx.result.library_path = build_result.library_path
        if build_result.build_log:
            ctx.result.build_log = build_result.build_log
        ctx.result.warnings.extend(build_result.warnings)
        return ctx
