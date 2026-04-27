import asyncio
import os
import time
from pathlib import Path

import click

from darml import __version__
from darml.config import get_settings
from darml.container import get_container
from darml.domain.enums import OutputKind, ReportMode
from darml.domain.exceptions import DarmlError
from darml.domain.models import BuildRequest


@click.group()
@click.version_option(__version__, "-V", "--version", package_name="darml")
def cli() -> None:
    """Darml — Model in. Firmware out."""


@cli.command(name="version")
def version_cmd() -> None:
    """Print Darml version + Pro license status."""
    from darml.plugins import hooks, license_status

    s = license_status()
    plan_color = {
        "pro": "green", "trial": "yellow",
        "expired": "red", "invalid": "red", "free": "cyan",
    }.get(s.plan, "white")
    click.echo(f"Darml {__version__}")
    click.echo(f"  Pro installed: {'yes' if hooks.has_pro() else 'no'}")
    click.echo(
        "  License plan:  "
        + click.style(s.plan, fg=plan_color, bold=True)
    )
    if s.customer:
        click.echo(f"  Licensed to:   {s.customer}")
    if s.expires_at:
        click.echo(f"  Expires:       {s.expires_at}")
    if s.message:
        click.echo(f"  {s.message}")


@cli.command()
@click.argument("model_file", type=click.Path(exists=True, path_type=Path))
def info(model_file: Path) -> None:
    """Print model metadata."""
    c = get_container()
    try:
        m = c.parse_model.execute(model_file)
    except DarmlError as e:
        raise click.ClickException(str(e))
    click.echo(f"Format:       {m.format.value}")
    click.echo(f"File size:    {m.file_size_bytes} bytes ({m.file_size_bytes/1024:.1f} KB)")
    click.echo(f"Input:        {list(m.input_shape)} {m.input_dtype.value}")
    click.echo(f"Output:       {list(m.output_shape)} {m.output_dtype.value}")
    click.echo(f"Operators:    {m.num_ops}")
    click.echo(f"Quantized:    {'yes' if m.is_quantized else 'no'}")


@cli.command()
@click.argument("model_file", type=click.Path(exists=True, path_type=Path))
@click.option("--target", required=True, help="Target hardware id (e.g. stm32f4)")
def check(model_file: Path, target: str) -> None:
    """Check whether a model fits on a given target."""
    c = get_container()
    try:
        m = c.parse_model.execute(model_file)
        res = c.check_size.execute(m, target)
    except DarmlError as e:
        raise click.ClickException(str(e))
    tag = click.style("OK", fg="green") if res.fits else click.style("TOO LARGE", fg="red")
    click.echo(
        f"[{tag}] RAM {res.model_ram_kb:6.1f} / {res.target_ram_kb:.0f} KB   "
        f"Flash {res.model_flash_kb:6.1f} / {res.target_flash_kb:.0f} KB"
    )
    if res.warning:
        click.echo(res.warning)


@cli.command()
def targets() -> None:
    """List supported hardware targets."""
    c = get_container()
    for t in c.list_targets.execute():
        ram = t.ram_kb + t.psram_kb
        click.echo(
            f"  {t.id:14s}  {ram:>9,} KB RAM  {t.flash_kb:>9,} KB flash  {t.runtime.value}"
        )


