from pathlib import Path

from darml.application.ports.converter import ConverterPort
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ConversionFailed


class SklearnToCConverter(ConverterPort):
    """Convert scikit-learn models to pure C via emlearn.

    Writes a model.h into `output_path.parent` and returns that header path.
    """

    @property
    def source_format(self) -> ModelFormat:
        return ModelFormat.SKLEARN

    @property
    def target_format(self) -> ModelFormat:
        # emlearn emits C, not another model format — we signal SKLEARN here to
        # indicate no transformation at the ModelFormat layer; AVRBuilder handles
        # the actual C generation directly as part of the inject step.
        return ModelFormat.SKLEARN

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        quantize: bool = False,  # noqa: ARG002 — emlearn output is already small
        calibration_data_path: "Path | None" = None,  # noqa: ARG002
    ) -> Path:
        try:
            import emlearn  # type: ignore
            import joblib  # type: ignore
        except ImportError as e:
            raise ConversionFailed(
                "sklearn→C conversion requires emlearn and joblib. "
                "Install with: pip install darml[sklearn]"
            ) from e

        try:
            model = joblib.load(input_path)
            c_model = emlearn.convert(model)
            header = output_path.with_suffix(".h")
            c_model.save(file=str(header), name="darml_model")
            return header
        except Exception as e:
            raise ConversionFailed(f"emlearn conversion failed: {e}") from e
