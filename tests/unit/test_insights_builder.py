from apps.intelligence.services.insights import SYSTEM_PROMPT, InsightsBuilder


def _vehicle(slug, attrs):
    return {"version": slug, "display_name": slug, "attributes": attrs}


def _attr(key, value):
    return {"key": key, "label": key, "value": value, "unit": None}


class TestComputeKeyDifferences:
    def test_all_equal_no_difference(self):
        vehicles = [
            _vehicle("v1", [_attr("potencia", 250.0)]),
            _vehicle("v2", [_attr("potencia", 250.0)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["potencia"])
        assert result == []

    def test_single_winner_boolean(self):
        vehicles = [
            _vehicle("v1", [_attr("tracao", False)]),
            _vehicle("v2", [_attr("tracao", True)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["tracao"])
        assert len(result) == 1
        assert result[0]["winner"] == "v2"

    def test_multi_winner_boolean(self):
        vehicles = [
            _vehicle("v1", [_attr("tracao", True)]),
            _vehicle("v2", [_attr("tracao", False)]),
            _vehicle("v3", [_attr("tracao", True)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["tracao"])
        assert len(result) == 1
        assert set(result[0]["winner"]) == {"v1", "v3"}

    def test_numeric_higher_is_better(self):
        vehicles = [
            _vehicle("v1", [_attr("potencia", 200.0)]),
            _vehicle("v2", [_attr("potencia", 300.0)]),
            _vehicle("v3", [_attr("potencia", 250.0)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["potencia"])
        assert result[0]["winner"] == "v2"

    def test_numeric_lower_is_better(self):
        vehicles = [
            _vehicle("v1", [_attr("peso_em_ordem_de_marchas", 2200.0)]),
            _vehicle("v2", [_attr("peso_em_ordem_de_marchas", 1900.0)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["peso_em_ordem_de_marchas"])
        assert result[0]["winner"] == "v2"

    def test_neutral_numeric_no_winner(self):
        vehicles = [
            _vehicle("v1", [_attr("comprimento", 5200.0)]),
            _vehicle("v2", [_attr("comprimento", 4900.0)]),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["comprimento"])
        assert len(result) == 1
        assert "winner" not in result[0]

    def test_missing_value_excluded_from_winner(self):
        vehicles = [
            _vehicle("v1", [_attr("potencia", 300.0)]),
            _vehicle("v2", []),  # no potencia value
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["potencia"])
        # Only v1 has a value, but all present values are equal in set → still reported
        assert result[0]["winner"] == "v1"

    def test_empty_if_all_missing(self):
        vehicles = [
            _vehicle("v1", []),
            _vehicle("v2", []),
        ]
        result = InsightsBuilder().compute_key_differences(vehicles, ["potencia"])
        assert result == []


class TestBuildPrompt:
    def test_system_prompt_is_constant(self):
        b = InsightsBuilder()
        sys1, _ = b.build_prompt([], [], None)
        sys2, _ = b.build_prompt([_vehicle("v1", [])], ["potencia"], "premium")
        assert sys1 == sys2 == SYSTEM_PROMPT

    def test_user_prompt_contains_vehicle_slugs(self):
        vehicles = [_vehicle("xlt", [_attr("potencia", 250.0)])]
        _, user = InsightsBuilder().build_prompt(vehicles, ["potencia"], None)
        assert "xlt" in user

    def test_user_prompt_contains_attribute_key(self):
        vehicles = [_vehicle("v1", [_attr("potencia", 250.0)])]
        _, user = InsightsBuilder().build_prompt(vehicles, ["potencia"], None)
        assert "potencia" in user

    def test_user_prompt_contains_focus(self):
        vehicles = [_vehicle("v1", [_attr("potencia", 250.0)])]
        _, user = InsightsBuilder().build_prompt(vehicles, ["potencia"], "off-road")
        assert "off-road" in user

    def test_user_prompt_defaults_when_no_focus(self):
        vehicles = [_vehicle("v1", [])]
        _, user = InsightsBuilder().build_prompt(vehicles, [], None)
        assert "general comparison" in user
