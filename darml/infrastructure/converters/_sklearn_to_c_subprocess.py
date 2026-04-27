"""Subprocess worker for emlearn sklearn→C conversion.

Run as: python -m darml.infrastructure.converters._sklearn_to_c_subprocess
        <pickle_path> <output_h_path>

Loads the pickle, runs emlearn.convert(), writes the .h file, exits.

Same threat model as _sklearn_subprocess.py: joblib.load is arbitrary
code execution. Even though the parser already sandboxed the parse,
calling joblib.load again here re-exposes the main process. Subprocess
isolation + rlimits stops a malicious pickle from poisoning the API
worker.
"""

from __future__ import annotations

import resource
import sys
from pathlib import Path


def _set_limits() -> None:
    MEM = 512 * 1024 * 1024  # 512 MB — emlearn convert can balloon
    CPU = 60
    FSIZE = 200 * 1024 * 1024
    for which, val in (
        (resource.RLIMIT_AS, MEM),
        (resource.RLIMIT_CPU, CPU),
        (resource.RLIMIT_FSIZE, FSIZE),
    ):
        try:
            soft, hard = resource.getrlimit(which)
            new_soft = min(val, hard) if hard != resource.RLIM_INFINITY else val
            resource.setrlimit(which, (new_soft, hard))
        except (ValueError, OSError):
            pass


def _deny_network() -> None:
    """Defense in depth — same as the parser worker. See parsers/_sklearn_subprocess.py."""
    import socket

    def _refuse(*_args, **_kwargs):
        raise OSError(
            "Network access is disabled in the Darml unpickle worker."
        )

    _orig = socket.socket

    class _DenySocket(_orig):  # type: ignore[misc, valid-type]
        def connect(self, *args, **kwargs):
            _refuse()

        def connect_ex(self, *args, **kwargs):
            _refuse()

    socket.socket = _DenySocket  # type: ignore[assignment, misc]
    socket.create_connection = _refuse  # type: ignore[assignment]


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: _sklearn_to_c_subprocess <pickle_path> <output_h_path>",
            file=sys.stderr,
        )
        return 2

    _set_limits()
    _deny_network()

    in_path = sys.argv[1]
    out_path = Path(sys.argv[2])

    try:
        import emlearn  # type: ignore
        import joblib  # type: ignore
    except ImportError as e:
        print(f"emlearn/joblib not installed in worker env: {e}", file=sys.stderr)
        return 3

    try:
        model = joblib.load(in_path)
    except MemoryError:
        print("Pickle deserialization exceeded memory cap.", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"joblib.load failed: {e}", file=sys.stderr)
        return 5

    try:
        c_model = emlearn.convert(model)
        c_model.save(file=str(out_path), name="darml_model")
    except Exception as e:
        print(f"emlearn.convert failed: {e}", file=sys.stderr)
        return 6

    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
