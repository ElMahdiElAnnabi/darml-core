from dataclasses import dataclass
from pathlib import Path

from darml.application.factories.parser_factory import ParserFactory
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ModelFormatUnsupported
from darml.domain.models import ModelInfo


@dataclass
class ParseModel:
    """Parse any supported model file into a uniform ModelInfo."""

    parser_factory: ParserFactory

    def execute(self, path: Path, format_hint: ModelFormat | None = None) -> ModelInfo:
        fmt = format_hint or self._detect_format(path)
        parser = self.parser_factory.for_format(fmt)
        return parser.parse(path)

    @staticmethod
    def _detect_format(path: Path) -> ModelFormat:
        suffix = path.suffix.lower()
        if suffix == ".tflite":
            return ModelFormat.TFLITE
        if suffix == ".onnx":
            return ModelFormat.ONNX
        if suffix in {".pkl", ".joblib"}:
            return ModelFormat.SKLEARN
        raise ModelFormatUnsupported(
            f"Cannot detect model format from file suffix: {suffix!r}"
        )