@cli.command()
@click.argument("model_file", type=click.Path(exists=True, path_type=Path))
@click.option("--target", required=True)
@click.option("--quantize", is_flag=True, help="Enable INT8 post-training quantization")
@click.option(
    "--calibration-data", "calibration_data",
    type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None,
    help="Path to a .npy/.npz of representative input samples for INT8 PTQ. "
         "Without this, Darml uses synthetic random N(0,1) calibration which "
         "typically degrades accuracy 1-15% — supply real samples for production.",
)
@click.option("--output", type=click.Choice(["firmware", "library", "both"]), default="firmware")
@click.option("--report", type=click.Choice(["serial", "http", "mqtt"]), default="serial")
@click.option(
    "--local/--remote", "local_mode", default=None,
    help="Run the build in-process (--local, default) or against a server "
         "(--remote, requires --server).",
)
@click.option(
    "--server", default=None,
    help="HTTP base URL of an Darml server. Defaults to env DARML_SERVER. "
         "Implies --remote when set.",
)
@click.option(
    "--out", "out_path", type=click.Path(path_type=Path), default=None,
    help="Where to write the downloaded artifact zip (remote mode).",
)
def build(
    model_file: Path,
    target: str,
    quantize: bool,
    calibration_data: Path | None,
    output: str,
    report: str,
    local_mode: bool | None,
    server: str | None,
    out_path: Path | None,
) -> None:
    """Build firmware for a target.

    Default is local: the CLI runs the pipeline in-process. Pass --remote
    plus --server URL (or set DARML_SERVER) to dispatch the build to a
    running Darml instance and stream back the artifact.
    """
    if calibration_data and not quantize:
        raise click.ClickException(
            "--calibration-data only meaningful with --quantize."
        )
    if quantize and not calibration_data:
        click.secho(
            "warning: --quantize without --calibration-data uses synthetic "
            "N(0,1) random calibration. Accuracy may drop 1-15% vs FP32. "
            "Supply real calibration samples for production builds.",
            fg="yellow", err=True,
        )

    server = server or os.getenv("DARML_SERVER")
    use_remote = (local_mode is False) or (local_mode is None and server is not None)

    if use_remote:
        if not server:
            raise click.ClickException(
                "--remote requires --server URL or DARML_SERVER env var."
            )
        _build_remote(
            model_file, target, quantize, calibration_data,
            output, report, server, out_path,
        )
        return

    _build_local(model_file, target, quantize, calibration_data, output, report)


def _build_local(
    model_file: Path, target: str, quantize: bool,
    calibration_data: Path | None,
    output: str, report: str,
) -> None:
    from darml.free_tier import consume_free_build

    # Free tier: 5 builds/UTC-day enforced via ~/.darml/counter.
    # Pro is unlimited; consume_free_build no-ops in that case.
    try:
        usage = consume_free_build()
    except DarmlError as e:
        raise click.ClickException(str(e))

    c = get_container()
    request = BuildRequest(
        model_path=model_file.resolve(),
        target_id=target,
        quantize=quantize,
        calibration_data_path=calibration_data.resolve() if calibration_data else None,
        output_kind=OutputKind(output),
        report_mode=ReportMode(report),
    )
    try:
        result = asyncio.run(c.build_firmware.execute(request))
    except DarmlError as e:
        raise click.ClickException(str(e))
    click.echo(f"Build {result.status.value}: {result.build_id}")
    for w in result.warnings:
        # Multi-line warnings (e.g. the ACCURACY NOTICE) need each line prefixed
        # so they stay visually grouped instead of getting lost.
        is_accuracy = w.startswith("ACCURACY NOTICE")
        color = "yellow" if is_accuracy else None
        for line in w.splitlines():
            click.secho(f"  ! {line}" if line.startswith("ACCURACY") else f"    {line}",
                        fg=color)
    if result.artifact_zip_path:
        click.echo(f"Artifact: {result.artifact_zip_path}")
    if result.error:
        raise click.ClickException(result.error)
    # Friendly nudge — only for free tier users.
    if usage.message:
        click.echo(usage.message)


