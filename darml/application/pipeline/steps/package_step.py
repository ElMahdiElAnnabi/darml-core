import json
import zipfile
from datetime import datetime, timezone

from darml.domain.enums import BuildStatus
from darml.infrastructure.flash_docs import flasher_id_for, render_flash_readme

from ..context import BuildContext
from ..step import PipelineStep


class PackageStep(PipelineStep):
    @property
    def name(self) -> str:
        return "package"

    @property
    def status(self) -> BuildStatus:
        return BuildStatus.PACKAGING

    async def run(self, ctx: BuildContext) -> BuildContext:
        # Persist the build log to disk (separate from the artifact .zip) so
        # operators can debug builds without unzipping anything.
        log_path = ctx.workspace / "build_log.txt"
        if ctx.result.build_log:
            log_path.write_text(ctx.result.build_log)

        manifest = self._manifest(ctx)
        flash_md = render_flash_readme(
            ctx.request.target_id, ctx.request.output_kind, ctx.result.build_id,
        )

        zip_path = ctx.workspace / f"{ctx.result.build_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if ctx.result.firmware_path and ctx.result.firmware_path.exists():
                zf.write(ctx.result.firmware_path, arcname=ctx.result.firmware_path.name)
            if ctx.result.library_path and ctx.result.library_path.exists():
                zf.write(ctx.result.library_path, arcname=ctx.result.library_path.name)
            if ctx.result.build_log:
                zf.writestr("build_log.txt", ctx.result.build_log)
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("FLASH.md", flash_md)
            zf.writestr("README.txt", self._readme(ctx))
        ctx.result.artifact_zip_path = zip_path
        return ctx

    @staticmethod
    def _manifest(ctx: BuildContext) -> dict:
        firmware_name = (
            ctx.result.firmware_path.name
            if ctx.result.firmware_path and ctx.result.firmware_path.exists()
            else None
        )
        library_name = (
            ctx.result.library_path.name
            if ctx.result.library_path and ctx.result.library_path.exists()
            else None
        )
        return {
            "schema_version": 1,
            "build_id": ctx.result.build_id,
            "target": ctx.request.target_id,
            "flasher": flasher_id_for(ctx.request.target_id),
            "output_kind": ctx.request.output_kind.value,
            "quantize": ctx.request.quantize,
            "report_mode": ctx.request.report_mode.value,
            "firmware": firmware_name,
            "library": library_name,
            "warnings": list(ctx.result.warnings),
            "model": {
                "format": ctx.model_info.format.value if ctx.model_info else None,
                "input_shape": list(ctx.model_info.input_shape) if ctx.model_info else None,
                "output_shape": list(ctx.model_info.output_shape) if ctx.model_info else None,
                "is_quantized": ctx.model_info.is_quantized if ctx.model_info else None,
            },
            "size_check": (
                {
                    "fits": ctx.result.size_check.fits,
                    "model_ram_kb": ctx.result.size_check.model_ram_kb,
                    "model_flash_kb": ctx.result.size_check.model_flash_kb,
                    "target_ram_kb": ctx.result.size_check.target_ram_kb,
                    "target_flash_kb": ctx.result.size_check.target_flash_kb,
                }
                if ctx.result.size_check else None
            ),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _readme(ctx: BuildContext) -> str:
        lines = [
            f"Darml build {ctx.result.build_id}",
            f"Target: {ctx.request.target_id}",
            f"Quantized: {ctx.request.quantize}",
            f"Output kind: {ctx.request.output_kind.value}",
            f"Report mode: {ctx.request.report_mode.value}",
            "",
            "See FLASH.md in this archive for target-specific flash instructions.",
            "manifest.json contains structured build metadata for tooling.",
        ]
        if ctx.result.size_check:
            sc = ctx.result.size_check
            lines.append("")
            lines.append(f"Estimated RAM: {sc.model_ram_kb:.1f}KB / {sc.target_ram_kb:.0f}KB")
            lines.append(f"Estimated Flash: {sc.model_flash_kb:.1f}KB / {sc.target_flash_kb:.0f}KB")
        return "\n".join(lines) + "\n"
