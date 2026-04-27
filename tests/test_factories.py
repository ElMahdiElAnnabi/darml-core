import pytest

from darml.application.factories.parser_factory import ParserFactory
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ModelFormatUnsupported


def test_parser_factory_returns_matching_parser(fake_tflite_parser):
    factory = ParserFactory([fake_tflite_parser])
    assert factory.for_format(ModelFormat.TFLITE) is fake_tflite_parser


def test_parser_factory_reports_supported_formats(fake_tflite_parser):
    factory = ParserFactory([fake_tflite_parser])
    assert ModelFormat.TFLITE in factory.supported_formats()


def test_parser_factory_unknown_format_raises():
    factory = ParserFactory([])
    with pytest.raises(ModelFormatUnsupported):
        factory.for_format(ModelFormat.ONNX)
