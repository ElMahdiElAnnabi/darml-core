# Darml — model to firmware (GitHub Action)

Compile an ML model (`.onnx` / `.tflite` / `.pkl`) to flashable firmware
on every push, via the [Darml](https://darml.dev) hosted API.

## Why

CI for embedded ML is annoying:
- Toolchain installs are 500+ MB per target (PlatformIO, ARM GCC, IDF…)
- Cross-compile failures surface 8 minutes into a build
- Nobody wants to maintain that across 11 targets

This action sidesteps the install entirely. The Darml hosted API has
the toolchains already; you upload the model, get a firmware zip back.
Cache hits return in <500 ms and don't burn your monthly quota.

## Usage

```yaml
- uses: ElMahdiElAnnabi/darml-core/.github/actions/build@main
  with:
    model: model.onnx
    target: esp32-s3
    api-key: ${{ secrets.DARML_API_KEY }}
```

## Inputs

| Input | Required | Default | Notes |
|-------|----------|---------|-------|
| `model` | yes | — | Path to the model file in the repo. |
| `target` | yes | — | Board ID. See `darml targets` or [the API](https://api.darml.dev/v1/targets). |
| `api-key` | yes | — | Pass via `${{ secrets.DARML_API_KEY }}`. |
| `server` | no | `https://api.darml.dev` | Override for self-hosted Pro. |
| `output` | no | `firmware` | `firmware` / `library` / `both`. |
| `quantize` | no | `false` | INT8 PTQ. |
| `output-path` | no | `darml-build.zip` | Where the artifact lands in the workspace. |

## Outputs

- `artifact-path` — path to the firmware zip, ready to feed into
  `actions/upload-artifact` or your release workflow.

## Cost

The action consumes one build from your monthly hosted quota per
matrix leg. Cache hits (identical model bytes + target + flags) don't
count. See [pricing](https://darml.dev/#pricing) for tier limits.

## Example

A complete workflow that builds for four MCU targets in parallel and
uploads each firmware as a release artifact lives at
[`example-build.yml`](../../workflows/example-build.yml).

## Pinning

For production, pin to a release tag instead of `@main`:

```yaml
- uses: ElMahdiElAnnabi/darml-core/.github/actions/build@v0.1.2
```
