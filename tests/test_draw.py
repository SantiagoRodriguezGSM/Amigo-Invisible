import random

import pytest

from amigo_invisible.draw import draw_assignments
from amigo_invisible.errors import DrawError
from amigo_invisible.participants import Participant


def test_everyone_gives_and_receives_exactly_once(people):
    for seed in range(200):
        result = draw_assignments(people, rng=random.Random(seed))
        assert sorted(g.name for g, _ in result) == sorted(p.name for p in people)
        assert sorted(r.name for _, r in result) == sorted(p.name for p in people)


def test_nobody_gets_themselves_or_an_excluded_person(people):
    for seed in range(200):
        for giver, receiver in draw_assignments(people, rng=random.Random(seed)):
            assert giver != receiver
            assert receiver.name not in giver.exclude


def test_two_participants_swap():
    a, b = Participant("A", "a@x.com"), Participant("B", "b@x.com")
    result = draw_assignments([a, b], rng=random.Random(1))
    assert [(g.name, r.name) for g, r in result] == [("A", "B"), ("B", "A")]


def test_seeded_rng_is_reproducible(people):
    first = draw_assignments(people, rng=random.Random(7))
    second = draw_assignments(people, rng=random.Random(7))
    assert first == second


def test_impossible_exclusions_raise():
    a = Participant("A", "a@x.com", ("B",))
    b = Participant("B", "b@x.com")
    with pytest.raises(DrawError):
        draw_assignments([a, b])


def test_unsatisfiable_combination_raises():
    # A solo puede dar a C, B solo a C: dos personas no pueden regalar a la misma.
    a = Participant("A", "a@x.com", ("B",))
    b = Participant("B", "b@x.com", ("A",))
    c = Participant("C", "c@x.com")
    with pytest.raises(DrawError):
        draw_assignments([a, b, c], max_attempts=500)
