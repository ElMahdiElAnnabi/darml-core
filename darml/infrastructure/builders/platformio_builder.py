import shutil
from dataclasses import dataclass
from pathlib import Path

from darml.domain.models import BuildRequest, ModelInfo
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .base_builder import BaseBuilder


@dataclass
class PlatformIOBuilderConfig:
    target_id: str
    template_subdir: str       # e.g. "esp32", "stm32", "avr"
    pio_environment: str       # environment name inside platformio.ini
    tensor_arena_min_bytes: int = 8192
    # Hard cap on the tensor arena. The arena is a static `uint8_t[]` member
    # of the EloquentTinyML Sequential template, so it lives in DRAM (.bss).
    # Going past the chip's DRAM segment causes a linker error like
    # "region `dram0_0_seg' overflowed by N bytes". Per-target caps reflect
    # what fits after framework + runtime + interpreter + input buffers.
    tensor_arena_max_bytes: int = 256 * 1024


class PlatformIOBuilder(BaseBuilder):
    """Shared implementation for any PlatformIO-based target (ESP32/STM32/AVR).

    Per-target differences are isolated to a PlatformIOBuilderConfig + the
    template directory layout. Subclasses exist only to give each target a
    distinct class identity for the factory; override hooks if a target needs
    special injection logic.
    """

    def __init__(
        self,
        config: PlatformIOBuilderConfig,
        templates_root: Path,
        pio: PlatformIORunner,
    ):
        self._config = config
        self._template_dir = templates_root / config.template_subdir
        self._pio = pio

    @property
    def target_id(self) -> str:
        return self._config.target_id

    def _prepare_project(self, workspace: Path) -> Path:
        project = workspace / "project"
        if project.exists():
            shutil.rmtree(project)
        shutil.copytree(self._template_dir, project)
        return project

    _RENDERABLE_NAMES: tuple[str, ...] = (
        "main.cpp",
        "main.c",
        "darml.cpp",
        "darml.h",
        "platformio.ini",
    )

    def _inject_model(
        self,
        project_dir: Path,
        model_path: Path,
        model_info: ModelInfo,
        request: BuildRequest,
    ) -> None:
        self._inject_model_header(project_dir, model_path)
        self._render_templates(project_dir, model_info, request)

    def _inject_model_header(self, project_dir: Path, model_path: Path) -> None:
        model_bytes = model_path.read_bytes()
        header = self.to_c_byte_array("model_data", model_bytes)
        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "model_data.h").write_text(header)

    def _render_templates(
        self,
        project_dir: Path,
        model_info: ModelInfo,
        request: BuildRequest,
    ) -> None:
        values, warnings = self._template_values(model_info, request)
        for path in project_dir.rglob("*"):
            if path.is_file() and path.name in self._RENDERABLE_NAMES:
                path.write_text(self.render_template(path.read_text(), values))
        # Surface arena-cap warnings on the build context so the API/CLI
        # can show them. We attach via an instance attr that BaseBuilder
        # picks up after _inject_model returns.
        self._last_render_warnings = warnings

    def _template_values(
        self,
        model_info: ModelInfo,
        request: BuildRequest,
    ) -> tuple[dict[str, str], list[str]]:
        ideal = max(
            self._config.tensor_arena_min_bytes,
            model_info.input_elements * 8,
        )
        capped = min(ideal, self._config.tensor_arena_max_bytes)
        warnings: list[str] = []
        if capped < ideal:
            warnings.append(
                f"Tensor arena capped at {capped // 1024} KB (ideal "
                f"{ideal // 1024} KB) to fit {self._config.target_id} DRAM. "
                "If AllocateTensors() fails at runtime, switch to a target "
                "with PSRAM (e.g. esp32-s3-devkitc-1-n16r8) or a larger MCU "
                "(stm32h7 has 1 MB SRAM)."
            )
        return {
            "INPUT_SIZE": str(model_info.input_elements),
            "OUTPUT_SIZE": str(model_info.output_elements),
            "TENSOR_ARENA_SIZE": str(capped),
            "INFERENCE_INTERVAL_MS": str(request.inference_interval_ms),
            "REPORT_MODE": request.report_mode.value,
            "REPORT_URL": request.report_url or "",
            "WIFI_SSID": request.wifi_ssid or "",
            "WIFI_PASS": request.wifi_password or "",
        }, warnings

    async def _compile(self, project_dir: Path) -> tuple[dict[str, Path], str]:
        output = await self._pio.run(project_dir, environment=self._config.pio_environment)
        return {"firmware": output.firmware_path}, output.log
