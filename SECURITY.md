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

## Hardening notes for self-hosters

- Set `DARML_AUTH_ENABLED=true` for any internet-facing deployment
- Set `DARML_MAX_MODEL_SIZE_MB` to a value that matches your storage budget
- Front the server with a reverse proxy that enforces TLS
- Restrict `DARML_CORS_ORIGINS` to the domains you actually use
- Treat `DARML_API_KEYS` as a secret — do not commit it to git or log it

Thanks for helping keep Darml safe.
