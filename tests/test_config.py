import pytest

from amigo_invisible.config import Settings, load_settings
from amigo_invisible.errors import ConfigError


def test_reads_credentials_from_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SMTP_USER=yo@example.com\nSMTP_PASSWORD=abcd efgh\nEVENT_BUDGET=10 €\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.smtp_user == "yo@example.com"
    assert settings.smtp_password == "abcd efgh"
    assert settings.budget == "10 €"
    settings.require_smtp()


def test_real_environment_overrides_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SMTP_USER=file@example.com\n", encoding="utf-8")
    monkeypatch.setenv("SMTP_USER", "env@example.com")
    assert load_settings(env).smtp_user == "env@example.com"


def test_defaults_and_blank_values(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SMTP_PORT=\nEVENT_DATE=\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.smtp_port == 465
    assert settings.event_date == "Nochebuena"


def test_missing_file_is_fine_until_sending(tmp_path):
    settings = load_settings(tmp_path / "no-existe.env")
    with pytest.raises(ConfigError, match="SMTP_USER y SMTP_PASSWORD"):
        settings.require_smtp()


def test_invalid_port(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SMTP_PORT=abc\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(env)


def test_password_is_not_in_repr():
    assert "secreto123" not in repr(Settings(smtp_user="a@b.com", smtp_password="secreto123"))
