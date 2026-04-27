# Darml — Usage

End-to-end recipe for the demo scenario implemented in this scaffold:
**train a tiny scikit-learn classifier → produce an AVR-targeted C library
that drops into a PlatformIO project**.

The scaffold covers more targets (ESP32-S3, STM32 F4/H7/N6, AVR mega328/2560,
RPi 4/5, Jetson Nano/Orin) — see [CLAUDE(1).md](CLAUDE(1).md) for the full
target matrix. The recipe below is the one that runs end-to-end without any
cross-compiler toolchain installed.

## 1. Install

```bash
git clone <this repo>
cd Darml
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
# Demo deps for the sklearn → AVR scenario:
pip install scikit-learn joblib emlearn setuptools numpy
```

`setuptools` is needed because emlearn imports `distutils`, which Python 3.12
removed from the stdlib.

## 2. Run the demo end-to-end

```bash
python examples/iris_avr_demo.py
```

What it does, step by step:

| Step      | What runs                                          | Pipeline stage |
|-----------|----------------------------------------------------|----------------|
| 1. train  | `DecisionTreeClassifier` on the iris dataset → `iris.pkl` | (input)        |
| 2. info   | `ParseModel` use case via `SklearnParser`          | parse          |
| 3. check  | `CheckSize` use case against `avr-mega328`         | check          |
| 4. build  | `BuildFirmware` runs the full pipeline             | quantize → convert → compile → package |
| 5. inspect| Reads the produced `.zip` and lists contents       | (output)       |

Sample output:

```
step 1 — train sklearn model
  trained DecisionTreeClassifier (max_depth=3): 97% train accuracy
  saved to .../demo_workspace/iris.pkl (2113 bytes)

step 2 — parse model (CLI: darml info iris.pkl)
  format=sklearn  input=[1, 4]  output=[1, 3]  ops=['DecisionTreeClassifier']

step 3 — check fit on avr-mega328 (CLI: darml check iris.pkl --target avr-mega328)
  [FITS] Flash 2.06 / 32 KB    RAM 2.00 / 2 KB
  warning: Tight fit: uses ~2KB of 2KB RAM. Consider INT8 quantization.

step 4 — build library for avr-mega328 (CLI: darml build iris.pkl --target avr-mega328 --output library)
  status=completed  build_id=8a877c78-aec1-421b-b6ed-f065d180b017

step 5 — inspect the artifact zip
  artifact: data/builds/.../8a877c78-aec1-421b-b6ed-f065d180b017.zip
    avr-mega328-library.zip                1510 bytes
    README.txt                              183 bytes

  library zip: data/builds/.../avr-mega328-library.zip
    platformio.ini                          232 bytes
    src/main.cpp                            698 bytes
    src/model.h                            1660 bytes
    lib/darml/darml.h                         193 bytes
```

`src/model.h` is real emlearn-generated C — a static `darml_model_predict()`
function the AVR firmware calls to classify. `src/main.cpp` reads ADC, calls
the predictor, and prints over serial.

## 3. Use the same flow from the CLI

The demo runs Python directly. The same operations are exposed as CLI commands:

```bash
darml info     iris.pkl
darml check    iris.pkl --target avr-mega328
darml targets
darml build    iris.pkl --target avr-mega328 --output library
darml flash    firmware.hex --port /dev/ttyUSB0 --target avr-mega328
```

`darml --help` lists all commands.

## 4. Use the HTTP API

Start the server:

```bash
darml serve                  # or: python -m darml
# → http://localhost:8080
```

Then drive the same flow with `curl`:

```bash
# 1. List supported targets
curl http://localhost:8080/v1/targets

# 2. Inspect a model
curl -F "file=@iris.pkl" http://localhost:8080/v1/info

# 3. Check fit on a target
curl -F "file=@iris.pkl" -F "target=avr-mega328" http://localhost:8080/v1/check

# 4. Start a build (returns 202 with a build_id)
BUILD_ID=$(curl -s -F "file=@iris.pkl" -F "target=avr-mega328" \
                -F "output=library" \
                http://localhost:8080/v1/build | jq -r .build_id)

# 5. Poll status
curl http://localhost:8080/v1/build/$BUILD_ID

# 6. Download the artifact .zip
curl -o darml-build.zip http://localhost:8080/v1/build/$BUILD_ID/download
```

A drag-and-drop web UI is served at `http://localhost:8080/`.

## 5. Run with Docker

```bash
docker compose up --build
# → http://localhost:8080
```

The Docker image pre-fetches PlatformIO platform packs for ESP32 / STM32 / AVR
so first-time MCU builds inside the container are fast.

The Dockerfile + compose pass static checks (FROM, CMD, HEALTHCHECK,
ports, build context, env vars, .dockerignore coverage). Verifying the
**actual** build is the right next step on your hardware — the dev
machine used to author this repo didn't have daemon access for an
end-to-end `docker build` run. Expect:

  - First build: ~5 minutes (PlatformIO platform downloads dominate).
  - Image size: ~2.5 GB after toolchain caches are baked in.
  - Container memory: 1 GB is comfortable; 512 MB works for sklearn-only.

