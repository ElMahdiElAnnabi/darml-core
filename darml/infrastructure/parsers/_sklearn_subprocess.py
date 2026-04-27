"""Subprocess worker for joblib.load.

Run as: python -m darml.infrastructure.parsers._sklearn_subprocess <pickle_path>

Loads a pickle in an isolated process with CPU + memory + file-size
caps, extracts metadata, prints JSON to stdout, exits.

Why a separate process: joblib.load() is unpickle, which is arbitrary-
Python execution. Even our magic-byte sniff (0x80) only validates
format, not content. A malicious .pkl can spawn shells, exfiltrate
files, or crash the interpreter at deserialization time. Running in a
subprocess means:
  - The main API server keeps running if the worker crashes
  - rlimit-based caps stop runaway memory and CPU
  - On Linux, the worker is in its own pid namespace (when run via
    systemd/Docker) — we don't add seccomp here but the API host should
    sandbox this further (Docker --read-only --network=none).

Output format (stdout, exit 0):
    {"format": "sklearn", "n_features": 4, "n_classes": 3,
     "estimator_class": "RandomForestClassifier"}

Error format (stderr, non-zero exit):
    Plain-text error message. Caller treats any non-zero exit as a
    parse failure.

If you're reading this in production logs and want to debug, the
parent process passes the path as argv[1]; reproduce locally with:
    python -m darml.infrastructure.parsers._sklearn_subprocess /path/to/file.pkl
"""

from __future__ import annotations

import json
import resource
import sys


def _set_limits() -> None:
    """Best-effort resource caps. POSIX only; silently skipped on Windows."""
    # 256 MB address space — bigger than any sklearn model we plausibly
    # support, small enough to bound a malicious unpickle.
    MEM = 256 * 1024 * 1024
    # 30 seconds of CPU time. Real models load in <1s.
    CPU = 30
    # 200 MB max single-file output (sane upper bound).
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
            # Already-tighter limit, or platform doesn't support it.
            pass


def _deny_network() -> None:
    """Defense in depth — deny outbound connections from the unpickle worker.

    A malicious pickle can still call ctypes / re-import the C `socket`
    module to bypass this; that's why the docstring at the top of this
    file calls it 'best-effort'. The real isolation is at the OS layer:
    `unshare -n` / `firejail --net=none` / Docker `--network=none`.

    What this stops: every reasonable Python exfiltration pattern
    (urllib, requests, http.client, smtplib, raw socket.connect). It
    raises the bar and produces clear error messages in `flyctl logs`
    if a malicious pickle tries to phone home.
    """
    import socket

    def _refuse(*_args, **_kwargs):
        raise OSError(
            "Network access is disabled in the Darml unpickle worker."
        )

    # Wrap socket.socket so any newly-created socket refuses connect.
    _orig = socket.socket

    class _DenySocket(_orig):  # type: ignore[misc, valid-type]
        def connect(self, *args, **kwargs):
            _refuse()

        def connect_ex(self, *args, **kwargs):
            _refuse()

    socket.socket = _DenySocket  # type: ignore[assignment, misc]
    socket.create_connection = _refuse  # type: ignore[assignment]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: _sklearn_subprocess <pickle_path>", file=sys.stderr)
        return 2

    _set_limits()
    _deny_network()

    path = sys.argv[1]
    try:
        import joblib  # type: ignore
    except ImportError:
        print(
            "joblib is not installed in this environment. "
            "Install with: pip install darml[sklearn]",
            file=sys.stderr,
        )
        return 3

    try:
        model = joblib.load(path)
    except MemoryError:
        print("Pickle deserialization exceeded the memory cap (256 MB).", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"Failed to load pickle: {e}", file=sys.stderr)
        return 5

    if not hasattr(model, "predict") and not hasattr(model, "predict_proba"):
        print(
            f"Loaded object is a {type(model).__name__}, not a scikit-learn "
            f"estimator (missing .predict / .predict_proba).",
            file=sys.stderr,
        )
        return 6

    n_features = int(getattr(model, "n_features_in_", 0) or 0)
    classes = getattr(model, "classes_", None)
    n_classes = int(len(classes)) if classes is not None else 1

    print(json.dumps({
        "format": "sklearn",
        "n_features": n_features,
        "n_classes": n_classes,
        "estimator_class": type(model).__name__,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
