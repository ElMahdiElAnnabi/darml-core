"""PlatformIO-missing path: clean ToolchainMissing instead of generic crash."""

from __future__ import annotations

import asyncio

import pytest

from darml.domain.exceptions import ToolchainMissing
from darml.infrastructure.platformio.platformio_runner import PlatformIORunner


def test_runner_raises_toolchain_missing_when_pio_absent(monkeypatch, tmp_path):
    runner = PlatformIORunner.__new__(PlatformIORunner)  # bypass __init__ side effects
    runner._configured_path = "definitely-not-on-path-darml"
    runner._timeout = 5
    runner._cmd_prefix = None  # simulate "couldn't find platformio"

    with pytest.raises(ToolchainMissing) as exc:
        asyncio.run(runner.run(tmp_path))

    msg = str(exc.value)
    assert "PlatformIO" in msg
    assert "pip install platformio" in msg
    assert "output=library" in msg


def test_runner_resolves_python_m_platformio_in_venv():
    """When platformio is importable, runner should pick `python -m platformio`."""
    pytest.importorskip("platformio")
    runner = PlatformIORunner()
    assert runner._cmd_prefix is not None
    # Either a `pio` shim on PATH or python -m platformio — both are valid.
    joined = " ".join(runner._cmd_prefix)
    assert "platformio" in joined or runner._cmd_prefix[0].endswith("pio")
