import pytest

from darml.application.factories.parser_factory import ParserFactory
from darml.application.use_cases.parse_model import ParseModel
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ModelFormatUnsupported


def test_parse_detects_tflite_from_suffix(tmp_path, fake_tflite_parser):
    path = tmp_path / "model.tflite"
    path.write_bytes(b"dummy")
    uc = ParseModel(ParserFactory([fake_tflite_parser]))

    info = uc.execute(path)

    assert info.format == ModelFormat.TFLITE
    assert info.input_shape == (1, 10)


def test_parse_respects_explicit_format_hint(tmp_path, fake_tflite_parser):
    path = tmp_path / "model.bin"
    path.write_bytes(b"dummy")
    uc = ParseModel(ParserFactory([fake_tflite_parser]))

    info = uc.execute(path, format_hint=ModelFormat.TFLITE)

    assert info.format == ModelFormat.TFLITE


def test_parse_unknown_suffix_raises(tmp_path, fake_tflite_parser):
    path = tmp_path / "model.bin"
    path.write_bytes(b"dummy")
    uc = ParseModel(ParserFactory([fake_tflite_parser]))

    with pytest.raises(ModelFormatUnsupported):
        uc.execute(path)


def test_parse_missing_parser_raises(tmp_path):
    path = tmp_path / "model.tflite"
    path.write_bytes(b"dummy")
    uc = ParseModel(ParserFactory([]))

    with pytest.raises(ModelFormatUnsupported):
        uc.execute(path)
