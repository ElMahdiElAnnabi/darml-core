from collections.abc import Iterable

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ModelFormatUnsupported


class ParserFactory:
    """Select the right ModelParser for a given format."""

    def __init__(self, parsers: Iterable[ModelParserPort]):
        self._parsers: dict[ModelFormat, ModelParserPort] = {p.format: p for p in parsers}

    def for_format(self, fmt: ModelFormat) -> ModelParserPort:
        parser = self._parsers.get(fmt)
        if parser is None:
            raise ModelFormatUnsupported(f"No parser registered for format: {fmt.value}")
        return parser

    def supported_formats(self) -> list[ModelFormat]:
        return list(self._parsers.keys())