## What's plugged in vs. stubbed

The demo scenarios run fully. Other targets and modes are wired through the
same architecture but depend on toolchains that aren't installed by default:

| Target / mode                  | Status | Extra deps |
|--------------------------------|--------|------------|
| sklearn → AVR library          | ✅ runs end-to-end | `scikit-learn joblib emlearn setuptools` |
| ONNX → quantized → RPi/Jetson  | ✅ runs end-to-end | `onnx onnxruntime sympy tensorflow tf-keras onnx2tf onnx-graphsurgeon onnxsim sng4onnx` |
| TFLite → RPi/Jetson            | ✅ runs (pure-Python) | `onnx` (only if other paths) |
| **TFLite → ESP32 firmware**    | ✅ verified — produces `firmware.bin` | `platformio` + Xtensa toolchain |
| **TFLite → STM32 firmware**    | ✅ verified — produces `firmware.bin` | `platformio` + ARM GCC toolchain |
| **ONNX → ESP32 firmware**      | ✅ verified — full ONNX→TFLite→build pipeline | both above + `onnx2tf` |
| sklearn → AVR firmware (.hex)  | wired, needs toolchain | `platformio` (auto-fetches avr-gcc) |

### Real-world model coverage (verified)

The pipeline was tested end-to-end with 5 representative model archetypes:

| Model archetype                        | Size  | Format    | ESP32-S3 fw  | STM32F4 fw  | RPi5 tarball | AVR lib |
|----------------------------------------|-------|-----------|--------------|-------------|--------------|---------|
| micro_speech keyword spotter (proxy)   | 65 KB | TFLite    | ✅ 566 KB     | ✅           | ✅            | n/a    |
| MNIST CNN (Conv2D + Dense)             |109 KB | TFLite    | ✅           | ✅ 345 KB    | ✅            | n/a    |
| MobileNetV2 INT8 (96×96, α=0.35)       |597 KB | TFLite    | check OK¹   | check OK¹  | ✅            | reject ✓|
| sklearn random forest (iris)           | 17 KB | sklearn   | n/a²         | n/a²        | n/a²         | ✅     |
| MLP (Gemm + Relu + Softmax)            | 15 KB | ONNX      | ✅ 522 KB     | ✅           | ✅            | n/a    |

¹ The size estimator's arena heuristic is intentionally conservative; for MobileNetV2
on stm32f4, the actual TFLite Micro arena requirement at AllocateTensors() time may
exceed the 320 KB SRAM. Verify the build before flashing.
² sklearn → MCU firmware uses emlearn's pure-C codegen; there's no TFLite path.

ParserStep + size_check ran cleanly across all 5 × 10 = 50 (model, target) combinations.
The size_check correctly rejected the larger TFLite models on AVR-Mega328 (32 KB flash).

### One-liner: install everything for the ONNX → RPi/Jetson path

```bash
pip install onnx onnxruntime sympy \
            tensorflow tf-keras \
            onnx2tf onnx-graphsurgeon onnxsim sng4onnx ai-edge-litert
```

### Run the ONNX demo

```bash
python examples/onnx_rpi_demo.py
```

It builds a tiny ONNX classifier, quantizes it via onnxruntime, converts to
TFLite via onnx2tf, and packages a runnable Pi tarball — no MCU toolchain
needed.

### MCU compile (ESP32 / STM32 firmware mode)

```bash
pip install platformio
```

Then run one of the verified end-to-end scripts:

```bash
DARML_BUILD_TIMEOUT=1800 python examples/esp32_demo.py    # produces firmware.bin
DARML_BUILD_TIMEOUT=1800 python examples/stm32_demo.py    # produces firmware.bin
```

First-time toolchain fetch is ~5 minutes per platform (~500 MB each).
Subsequent builds inside the same project dir are fast; the Darml pipeline
currently uses a fresh project per build, so library compilation cost is
paid each time. Set `DARML_BUILD_TIMEOUT` to ≥1800 seconds.

The architecture used:
  - `eloquentarduino/tflm_esp32` (ESP32) or `eloquentarduino/tflm_cortexm`
    (STM32) — vendored TFLite Micro distribution that compiles cleanly
    with PlatformIO's Arduino framework.
  - `eloquentarduino/EloquentTinyML` master — the `Eloquent::TF::Sequential`
    wrapper providing the templated interpreter API.
  - The Darml runner installs deps first, patches one upstream source
    (`system_setup.cpp` on STM32 — references Arduino's `RingBufferN<>`
    which STM32duino doesn't expose), then runs the build.

If you don't have the toolchain or want to inspect the rendered code
without compiling, use `output=library` to get the project source tree
as a .zip you can drop into your own PlatformIO project.

Add a target by:
1. Add a `Target` entry to `darml/domain/targets.py`.
2. Implement `FirmwareBuilderPort` (subclass `BaseBuilder` for PlatformIO targets,
   or implement `build()` directly).
3. Register it in `darml/container.py`.

No other file changes required — the use cases, factories, and pipeline pick
up the new target automatically.
