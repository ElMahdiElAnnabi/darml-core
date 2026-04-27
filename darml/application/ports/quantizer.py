from abc import ABC, abstractmethod
from pathlib import Path

from darml.domain.enums import ModelFormat
from darml.domain.models import QuantizeResult


class QuantizerPort(ABC):
    """Quantize a model to reduce size and RAM footprint."""

    @property
    @abstractmethod
    def format(self) -> ModelFormat: ...

    @abstractmethod
    def quantize(self, input_path: Path, output_path: Path) -> QuantizeResult: ...
