"""Live OpenAI smoke test — skipped unless RUN_OPENAI_SMOKE=1.

Run:
    docker compose exec -e RUN_OPENAI_SMOKE=1 web pytest tests/smoke/test_openai_live.py -v
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_OPENAI_SMOKE") != "1",
    reason="Set RUN_OPENAI_SMOKE=1 to run live OpenAI tests",
)


@pytest.mark.django_db
def test_insights_live_returns_summary(seeded_catalog, analyst_auth_client):

    from apps.intelligence.services.insights import get_default_client

    client = get_default_client()
    vehicles_data = [
        {
            "version": "xlt_3_0l_v6_at_26my",
            "display_name": "XLT 3.0L V6 AT 26MY",
            "attributes": [{"key": "potencia", "label": "Potência", "value": 250.0, "unit": "cv"}],
        },
        {
            "version": "xlt_3_0l_v6_at_26my_v2",
            "display_name": "XLT 3.0L V6 AT 26MY v2",
            "attributes": [{"key": "potencia", "label": "Potência", "value": 300.0, "unit": "cv"}],
        },
    ]

    result = client.generate(vehicles_data, ["potencia"], focus=None)

    assert isinstance(result.summary, str)
    assert len(result.summary) > 10
    assert result.model == "gpt-4o-mini"
