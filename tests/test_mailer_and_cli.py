import smtplib
from unittest.mock import MagicMock

import pytest

from amigo_invisible import cli
from amigo_invisible.config import Settings
from amigo_invisible.mailer import ATTACHMENT_NAME, Mailer, build_message
from amigo_invisible.pdf import create_assignment_pdf

SETTINGS = Settings(smtp_user="organizador@example.com", smtp_password="Tr0ub4dor-secreta")


@pytest.fixture
def smtp(monkeypatch):
    """Sustituye la conexión SMTP real por un mock."""
    instance = MagicMock()
    factory = MagicMock(return_value=instance)
    monkeypatch.setattr("amigo_invisible.mailer.smtplib.SMTP_SSL", factory)
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    return instance


def test_build_message(tmp_path):
    pdf = create_assignment_pdf("Raúl", "Ana", tmp_path / "x.pdf", SETTINGS)
    msg = build_message(SETTINGS, "Raúl <&>", "raul@example.com", pdf)

    assert msg["To"].endswith("<raul@example.com>")
    assert "organizador@example.com" in msg["From"]
    assert msg["Subject"] == SETTINGS.email_subject
    assert msg["Message-ID"].endswith("@example.com>")
    assert msg["Date"]
    attachment = next(msg.iter_attachments())
    assert attachment.get_filename() == ATTACHMENT_NAME
    assert attachment.get_content_type() == "application/pdf"
    html = msg.get_body(("html",)).get_content()
    assert "Raúl &lt;&amp;&gt;" in html  # el HTML escapa los nombres
    assert SETTINGS.smtp_password not in msg.as_string()  # la contraseña no viaja en el correo


def test_mailer_logs_in_and_sends(tmp_path, smtp):
    pdf = create_assignment_pdf("A", "B", tmp_path / "x.pdf", SETTINGS)
    with Mailer(SETTINGS) as mailer:
        mailer.send("A", "a@example.com", pdf)
    smtp.login.assert_called_once_with("organizador@example.com", "Tr0ub4dor-secreta")
    smtp.send_message.assert_called_once()
    smtp.quit.assert_called_once()


def test_mailer_requires_context_manager(tmp_path):
    with pytest.raises(RuntimeError):
        Mailer(SETTINGS).send("A", "a@example.com", tmp_path / "x.pdf")


def write_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SMTP_USER=organizador@example.com\nSMTP_PASSWORD=pw-de-prueba\n", encoding="utf-8")
    return env


def test_send_sends_one_email_per_person_and_leaves_no_pdfs(tmp_path, participants_file, smtp):
    out = tmp_path / "pdfs"
    code = cli.main(
        [
            "send",
            "-p",
            str(participants_file),
            "--env-file",
            str(write_env(tmp_path)),
            "-o",
            str(out),
            "--yes",
        ]
    )
    assert code == 0
    assert smtp.send_message.call_count == 5
    recipients = {call.args[0]["To"].split("<")[-1].rstrip(">") for call in smtp.send_message.call_args_list}
    assert recipients == {
        "lucia@example.com",
        "inigo@example.com",
        "raul@example.com",
        "ana@example.com",
        "martin@example.com",
    }
    assert not out.exists()  # privacidad: no se guardan PDF si todo va bien


def test_dry_run_writes_pdfs_and_sends_nothing(tmp_path, participants_file, smtp):
    out = tmp_path / "pdfs"
    # Sin credenciales: en modo de prueba no hacen falta.
    code = cli.main(
        ["send", "--dry-run", "-p", str(participants_file), "--env-file", str(tmp_path / "nada.env"), "-o", str(out)]
    )
    assert code == 0
    assert len(list(out.glob("*.pdf"))) == 5
    smtp.send_message.assert_not_called()


def test_failed_recipient_keeps_only_their_pdf(tmp_path, participants_file, smtp):
    calls = {"n": 0}

    def flaky(msg):
        calls["n"] += 1
        if calls["n"] == 2:
            raise smtplib.SMTPRecipientsRefused({})

    smtp.send_message.side_effect = flaky
    out = tmp_path / "pdfs"
    code = cli.main(
        ["send", "-p", str(participants_file), "--env-file", str(write_env(tmp_path)), "-o", str(out), "--yes"]
    )
    assert code == 1
    assert smtp.send_message.call_count == 5
    assert len(list(out.glob("*.pdf"))) == 1


def test_send_without_credentials_fails_cleanly(tmp_path, participants_file, capsys):
    code = cli.main(["send", "--yes", "-p", str(participants_file), "--env-file", str(tmp_path / "nada.env")])
    assert code == 2
    assert "SMTP_USER" in capsys.readouterr().err


def test_confirmation_can_cancel(tmp_path, participants_file, smtp, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    code = cli.main(["send", "-p", str(participants_file), "--env-file", str(write_env(tmp_path))])
    assert code == 1
    smtp.send_message.assert_not_called()


def test_preview(tmp_path):
    out = tmp_path / "preview.pdf"
    assert cli.main(["preview", "-o", str(out), "--env-file", str(tmp_path / "nada.env")]) == 0
    assert out.read_bytes().startswith(b"%PDF")


def test_slug():
    assert cli._slug("María José Núñez") == "maria_jose_nunez"
    assert cli._slug("???") == "participante"
