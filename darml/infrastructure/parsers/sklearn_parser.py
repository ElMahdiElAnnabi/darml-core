"""Sklearn model parser — sandboxed unpickle.

joblib.load is arbitrary-code execution on user input. We run it in a
subprocess (see _sklearn_subprocess.py) with rlimit-based memory + CPU
caps so a malicious pickle can't trash the API server.

This isn't a complete sandbox — full isolation needs seccomp/nsjail or
running the API host with `docker run --read-only --network=none`. The
subprocess+rlimit pair is the cheapest improvement that lets the
process crash without taking the parent down.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from darml.application.ports.model_parser import ModelParserPort
from darml.domain.enums import DType, ModelFormat
from darml.domain.exceptions import ModelParseError
from darml.domain.models import ModelInfo


# Hard wall-clock cap on the subprocess. The worker itself sets a 30s
# CPU rlimit; this is the higher-level escape hatch in case CPU is
# yielded but the worker hangs (e.g. on a syscall).
_WORKER_TIMEOUT_S = 60


class SklearnParser(ModelParserPort):
    @property
    def format(self) -> ModelFormat:
        return ModelFormat.SKLEARN

    def parse(self, path: Path) -> ModelInfo:
        # Cheap pre-check before spawning a subprocess.
        if path.stat().st_size < 2:
            raise ModelParseError("File is too small to be a valid pickle.")
        with path.open("rb") as f:
            if f.read(1) != b"\x80":
                raise ModelParseError(
                    "File does not look like a pickle (missing 0x80 protocol "
                    "marker). Did you upload the right file?"
                )

        # Spawn the sandboxed worker. We use the same Python interpreter so
        # joblib resolves to the version installed in the API venv.
        try:
            result = subprocess.run(
                [sys.executable, "-m",
                 "darml.infrastructure.parsers._sklearn_subprocess",
                 str(path)],
                capture_output=True,
                timeout=_WORKER_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise ModelParseError(
                f"sklearn parse worker timed out after {_WORKER_TIMEOUT_S}s "
                "(suspicious pickle or extremely large model)."
            )

        if result.returncode != 0:
            err = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ModelParseError(
                f"sklearn parse failed (exit {result.returncode}): "
                f"{err or '(no stderr)'}"
            )

        try:
            payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            raise ModelParseError(
                f"sklearn parse worker produced invalid JSON: {e}"
            )

        n_features = int(payload.get("n_features", 0))
        n_classes = int(payload.get("n_classes", 1))
        estimator_class = payload.get("estimator_class", "Estimator")

        return ModelInfo(
            format=ModelFormat.SKLEARN,
            file_size_bytes=path.stat().st_size,
            input_shape=(1, n_features),
            output_shape=(1, n_classes),
            input_dtype=DType.FLOAT32,
            output_dtype=DType.FLOAT32,
            num_ops=1,
            is_quantized=False,
            ops_list=(estimator_class,),
        )
