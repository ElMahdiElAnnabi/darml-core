# Changelog

All notable changes to Darml. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and Darml
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- **Local builds are now unlimited on every tier** — the 5/day local cap
  has been deprecated. Set `DARML_METERING_V2=1` to disable it now;
  it will be removed entirely in the next minor release.
- Hosted-build metering moved to a 30-day rolling window. New limits:
  - Free signup: 30 hosted builds / month
  - Pro Solo: 500 / month
  - Pro Team: 2,500 / month
  - See [pricing](https://darml.dev/#pricing).
- Cache hits don't count toward your hosted-build quota. Identical
  inputs (same model bytes + target + flags) within 60 minutes return
  the cached firmware and don't burn a build.

### Added
- `darml quota` — show your current hosted-build quota state without
  running a build. Reads `DARML_API_KEY` and `DARML_SERVER`.
- New tier values: `free_signup`, `pro_team`. Existing `free` and `pro`
  unchanged.
- `X-Build-Quota-*` response headers on every `/v1/build` reply
  (Limit, Remaining, Reset, Cache-Hit).

### Deprecated
- `darml/free_tier.py` — the local daily counter. The CLI prints a
  deprecation warning when the legacy path runs. Delete the module
  and the warning in v0.2.

### Internal (server)
- New SQLite tables: `build_events` (rolling-window quota), `build_cache`
  (firmware cache), `processed_webhooks` (Stripe idempotency).
- Stripe `customer.subscription.updated` is now handled — needed for
  `cancel_at_period_end` honor and for plan changes (Solo↔Team).
- `customer.subscription.deleted` now downgrades to `free_signup`
  instead of revoking; the customer keeps their key and history if
  they re-subscribe.
- API keys are stored hashed at rest (`sha256(plaintext)` + 12-char
  prefix). The plaintext is shown ONCE at creation; the DB never
  holds it.

## [Unreleased] — Pro feature roadmap (P0 + P1.1)

### Added
- `darml login` command — saves API key to `~/.darml/credentials`
  (chmod 0600) or OS keychain when `DARML_USE_KEYCHAIN=1`. Verifies
  against the server before saving.
- `darml build --remote` now reads credentials from the saved file
  in addition to env vars (precedence: env > file).
- HTML build report (`build_report.py` + report panel in the artifact
  bundle). Shows per-layer profile when the parser populates it,
  falls back to op-type histogram. Self-contained; opens offline;
  print-friendly. <200 KB.
- `LayerInfo` domain type — optional richer per-layer metadata that
  parsers may populate.
- GitHub Action at `.github/actions/build/` — `darml/build@main` for
  CI workflows. Caches the install across runs; matrix-friendly.
- Example workflow at `.github/workflows/example-build.yml` —
  parallel build across 4 MCU targets on every push.

### Scaffolded (NOT launch-ready — see docs)
- `MixedPrecisionQuantizer` — port + Pro adapter. Implements QAT
  fake-quant detection (real). The Pareto-search core is stubbed
  pending real ML iteration — see `docs/MIXED_PRECISION_ROADMAP.md`.
  Calling `.quantize()` raises `NotImplementedError` unless the
  caller passes `_allow_scaffold=True` (acknowledges the kill-criterion
  benchmark hasn't been run).
