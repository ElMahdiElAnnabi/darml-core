"""API key + tier domain types.

Tiers:
  - FREE  : 5 builds per UTC-day, hard cap.
  - PRO   : unlimited builds.

Auth is opt-in: set DARML_AUTH_ENABLED=true to require keys. When disabled,
all requests are treated as anonymous PRO (compatible with the local-only
default install).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"


@dataclass(frozen=True)
class APIKey:
    key: str            # full secret — opaque to callers, never displayed
    tier: Tier
    label: str = ""     # human-friendly name for ops dashboards
    daily_quota: int = 5  # only consulted for FREE tier; PRO is unlimited

    @property
    def is_unlimited(self) -> bool:
        return self.tier == Tier.PRO
