# Contributing to Darml

Thanks for showing up. Darml is small, and contributions of any size — bug
reports, fixes, new targets, docs — are welcome.

## Quick start for contributors

```bash
git clone https://github.com/ElMahdiElAnnabi/darml-core.git
cd darml
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,full]'
pytest                                          # 49+ tests, runs in seconds
```

## What to work on

Good first issues:

- **New target** — pick a board (Pico, Wio Terminal, Arduino Nano 33 BLE,
  Teensy, …). Add a `Target` to [darml/domain/targets.py](darml/domain/targets.py),
  a `FirmwareBuilderPort` impl in [darml/infrastructure/builders/](darml/infrastructure/builders/),
  one line in [darml/container.py](darml/container.py). No use case or route
  changes needed.
- **New parser/quantizer/converter** — same idea, plug into the existing ports.
- **Docs** — anywhere [USAGE.md](USAGE.md) or [README.md](README.md) is wrong
  or missing.
- **Tests** — anywhere coverage is thin. Run `pytest --cov=darml` to see gaps.

Bigger items live in the GitHub issue tracker labeled `help wanted` or
`good first issue`.

## Architecture rule

Keep the dependency direction:

```
domain  ←  application  ←  infrastructure  ←  interfaces
```

Domain has no external imports. Application depends only on domain (and
its own ports). Infrastructure adapters implement application ports.
Interfaces (FastAPI / CLI) wire the composition root in
[darml/container.py](darml/container.py). If your change crosses these
arrows, please mention it in the PR description so we can review the
boundary.

## Pull request checklist

- [ ] `pytest` passes locally
- [ ] New code has a test or a clear note about why it can't be tested
- [ ] Docs updated if behavior visible to users changed (README / USAGE / FLASH.md)
- [ ] Commit message explains the **why**, not just the **what**
- [ ] No new `.env` / secrets / large binaries in the diff

## Code style

- Python 3.12+
- `ruff` for lint + format (config in [pyproject.toml](pyproject.toml))
- Type hints encouraged, not enforced
- Keep functions short; prefer composition over class hierarchies
- No emojis in source code

## License of contributions

By submitting a PR you agree your contribution is licensed under the
[Business Source License 1.1](LICENSE) of the project, with the same
Change Date and Change License as the repository it's merged into.

If you need to ask anything before opening a PR, file an issue or open a
draft PR — easier to iterate together than to write the perfect change
in one shot.
