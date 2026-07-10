import pytest

from app.config import load_settings


def test_production_defaults_to_live_without_silent_mock_fallback(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENABLE_MOCK_SUPPLIER", raising=False)
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    settings = load_settings()
    assert settings.enable_mock_supplier is False
    assert settings.app_mode == "live"
    assert settings.frontend_origins == ()


def test_production_demo_requires_explicit_mock_enablement(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_MOCK_SUPPLIER", "true")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://splitfare.test")
    settings = load_settings()
    assert settings.enable_mock_supplier is True
    assert settings.is_demo is True
    assert settings.frontend_origins == ("https://splitfare.test",)


def test_production_rejects_wildcard_cors(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")
    with pytest.raises(ValueError, match="cannot contain"):
        load_settings()
