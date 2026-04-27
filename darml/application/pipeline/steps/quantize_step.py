from darml.application.factories.quantizer_factory import QuantizerFactory
from darml.domain.enums import BuildStatus, ModelFormat, Runtime
from darml.domain.exceptions import ProFeatureRequired
from darml.domain.targets import get_target

from ..context import BuildContext
from ..step import PipelineStep


def _runtime_to_format(runtime: Runtime) -> ModelFormat | None:
    if runtime in {Runtime.TFLITE_MICRO, Runtime.TFLITE}:
        return ModelFormat.TFLITE
    if runtime == Runtime.EMLEARN:
        return ModelFormat.SKLEARN
    return None


class QuantizeStep(PipelineStep):
    """Optional in-format quantization step.

    Quantizes BEFORE the convert step, only when no format conversion is
    coming. If the model needs converting (e.g. ONNX → TFLite), we defer
    quantization to the converter — onnx2tf's INT8 PTQ produces native
    TFLite ops, whereas pre-converting at the ONNX layer leaves Flex /
    Select-TF ops in the result, which tflite-micro can't load.

    Without darml_pro installed, no quantizer is registered. If the user
    explicitly asked for quantization, we raise a friendly
    ProFeatureRequired pointing at the trial AND a manual fallback.
    """

    def __init__(self, factory: QuantizerFactory):
        self._factory = factory

    @property
    def name(self) -> str:
        return "quantize"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.QUANTIZING

    async def run(self, ctx: BuildContext) -> BuildContext:
        if not ctx.request.quantize:
            return ctx
        assert ctx.model_info is not None
        if ctx.model_info.is_quantized:
            ctx.result.warnings.append("Model is already quantized; skipping.")
            return ctx

        # If the convert step is going to change formats, defer to it —
        # the converter knows how to produce native, runtime-compatible
        # quantized ops for the target format.
        target = get_target(ctx.request.target_id)
        if target is not None:
            required = _runtime_to_format(target.runtime)
            if required is not None and required != ctx.model_info.format:
                return ctx

        quantizer = self._factory.for_format(ctx.model_info.format)
        if quantizer is None:
            raise ProFeatureRequired.for_feature(
                feature="INT8 auto-quantization",
                free_alternative=(
                    "quantize manually before uploading: "
                    "use `tf.lite.TFLiteConverter` with "
                    "`optimizations=[tf.lite.Optimize.DEFAULT]`, then re-run "
                    "`darml build` with the pre-quantized model"
                ),
            )
        output = ctx.workspace / f"model_q{ctx.current_model_path.suffix}"
        q = quantizer.quantize(ctx.current_model_path, output)
        ctx.result.quantize_result = q
        ctx.current_model_path = q.output_path
        return ctx
