from pathlib import Path

from darml.domain.enums import ReportMode
from darml.domain.models import BuildRequest, ModelInfo
from darml.domain.enums import DType, ModelFormat
from darml.infrastructure.builders.esp32_builder import ESP32Builder
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "darml" / "infrastructure" / "templates"


def _model_info(input_elements=64, quantized=False):
    return ModelInfo(
        format=ModelFormat.TFLITE,
        file_size_bytes=1024,
        input_shape=(1, input_elements),
        output_shape=(1, 4),
        input_dtype=DType.INT8 if quantized else DType.FLOAT32,
        output_dtype=DType.FLOAT32,
        num_ops=3,
        is_quantized=quantized,
        ops_list=("CONV_2D",),
    )


def test_esp32_builder_injects_model_and_renders_arena_into_platformio_ini(tmp_path):
    model = tmp_path / "model.tflite"
    model.write_bytes(b"\x01\x02\x03\x04" * 64)

    builder = ESP32Builder(TEMPLATES_ROOT, PlatformIORunner())
    project = builder._prepare_project(tmp_path)  # noqa: SLF001
    builder._inject_model(  # noqa: SLF001
        project,
        model,
        _model_info(),
        BuildRequest(model_path=model, target_id="esp32-s3", report_mode=ReportMode.SERIAL),
    )

    main_cpp = (project / "src" / "main.cpp").read_text()
    assert "{{INPUT_SIZE}}" not in main_cpp
    assert "{{OUTPUT_SIZE}}" not in main_cpp

    pio_ini = (project / "platformio.ini").read_text()
    assert "{{TENSOR_ARENA_SIZE}}" not in pio_ini
    assert "TENSOR_ARENA_SIZE=" in pio_ini

    model_header = (project / "src" / "model_data.h").read_text()
    assert "model_data" in model_header
    assert "model_data_len = 256" in model_header
