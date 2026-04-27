class DarmlError(Exception):
    """Base class for all Darml domain errors."""


class ModelFormatUnsupported(DarmlError):
    pass


class ModelParseError(DarmlError):
    pass


class TargetUnknown(DarmlError):
    pass


class TargetIncompatible(DarmlError):
    pass


class ModelTooLarge(DarmlError):
    pass


class BuildFailed(DarmlError):
    pass


class BuildNotFound(DarmlError):
    pass


class QuantizationFailed(DarmlError):
    pass


class ConversionFailed(DarmlError):
    pass


class FlashFailed(DarmlError):
    pass


class ModelTooLargeUpload(DarmlError):
    """Uploaded model exceeds DARML_MAX_MODEL_SIZE_MB."""


class ToolchainMissing(DarmlError):
    """A required toolchain (e.g. PlatformIO) is not installed."""


class AuthRequired(DarmlError):
    """Caller must present a valid API key."""


class QuotaExceeded(DarmlError):
    """API key has hit its daily build quota."""


class ProFeatureRequired(DarmlError):
    """A Pro-only feature was requested while only Darml Core is installed.

    The message must always include three things:
      1. Which feature was requested.
      2. How to get Pro (trial link).
      3. The free-tier alternative — keeps the message non-hostile and
         keeps user trust.
    """

    @classmethod
    def for_feature(
        cls,
        feature: str,
        free_alternative: str,
    ) -> "ProFeatureRequired":
        msg = (
            f"{feature} is a Darml Pro feature.\n\n"
            f"  → Start a free 14-day trial:  https://darml.dev/trial\n"
            f"  → Or {free_alternative}\n\n"
            f"Learn more: https://darml.dev/pricing"
        )
        return cls(msg)
