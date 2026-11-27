"""Construcción y envío de los correos con el PDF adjunto."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from html import escape
from pathlib import Path
from types import TracebackType

from .config import Settings

SMTP_TIMEOUT = 30
ATTACHMENT_NAME = "amigo-invisible.pdf"  # nombre genérico: no delata nada


def build_message(settings: Settings, to_name: str, to_email: str, pdf_path: str | Path) -> EmailMessage:
    """Crea el correo (texto plano + HTML) con el PDF adjunto."""
    msg = EmailMessage()
    msg["From"] = formataddr((settings.sender_name, settings.smtp_user))
    msg["To"] = formataddr((to_name, to_email))
    msg["Subject"] = settings.email_subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=settings.smtp_user.rpartition("@")[2] or None)

    msg.set_content(
        f"Hola, {to_name}:\n\n"
        "Ya tienes disponible el PDF con la persona a la que te ha tocado hacer el regalo "
        "del Amigo Invisible. Ábrelo desde el archivo adjunto.\n\n"
        f"Presupuesto: {settings.budget}\n"
        f"Entrega: {settings.event_date}\n\n"
        "¡Que tengas unas muy felices fiestas!\n\n"
        "-- \n"
        "Este mensaje ha sido enviado automáticamente por el organizador del Amigo Invisible."
    )

    msg.add_alternative(
        _html_body(escape(to_name), escape(settings.budget), escape(settings.event_date)),
        subtype="html",
    )

    msg.add_attachment(
        Path(pdf_path).read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=ATTACHMENT_NAME,
    )
    return msg


def _html_body(name: str, budget: str, event_date: str) -> str:
    return f"""\
<html>
<body style="font-family: Arial, sans-serif; background-color: #fafafa; padding: 20px;">
  <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 24px;
              border-radius: 8px; border: 1px solid #e5e5e5;">
    <h2 style="text-align: center; color: #b30000; margin: 0 0 14px; font-size: 22px;">
      Tu Amigo Invisible
    </h2>
    <p style="font-size: 15px; color: #333333; line-height: 1.5;">
      Hola, {name}:<br><br>
      Ya tienes disponible el PDF con la persona a la que te ha tocado hacer el regalo
      del Amigo Invisible. Lo encontrarás adjunto a este correo.
    </p>
    <div style="margin: 20px 0; padding: 10px 14px; background: #f7f2ed; border-left: 4px solid #b30000;">
      <p style="margin: 0; font-size: 14px; color: #444; line-height: 1.6;">
        <strong>Presupuesto:</strong> {budget}<br>
        <strong>Entrega:</strong> {event_date}
      </p>
    </div>
    <p style="font-size: 14px; color: #555; line-height: 1.5; text-align: center;">
      ¡Que tengas unas muy felices fiestas!
    </p>
  </div>
  <p style="text-align: center; font-size: 12px; color: #999; margin-top: 20px;">
    Este mensaje ha sido enviado automáticamente por el organizador del Amigo Invisible.
  </p>
</body>
</html>
"""


class Mailer:
    """Conexión SMTP reutilizable; se usa como gestor de contexto.

    El puerto 465 usa SSL directo; cualquier otro (p. ej. 587) usa STARTTLS.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._smtp: smtplib.SMTP | None = None

    def __enter__(self) -> Mailer:
        s = self.settings
        context = ssl.create_default_context()
        if s.smtp_port == 465:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, context=context, timeout=SMTP_TIMEOUT)
        else:
            smtp = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT)
            smtp.starttls(context=context)
        try:
            smtp.login(s.smtp_user, s.smtp_password)
        except Exception:
            smtp.close()
            raise
        self._smtp = smtp
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._smtp is not None:
            try:
                self._smtp.quit()
            except smtplib.SMTPException:
                self._smtp.close()
            self._smtp = None

    def send(self, to_name: str, to_email: str, pdf_path: str | Path) -> None:
        if self._smtp is None:
            raise RuntimeError("Mailer debe usarse dentro de un bloque 'with'.")
        self._smtp.send_message(build_message(self.settings, to_name, to_email, pdf_path))
