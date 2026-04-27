# Security policy

## Reporting a vulnerability

If you find a security issue in Darml, please **do not** open a public
GitHub issue. Instead, email a description and reproduction steps to:

> security@darml.dev

Include:

- The affected version (commit hash if you can)
- A minimal proof-of-concept
- Your assessment of impact

We will:

1. Acknowledge receipt within **3 business days**.
2. Investigate and confirm or dispute the issue within **14 days**.
3. Coordinate a fix and disclosure timeline with you. Default disclosure
   is **90 days** from confirmation, shorter if a fix lands sooner.

## Scope

In scope:

- Code in this repository
- The bundled Docker image
- The hosted Darml service (if/when deployed at darml.dev)

Out of scope:

- Third-party dependencies (report upstream — we'll bump our pin)
- Vulnerabilities in user-supplied model files (we validate magic bytes
  but the underlying TFLite/ONNX/sklearn parsers are upstream code)
- Findings against `output=library` artifacts that the user themselves
  modifies before flashing

## Known threat model

### `joblib` / pickle deserialization

scikit-learn models distribute as `.pkl` / `.joblib` files. These are
Python pickles, which means **`joblib.load(path)` is arbitrary code
execution against the loading process**. Magic-byte sniffing (`0x80`
protocol marker) catches *format* mistakes, not *content* attacks — a
malicious pickle with a valid header still runs.

What we do:

- **Subprocess isolation.** The sklearn parser
  ([`darml/infrastructure/parsers/sklearn_parser.py`](darml/infrastructure/parsers/sklearn_parser.py))
  and the sklearn→C converter
  ([`darml/infrastructure/converters/sklearn_to_c.py`](darml/infrastructure/converters/sklearn_to_c.py))
  spawn a separate Python process for the unpickle. The worker sets
  `RLIMIT_AS` (256 MB / 512 MB), `RLIMIT_CPU` (30 s / 60 s), and
  `RLIMIT_FSIZE` (200 MB) before calling `joblib.load`. A malicious
  pickle that tries to fork-bomb, exhaust memory, or burn CPU dies in
  the worker without affecting the API server.
- **Wall-clock kill switch.** The parent applies a `subprocess.run`
  timeout on top of the worker's CPU rlimit, in case the worker is
  blocked on a syscall.

What we do **not** do (yet) — recommended hardening for hosted
deployments handling untrusted uploads:

- `seccomp` or `nsjail` around the worker (tighter syscall filter)
- Running the API host with `docker run --read-only --network=none
  --cap-drop=ALL --user nobody`
- Pre-scanning uploads through `pickletools` / `fickling` to flag
  obviously-malicious opcodes before invoking `joblib.load`

If you self-host, **isolate the build worker**: separate user, no
network, no API-key DB access, no shared filesystem with the parent.

### Other surfaces

- **License signing secret.** `darml-pro` ships with a committed dev
  secret used only by the test suite (gated by
  `DARML_LICENSE_DEV_OK=1`). Production refuses to fall back to it; a
  startup error fires if `DARML_LICENSE_SIGNING_SECRET` isn't set.
- **SSRF on `report_url`.** The build endpoint validates `report_url`
  before persisting: HTTPS-only, no userinfo, must resolve to a public
  IP (private/loopback/link-local rejected), no privileged ports.
- **Path traversal.** `FilesystemStorage` resolves every path and
  asserts it stays inside `data_dir` before any write.
- **C-template injection.** `wifi_ssid`, `wifi_password`, `report_url`
  are rendered into C string literals in the firmware. They're now
  validated through allowlists (printable ASCII, length-bounded; URL
  re-serialized through `urlparse`).
- **Admin-token timing.** Bearer-token comparison uses
  `hmac.compare_digest` to defeat the byte-by-byte short-circuit
  attack.
- **PII in logs.** Customer emails are never logged in cleartext;
  they're hashed (SHA-256, first 12 hex chars) for correlation.

## Hardening notes for self-hosters

- Set `DARML_AUTH_ENABLED=true` for any internet-facing deployment
- Set `DARML_STRICT_CONFIG=true` so a missing critical secret fails the
  boot loud rather than silently downgrading
- Set `DARML_MAX_MODEL_SIZE_MB` to a value that matches your storage
  budget
- Front the server with a reverse proxy that enforces TLS
- Restrict `DARML_CORS_ORIGINS` to the domains you actually use (the
  default is `()` — empty allowlist; you must opt in)
- Treat `DARML_API_KEYS`, `DARML_ADMIN_TOKEN`, `DARML_LICENSE_SIGNING_SECRET`,
  and `STRIPE_*` secrets as production secrets — never log, never
  commit, rotate when staff turn over
- For uploads from untrusted sources, run the build worker in a sandbox
  beyond the in-process subprocess we ship (Docker, nsjail, or
  systemd's `ProtectHome=`/`PrivateTmp=`/`SystemCallFilter=`)

Thanks for helping keep Darml safe.
