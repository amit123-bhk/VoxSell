"""
Unit tests for configuration validation and settings loading.
"""

from app.config import Settings, get_settings


def test_settings_defaults():
    """
    Assert default settings load with expected standard values.
    """
    settings = get_settings()
    assert settings.APP_NAME == "VoxSell"
    assert settings.APP_PORT == 8000
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "postgresql" in settings.DATABASE_URL
    assert "redis" in settings.REDIS_URL
