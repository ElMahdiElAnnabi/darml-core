from pathlib import Path

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import DType, ModelFormat
from darml.domain.exceptions import ModelParseError
from darml.domain.models import ModelInfo

_ONNX_DTYPE_MAP: dict[int, DType] = {
    1: DType.FLOAT32,
    2: DType.UINT8,
    3: DType.INT8,
    5: DType.INT16,
    6: DType.INT32,
    10: DType.FLOAT16,
}


class ONNXParser(ModelParserPort):
    @property
    def format(self) -> ModelFormat:
        return ModelFormat.ONNX

    def parse(self, path: Path) -> ModelInfo:
        try:
            import onnx  # type: ignore
        except ImportError as e:
            raise ModelParseError(
                "Parsing .onnx requires the onnx package. "
                "Install with: pip install darml[onnx]"
            ) from e

        # ONNX has an "external data" format where tensors >2 GB live in
        # sidecar files (e.g. resnet18.onnx + resnet18.onnx.data). For
        # *parsing metadata* we don't need the weights — pass
        # load_external_data=False to read the graph proto only. The
        # ConvertStep (ONNX→TFLite) will surface its own error later if
        # the weights are actually needed for that build.
        try:
            model = onnx.load(str(path), load_external_data=False)
        except Exception as e:
            raise ModelParseError(
                f"File is not a valid ONNX protobuf: {e}. "
                "Did you upload the right file?"
            ) from e

        graph = model.graph
        if not graph.input or not graph.output:
            raise ModelParseError("ONNX model has no inputs or outputs.")

        input_spec = graph.input[0]
        output_spec = graph.output[0]

        input_shape = tuple(
            d.dim_value if d.dim_value > 0 else -1
            for d in input_spec.type.tensor_type.shape.dim
        )
        output_shape = tuple(
            d.dim_value if d.dim_value > 0 else -1
            for d in output_spec.type.tensor_type.shape.dim
        )

        input_dtype = _ONNX_DTYPE_MAP.get(
            input_spec.type.tensor_type.elem_type, DType.FLOAT32
        )
        output_dtype = _ONNX_DTYPE_MAP.get(
            output_spec.type.tensor_type.elem_type, DType.FLOAT32
        )

        ops_list = tuple(node.op_type for node in graph.node)
        is_quantized = any(
            "Quant" in op or "QLinear" in op for op in ops_list
        )

        return ModelInfo(
            format=ModelFormat.ONNX,
            file_size_bytes=path.stat().st_size,
            input_shape=input_shape,
            output_shape=output_shape,
            input_dtype=input_dtype,
            output_dtype=output_dtype,
            num_ops=len(ops_list),
            is_quantized=is_quantized,
            ops_list=ops_list,
        )
