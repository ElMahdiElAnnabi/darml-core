import pytest

from darml.application.use_cases.check_size import CheckSize
from darml.domain.enums import DType, ModelFormat
from darml.domain.exceptions import TargetUnknown
from darml.domain.models import ModelInfo


def _mk(size_bytes=100_000, input_elements=1000, quantized=False) -> ModelInfo:
    return ModelInfo(
        format=ModelFormat.TFLITE,
        file_size_bytes=size_bytes,
        input_shape=(1, input_elements),
        output_shape=(1, 10),
        input_dtype=DType.INT8 if quantized else DType.FLOAT32,
        output_dtype=DType.FLOAT32,
        num_ops=10,
        is_quantized=quantized,
        ops_list=(),
    )


def test_check_fits_small_model_on_esp32():
    uc = CheckSize()
    result = uc.execute(_mk(size_bytes=50_000, input_elements=100), "esp32-s3")
    assert result.fits
    assert result.model_flash_kb < result.target_flash_kb


def test_check_too_large_for_avr():
    uc = CheckSize()
    result = uc.execute(_mk(size_bytes=500_000, input_elements=10_000), "avr-mega328")
    assert not result.fits
    assert result.warning is not None


def test_check_quantized_model_has_smaller_ram_footprint():
    uc = CheckSize()
    float_res = uc.execute(_mk(input_elements=10_000, quantized=False), "stm32f4")
    int8_res = uc.execute(_mk(input_elements=10_000, quantized=True), "stm32f4")
    assert int8_res.model_ram_kb < float_res.model_ram_kb


def test_check_unknown_target_raises():
    uc = CheckSize()
    with pytest.raises(TargetUnknown):
        uc.execute(_mk(), "not-a-real-target")
