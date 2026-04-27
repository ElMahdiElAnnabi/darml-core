"""Core's 5/day file-based rate limiter."""

from __future__ import annotations

from pathlib import Path

import pytest

from darml import free_tier
from darml.domain.exceptions import QuotaExceeded


def test_counter_increments_until_quota(tmp_path, monkeypatch):
    monkeypatch.setattr(free_tier, "is_pro_active", lambda: False)
    counter = tmp_path / "counter"
    for i in range(1, 6):
        usage = free_tier.consume_free_build(counter_path=counter, quota=5)
        assert usage.used == i
        assert usage.remaining == 5 - i
    # 6th call → over quota
    with pytest.raises(QuotaExceeded):
        free_tier.consume_free_build(counter_path=counter, quota=5)


def test_pro_active_bypasses_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(free_tier, "is_pro_active", lambda: True)
    counter = tmp_path / "counter"
    for _ in range(20):
        usage = free_tier.consume_free_build(counter_path=counter, quota=5)
        assert usage.remaining == -1
    # Counter file should remain absent — Pro path doesn't touch it.
    assert not counter.exists()


def test_quota_resets_on_new_day(tmp_path, monkeypatch):
    monkeypatch.setattr(free_tier, "is_pro_active", lambda: False)
    counter = tmp_path / "counter"
    # Pre-write yesterday's count at the cap.
    import json
    counter.parent.mkdir(parents=True, exist_ok=True)
    counter.write_text(json.dumps({"2000-01-01": 999}))
    # Today's call should still succeed because the date key differs.
    usage = free_tier.consume_free_build(counter_path=counter, quota=5)
    assert usage.used == 1


def test_message_changes_at_zero_remaining(tmp_path, monkeypatch):
    monkeypatch.setattr(free_tier, "is_pro_active", lambda: False)
    counter = tmp_path / "counter"
    last = None
    for _ in range(5):
        last = free_tier.consume_free_build(counter_path=counter, quota=5)
    assert last is not None and last.remaining == 0
    assert last.message == ""  # don't nag once they hit the wall
