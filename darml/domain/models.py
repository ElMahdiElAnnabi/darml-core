from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .enums import BuildStatus, DType, ModelFormat, OutputKind, ReportMode, Runtime


@dataclass(frozen=True)
class LayerInfo:
    """Per-layer profile data, populated by parsers when they can extract
    it. The build report renders one table row per layer when this is
    populated. When empty, the report falls back to a model-level
    summary (built from ops_list)."""
    name: str                           # parser-provided or "op_<idx>"
    op_type: str                        # e.g. CONV_2D, FULLY_CONNECTED, MatMul
    input_shape: tuple[int, ...] = ()
    output_shape: tuple[int, ...] = ()
    weight_bytes: int = 0               # parameter bytes for this layer
    activation_bytes: int = 0           # peak intermediate tensor bytes
    quantization: str = ""              # "fp32", "int8", "int8_per_channel", …
    macs: int = 0                       # multiply-accumulate ops; 0 = unknown


@dataclass(frozen=True)
class ModelInfo:
    format: ModelFormat
    file_size_bytes: int
    input_shape: tuple[int, ...]
    output_shape: tuple[int, ...]
    input_dtype: DType
    output_dtype: DType
    num_ops: int
    is_quantized: bool
    ops_list: tuple[str, ...]
    # Optional richer profile. Default empty for backward compatibility
    # — parsers that don't populate it produce summary-only reports.
    layers: tuple[LayerInfo, ...] = ()

    @property
    def input_elements(self) -> int:
        n = 1
        for d in self.input_shape:
            if d > 0:
                n *= d
        return n

    @property
    def output_elements(self) -> int:
        n = 1
        for d in self.output_shape:
            if d > 0:
                n *= d
        return n


@dataclass(frozen=True)
class Target:
    id: str
    ram_kb: int
    flash_kb: int
    runtime: Runtime
    psram_kb: int = 0
    platformio_board: str | None = None
    platformio_platform: str | None = None

    @property
    def is_microcontroller(self) -> bool:
        return self.runtime in {Runtime.TFLITE_MICRO, Runtime.EMLEARN}

    @property
    def available_ram_kb(self) -> int:
        return self.ram_kb + self.psram_kb


@dataclass(frozen=True)
class SizeCheckResult:
    fits: bool
    model_ram_kb: float
    model_flash_kb: float
    target_ram_kb: float
    target_flash_kb: float
    warning: str | None = None


@dataclass(frozen=True)
class QuantizeResult:
    input_path: Path
    output_path: Path
    original_size_bytes: int
    quantized_size_bytes: int

    @property
    def compression_ratio(self) -> float:
        if self.quantized_size_bytes == 0:
            return 0.0
        return self.original_size_bytes / self.quantized_size_bytes


@dataclass(frozen=True)
class BuildRequest:
    model_path: Path
    target_id: str
    quantize: bool = False
    # When `quantize=True`, point this at a .npy or .npz of real
    # representative input samples to improve INT8 PTQ accuracy. If left
    # None, Darml falls back to synthetic N(0, 1) random calibration —
    # which is fast and convenient but typically degrades model accuracy
    # by 1–15% depending on architecture. See ConvertStep for the
    # accuracy notice surfaced on every quantized build.
    calibration_data_path: Path | None = None
    output_kind: OutputKind = OutputKind.FIRMWARE
    report_mode: ReportMode = ReportMode.SERIAL
    report_url: str | None = None
    # 1 ms .. 1 hour. The lower bound stops a misconfigured device from
    # spinning a 0-ms loop that hangs the watchdog; the upper bound is
    # purely sanity (an hour-long sleep on an MCU likely indicates a unit
    # error, e.g. someone passed seconds expecting ms).
    inference_interval_ms: int = 1000

    def __post_init__(self):
        if not (1 <= self.inference_interval_ms <= 3_600_000):
            raise ValueError(
                f"inference_interval_ms must be in [1, 3_600_000] ms; "
                f"got {self.inference_interval_ms}."
            )
    wifi_ssid: str | None = None
    wifi_password: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BuildResult:
    build_id: str
    target_id: str
    status: BuildStatus
    model_info: ModelInfo | None = None
    size_check: SizeCheckResult | None = None
    quantize_result: QuantizeResult | None = None
    firmware_path: Path | None = None
    library_path: Path | None = None
    artifact_zip_path: Path | None = None
    build_log: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=_now)
    completed_at: datetime | None = None

    @property
    def build_time_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()

    @classmethod
    def new(cls, target_id: str) -> "BuildResult":
        return cls(
            build_id=str(uuid4()),
            target_id=target_id,
            status=BuildStatus.PENDING,
        )
