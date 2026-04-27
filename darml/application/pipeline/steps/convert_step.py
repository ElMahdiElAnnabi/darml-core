from darml.application.ports.converter import ConverterPort
from darml.domain.enums import BuildStatus, ModelFormat, Runtime
from darml.domain.exceptions import ProFeatureRequired
from darml.domain.targets import get_target

from ..context import BuildContext
from ..step import PipelineStep


class ConvertStep(PipelineStep):
    """Convert model format to whatever the target runtime needs, if necessary."""

    def __init__(self, converters: list[ConverterPort]):
        self._converters: dict[tuple[ModelFormat, ModelFormat], ConverterPort] = {
            (c.source_format, c.target_format): c for c in converters
        }

    @property
    def name(self) -> str:
        return "convert"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.CONVERTING

    async def run(self, ctx: BuildContext) -> BuildContext:
        assert ctx.model_info is not None
        target = get_target(ctx.request.target_id)
        if target is None:
            return ctx

        required = self._runtime_to_format(target.runtime)
        if required is None or required == ctx.model_info.format:
            return ctx

        converter = self._converters.get((ctx.model_info.format, required))
        if converter is None:
            # ONNX → TFLite is the most common missing converter; it's a
            # Pro feature. Be explicit so the user knows what to do.
            if ctx.model_info.format == ModelFormat.ONNX and required == ModelFormat.TFLITE:
                raise ProFeatureRequired.for_feature(
                    feature="ONNX → TFLite auto-conversion",
                    free_alternative=(
                        "convert manually with onnx2tf or tf.lite.TFLiteConverter, "
                        "then re-run `darml build` with the resulting .tflite"
                    ),
                )
            # Otherwise let the builder produce a clearer error for this combo.
            return ctx

        output = ctx.workspace / f"model.{required.value}"
        # Pass `quantize` through to the converter. For ONNX→TFLite this is
        # the ONLY effective place to quantize: onnx2tf with INT8 PTQ
        # produces native TFLite ops, while a separate ONNX-side quant
        # step yields Flex/Select-TF ops that tflite-micro can't run.
        new_path = converter.convert(
            ctx.current_model_path,
            output,
            quantize=ctx.request.quantize,
            calibration_data_path=ctx.request.calibration_data_path,
        )
        ctx.current_model_path = new_path
        if ctx.request.quantize:
            calib_kind = (
                "your supplied calibration data"
                if ctx.request.calibration_data_path
                else "SYNTHETIC random N(0, 1) samples"
            )
            ctx.result.warnings.append(
                "ACCURACY NOTICE — INT8 post-training quantization was "
                f"applied using {calib_kind}.\n"
                "  · Darml does NOT perform quantization-aware training (QAT).\n"
                "  · Expected accuracy drop vs your FP32 model:\n"
                "      small dense:           1-3%\n"
                "      CNNs (mnist-class):    3-8%\n"
                "      larger CNNs (mobilenet/resnet):  5-15%+\n"
                "  · ALWAYS validate the quantized model against your held-out\n"
                "    test set before deploying to production hardware.\n"
                + (
                    "  · To improve accuracy, re-run with --calibration-data\n"
                    "    pointing to a .npy/.npz of representative inputs."
                    if not ctx.request.calibration_data_path else ""
                )
            )
        return ctx

    @staticmethod
    def _runtime_to_format(runtime: Runtime) -> ModelFormat | None:
        if runtime in {Runtime.TFLITE_MICRO, Runtime.TFLITE}:
            return ModelFormat.TFLITE
        if runtime == Runtime.EMLEARN:
            return ModelFormat.SKLEARN
        return None
