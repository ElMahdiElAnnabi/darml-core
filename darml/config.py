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
    cors_origins: tuple[str, ...] = ("*",)
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
        cors_origins=_env_csv("DARML_CORS_ORIGINS", ("*",)),
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
    )
