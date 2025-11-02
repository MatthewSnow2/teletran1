"""Configuration Tests.

Deliverable #6: Settings validation ✅
"""

from chad_config.settings import Settings


def test_settings_load_defaults():
    """Test settings load with defaults."""
    settings = Settings()
    assert settings.API_PORT == 8000
    assert settings.EMBED_INDEX_TYPE == "IVF"


def test_settings_validates_asyncpg():
    """Test DATABASE_URL uses asyncpg driver."""
    settings = Settings()
    assert "asyncpg" in settings.DATABASE_URL
    assert "psycopg2" not in settings.DATABASE_URL
