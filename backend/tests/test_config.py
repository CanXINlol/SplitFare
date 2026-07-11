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


def test_sandbox_mode_is_explicit_and_never_mixes_mock(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_MOCK_SUPPLIER", "false")
    monkeypatch.setenv("DUFFEL_MODE", "sandbox")
    monkeypatch.setenv("DUFFEL_API_TOKEN", "duffel_test_fixture")
    settings = load_settings()
    assert settings.app_mode == "sandbox"
    assert settings.enable_mock_supplier is False
    assert settings.duffel_enabled is True


def test_mock_and_real_supplier_mode_combination_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_MOCK_SUPPLIER", "true")
    monkeypatch.setenv("DUFFEL_MODE", "sandbox")
    with pytest.raises(ValueError, match="must be disabled"):
        load_settings()


def test_no_duffel_credential_still_loads_disabled_mode(monkeypatch) -> None:
    monkeypatch.delenv("DUFFEL_API_TOKEN", raising=False)
    monkeypatch.delenv("DUFFEL_MODE", raising=False)
    settings = load_settings()
    assert settings.duffel_mode == "disabled"
    assert settings.duffel_enabled is False


def test_production_rejects_wildcard_cors(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_ORIGIN", "*")
    with pytest.raises(ValueError, match="cannot contain"):
        load_settings()
