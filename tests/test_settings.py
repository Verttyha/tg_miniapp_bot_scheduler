from __future__ import annotations

from scheduler_app.settings import Settings


def test_scheduler_interval_defaults_to_five_minutes():
    settings = Settings(_env_file=None)

    assert settings.scheduler_interval_seconds == 300


def test_scheduler_interval_can_be_overridden():
    settings = Settings(_env_file=None, SCHEDULER_INTERVAL_SECONDS=120)

    assert settings.scheduler_interval_seconds == 120
