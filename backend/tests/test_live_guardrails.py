import importlib
import os


def reload_settings(monkeypatch, **overrides):
    env_defaults = {
        "SECRET_KEY": "a" * 32,
        "POSTGRES_PASSWORD": "devpassword",
        "JWT_SECRET": "b" * 32,
        "ADMIN_PASSWORD": "adminpass",
        "ACTIVE_BROKER": "paper",
        "TRADING_MODE": "paper",
        "LIVE_TRADING_ENABLED": "false",
        "PAPER_AUTO_TRADING_ENABLED": "false",
    }
    env_defaults.update(overrides)

    for key in [
        "SECRET_KEY",
        "POSTGRES_PASSWORD",
        "JWT_SECRET",
        "ADMIN_PASSWORD",
        "ACTIVE_BROKER",
        "TRADING_MODE",
        "LIVE_TRADING_ENABLED",
        "PAPER_AUTO_TRADING_ENABLED",
    ]:
        monkeypatch.delenv(key, raising=False)

    for key, value in env_defaults.items():
        monkeypatch.setenv(key, str(value))

    import app.config as config_module
    import app.services.broker as broker_module
    importlib.reload(config_module)
    importlib.reload(broker_module)
    return config_module


def test_default_live_mode_is_blocked(monkeypatch):
    config = reload_settings(monkeypatch)

    assert config.settings.live_trading_enabled is False
    assert config.settings.is_live_trading_allowed is False
    assert config.settings.paper_auto_trading_enabled is False

    from app.services.broker import get_broker

    broker = get_broker()
    assert broker.__class__.__name__ == "PaperBroker"


def test_live_mode_requires_explicit_enablement(monkeypatch):
    config = reload_settings(
        monkeypatch,
        ACTIVE_BROKER="angelone",
        TRADING_MODE="live",
        LIVE_TRADING_ENABLED="true",
    )

    assert config.settings.is_live_trading_allowed is True

    from app.services.broker import get_broker

    broker = get_broker()
    assert broker.__class__.__name__ == "AngelOneBroker"
