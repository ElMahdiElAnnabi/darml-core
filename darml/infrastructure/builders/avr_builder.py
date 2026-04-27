from pathlib import Path

from darml.domain.enums import ModelFormat
from darml.domain.exceptions import TargetIncompatible
from darml.domain.models import BuildRequest, ModelInfo
from darml.infrastructure.converters.sklearn_to_c import SklearnToCConverter
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .platformio_builder import PlatformIOBuilder, PlatformIOBuilderConfig


class AVRBuilder(PlatformIOBuilder):
    """AVR (ATmega) builder — sklearn-only via emlearn.

    Overrides `_inject_model` to call emlearn and emit a model.h C header instead
    of the byte-array approach used for TFLite Micro targets.
    """

    def __init__(
        self,
        target_id: str,
        pio_environment: str,
        templates_root: Path,
        pio: PlatformIORunner,
    ):
        super().__init__(
            config=PlatformIOBuilderConfig(
                target_id=target_id,
                template_subdir="avr",
                pio_environment=pio_environment,
                tensor_arena_min_bytes=0,
                # AVR uses emlearn (no arena needed). Keep a tiny cap so the
                # placeholder substitution always produces valid C.
                tensor_arena_max_bytes=512,
            ),
            templates_root=templates_root,
            pio=pio,
        )
        self._converter = SklearnToCConverter()

    def _inject_model(
        self,
        project_dir: Path,
        model_path: Path,
        model_info: ModelInfo,
        request: BuildRequest,
    ) -> None:
        if model_info.format != ModelFormat.SKLEARN:
            raise TargetIncompatible(
                "AVR targets support scikit-learn models only. "
                "Use STM32 or ESP32 for neural networks."
            )
        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        header = src_dir / "model.h"
        self._converter.convert(model_path, header)
        self._render_templates(project_dir, model_info, request)


class AVRMega328Builder(AVRBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__("avr-mega328", "avr-mega328", templates_root, pio)


class AVRMega2560Builder(AVRBuilder):
    def __init__(self, templates_root: Path, pio: PlatformIORunner):
        super().__init__("avr-mega2560", "avr-mega2560", templates_root, pio)
