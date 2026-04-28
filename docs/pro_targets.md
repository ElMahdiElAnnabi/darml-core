# Pro targets

Pro Cloud and Pro Team subscriptions unlock additional hardware
targets in the hosted build farm. Local builds are not affected —
every target is buildable locally with `darml build` if you have the
PlatformIO toolchain installed yourself.

| | | |
|---|---|---|
| **target** | **chip / class** | **plan** |
| `nrf52840` | Cortex-M4F + BLE 5 (Nordic) | Pro Cloud |
| `rp2040` | Dual Cortex-M0+ (Raspberry Pi Pico) | Pro Cloud |
| `stm32u5` | Cortex-M33 + TrustZone (STM32U5 series) | Pro Cloud |
| `alif-ensemble-e7` | Cortex-M55 + Helium + Ethos-U55 NPU | Pro Team — early access |

The full live list with RAM/flash specs is at
`https://api.darml.dev/v1/targets` (or `darml targets`).

## Why these are Pro

The Core 11 targets cover the popular open boards (AVR, STM32 F4/H7/N6,
ESP32, RPi, Jetson) and are MIT-licensed. The boards below need extra
toolchain plumbing in our build farm, vendor-specific kernel tuning,
or — in Alif's case — a closed-source compiler. That cost lives behind
the Pro tier so the Core install stays small and self-contained.

### `nrf52840` — Cortex-M4F + BLE 5

Nordic's tinyML-on-BLE niche. The build ships an Arduino-framework
firmware via the `nordicnrf52` PlatformIO platform, with the same
`tflm_cortexm` int8 kernels we use on STM32. The Pro value is:

- The hosted farm has the Nordic toolchain pre-installed (saves you the
  ~700 MB Nordic SDK download).
- BLE-aware firmware templates are on the roadmap — emit inferences
  over a GATT characteristic without writing softdevice glue. v1
  template is Serial-only.

256 KB SRAM. With softdevice S140 active, ~140 KB is usable for the
tensor arena; without softdevice, ~200 KB. We cap at 128 KB by default
to leave headroom for either case.

### `rp2040` — Dual Cortex-M0+

Raspberry Pi Pico, ~$4 board. Cortex-M0+ has no FPU, so floating-point
ops compile to soft-float — a stock TFLite-Micro Arduino build runs
about 4× slower than necessary. Pro hosted builds ship a `tflm_cortexm`
+ CMSIS-NN combination tuned for the M0+ instruction set, plus
multi-core scheduling on the roadmap (currently runs on core 0 only).

264 KB SRAM, ~192 KB available for the arena after framework + USB +
stacks.

### `stm32u5` — Cortex-M33 + TrustZone

STM32U585 — newer-generation STM32 with TrustZone, secure-element
integration, and ULP modes. Aimed at industrial customers who want
their model running in the secure side of a TZ-partitioned firmware.
The Pro value is:

- We maintain the secure-side / non-secure-side split in the firmware
  template; you flip a build flag instead of writing it yourself.
- 768 KB SRAM, 2 MB flash. We default the arena to 512 KB and reserve
  ~256 KB for framework + interpreter + secure carveout.

### `alif-ensemble-e7` — Cortex-M55 + Helium + Ethos-U55 NPU

The actual edge-AI accelerator. M55 cores with Arm Helium (MVE) for
SIMD on Cortex-M, plus an Ethos-U55 NPU for INT8 conv-heavy workloads.
Performance vs a plain M4 on a small CNN: roughly 25–50× per second
with the same memory budget.

This is **Pro Team only** and currently **early access** — the Vela
compiler isn't live in the hosted farm yet. Hitting `/v1/build` for
this target returns:

```json
{
  "detail": "alif-ensemble-e7 is in early access — the build toolchain isn't live in the hosted farm yet. Email hello@darml.dev to join the pilot. Pro Team subscribers get priority."
}
```

(HTTP 503.) Email <hello@darml.dev> if you have an Alif AI/ML AppKit
or DevKit-E7 and want to be on the bring-up list.

## Trying a Pro target

Once you have a Pro Cloud or Pro Team API key:

```bash
export DARML_API_KEY=sk_pro_…
darml build model.onnx --target nrf52840 --remote --server https://api.darml.dev
```

The CLI surfaces tier on the targets list:

```
$ darml targets
  esp32-s3              520 KB RAM    16,384 KB flash    tflite-micro
  nrf52840              256 KB RAM     1,024 KB flash    tflite-micro  [PRO]
  rp2040                264 KB RAM     2,048 KB flash    tflite-micro  [PRO]
  stm32u5               768 KB RAM     2,048 KB flash    tflite-micro  [PRO]
  alif-ensemble-e7   13,500 KB RAM     5,376 KB flash    tflite-micro  [PRO_TEAM]
  …
```

If you build a Pro target with a free key, the API returns 402:

```json
{
  "detail": "Target 'nrf52840' requires a Pro Cloud or Pro Team subscription. Your current tier is 'free_signup'. Upgrade at https://darml.dev/#pricing."
}
```

## Quota interaction

Pro target builds consume hosted-build quota the same way free targets
do: cache hits don't count, cache misses cost one. `nrf52840` and
`rp2040` builds are typically ~10 s and ~15 s respectively on the farm;
`stm32u5` runs ~25 s; `alif-ensemble-e7` will be longer when it ships
(NPU memory plan + Vela schedule are not free).

The 30-day rolling quota in `quota_v2` is shared across free + Pro
targets — there is no per-target sub-quota.

## Local builds

Every Pro target is buildable locally for free if you have the
PlatformIO platform installed:

```bash
# nrf52840:
pio platform install nordicnrf52

# rp2040:
pio platform install raspberrypi

# stm32u5:
pio platform install ststm32  # already installed if you've built any STM32

# Then:
darml build model.onnx --target nrf52840 --local
```

Local Pro builds don't hit any tier check — that gate only applies to
`/v1/build`. The Pro tier exists to monetize the hosted farm and the
maintenance cost of keeping these toolchains green; the open-source
build path stays open.

`alif-ensemble-e7` is the exception: there is no FOSS Vela toolchain we
can ship with Core, and the Cortex-M55 + Ethos-U combination needs
ahead-of-time NPU scheduling. Local builds for it will fail until Vela
support lands. Pilot users get the toolchain bundled in the early-access
build farm.

## Asking for a new target

If you're shipping a board that isn't in the list, open an issue at
<https://github.com/ElMahdiElAnnabi/darml-core/issues> with the chip,
the dev kit you're using, and (if you have it) a working
`platformio.ini` from a non-Darml project. We prioritize requests with
real hardware on the bench and a customer attached.
