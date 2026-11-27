"""Carga de la configuración desde variables de entorno y un archivo ``.env``.

Las credenciales viven fuera del código: se leen del archivo ``.env`` (que está
en ``.gitignore``) o de variables de entorno reales, que tienen prioridad.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import dotenv_values

from .errors import ConfigError

DEFAULT_ENV_FILE = ".env"


@dataclass(frozen=True)
class Settings:
    """Ajustes de la aplicación."""

    smtp_user: str = ""
    # repr=False evita que la contraseña aparezca en logs o trazas.
    smtp_password: str = field(default="", repr=False)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    sender_name: str = "Amigo Invisible"
    email_subject: str = "Tu asignación del Amigo Invisible"
    budget: str = "20 € – 30 €"
    event_date: str = "Nochebuena"
    event_year: int = field(default_factory=lambda: date.today().year)

    def require_smtp(self) -> None:
        """Comprueba que hay credenciales; se llama solo cuando se van a enviar correos."""
        missing = [
            name for name, value in (("SMTP_USER", self.smtp_user), ("SMTP_PASSWORD", self.smtp_password)) if not value
        ]
        if missing:
            raise ConfigError(
                f"Faltan {' y '.join(missing)} en la configuración. "
                "Copia .env.example a .env y rellénalo (consulta el README)."
            )


def _get(values: Mapping[str, str | None], key: str, default: str) -> str:
    value = (values.get(key) or "").strip()
    return value or default


def load_settings(env_file: str | os.PathLike[str] = DEFAULT_ENV_FILE) -> Settings:
    """Lee ``env_file`` (si existe) y las variables de entorno, que tienen prioridad."""
    path = Path(env_file)
    values: dict[str, str | None] = dict(dotenv_values(path)) if path.is_file() else {}
    values.update(os.environ)

    defaults = Settings()
    try:
        port = int(_get(values, "SMTP_PORT", str(defaults.smtp_port)))
        year = int(_get(values, "EVENT_YEAR", str(defaults.event_year)))
    except ValueError as exc:
        raise ConfigError(f"SMTP_PORT y EVENT_YEAR deben ser números enteros ({exc}).") from exc

    return Settings(
        smtp_user=_get(values, "SMTP_USER", ""),
        smtp_password=(values.get("SMTP_PASSWORD") or "").strip(),
        smtp_host=_get(values, "SMTP_HOST", defaults.smtp_host),
        smtp_port=port,
        sender_name=_get(values, "SENDER_NAME", defaults.sender_name),
        email_subject=_get(values, "EMAIL_SUBJECT", defaults.email_subject),
        budget=_get(values, "EVENT_BUDGET", defaults.budget),
        event_date=_get(values, "EVENT_DATE", defaults.event_date),
        event_year=year,
    )
