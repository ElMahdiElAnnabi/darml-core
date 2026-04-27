"""API key + tier domain types.

Tiers (post-freemium-rearchitecture, see MIGRATION_NOTES.md):
  - FREE         : legacy/anonymous local CLI. Local builds are unmetered;
                   hosted builds (when /v1/build is called without auth)
                   get the 5-builds-per-day fallback.
  - FREE_SIGNUP  : authenticated free tier (email-only, no payment).
                   30 hosted builds / 30-day rolling window.
  - PRO          : Pro Solo. 500 hosted builds / 30 days. Local unmetered.
  - PRO_TEAM     : Pro Team. 2,500 hosted builds / 30 days. Local unmetered.

Local builds are unmetered on EVERY tier post-rearchitecture — the daily
counter goes away. The legacy `daily_quota` field on APIKey is kept
during the deprecation window but no longer consulted; quota lives in
SQLite (build_events table) and per-tier defaults live in
darml_pro.api.quota_v2.

Auth is opt-in: set DARML_AUTH_ENABLED=true to require keys. When
disabled, all requests are treated as anonymous PRO (compatible with the
local-only default install).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    FREE         = "free"
    FREE_SIGNUP  = "free_signup"
    PRO          = "pro"
    PRO_TEAM     = "pro_team"


# Legacy alias — auth code paths checked is_unlimited. After v2 ships,
# every tier above FREE_SIGNUP is "unlimited local". Hosted limits are
# enforced in quota_v2 against build_events, not via this property.
_UNLIMITED_LOCAL_TIERS = {Tier.PRO, Tier.PRO_TEAM}


@dataclass(frozen=True)
class APIKey:
    key: str            # full secret — opaque to callers, never displayed
    tier: Tier
    label: str = ""     # human-friendly name for ops dashboards
    # Legacy field — only consulted on the pre-v2 metering path. After
    # DARML_METERING_V2=true, the field is ignored and per-tier limits
    # come from quota_v2.quota_for_tier(). Kept on the type for backward
    # compatibility through the deprecation window.
    daily_quota: int = 5

    @property
    def is_unlimited(self) -> bool:
        """Legacy: 'doesn't hit the daily cap'. Post-v2, every paid tier is
        unlimited LOCALLY but capped in the 30-day window for hosted
        builds — that distinction is made in the build endpoint, not
        here."""
        return self.tier in _UNLIMITED_LOCAL_TIERS
