import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    port: int = 8080
    host: str = "0.0.0.0"
    data_dir: str = "./data"
    max_model_size_mb: int = 100
    build_timeout_s: int = 300
    platformio_path: str = "pio"
    use_sqlite: bool = False
    sqlite_path: str = "./data/darml.db"
    debug: bool = False
    # Default empty — operators must explicitly set DARML_CORS_ORIGINS to
    # allow cross-origin browser callers. Avoids accidentally shipping a
    # public-API server that any malicious page can fetch from.
    cors_origins: tuple[str, ...] = ()
    cache_enabled: bool = True
    cache_dir: str = "./data/cache"
    auth_enabled: bool = False
    api_keys_raw: str = ""
    free_tier_daily_quota: int = 5
    sentry_dsn: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_cloud: str = ""
    stripe_price_pro_selfhost: str = ""
    public_base_url: str = "http://localhost:8080"
    # API-key persistence (Pro). Empty path → fall back to env-only store.
    api_keys_db_path: str = "./data/api_keys.db"
    # Admin API bearer token. When unset, admin endpoints are disabled (503).
    admin_token: str = ""
    # Transactional email (Resend).
    resend_api_key: str = ""
    resend_from: str = "no-reply@darml.dev"
    # Public URL for the API server (used in email templates so users have
    # a clickable dashboard link). Distinct from public_base_url which
    # points at the marketing site (darml.dev).
    api_base_url: str = "https://api.darml.dev"
    # Strict-mode startup validation. When true, missing production secrets
    # (Resend, Stripe, license signing) raise on boot — refuses to start
    # silently mis-configured. When false (default), only warnings are logged.
    strict_config: bool = False
    # Per-IP requests-per-minute cap on /v1/billing/checkout/{plan}. Prevents
    # someone hammering the endpoint to spam Stripe with abandoned sessions.
    # Set to 0 to disable.
    checkout_rate_limit_per_minute: int = 10
    # Freemium re-architecture feature flag. When False (default), the
    # legacy local-cap + per-key daily quota path runs unchanged. When
    # True, /v1/build uses the new 30-day rolling window quota +
    # build cache. See MIGRATION_NOTES.md (Step 4 onwards).
    metering_v2: bool = False


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(key)
    if raw is None:
        return default
    parts = tuple(p.strip() for p in raw.split(",") if p.strip())
    return parts or default


@lru_cache
def get_settings() -> Settings:
    return Settings(
        port=int(os.getenv("DARML_PORT", "8080")),
        host=os.getenv("DARML_HOST", "0.0.0.0"),
        data_dir=os.getenv("DARML_DATA_DIR", "./data"),
        max_model_size_mb=int(os.getenv("DARML_MAX_MODEL_SIZE_MB", "100")),
        build_timeout_s=int(os.getenv("DARML_BUILD_TIMEOUT", "300")),
        platformio_path=os.getenv("DARML_PLATFORMIO_PATH", "pio"),
        use_sqlite=_env_bool("DARML_USE_SQLITE", False),
        sqlite_path=os.getenv("DARML_SQLITE_PATH", "./data/darml.db"),
        debug=_env_bool("DARML_DEBUG", False),
        cors_origins=_env_csv("DARML_CORS_ORIGINS", ()),
        cache_enabled=_env_bool("DARML_CACHE_ENABLED", True),
        cache_dir=os.getenv("DARML_CACHE_DIR", "./data/cache"),
        auth_enabled=_env_bool("DARML_AUTH_ENABLED", False),
        api_keys_raw=os.getenv("DARML_API_KEYS", ""),
        free_tier_daily_quota=int(os.getenv("DARML_FREE_TIER_DAILY_QUOTA", "5")),
        sentry_dsn=os.getenv("SENTRY_DSN", ""),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        stripe_price_pro_cloud=os.getenv("STRIPE_PRICE_PRO_CLOUD", ""),
        stripe_price_pro_selfhost=os.getenv("STRIPE_PRICE_PRO_SELFHOST", ""),
        public_base_url=os.getenv("DARML_PUBLIC_BASE_URL", "http://localhost:8080"),
        api_keys_db_path=os.getenv("DARML_API_KEYS_DB", "./data/api_keys.db"),
        admin_token=os.getenv("DARML_ADMIN_TOKEN", ""),
        resend_api_key=os.getenv("RESEND_API_KEY", ""),
        resend_from=os.getenv("DARML_FROM_EMAIL", "no-reply@darml.dev"),
        api_base_url=os.getenv("DARML_API_BASE_URL", "https://api.darml.dev"),
        strict_config=_env_bool("DARML_STRICT_CONFIG", False),
        checkout_rate_limit_per_minute=int(
            os.getenv("DARML_CHECKOUT_RATE_LIMIT", "10")
        ),
        metering_v2=_env_bool("DARML_METERING_V2", False),
    )
