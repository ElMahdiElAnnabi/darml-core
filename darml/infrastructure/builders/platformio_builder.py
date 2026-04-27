import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from darml.domain.models import BuildRequest, ModelInfo
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner

from .base_builder import BaseBuilder


# ── Template-injection guards ──────────────────────────────────────────────
#
# These three values land inside C string literals in the firmware
# templates (see infrastructure/templates/{esp32,stm32,avr}/lib/darml/).
# A naive `text.replace("{{KEY}}", val)` substitution treats the value
# as opaque text — but if a value contains `}}; system("…"); /*` the
# attacker is one bad template tweak away from arbitrary C compiled
# into the firmware.
#
# "Printable ASCII" alone isn't enough — `"` closes the string literal
# and `\` starts an escape sequence. Both can break out without any
# control byte. So the rule is: printable ASCII MINUS the four chars
# that can subvert a C string: " \ NUL CR LF.
#
# Real Wi-Fi APs don't accept those bytes in SSIDs/passwords either,
# so this matches what the radio stack would do anyway.

# Printable ASCII (0x20-0x7e) excluding " (0x22) and \ (0x5c). NUL/CR/LF
# are already outside 0x20-0x7e so the range exclusion handles them.
_SSID_RE = re.compile(r'^[\x20-\x21\x23-\x5b\x5d-\x7e]{1,32}$')
_WPA_RE  = re.compile(r'^[\x20-\x21\x23-\x5b\x5d-\x7e]{8,63}$')


def _safe_template_ssid(ssid: str | None) -> str:
    if not ssid:
        return ""
    if not _SSID_RE.fullmatch(ssid):
        raise ValueError(
            "Invalid wifi_ssid: 1-32 printable ASCII characters, excluding "
            "double-quote and backslash."
        )
    return ssid


def _safe_template_wpa_pass(pwd: str | None) -> str:
    if not pwd:
        return ""
    if not _WPA_RE.fullmatch(pwd):
        raise ValueError(
            "Invalid wifi_password: 8-63 printable ASCII characters, "
            "excluding double-quote and backslash."
        )
    return pwd


def _safe_template_url(url: str | None) -> str:
    """Re-serialize through urlparse, then reject any byte that could
    break out of a C string literal. Defense in depth: SSRF + scheme
    checks already happened at the API edge in routes/build.py; this is
    the last gate before the URL becomes literal C source."""
    if not url:
        return ""
    # Check the RAW input first — newer Python urlparse silently strips
    # some control chars (CVE-2023-24329 mitigation), so by the time we
    # round-trip through urlparse+urlunparse the dangerous bytes might
    # be gone from the rebuilt string. If we only checked the rebuilt
    # form, e.g. a CR-injected URL would pass.
    forbidden_chars = {'"', "\\", "\n", "\r", "\0"}
    if any(c in forbidden_chars or ord(c) < 0x20 for c in url):
        raise ValueError(
            "Invalid report_url: contains a control or string-breakout "
            'character (one of: NUL, CR, LF, " or \\).'
        )
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        # http allowed for local dev; full SSRF check happens at the API
        # boundary (see darml_pro/api/routes/build.py:_validate_report_url).
        raise ValueError(f"Invalid report_url scheme: {parsed.scheme!r}")
    return urlunparse(parsed)


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
            "REPORT_URL": _safe_template_url(request.report_url),
            "WIFI_SSID": _safe_template_ssid(request.wifi_ssid),
            "WIFI_PASS": _safe_template_wpa_pass(request.wifi_password),
        }, warnings

    async def _compile(self, project_dir: Path) -> tuple[dict[str, Path], str]:
        output = await self._pio.run(project_dir, environment=self._config.pio_environment)
        return {"firmware": output.firmware_path}, output.log
