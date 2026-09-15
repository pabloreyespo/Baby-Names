import pytest

from app.fonetica import key

SAME = [
    ["Christopher", "Cristofer", "Khristopher", "Cristopher", "Kristofer", "Christofer"],
    ["Alexander", "Aleksander", "Alexsander", "Alecsander"],
    ["Ximena", "Jimena", "Gimena"],
    ["Katherine", "Catherine", "Katerine", "Caterine"],
    ["Rebeca", "Rebecca", "Rebeka"],
    ["Jhon", "John", "Jon"],
    ["Bryan", "Brian"],
    ["Yasna", "Llasna"],
    ["Vanessa", "Banesa", "Vanesa"],
    ["Guillermo", "Guiyermo"],
    ["Christian", "Cristian", "Kristian"],
    ["María", "Maria"],
]

DIFFERENT = [("Christopher", "Cristobal"), ("Ximena", "Ximeno"), ("Brayan", "Brian"), ("Gerardo", "Guerardo"), ("Nicole", "Nicol")]


@pytest.mark.parametrize("group", SAME)
def test_same_sound_same_key(group):
    keys = {key(n) for n in group}
    assert len(keys) == 1, keys


@pytest.mark.parametrize("a,b", DIFFERENT)
def test_different_sound_different_key(a, b):
    assert key(a) != key(b)


def test_specific_keys():
    assert key("Christopher") == "kristofer"
    assert key("Alexander") == "aleksander"
    assert key("Ximena") == "jimena"
    assert key("Miguel") == "migel"
    assert key("Chantal") == "chantal"
    assert key("O'Higgins") == "oijins"
