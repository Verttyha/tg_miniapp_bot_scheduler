from __future__ import annotations

from pathlib import Path

from scheduler_app.core.settings import Settings


def test_scheduler_interval_defaults_to_five_minutes():
    settings = Settings(_env_file=None)

    assert settings.scheduler_interval_seconds == 300


def test_scheduler_interval_can_be_overridden():
    settings = Settings(_env_file=None, SCHEDULER_INTERVAL_SECONDS=120)

    assert settings.scheduler_interval_seconds == 120


def test_project_root_points_to_repository_root():
    settings = Settings(_env_file=None)

    assert settings.project_root == Path("C:/TGminiapp")
    assert settings.resolved_sqlite_path == Path("C:/TGminiapp/data/app.db")


def test_frontend_dist_dir_points_to_scheduler_static_app():
    settings = Settings(_env_file=None)

    assert settings.frontend_dist_dir == Path("C:/TGminiapp/apps/server/scheduler_app/static/app")


def test_telegram_proxy_url_can_be_overridden():
    settings = Settings(_env_file=None, TELEGRAM_PROXY_URL="socks5://127.0.0.1:1080")

    assert settings.telegram_proxy_url == "socks5://127.0.0.1:1080"
