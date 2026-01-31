from app.core.config import settings

def test_settings_loaded():
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000
    assert settings.SECRET_KEY

def test_database_url():
    assert "sqlite" in settings.DATABASE_URL
