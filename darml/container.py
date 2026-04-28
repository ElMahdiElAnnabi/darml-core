"""Composition root for Darml Core.

Core wires up the always-free pipeline: parsers, builders, the build
firmware orchestrator. Pro features (quantizer, ONNX→TFLite converter,
build cache, FastAPI server, auth) are pulled from the plugin registry
in `darml.plugins.hooks` — populated when `darml_pro` is imported.

If `darml_pro` is not installed:
  - Quantize/Convert/Cache steps no-op or raise a friendly upgrade error
  - `darml serve` prints a clear "Pro required" message
  - Everything else (info, check, build, flash) works fully
"""

from functools import lru_cache
from pathlib import Path

from darml.application.factories.builder_factory import BuilderFactory
from darml.application.factories.parser_factory import ParserFactory
from darml.application.factories.quantizer_factory import QuantizerFactory
from darml.application.pipeline.pipeline import BuildPipeline
from darml.application.pipeline.steps.check_step import CheckStep
from darml.application.pipeline.steps.compile_step import CompileStep
from darml.application.pipeline.steps.convert_step import ConvertStep
from darml.application.pipeline.steps.package_step import PackageStep
from darml.application.pipeline.steps.parse_step import ParseStep
from darml.application.pipeline.steps.quantize_step import QuantizeStep
from darml.application.ports.build_repository import BuildRepositoryPort
from darml.application.use_cases.build_firmware import BuildFirmware
from darml.application.use_cases.check_size import CheckSize
from darml.application.use_cases.flash_device import FlashDevice
from darml.application.use_cases.get_build_status import GetBuildStatus
from darml.application.use_cases.list_targets import ListTargets
from darml.application.use_cases.parse_model import ParseModel
from darml.config import Settings, get_settings
from darml.infrastructure.builders.avr_builder import AVRMega2560Builder, AVRMega328Builder
from darml.infrastructure.builders.esp32_builder import ESP32Builder, ESP32S3Builder
from darml.infrastructure.builders.jetson_builder import (
    JetsonNanoBuilder,
    JetsonOrinBuilder,
)
from darml.infrastructure.builders.nrf52840_builder import NRF52840Builder
from darml.infrastructure.builders.rp2040_builder import RP2040Builder
from darml.infrastructure.builders.rpi_builder import RPi4Builder, RPi5Builder
from darml.infrastructure.builders.stm32_builder import (
    STM32F4Builder,
    STM32H7Builder,
    STM32N6Builder,
    STM32U5Builder,
)
from darml.infrastructure.flashers.esptool_flasher import (
    AvrdudeFlasher,
    EsptoolFlasher,
    STM32Flasher,
)
from darml.infrastructure.parsers.onnx_parser import ONNXParser
from darml.infrastructure.parsers.sklearn_parser import SklearnParser
from darml.infrastructure.parsers.tflite_parser import TFLiteParser
from darml.infrastructure.persistence.in_memory_build_repo import InMemoryBuildRepository
from darml.infrastructure.persistence.sqlite_build_repo import SQLiteBuildRepository
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner
from darml.infrastructure.reporting.log_reporter import LogReporter
from darml.infrastructure.storage.filesystem_storage import FileSystemStorage
from darml.plugins import hooks


class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        templates_root = Path(__file__).parent / "infrastructure" / "templates"

        # --- Always-free adapters ------------------------------------------
        self.parser_factory = ParserFactory([
            TFLiteParser(),
            ONNXParser(),
            SklearnParser(),
        ])

        # Quantizers come from the Pro hook registry. With Core only, this
        # factory is empty and the QuantizeStep raises ProFeatureRequired
        # if the user passed --quantize.
        self.quantizer_factory = QuantizerFactory(list(hooks.quantizers.values()))

        self.pio = PlatformIORunner(settings.platformio_path, settings.build_timeout_s)

        self.builder_factory = BuilderFactory([
            ESP32Builder(templates_root, self.pio),
            ESP32S3Builder(templates_root, self.pio),
            STM32F4Builder(templates_root, self.pio),
            STM32H7Builder(templates_root, self.pio),
            STM32N6Builder(templates_root, self.pio),
            STM32U5Builder(templates_root, self.pio),
            NRF52840Builder(templates_root, self.pio),
            RP2040Builder(templates_root, self.pio),
            AVRMega328Builder(templates_root, self.pio),
            AVRMega2560Builder(templates_root, self.pio),
            RPi4Builder(templates_root),
            RPi5Builder(templates_root),
            JetsonNanoBuilder(templates_root),
            JetsonOrinBuilder(templates_root),
        ])

        self.repo: BuildRepositoryPort = (
            SQLiteBuildRepository(Path(settings.sqlite_path))
            if settings.use_sqlite
            else InMemoryBuildRepository()
        )
        self.storage = FileSystemStorage(Path(settings.data_dir))
        self.reporter = LogReporter()

        # --- Use cases -----------------------------------------------------
        self.parse_model = ParseModel(self.parser_factory)
        self.check_size = CheckSize()
        self.list_targets = ListTargets()
        self.get_build_status = GetBuildStatus(self.repo)
        self.flash_device = FlashDevice([
            EsptoolFlasher(),
            AvrdudeFlasher(),
            STM32Flasher(),
        ])

        # --- Pipeline ------------------------------------------------------
        # Converters come from the Pro hook registry. ONNX→TFLite is Pro;
        # without it, ConvertStep no-ops and the builder chain may reject
        # an ONNX input for an MCU target with a clear error.
        self.pipeline = BuildPipeline(
            steps=[
                ParseStep(self.parse_model),
                CheckStep(self.check_size, strict=False),
                QuantizeStep(self.quantizer_factory),
                ConvertStep(converters=list(hooks.converters.values())),
                CompileStep(self.builder_factory),
                PackageStep(),
            ],
            reporter=self.reporter,
        )

        # Build cache is a Pro hook. None in Core → no caching, every build
        # runs fresh.
        self.cache = hooks.build_cache

        self.build_firmware = BuildFirmware(
            pipeline=self.pipeline,
            repo=self.repo,
            storage=self.storage,
            cache=self.cache,
            timeout_s=settings.build_timeout_s,
        )


@lru_cache
def get_container() -> Container:
    return Container(get_settings())