def _build_remote(
    model_file: Path,
    target: str,
    quantize: bool,
    calibration_data: Path | None,
    output: str,
    report: str,
    server: str,
    out_path: Path | None,
) -> None:
    import httpx

    server = server.rstrip("/")
    click.echo(f"→ POST {server}/v1/build  (target={target}, output={output})")
    try:
        opener_handles = [model_file.open("rb")]
        files: dict = {
            "file": (model_file.name, opener_handles[0], "application/octet-stream"),
        }
        if calibration_data is not None:
            opener_handles.append(calibration_data.open("rb"))
            files["calibration_data"] = (
                calibration_data.name, opener_handles[1], "application/octet-stream",
            )
        try:
            data = {
                "target": target,
                "quantize": "true" if quantize else "false",
                "output": output,
                "report_mode": report,
            }
            with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                resp = client.post(f"{server}/v1/build", files=files, data=data)
        finally:
            for h in opener_handles:
                h.close()
        if resp.status_code >= 400:
            raise click.ClickException(f"server returned {resp.status_code}: {resp.text}")
        build_id = resp.json()["build_id"]
        click.echo(f"  build_id={build_id}")

        # Poll for completion.
        with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
            last_status = ""
            while True:
                r = client.get(f"{server}/v1/build/{build_id}")
                if r.status_code >= 400:
                    raise click.ClickException(f"poll failed: {r.text}")
                body = r.json()
                status = body["status"]
                if status != last_status:
                    click.echo(f"  status={status}")
                    last_status = status
                if status in ("completed", "failed"):
                    if status == "failed":
                        raise click.ClickException(body.get("error") or "build failed")
                    break
                time.sleep(2.0)

            # Download.
            dst = out_path or Path(f"darml-{build_id}.zip")
            with client.stream("GET", f"{server}/v1/build/{build_id}/download") as r:
                if r.status_code >= 400:
                    raise click.ClickException(f"download failed: {r.text}")
                with dst.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        click.echo(f"Artifact: {dst}")
    except httpx.HTTPError as e:
        raise click.ClickException(f"network error: {e}")


@cli.command()
@click.argument("artifact", type=click.Path(exists=True, path_type=Path))
@click.option("--port", required=True, help="Serial port (e.g. /dev/ttyUSB0)")
@click.option(
    "--target", default=None,
    help="Override target. If omitted and the file is an Darml .zip, the "
         "target is read from manifest.json.",
)
def flash(artifact: Path, port: str, target: str | None) -> None:
    """Flash a firmware file onto a device.

    Accepts either:
      - a raw firmware file (.bin/.hex/.elf) — requires --target
      - an Darml artifact .zip — target auto-detected from manifest.json
    """
    import json
    import tempfile
    import zipfile

    firmware: Path
    is_zip = artifact.suffix == ".zip" and zipfile.is_zipfile(artifact)
    if is_zip:
        # Extract manifest + the firmware file referenced therein.
        try:
            with zipfile.ZipFile(artifact) as zf:
                if "manifest.json" not in zf.namelist():
                    raise click.ClickException(
                        "Zip is missing manifest.json — pass --target manually "
                        "or rebuild with a current Darml version."
                    )
                manifest = json.loads(zf.read("manifest.json"))
                detected_target = target or manifest.get("target")
                fw_name = manifest.get("firmware")
                if not detected_target:
                    raise click.ClickException("manifest.json has no target")
                if not fw_name or fw_name not in zf.namelist():
                    raise click.ClickException(
                        "manifest.json references a firmware file that's not in the zip "
                        "(this is a library-mode build — it has no firmware to flash). "
                        "Rebuild with --output firmware."
                    )
                tmp_dir = Path(tempfile.mkdtemp(prefix="darml-flash-"))
                firmware = Path(zf.extract(fw_name, tmp_dir))
                target = detected_target
                click.echo(
                    f"detected target={target} flasher={manifest.get('flasher')} "
                    f"firmware={fw_name}"
                )
        except zipfile.BadZipFile as e:
            raise click.ClickException(f"not a valid zip: {e}")
    else:
        if not target:
            raise click.ClickException(
                "--target required when flashing a raw firmware file."
            )
        firmware = artifact

    c = get_container()
    try:
        out = c.flash_device.execute(firmware, port, target)
    except DarmlError as e:
        raise click.ClickException(str(e))
    click.echo(out)


@cli.command()
def serve() -> None:
    """Start the Darml HTTP server (Pro feature)."""
    from darml.plugins import hooks
    if hooks.server_factory is None:
        raise click.ClickException(
            "The Darml web dashboard requires Darml Pro.\n\n"
            "  → Start a free 14-day trial:  https://darml.dev/trial\n"
            "  → The CLI works fully without Pro:\n"
            "    darml build model.tflite --target esp32-s3\n\n"
            "Learn more: https://darml.dev/pricing"
        )

    import uvicorn  # noqa: PLC0415  — only needed for the serve path
    s = get_settings()
    app = hooks.server_factory(get_container())
    uvicorn.run(app, host=s.host, port=s.port)


if __name__ == "__main__":
    cli()
