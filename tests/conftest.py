import json

import pytest

from amigo_invisible.participants import Participant


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Evita que variables reales del entorno contaminen los tests."""
    for key in (
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_HOST",
        "SMTP_PORT",
        "SENDER_NAME",
        "EMAIL_SUBJECT",
        "EVENT_BUDGET",
        "EVENT_DATE",
        "EVENT_YEAR",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def people():
    return [
        Participant("Lucía Muñoz", "lucia@example.com", ("Íñigo Peña",)),
        Participant("Íñigo Peña", "inigo@example.com", ("Lucía Muñoz",)),
        Participant("Raúl Núñez", "raul@example.com"),
        Participant("Ana Belén", "ana@example.com"),
        Participant("Martín", "martin@example.com"),
    ]


@pytest.fixture
def participants_file(tmp_path, people):
    path = tmp_path / "participants.json"
    data = [{"name": p.name, "email": p.email, "exclude": list(p.exclude)} for p in people]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path
