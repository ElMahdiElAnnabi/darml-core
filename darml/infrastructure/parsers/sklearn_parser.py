from pathlib import Path

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import DType, ModelFormat
from darml.domain.exceptions import ModelParseError
from darml.domain.models import ModelInfo


class SklearnParser(ModelParserPort):
    @property
    def format(self) -> ModelFormat:
        return ModelFormat.SKLEARN

    def parse(self, path: Path) -> ModelInfo:
        try:
            import joblib  # type: ignore
        except ImportError as e:
            raise ModelParseError(
                "Parsing scikit-learn models requires joblib. "
                "Install with: pip install darml[sklearn]"
            ) from e

        # joblib pickles always start with the pickle protocol marker.
        if path.stat().st_size < 2:
            raise ModelParseError("File is too small to be a valid pickle.")
        with path.open("rb") as f:
            if f.read(1) != b"\x80":
                raise ModelParseError(
                    "File does not look like a pickle (missing 0x80 protocol "
                    "marker). Did you upload the right file?"
                )

        try:
            model = joblib.load(path)
        except Exception as e:
            raise ModelParseError(f"Failed to load sklearn model: {e}") from e

        if not hasattr(model, "predict") and not hasattr(model, "predict_proba"):
            raise ModelParseError(
                f"Loaded object is a {type(model).__name__}, not a "
                "scikit-learn estimator (missing .predict / .predict_proba)."
            )

        n_features = int(getattr(model, "n_features_in_", 0) or 0)
        classes = getattr(model, "classes_", None)
        n_classes = int(len(classes)) if classes is not None else 1

        return ModelInfo(
            format=ModelFormat.SKLEARN,
            file_size_bytes=path.stat().st_size,
            input_shape=(1, n_features),
            output_shape=(1, n_classes),
            input_dtype=DType.FLOAT32,
            output_dtype=DType.FLOAT32,
            num_ops=1,
            is_quantized=False,
            ops_list=(type(model).__name__,),
        )
