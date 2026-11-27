"""Sorteo: asigna a cada participante a quién le toca regalar."""

from __future__ import annotations

import random

from .errors import DrawError
from .participants import Participant

MAX_ATTEMPTS = 100_000


def draw_assignments(
    participants: list[Participant],
    rng: random.Random | None = None,
    max_attempts: int = MAX_ATTEMPTS,
) -> list[tuple[Participant, Participant]]:
    """Devuelve una lista de pares ``(quien_regala, quien_recibe)``.

    Nadie se toca a sí mismo ni a las personas de su lista ``exclude``. Se baraja
    hasta dar con una permutación válida, lo que da un resultado uniforme entre
    todos los sorteos posibles. Por defecto usa ``random.SystemRandom`` (fuente de
    aleatoriedad del sistema operativo), así que el resultado no es predecible.
    """
    rng = rng or random.SystemRandom()
    n = len(participants)
    index_by_name = {p.name.casefold(): i for i, p in enumerate(participants)}

    forbidden: list[set[int]] = []
    for i, p in enumerate(participants):
        banned = {i} | {index_by_name[e.casefold()] for e in p.exclude}
        if len(banned) == n:
            raise DrawError(f"{p.name} no podría regalar a nadie con las exclusiones indicadas.")
        forbidden.append(banned)

    receivers = list(range(n))
    for _ in range(max_attempts):
        rng.shuffle(receivers)
        if all(receivers[i] not in forbidden[i] for i in range(n)):
            return [(participants[i], participants[receivers[i]]) for i in range(n)]

    raise DrawError(
        "No he encontrado ningún sorteo válido. Revisa las exclusiones: puede que sean demasiado restrictivas."
    )
