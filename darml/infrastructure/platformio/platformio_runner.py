import asyncio
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from darml.domain.exceptions import ToolchainMissing


@dataclass
class PIOBuildOutput:
    firmware_path: Path
    log: str


class PlatformIORunner:
    """Subprocess wrapper around the PlatformIO CLI.

    Resolves how to invoke PlatformIO once at construction so individual
    builders never have to deal with venv/PATH variability:
      - explicit pio_path                        → use it
      - "pio" on PATH                            → use it
      - `python -m platformio` works in current  → use sys.executable -m
        interpreter
      - none of the above                        → raise on first use with
        a clear error
    """

    def __init__(self, pio_path: str = "pio", timeout_s: int = 600):
        self._configured_path = pio_path
        self._timeout = timeout_s
        self._cmd_prefix = self._resolve_command(pio_path)

    @staticmethod
    def _resolve_command(configured: str) -> list[str] | None:
        if configured and configured != "pio":
            return [configured]
        if shutil.which("pio"):
            return ["pio"]
        if shutil.which("platformio"):
            return ["platformio"]
        try:
            __import__("platformio")
            return [sys.executable, "-m", "platformio"]
        except ImportError:
            return None

    async def run(
        self,
        project_dir: Path,
        environment: str | None = None,
    ) -> PIOBuildOutput:
        if self._cmd_prefix is None:
            raise ToolchainMissing(
                f"PlatformIO is required to compile firmware for this target "
                f"but was not found (looked for {self._configured_path!r} on "
                "PATH, the `pio` and `platformio` executables, and "
                "`python -m platformio`).\n"
                "Install with: pip install platformio\n"
                "Or use output=library to skip the cross-compile and get "
                "the rendered C/C++ sources as a .zip."
            )

        # Two-pass: install libs, then patch known-broken files, then build.
        # The patches target upstream sources that don't compile cleanly on
        # certain Arduino cores (e.g. tflm_cortexm references RingBufferN<>
        # which STM32duino doesn't expose).
        install_log = await self._exec(
            [*self._cmd_prefix, "pkg", "install", "-d", str(project_dir)]
            + (["-e", environment] if environment else [])
        )
        self._apply_libdep_patches(project_dir, environment)

        log = install_log + await self._exec(
            [*self._cmd_prefix, "run", "-d", str(project_dir)]
            + (["-e", environment] if environment else [])
        )

        firmware = self._find_firmware(project_dir, environment)
        return PIOBuildOutput(firmware_path=firmware, log=log)

    async def _exec(self, cmd: list[str]) -> str:
        # start_new_session=True puts the child in its own process group so
        # we can kill the whole tree (pio + every gcc it spawns) on timeout
        # or cancellation. Without this, asyncio.wait_for cancels the
        # await but leaves dozens of orphan compiler processes running and
        # produces "Event loop is closed" tracebacks at gc time.
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        except FileNotFoundError as e:
            raise ToolchainMissing(
                f"PlatformIO CLI not executable: {cmd[0]}. "
                "Install with: pip install platformio"
            ) from e

        try:
            stdout_bytes, _ = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except (asyncio.TimeoutError, asyncio.CancelledError) as e:
            await self._terminate(proc)
            if isinstance(e, asyncio.CancelledError):
                raise
            raise RuntimeError(
                f"PlatformIO command timed out after {self._timeout}s "
                "and the subprocess group was killed"
            ) from e

        log = stdout_bytes.decode(errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"PlatformIO command failed (exit {proc.returncode}):\n{log}")
        return log

    @staticmethod
    async def _terminate(proc: asyncio.subprocess.Process) -> None:
        """Best-effort: SIGTERM the whole process group, then SIGKILL after 5s."""
        import os
        import signal

        if proc.returncode is not None:
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return
        except asyncio.TimeoutError:
            pass
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass

    @staticmethod
    def _apply_libdep_patches(project_dir: Path, environment: str | None) -> None:
        """Stub out upstream sources known to break under our Arduino cores.

        - tflm_cortexm/src/tensorflow/lite/micro/system_setup.cpp: pulls in
          Arduino's RingBufferN<>, which STM32duino does not expose. The file
          is debug-only test_over_serial scaffolding; replacing it with a
          one-line stub leaves real inference untouched.
        """
        libdeps = project_dir / ".pio" / "libdeps"
        if environment:
            libdeps = libdeps / environment
        if not libdeps.exists():
            return
        targets = (
            libdeps / "tflm_cortexm" / "src" / "tensorflow" / "lite" / "micro" / "system_setup.cpp",
        )
        for path in targets:
            if path.exists() and path.stat().st_size > 200:
                path.write_text("// Darml: replaced upstream test_over_serial scaffolding\n")

    @staticmethod
    def _find_firmware(project_dir: Path, environment: str | None) -> Path:
        build_dir = project_dir / ".pio" / "build"
        if environment:
            build_dir = build_dir / environment
        for suffix in ("firmware.bin", "firmware.hex", "firmware.elf"):
            hits = list(build_dir.rglob(suffix))
            if hits:
                return hits[0]
        raise FileNotFoundError(f"No firmware artifact found under {build_dir}")
