"""Raptor validation tests — verifies lookup returns correct Raptor 26MY spec values."""

import io
from pathlib import Path

import pytest
from django.core.management import call_command
from rest_framework_simplejwt.tokens import RefreshToken

LOOKUP_URL = "/api/v1/intelligence/lookup/"

CSV_PATH = str(Path(__file__).parent.parent.parent / "data" / "ranger_raptor_26my.csv")

RAPTOR_PAYLOAD_BASE = {
    "brand": "Ford",
    "model": "Ranger",
    "version": "RAPTOR 3.0L V6 BiTurbo 26MY",
}

ALL_ATTRS = [
    "Potência",
    "Torque",
    "Cilindrada",
    "Tecnologia BiTurbo",
    "Transmissão Automática",
    "Quantidade de marchas",
    "Peso em ordem de marchas",
    "Polegadas",
    "Airbag (cada)",
    "Trail Control",
    "Controle de descida",
    "Câmera 360 graus",
    "Tração integral (AWD)",
    "Tração 4x4 (high/low)",
    "Suspensão Off road FOX Live Valve Eixo Frontal/Traseiro",
    "Diferencial traseiro blocante",
    "Terrain Management System (i.e: Modes Auto,Sand,Snow,Mud,Rock)",
    "Freios Brembo (Por Eixo)",
    "Protetor de cárter",
]


@pytest.fixture
def raptor_catalog(db):
    buf = io.StringIO()
    call_command(
        "import_catalog",
        CSV_PATH,
        brand="Ford",
        model="Ranger",
        stdout=buf,
    )


@pytest.fixture
def viewer_auth_client(api_client, db):
    from tests.factories import UserFactory

    user = UserFactory(role="VIEWER")
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


def _attr_map(data):
    return {a["key"]: a for a in data["attributes"]}


@pytest.mark.django_db
class TestRaptorLookupHappyPath:
    def test_returns_200(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ["Potência"]}
        resp = auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 200

    def test_version_identity(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ["Potência"]}
        data = auth_client.post(LOOKUP_URL, payload, format="json").json()
        assert data["vehicle"]["brand"] == "ford"
        assert data["vehicle"]["model"] == "ranger"
        assert "raptor" in data["vehicle"]["version"]

    def test_no_missing_attributes(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ALL_ATTRS}
        data = auth_client.post(LOOKUP_URL, payload, format="json").json()
        assert data["missing_attributes"] == []

    def test_all_attributes_available(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ALL_ATTRS}
        data = auth_client.post(LOOKUP_URL, payload, format="json").json()
        unavailable = [a["key"] for a in data["attributes"] if not a["available"]]
        assert unavailable == []


@pytest.mark.django_db
class TestRaptorNumericAttributes:
    def _attrs(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ALL_ATTRS}
        data = auth_client.post(LOOKUP_URL, payload, format="json").json()
        return _attr_map(data)

    def test_potencia_397cv(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["potencia"]["value"] == 397.0
        assert attrs["potencia"]["unit"] == "cv"

    def test_torque_583nm(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["torque"]["value"] == 583.0
        assert attrs["torque"]["unit"] == "Nm"

    def test_cilindrada_3l(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["cilindrada"]["value"] == 3.0

    def test_quantidade_marchas_10(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["quantidade_de_marchas"]["value"] == 10.0

    def test_peso_em_ordem_de_marchas_2540kg(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["peso_em_ordem_de_marchas"]["value"] == 2540.0
        assert attrs["peso_em_ordem_de_marchas"]["unit"] == "kg"

    def test_polegadas_17(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["polegadas"]["value"] == 17.0

    def test_airbag_cada_8(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["airbag_cada"]["value"] == 8.0


@pytest.mark.django_db
class TestRaptorBooleanAttributes:
    def _attrs(self, auth_client, raptor_catalog):
        payload = {**RAPTOR_PAYLOAD_BASE, "attributes": ALL_ATTRS}
        data = auth_client.post(LOOKUP_URL, payload, format="json").json()
        return _attr_map(data)

    def test_tecnologia_biturbo(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["tecnologia_biturbo"]["value"] is True

    def test_transmissao_automatica(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["transmissao_automatica"]["value"] is True

    def test_trail_control(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["trail_control"]["value"] is True

    def test_controle_de_descida(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["controle_de_descida"]["value"] is True

    def test_camera_360_graus(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["camera_360_graus"]["value"] is True

    def test_tracao_integral_awd(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["tracao_integral_awd"]["value"] is True

    def test_tracao_4x4_high_low(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["tracao_4x4_high_low"]["value"] is True

    def test_suspensao_fox_live_valve(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["suspensao_off_road_fox_live_valve_eixo_frontal_traseiro"]["value"] is True

    def test_diferencial_traseiro_blocante(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["diferencial_traseiro_blocante"]["value"] is True

    def test_terrain_management_system(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["terrain_management_system_i_e_modes_auto_sand_snow_mud_rock"]["value"] is True

    def test_freios_brembo(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["freios_brembo_por_eixo"]["value"] is True

    def test_protetor_de_carter(self, auth_client, raptor_catalog):
        attrs = self._attrs(auth_client, raptor_catalog)
        assert attrs["protetor_de_carter"]["value"] is True
