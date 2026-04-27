from collections.abc import Iterable

from darml.application.ports.quantizer import QuantizerPort
from darml.domain.enums import ModelFormat


class QuantizerFactory:
    """Select a Quantizer for a given model format. Returns None if none registered."""

    def __init__(self, quantizers: Iterable[QuantizerPort]):
        self._quantizers: dict[ModelFormat, QuantizerPort] = {q.format: q for q in quantizers}

    def for_format(self, fmt: ModelFormat) -> QuantizerPort | None:
        return self._quantizers.get(fmt)
