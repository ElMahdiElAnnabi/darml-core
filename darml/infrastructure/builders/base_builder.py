import zipfile
from abc import abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from darml.application.ports.firmware_builder import FirmwareBuilderPort
from darml.domain.enums import BuildStatus, OutputKind
from darml.domain.exceptions import BuildFailed, ToolchainMissing
from darml.domain.models import BuildRequest, BuildResult, ModelInfo


class BaseBuilder(FirmwareBuilderPort):
    """Template Method: prepare → inject → (compile and/or package library).

    Subclasses override the three abstract hooks. Error handling, timing, the
    OutputKind dispatch, and the default library-packaging path all live here
    so every builder gets them for free.
    """

    async def build(
        self,
        request: BuildRequest,
        model_info: ModelInfo,
        model_path: Path,
        workspace: Path,
    ) -> BuildResult:
        result = BuildResult.new(target_id=self.target_id)
        try:
            project_dir = self._prepare_project(workspace)
            self._inject_model(project_dir, model_path, model_info, request)

            # Bubble up any warnings the inject/render step recorded (e.g.
            # "tensor arena capped at 256 KB").
            for w in getattr(self, "_last_render_warnings", ()) or ():
                if w not in result.warnings:
                    result.warnings.append(w)

            artifacts: dict[str, Path] = {}
            log = ""

            if request.output_kind in (OutputKind.FIRMWARE, OutputKind.BOTH):
                compile_artifacts, log = await self._compile(project_dir)
                artifacts.update(compile_artifacts)

            if request.output_kind in (OutputKind.LIBRARY, OutputKind.BOTH):
                artifacts.update(self._package_library(project_dir, workspace))

            result.firmware_path = artifacts.get("firmware")
            result.library_path = artifacts.get("library")
            result.build_log = log
            result.status = BuildStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            return result
        except (BuildFailed, ToolchainMissing):
            raise
        except Exception as e:
            raise BuildFailed(f"{self.target_id} build failed: {e}") from e

    def _package_library(self, project_dir: Path, workspace: Path) -> dict[str, Path]:
        """Default: zip the rendered project sources into `<target>-library.zip`.

        Subclasses can override to ship a smaller artifact (e.g. AVR ships only
        the emlearn-generated header).
        """
        library_zip = workspace / f"{self.target_id}-library.zip"
        with zipfile.ZipFile(library_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in project_dir.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=path.relative_to(project_dir))
        return {"library": library_zip}

    # --- Template hooks ------------------------------------------------------

    @abstractmethod
    def _prepare_project(self, workspace: Path) -> Path:
        """Copy/render the target's template into workspace, return project dir."""

    @abstractmethod
    def _inject_model(
        self,
        project_dir: Path,
        model_path: Path,
        model_info: ModelInfo,
        request: BuildRequest,
    ) -> None:
        """Write the model into the project (C byte array, header, etc.)."""

    @abstractmethod
    async def _compile(self, project_dir: Path) -> tuple[dict[str, Path], str]:
        """Run the toolchain. Return a dict of {kind: path} and a build log."""

    # --- Shared helpers ------------------------------------------------------

    @staticmethod
    def to_c_byte_array(symbol: str, data: bytes) -> str:
        lines = [
            f"#ifndef {symbol.upper()}_H",
            f"#define {symbol.upper()}_H",
            "",
            "#include <stdint.h>",
            "",
            f"const unsigned char {symbol}[] __attribute__((aligned(8))) = {{",
        ]
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            lines.append("  " + ", ".join(f"0x{b:02x}" for b in chunk) + ",")
        lines.append("};")
        lines.append(f"const unsigned int {symbol}_len = {len(data)};")
        lines.append("")
        lines.append(f"#endif  // {symbol.upper()}_H")
        return "\n".join(lines)

    @staticmethod
    def render_template(text: str, values: dict[str, str]) -> str:
        for key, val in values.items():
            text = text.replace("{{" + key + "}}", val)
        return text
