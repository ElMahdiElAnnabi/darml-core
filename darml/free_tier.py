"""5-builds-per-day file-based rate limiter for Darml Core.

A user-machine-local counter at ``~/.darml/counter`` tracks today's build
count. After the cap, builds are refused with a friendly message that
points to the trial.

This is friction-as-marketing, not DRM. ``rm ~/.darml/counter`` resets it.
That's intentional — we don't want users to feel the free tool is hostile
or trying to spy on them. The Pro upgrade path sells convenience and
support, not bypass-of-counter.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from darml.domain.exceptions import QuotaExceeded
from darml.plugins import is_pro_active

DEFAULT_QUOTA = 5
COUNTER_FILE = Path.home() / ".darml" / "counter"


@dataclass
class FreeTierConsume:
    used: int
    remaining: int
    quota: int

    @property
    def message(self) -> str:
        if self.remaining == 0:
            return ""
        return (
            f"{self.remaining} build{'s' if self.remaining != 1 else ''} "
            f"remaining today (resets at midnight UTC). "
            f"Need unlimited? https://darml.dev/pricing"
        )


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def consume_free_build(
    counter_path: Path = COUNTER_FILE,
    quota: int = DEFAULT_QUOTA,
) -> FreeTierConsume:
    """Charge one build to today's free-tier counter.

    Pro-active installations bypass the limit entirely. Free installs
    that exceed the quota raise QuotaExceeded with the upgrade pointer.

    Concurrency: read-update-write is wrapped in fcntl.flock on POSIX so
    two parallel `darml build` calls can't each see used=4 and both
    increment to 5 (effectively letting 6 builds through a quota of 5).
    On Windows we fall back to no-lock — the underlying threat is local-
    only abuse and the cap exists as a soft signal anyway.
    """
    if is_pro_active():
        return FreeTierConsume(used=0, remaining=-1, quota=-1)

    counter_path.parent.mkdir(parents=True, exist_ok=True)
    today = _today_utc()

    # Open in r+ if exists else w+ to keep an FD we can lock; advisory
    # lock prevents racing readers/writers across processes.
    try:
        import fcntl  # POSIX only
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    f = open(counter_path, "a+", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read()
        try:
            state = json.loads(raw) if raw.strip() else {}
        except Exception:
            state = {}
        used = int(state.get(today, 0))
        if used >= quota:
            raise QuotaExceeded(
                f"Free-tier daily build quota reached ({quota}/day).\n\n"
                f"  → Start a free 14-day Pro trial:  https://darml.dev/trial\n"
                f"  → Or wait until midnight UTC for the counter to reset.\n\n"
                f"To remove this limit entirely, install darml-pro and set your "
                f"license key. See https://darml.dev/pricing"
            )
        new_state = {today: used + 1}  # also drops yesterday's counter
        f.seek(0)
        f.truncate()
        f.write(json.dumps(new_state))
        f.flush()
        return FreeTierConsume(
            used=used + 1, remaining=quota - (used + 1), quota=quota,
        )
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        f.close()
