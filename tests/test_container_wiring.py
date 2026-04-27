from darml.application.factories.builder_factory import BuilderFactory
from darml.application.pipeline.steps.compile_step import CompileStep
from darml.application.pipeline.steps.convert_step import ConvertStep
from darml.application.pipeline.steps.quantize_step import QuantizeStep
from darml.container import Container, get_container
from darml.domain.enums import ModelFormat


def test_container_registers_onnx_quantizer():
    c = Container(get_container().settings)
    quantizer = c.quantizer_factory.for_format(ModelFormat.ONNX)
    assert quantizer is not None
    assert quantizer.format == ModelFormat.ONNX


def test_container_registers_onnx_to_tflite_converter():
    c = Container(get_container().settings)
    convert_steps = [s for s in c.pipeline.steps if isinstance(s, ConvertStep)]
    assert convert_steps, "pipeline must include a ConvertStep"
    # Pull the private dict to assert the (ONNX, TFLITE) pair is registered.
    converters = convert_steps[0]._converters  # noqa: SLF001
    assert (ModelFormat.ONNX, ModelFormat.TFLITE) in converters


def test_pipeline_contains_quantize_and_convert_in_order():
    c = Container(get_container().settings)
    names = [s.name for s in c.pipeline.steps]
    assert names.index("quantize") < names.index("convert"), (
        "quantize must run before convert: ONNX-quantize → TFLite-convert path"
    )


def test_all_targets_have_a_builder():
    c = Container(get_container().settings)
    factory: BuilderFactory = c.builder_factory
    expected = {t.id for t in c.list_targets.execute()}
    assert expected.issubset(set(factory.supported_targets()))


def test_pipeline_has_compile_step():
    c = Container(get_container().settings)
    assert any(isinstance(s, CompileStep) for s in c.pipeline.steps)
