from dataclasses import replace

import pytest

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import DType, ModelFormat
from darml.domain.models import ModelInfo


class FakeTFLiteParser(ModelParserPort):
    """Deterministic parser for tests — avoids the heavy tensorflow dep."""

    def __init__(self, info: ModelInfo | None = None):
        self._info = info

    @property
    def format(self) -> ModelFormat:
        return ModelFormat.TFLITE

    def parse(self, path):
        base = self._info or ModelInfo(
            format=ModelFormat.TFLITE,
            file_size_bytes=0,
            input_shape=(1, 10),
            output_shape=(1, 3),
            input_dtype=DType.FLOAT32,
            output_dtype=DType.FLOAT32,
            num_ops=5,
            is_quantized=False,
            ops_list=("FULLY_CONNECTED",),
        )
        return replace(base, file_size_bytes=path.stat().st_size)


@pytest.fixture
def fake_tflite_parser() -> FakeTFLiteParser:
    return FakeTFLiteParser()
