"""sklearn → C converter via emlearn — sandboxed unpickle.

Same threat model as the parser: joblib.load is arbitrary code execution.
Even though the parser already saw this file, re-loading in the main
process reopens the attack surface. We dispatch the load+convert into a
subprocess with rlimit caps; only the resulting .h file path comes back
to the parent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from darml.application.ports.converter import ConverterPort
from darml.domain.enums import ModelFormat
from darml.domain.exceptions import ConversionFailed


_WORKER_TIMEOUT_S = 120  # emlearn.convert can take a beat on large forests


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
        header = output_path.with_suffix(".h")
        try:
            result = subprocess.run(
                [sys.executable, "-m",
                 "darml.infrastructure.converters._sklearn_to_c_subprocess",
                 str(input_path), str(header)],
                capture_output=True,
                timeout=_WORKER_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ConversionFailed(
                f"sklearn→C worker timed out after {_WORKER_TIMEOUT_S}s. "
                "Either the pickle is suspicious or the model is too large "
                "for emlearn to convert in bounded time."
            )

        if result.returncode != 0:
            err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ConversionFailed(
                f"emlearn conversion failed (exit {result.returncode}): "
                f"{err or '(no stderr)'}"
            )

        # Worker prints the resulting header path on success.
        produced = (result.stdout or b"").decode("utf-8", errors="replace").strip()
        if not produced or not Path(produced).exists():
            raise ConversionFailed(
                "emlearn worker reported success but produced no .h file."
            )
        return Path(produced)
