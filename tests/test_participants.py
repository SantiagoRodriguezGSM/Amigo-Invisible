import json

import pytest

from amigo_invisible.errors import ParticipantsError
from amigo_invisible.participants import load_participants


def write(tmp_path, data):
    path = tmp_path / "p.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_loads_valid_file(participants_file):
    loaded = load_participants(participants_file)
    assert len(loaded) == 5
    assert loaded[0].exclude == ("Íñigo Peña",)


def test_missing_file(tmp_path):
    with pytest.raises(ParticipantsError, match="No encuentro"):
        load_participants(tmp_path / "nope.json")


def test_invalid_json(tmp_path):
    path = tmp_path / "p.json"
    path.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ParticipantsError, match="JSON"):
        load_participants(path)


@pytest.mark.parametrize(
    "data, message",
    [
        ([{"name": "A", "email": "a@x.com"}], "al menos 2"),
        ([{"name": "", "email": "a@x.com"}, {"name": "B", "email": "b@x.com"}], "no tiene 'name'"),
        ([{"name": "A", "email": "malo"}, {"name": "B", "email": "b@x.com"}], "no es válido"),
        ([{"name": "A", "email": "a@x.com"}, {"name": "a", "email": "b@x.com"}], "repetidos"),
        (
            [{"name": "A", "email": "a@x.com", "exclude": ["Z"]}, {"name": "B", "email": "b@x.com"}],
            "no existen",
        ),
        ({"name": "A"}, "lista"),
    ],
)
def test_invalid_data(tmp_path, data, message):
    with pytest.raises(ParticipantsError, match=message):
        load_participants(write(tmp_path, data))
