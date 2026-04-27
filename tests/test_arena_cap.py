"""PlatformIOBuilder caps the tensor arena to fit the chip's DRAM."""

from __future__ import annotations

from pathlib import Path

from darml.domain.enums import DType, ModelFormat, OutputKind, ReportMode
from darml.domain.models import BuildRequest, ModelInfo
from darml.infrastructure.builders.esp32_builder import ESP32Builder
from darml.infrastructure.builders.stm32_builder import STM32F4Builder
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

TEMPLATES = Path(__file__).resolve().parent.parent / "darml" / "infrastructure" / "templates"


def _info(input_elements: int) -> ModelInfo:
    return ModelInfo(
        format=ModelFormat.TFLITE,
        file_size_bytes=1024,
        input_shape=(1, input_elements),
        output_shape=(1, 4),
        input_dtype=DType.FLOAT32,
        output_dtype=DType.FLOAT32,
        num_ops=3,
        is_quantized=False,
        ops_list=("CONV_2D",),
    )


def _request() -> BuildRequest:
    return BuildRequest(
        model_path=Path("/dev/null"),
        target_id="esp32-s3",
        report_mode=ReportMode.SERIAL,
        output_kind=OutputKind.FIRMWARE,
    )


def test_esp32_arena_caps_at_150kb():
    builder = ESP32Builder(TEMPLATES, PlatformIORunner())
    # huge input that would otherwise demand a 1.6 MB arena
    values, warnings = builder._template_values(_info(200_000), _request())  # noqa: SLF001
    arena = int(values["TENSOR_ARENA_SIZE"])
    assert arena <= 150 * 1024
    assert any("capped" in w for w in warnings)


def test_esp32_arena_uses_ideal_when_under_cap():
    builder = ESP32Builder(TEMPLATES, PlatformIORunner())
    values, warnings = builder._template_values(_info(2000), _request())  # noqa: SLF001
    # 2000 * 8 = 16000, but tensor_arena_min_bytes = 65536 → arena = 65536
    arena = int(values["TENSOR_ARENA_SIZE"])
    assert arena == 65536
    assert not warnings


def test_stm32f4_arena_caps_at_96kb():
    builder = STM32F4Builder(TEMPLATES, PlatformIORunner())
    values, warnings = builder._template_values(_info(50_000), _request())  # noqa: SLF001
    arena = int(values["TENSOR_ARENA_SIZE"])
    assert arena <= 96 * 1024
    assert any("capped" in w for w in warnings)
