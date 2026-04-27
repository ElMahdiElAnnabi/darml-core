"""Darml — model-to-firmware compiler for edge AI.

Core is MIT-licensed and works fully on its own. If `darml_pro` is also
installed in the environment, importing it auto-registers Pro adapters
(quantizer, ONNX→TFLite converter, build cache, FastAPI server) into
`darml.plugins.hooks` — Core picks them up transparently.
"""

__version__ = "0.1.1"

# Best-effort: trigger Pro registration if the user has it installed.
# Failure modes:
#   - darml_pro not installed     → ImportError, Core continues in free mode
#   - darml_pro fails to import   → log warning, Core continues
try:
    import darml_pro  # noqa: F401
except ImportError:
    pass
except Exception as _e:  # pragma: no cover  — defensive
    import logging
    logging.getLogger("darml").warning("darml_pro import failed: %s", _e)
