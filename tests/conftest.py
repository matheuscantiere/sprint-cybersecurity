import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def viewer_user(db):
    from tests.factories import UserFactory

    return UserFactory(role="VIEWER")


@pytest.fixture
def analyst_user(db):
    from tests.factories import UserFactory

    return UserFactory(role="ANALYST")


@pytest.fixture
def admin_user(db):
    from tests.factories import UserFactory

    return UserFactory(role="ADMIN")


@pytest.fixture
def auth_client(api_client, analyst_user):
    token = RefreshToken.for_user(analyst_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def viewer_auth_client(api_client, viewer_user):
    token = RefreshToken.for_user(viewer_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def admin_auth_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def seeded_catalog(db):
    from apps.catalog.models import (
        Attribute,
        AttributeCategory,
        AttributeValue,
        Brand,
        ValueType,
        VehicleModel,
        Version,
    )

    brand = Brand.objects.create(slug="ford", name="Ford")
    model = VehicleModel.objects.create(
        brand=brand, slug="ranger", name="Ranger", model_year="26MY"
    )
    version = Version.objects.create(
        model=model,
        slug="xlt_3_0l_v6_at_26my",
        name="XLT 3.0L V6 AT 26MY",
        model_year="26MY",
    )
    cat_engine = AttributeCategory.objects.create(
        slug="engine_and_transmission", name="Engine & Transmission", display_order=0
    )
    cat_safety = AttributeCategory.objects.create(slug="safety", name="Safety", display_order=1)
    attr_potencia = Attribute.objects.create(
        key="potencia",
        label="Potência",
        value_type=ValueType.NUMERIC,
        unit="cv",
        category=cat_engine,
    )
    attr_airbag = Attribute.objects.create(
        key="airbag_cada",
        label="Airbag (cada)",
        value_type=ValueType.NUMERIC,
        unit="un",
        category=cat_safety,
    )
    attr_tracao = Attribute.objects.create(
        key="tracao_4x4_high_low",
        label="Tração 4x4 (high/low)",
        value_type=ValueType.BOOLEAN,
        unit=None,
        category=cat_engine,
    )
    AttributeValue.objects.create(
        version=version, attribute=attr_potencia, numeric_value=250.0, is_available=True
    )
    AttributeValue.objects.create(
        version=version, attribute=attr_airbag, numeric_value=7.0, is_available=True
    )
    AttributeValue.objects.create(
        version=version, attribute=attr_tracao, boolean_value=True, is_available=True
    )
    return {"brand": brand, "model": model, "version": version}


@pytest.fixture(autouse=True)
def clear_cache(settings):
    from django.core.cache import cache

    # Prod uses a DB-backed cache shared across workers; tests run in one process.
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

    cache.clear()
    yield
    cache.clear()
