from apps.common.utils import slugify_attribute


def test_potencia():
    assert slugify_attribute("Potência") == "potencia"


def test_teto_solar_eletrico():
    assert slugify_attribute("Teto Solar Elétrico") == "teto_solar_eletrico"


def test_engine_and_transmission():
    assert slugify_attribute("Engine & Transmission") == "engine_and_transmission"


def test_ar_condicionado():
    assert slugify_attribute("Ar Condicionado de duas zonas") == "ar_condicionado_de_duas_zonas"


def test_already_lowercase_no_accents():
    assert slugify_attribute("safety") == "safety"


def test_numeric_label():
    assert slugify_attribute("4X4") == "4x4"


def test_parentheses_stripped():
    assert slugify_attribute("Airbag (cada)") == "airbag_cada"


def test_truncation():
    long_value = "a" * 120
    assert len(slugify_attribute(long_value)) == 100


def test_leading_trailing_underscores_stripped():
    assert not slugify_attribute("  Potência  ").startswith("_")
    assert not slugify_attribute("  Potência  ").endswith("_")
