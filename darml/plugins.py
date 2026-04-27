"""Plugin hook registry — the only seam between Core and Pro.

Core never imports darml_pro. Pro imports darml.plugins and registers its
adapters into the slots below. Core checks each slot; if empty it either
falls back to a free-tier behavior or raises ProFeatureRequired with a
friendly upgrade message.

This is a deliberate single-module god-object so:
  - the contract is small and easy to audit (one file)
  - import-time registration in Pro is a one-shot side effect
  - tests can reset state via `reset_for_tests()` without monkeypatching

Slots
-----
  quantizers          dict[ModelFormat, QuantizerPort]
  converters          dict[(ModelFormat, ModelFormat), ConverterPort]
  build_cache         BuildCachePort | None
  report_modes        dict[str, ReportModeRenderer]   (free version registers "serial")
  server_factory      Callable[[Container], FastAPI] | None
  license_validator   Callable[[], LicenseStatus] | None

Pro registers into these on import; see darml_pro/__init__.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from darml.application.ports.build_cache import BuildCachePort
    from darml.application.ports.converter import ConverterPort
    from darml.application.ports.quantizer import QuantizerPort
    from darml.domain.enums import ModelFormat


@dataclass
class LicenseStatus:
    """Reported by darml_pro's license validator. Used by the CLI version
    command and by gating logic that distinguishes trial / paid / expired."""
    valid: bool
    plan: str = "free"           # "free" | "trial" | "pro" | "expired"
    expires_at: str | None = None
    customer: str | None = None
    message: str = ""


class _Hooks:
    """Module-level singleton. Importing darml.plugins exposes `hooks`."""

    def __init__(self) -> None:
        self.quantizers: dict["ModelFormat", "QuantizerPort"] = {}
        self.converters: dict[
            tuple["ModelFormat", "ModelFormat"], "ConverterPort"
        ] = {}
        self.build_cache: "BuildCachePort | None" = None
        self.report_modes: dict[str, Any] = {}
        self.server_factory: Callable[..., Any] | None = None
        self.license_validator: Callable[[], LicenseStatus] | None = None

    def reset_for_tests(self) -> None:
        self.__init__()  # type: ignore[misc]

    # Convenience: tells callers whether Pro features have registered.
    def has_pro(self) -> bool:
        return self.license_validator is not None or bool(self.quantizers) \
            or self.build_cache is not None or self.server_factory is not None


hooks = _Hooks()


def is_pro_active() -> bool:
    """True iff a license_validator is registered AND it reports valid."""
    if hooks.license_validator is None:
        return False
    try:
        return hooks.license_validator().valid
    except Exception:
        return False


def license_status() -> LicenseStatus:
    if hooks.license_validator is None:
        return LicenseStatus(valid=False, plan="free", message="Darml Core (free).")
    try:
        return hooks.license_validator()
    except Exception as e:
        return LicenseStatus(valid=False, plan="free", message=f"validator error: {e}")
