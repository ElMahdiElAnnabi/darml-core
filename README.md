# Darml — Model in. Firmware out.

A model-to-firmware compiler for edge AI. Upload a trained model
(`.tflite`, `.onnx`, or scikit-learn `.pkl`), pick a target hardware,
and get a flashable firmware binary or a drop-in C library.

11 supported targets across five hardware tiers — from a 2 KB AVR up to
a multi-GB Jetson — through a single uniform pipeline:

```
parse → check size → quantize → convert → compile → package
```

## Quick start

```bash
pip install darml
darml build path/to/model.tflite --target esp32-s3
darml flash darml-<build_id>.zip --port /dev/ttyUSB0
```

The first build downloads the cross-compiler toolchain (~5 minutes,
~500 MB per platform). Subsequent builds reuse the toolchain cache.

## Hardware support

| Target          | RAM         | Flash      | Runtime          |
|-----------------|-------------|------------|------------------|
| `avr-mega328`   | 2 KB        | 32 KB      | emlearn          |
| `avr-mega2560`  | 8 KB        | 256 KB     | emlearn          |
| `stm32f4`       | 320 KB      | 1 MB       | TFLite Micro     |
| `stm32h7`       | 1 MB        | 2 MB       | TFLite Micro     |
| `stm32n6`       | 1.5 MB      | 4 MB       | TFLite Micro     |
| `esp32`         | 520 KB      | 4 MB       | TFLite Micro     |
| `esp32-s3`      | 512 KB+8 MB | 16 MB      | TFLite Micro     |
| `rpi4` / `rpi5` | 4–8 GB      | —          | TFLite           |
| `jetson-nano`   | 4 GB        | —          | TensorRT/TFLite  |
| `jetson-orin`   | 8 GB        | —          | TensorRT/TFLite  |

Run `darml targets` for the full list with PlatformIO board IDs.

## CLI

```bash
darml info <model_file>                         # parse + show metadata
darml check <model_file> --target <target>      # estimate fit on hardware
darml targets                                   # list supported hardware
darml build <model_file> --target <target>      # parse → check → compile → zip
darml flash <artifact.zip> --port <serial>      # flash onto a device
darml version                                   # version + license status
```

`darml --help` and `darml <subcommand> --help` for full flags.

## Optional dependencies

The base install pulls only what's needed for the CLI to start. Pick
extras based on which model formats you'll feed it:

```bash
pip install 'darml[onnx]'        # ONNX parsing
pip install 'darml[tflite]'      # TFLite parsing without TensorFlow
pip install 'darml[sklearn]'     # sklearn parsing + emlearn → AVR C
pip install 'darml[build]'       # PlatformIO for MCU firmware compiles
pip install 'darml[all]'         # everything above
```

## Free tier

Darml Core is free under the MIT license, with a soft cap of 5 builds
per UTC-day enforced via `~/.darml/counter`. The CLI shows your
remaining count after each build.

```
$ darml build model.tflite --target esp32-s3
Build completed: 5f3e…
4 builds remaining today (resets at midnight UTC).
```

The cap is per-machine and per-user; deleting the counter file resets
it. This is friction-as-marketing, not DRM — Darml Pro (which lifts the
cap and adds quantization, ONNX conversion, web dashboard, and build
cache) is a separate package and a separate purchase.

## License

[MIT](https://opensource.org/licenses/MIT) — use Darml Core for
anything, commercial or not, no restrictions.
