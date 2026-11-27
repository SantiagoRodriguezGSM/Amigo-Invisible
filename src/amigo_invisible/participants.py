"""Lectura y validación del archivo de participantes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import ParticipantsError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Participant:
    """Una persona del sorteo.

    ``exclude`` lista los nombres de personas a las que NO puede tocarle regalar
    (por ejemplo, su pareja). La exclusión es unidireccional: para que ninguno de
    los dos se toque, hay que indicarla en ambas entradas.
    """

    name: str
    email: str
    exclude: tuple[str, ...] = ()


def load_participants(path: str | Path) -> list[Participant]:
    """Carga y valida los participantes desde un archivo JSON."""
    path = Path(path)
    if not path.is_file():
        raise ParticipantsError(
            f"No encuentro el archivo de participantes: {path}. Copia examples/participants.example.json y edítalo."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ParticipantsError(f"{path} no es un JSON válido: {exc}") from exc

    if not isinstance(raw, list):
        raise ParticipantsError(f"{path} debe contener una lista de participantes.")

    participants: list[Participant] = []
    for position, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ParticipantsError(f"El participante #{position} debe ser un objeto JSON.")
        name = str(item.get("name") or "").strip()
        email = str(item.get("email") or "").strip()
        exclude = item.get("exclude") or []
        if not name:
            raise ParticipantsError(f"El participante #{position} no tiene 'name'.")
        if not _EMAIL_RE.match(email):
            raise ParticipantsError(f"El correo de {name!r} no es válido: {email!r}.")
        if not isinstance(exclude, list) or not all(isinstance(e, str) for e in exclude):
            raise ParticipantsError(f"'exclude' de {name!r} debe ser una lista de nombres.")
        participants.append(Participant(name, email, tuple(e.strip() for e in exclude)))

    validate(participants)
    return participants


def validate(participants: list[Participant]) -> None:
    """Reglas que debe cumplir el conjunto de participantes."""
    if len(participants) < 2:
        raise ParticipantsError("Se necesitan al menos 2 participantes.")

    names = [p.name.casefold() for p in participants]
    duplicated = sorted({p.name for p, n in zip(participants, names, strict=True) if names.count(n) > 1})
    if duplicated:
        raise ParticipantsError(f"Hay nombres repetidos: {', '.join(duplicated)}.")

    known = set(names)
    for p in participants:
        unknown = [e for e in p.exclude if e.casefold() not in known]
        if unknown:
            raise ParticipantsError(f"'exclude' de {p.name!r} menciona nombres que no existen: {', '.join(unknown)}.")
