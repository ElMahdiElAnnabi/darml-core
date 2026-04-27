"""CI guard: assert the Core wheel doesn't ship Pro source or secrets.

Background: darml 0.1.0 and 0.1.1 were uploaded to PyPI with the
entire darml-pro/ tree accidentally included. This test exists so the
mistake can never recur silently — a future build-config regression
will fail the test before any `twine upload` runs.

What it asserts:

  1. No path inside the wheel starts with `darml-pro` or contains
     `darml_pro` as a path segment.
  2. The literal dev-secret string is nowhere in the wheel content.
  3. The wheel has at least one `darml/` file (sanity: we didn't go
     too far and exclude Core).

Marked `slow` because building the wheel takes ~5 seconds; skip with
`-k "not wheel_purity"` if iterating quickly. Runs unconditionally in
CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_SECRET_LITERAL = b"darml-dev-do-not-ship-this-secret"


@pytest.fixture(scope="module")
def core_wheel(tmp_path_factory) -> Path:
    """Build the Core wheel into a fresh tmp dir; return its path."""
    out_dir = tmp_path_factory.mktemp("wheel-purity")
    # `python -m build --wheel` is the canonical PEP-517 path; falls back
    # to setuptools-build_meta if `build` isn't installed.
    try:
        import build  # noqa: F401
        cmd = [sys.executable, "-m", "build", "--wheel",
               "--outdir", str(out_dir), str(REPO_ROOT)]
    except ImportError:
        # Fallback: invoke setuptools directly. Less hermetic but works
        # in environments without the `build` package.
        cmd = [sys.executable, "-m", "pip", "wheel",
               "--no-deps", "--no-build-isolation",
               "--wheel-dir", str(out_dir), str(REPO_ROOT)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        pytest.fail(
            f"Wheel build failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout[-2000:]}\n"
            f"STDERR:\n{result.stderr[-2000:]}"
        )

    wheels = list(out_dir.glob("darml-*.whl"))
    if not wheels:
        pytest.fail(f"No darml-*.whl produced in {out_dir}")
    yield wheels[0]
    shutil.rmtree(out_dir, ignore_errors=True)


def test_no_darml_pro_paths_in_wheel(core_wheel: Path) -> None:
    """No file path inside the wheel mentions Pro."""
    forbidden_path_fragments = ("darml-pro", "darml_pro")
    with zipfile.ZipFile(core_wheel) as zf:
        for name in zf.namelist():
            for frag in forbidden_path_fragments:
                assert frag not in name, (
                    f"PROPRIETARY LEAK: wheel {core_wheel.name} contains a "
                    f"file at path {name!r} which matches forbidden "
                    f"fragment {frag!r}. Check pyproject.toml "
                    f"[tool.setuptools.packages.find] and MANIFEST.in."
                )


def test_no_dev_secret_in_wheel(core_wheel: Path) -> None:
    """The committed dev-signing secret string must not appear anywhere."""
    with zipfile.ZipFile(core_wheel) as zf:
        for name in zf.namelist():
            with zf.open(name) as fh:
                content = fh.read()
                assert DEV_SECRET_LITERAL not in content, (
                    f"DEV SECRET LEAK: wheel {core_wheel.name} ships "
                    f"{DEV_SECRET_LITERAL!r} inside {name}. The committed "
                    f"dev secret must never reach a public wheel."
                )


def test_wheel_actually_contains_core(core_wheel: Path) -> None:
    """Sanity: we didn't over-exclude. The wheel should still have darml/."""
    with zipfile.ZipFile(core_wheel) as zf:
        names = zf.namelist()
    core_files = [n for n in names if n.startswith("darml/")]
    assert core_files, (
        f"Wheel {core_wheel.name} contains no darml/ files at all — "
        f"build config too aggressive. Found: {names[:10]}…"
    )
    # And the entrypoints + key modules are present.
    expected = {
        "darml/__init__.py",
        "darml/__main__.py",
        "darml/config.py",
        "darml/container.py",
        "darml/free_tier.py",
        "darml/plugins.py",
    }
    missing = expected - set(names)
    assert not missing, f"Wheel is missing expected modules: {missing}"
