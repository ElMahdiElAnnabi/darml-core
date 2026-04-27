from dataclasses import dataclass

from darml.domain.enums import Runtime
from darml.domain.exceptions import TargetUnknown
from darml.domain.models import ModelInfo, SizeCheckResult, Target
from darml.domain.targets import get_target


@dataclass
class CheckSize:
    """Estimate a model's RAM/Flash footprint vs a target's hardware constraints."""

    def execute(self, model_info: ModelInfo, target_id: str) -> SizeCheckResult:
        target = get_target(target_id)
        if target is None:
            raise TargetUnknown(f"Unknown target: {target_id}")

        flash_kb = model_info.file_size_bytes / 1024.0
        ram_kb = self._estimate_arena_kb(model_info, target)

        flash_ok = target.flash_kb == 0 or flash_kb <= target.flash_kb
        ram_ok = ram_kb <= target.available_ram_kb
        fits = flash_ok and ram_ok

        warning = None
        if not fits:
            warning = self._format_warning(flash_kb, ram_kb, target)
        elif target.is_microcontroller and ram_kb > target.available_ram_kb * 0.8:
            warning = (
                f"Tight fit: uses ~{ram_kb:.0f}KB of {target.available_ram_kb}KB RAM. "
                "Consider INT8 quantization."
            )

        return SizeCheckResult(
            fits=fits,
            model_ram_kb=ram_kb,
            model_flash_kb=flash_kb,
            target_ram_kb=float(target.available_ram_kb),
            target_flash_kb=float(target.flash_kb),
            warning=warning,
        )

    @staticmethod
    def _estimate_arena_kb(model_info: ModelInfo, target: Target) -> float:
        # emlearn-compiled sklearn models are tiny (< 5KB), arena is negligible.
        if target.runtime == Runtime.EMLEARN:
            return 2.0
        dtype_bytes = 1 if model_info.is_quantized else 4
        largest_tensor = max(model_info.input_elements, model_info.output_elements)
        # Arena ~= 2x largest tensor (rough TFLite heuristic).
        arena_bytes = largest_tensor * dtype_bytes * 2
        return arena_bytes / 1024.0

    @staticmethod
    def _format_warning(flash_kb: float, ram_kb: float, target: Target) -> str:
        parts = []
        if target.flash_kb and flash_kb > target.flash_kb:
            parts.append(f"needs {flash_kb:.0f}KB flash, target has {target.flash_kb}KB")
        if ram_kb > target.available_ram_kb:
            parts.append(
                f"needs ~{ram_kb:.0f}KB RAM, target has {target.available_ram_kb}KB"
            )
        return "Model does not fit on target: " + "; ".join(parts) + "."
