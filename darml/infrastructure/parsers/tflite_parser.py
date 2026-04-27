from pathlib import Path

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import DType, ModelFormat
from darml.domain.exceptions import ModelParseError
from darml.domain.models import ModelInfo


class TFLiteParser(ModelParserPort):
    """Parse a .tflite model using the tensorflow or tflite_runtime interpreter."""

    @property
    def format(self) -> ModelFormat:
        return ModelFormat.TFLITE

    def parse(self, path: Path) -> ModelInfo:
        self._validate_magic(path)
        interpreter = self._load_interpreter(path)
        interpreter.allocate_tensors()
        inputs = interpreter.get_input_details()
        outputs = interpreter.get_output_details()
        if not inputs or not outputs:
            raise ModelParseError("TFLite model has no inputs or outputs.")

        input_spec = inputs[0]
        output_spec = outputs[0]

        input_dtype = self._np_to_dtype(input_spec["dtype"])
        output_dtype = self._np_to_dtype(output_spec["dtype"])
        is_quantized = input_dtype in {DType.INT8, DType.UINT8}

        try:
            ops = interpreter._get_ops_details()  # type: ignore[attr-defined]
            ops_list = tuple(op.get("op_name", "") for op in ops)
        except Exception:
            ops_list = ()

        return ModelInfo(
            format=ModelFormat.TFLITE,
            file_size_bytes=path.stat().st_size,
            input_shape=tuple(int(d) for d in input_spec["shape"]),
            output_shape=tuple(int(d) for d in output_spec["shape"]),
            input_dtype=input_dtype,
            output_dtype=output_dtype,
            num_ops=len(ops_list),
            is_quantized=is_quantized,
            ops_list=ops_list,
        )

    @staticmethod
    def _validate_magic(path: Path) -> None:
        # TFLite flatbuffers carry the identifier "TFL3" at byte offset 4.
        # Reject anything that doesn't look like a flatbuffer up-front so we
        # don't waste time spinning up the interpreter on a renamed .jpg.
        if path.stat().st_size < 8:
            raise ModelParseError("File is too small to be a valid .tflite.")
        with path.open("rb") as f:
            header = f.read(8)
        if header[4:8] != b"TFL3":
            raise ModelParseError(
                "File does not look like a TFLite flatbuffer "
                "(missing 'TFL3' identifier). Did you upload the right file?"
            )

    @staticmethod
    def _load_interpreter(path: Path):
        try:
            import tensorflow as tf  # type: ignore
            return tf.lite.Interpreter(model_path=str(path))
        except ImportError:
            pass
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore
            return Interpreter(model_path=str(path))
        except ImportError as e:
            raise ModelParseError(
                "Parsing .tflite requires tensorflow or tflite-runtime. "
                "Install with: pip install darml[tflite]"
            ) from e

    @staticmethod
    def _np_to_dtype(dt) -> DType:
        try:
            import numpy as np  # type: ignore
        except ImportError:
            return DType.FLOAT32
        mapping = [
            (np.float32, DType.FLOAT32),
            (np.float16, DType.FLOAT16),
            (np.int8, DType.INT8),
            (np.uint8, DType.UINT8),
            (np.int16, DType.INT16),
            (np.int32, DType.INT32),
        ]
        for np_dt, our_dt in mapping:
            if dt == np_dt:
                return our_dt
        return DType.FLOAT32
