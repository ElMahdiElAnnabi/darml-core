from abc import ABC, abstractmethod
from pathlib import Path

from darml.domain.enums import ModelFormat


class ConverterPort(ABC):
    """Convert a model from one format to another."""

    @property
    @abstractmethod
    def source_format(self) -> ModelFormat: ...

    @property
    @abstractmethod
    def target_format(self) -> ModelFormat: ...

    @abstractmethod
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        quantize: bool = False,
        calibration_data_path: Path | None = None,
    ) -> Path:
        """Convert input model to target format.

        If `quantize` is True the implementation should produce an INT8
        quantized output where the target format supports it (TFLite),
        ensuring the resulting file uses native ops compatible with the
        target runtime (e.g. tflite-micro, no Flex/Select-TF ops).

        `calibration_data_path` is an optional .npy/.npz with
        representative input samples for INT8 PTQ. When None, the
        implementation should synthesize random samples and surface an
        accuracy warning to the caller. Implementations that don't
        support quantization may ignore both flags.
        """
