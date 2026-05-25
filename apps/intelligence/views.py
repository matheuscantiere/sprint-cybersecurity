from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import _get_request_id
from apps.common.permissions import HasRole
from apps.common.serializers import ErrorEnvelopeSerializer
from apps.intelligence.models import InsightsUsage
from apps.intelligence.serializers import (
    CompareRequestSerializer,
    CompareResponseSerializer,
    InsightsRequestSerializer,
    InsightsResponseSerializer,
    LookupRequestSerializer,
    LookupResponseSerializer,
)
from apps.intelligence.services.compare import ComparisonBuilder
from apps.intelligence.services.insights import (
    InsightsBuilder,
    InsightsFeatureDisabledError,
    InsightsUpstreamError,
    get_default_client,
)
from apps.intelligence.services.lookup import (
    StandardizedResponseBuilder,
    VehicleResolver,
)


@extend_schema(
    tags=["Intelligence"],
    summary="Lookup vehicle attributes",
    description=(
        "Returns standardized attribute values for a single vehicle version. "
        "Unknown attributes appear in `missing_attributes`. Order of `attributes` is preserved."
    ),
    request=LookupRequestSerializer,
    responses={
        200: LookupResponseSerializer,
        400: ErrorEnvelopeSerializer,
        401: ErrorEnvelopeSerializer,
        404: ErrorEnvelopeSerializer,
        429: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Ranger Limited — request",
            value={
                "brand": "Ford",
                "model": "Ranger",
                "version": "Limited 3.0L V6 26MY",
                "attributes": ["Potência", "Torque", "Airbag (cada)", "Câmera 360 graus"],
            },
            request_only=True,
        ),
        OpenApiExample(
            "Ranger Limited — success",
            value={
                "vehicle": {
                    "brand": "ford",
                    "model": "ranger",
                    "version": "limited_3_0l_v6_26my",
                    "display_name": "Limited 3.0L V6 26MY",
                    "model_year": "26MY",
                },
                "requested_at": "2026-05-21T14:00:00Z",
                "request_id": "8a7c9f12",
                "attributes": [
                    {
                        "key": "potencia",
                        "label": "Potência",
                        "category": "engine_and_transmission",
                        "value_type": "NUMERIC",
                        "value": 250,
                        "unit": "cv",
                        "available": True,
                    },  # noqa: E501
                    {
                        "key": "torque",
                        "label": "Torque",
                        "category": "engine_and_transmission",
                        "value_type": "NUMERIC",
                        "value": 600,
                        "unit": "Nm",
                        "available": True,
                    },  # noqa: E501
                    {
                        "key": "airbag_cada",
                        "label": "Airbag (cada)",
                        "category": "safety",
                        "value_type": "NUMERIC",
                        "value": 7,
                        "unit": "un",
                        "available": True,
                    },  # noqa: E501
                    {
                        "key": "camera_360_graus",
                        "label": "Câmera 360 graus",
                        "category": "high_tech",
                        "value_type": "BOOLEAN",
                        "value": False,
                        "unit": None,
                        "available": False,
                    },  # noqa: E501
                ],
                "missing_attributes": [],
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Brand not found — 404",
            value={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Brand 'toyota' not found.",
                    "details": {"resource": "brand"},
                },
                "request_id": "abc123",
            },  # noqa: E501
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
class LookupView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "lookup"

    def post(self, request):
        serializer = LookupRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        version = VehicleResolver().resolve(
            brand_slug=data["brand"],
            model_slug=data["model"],
            version_slug=data["version"],
        )

        result = StandardizedResponseBuilder().build(version, data["attributes"])
        result["request_id"] = _get_request_id(request)

        return Response(result)


@extend_schema(
    tags=["Intelligence"],
    summary="Compare multiple vehicle versions",
    description=(
        "Side-by-side attribute matrix for 2–5 vehicle versions. "
        "The `values` array index matches the `vehicles` array index."
    ),
    request=CompareRequestSerializer,
    responses={
        200: CompareResponseSerializer,
        400: ErrorEnvelopeSerializer,
        401: ErrorEnvelopeSerializer,
        404: ErrorEnvelopeSerializer,
        429: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "XLT vs Limited vs Limited+ — request",
            value={
                "vehicles": [
                    {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                    {"brand": "Ford", "model": "Ranger", "version": "Limited 3.0L V6 26MY"},
                    {"brand": "Ford", "model": "Ranger", "version": "Limited + 3.0L V6 26MY"},
                ],
                "attributes": ["Potência", "Torque", "Câmera 360 graus"],
            },
            request_only=True,
        ),
        OpenApiExample(
            "Compare — success",
            value={
                "vehicles": [
                    {
                        "brand": "ford",
                        "model": "ranger",
                        "version": "xlt_3_0l_v6_at_26my",
                        "display_name": "XLT 3.0L V6 AT 26MY",
                        "model_year": "26MY",
                    },  # noqa: E501
                    {
                        "brand": "ford",
                        "model": "ranger",
                        "version": "limited_3_0l_v6_26my",
                        "display_name": "Limited 3.0L V6 26MY",
                        "model_year": "26MY",
                    },  # noqa: E501
                ],
                "requested_at": "2026-05-21T14:00:00Z",
                "request_id": "8a7c9f12",
                "matrix": [
                    {
                        "attribute": {
                            "key": "potencia",
                            "label": "Potência",
                            "unit": "cv",
                            "value_type": "NUMERIC",
                        },
                        "values": [250, 250],
                    },  # noqa: E501
                    {
                        "attribute": {
                            "key": "camera_360_graus",
                            "label": "Câmera 360 graus",
                            "unit": None,
                            "value_type": "BOOLEAN",
                        },
                        "values": [False, True],
                    },  # noqa: E501
                ],
                "missing_attributes": [],
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class CompareView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "compare"

    def post(self, request):
        serializer = CompareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = ComparisonBuilder().build(data["vehicles"], data["attributes"])
        result["request_id"] = _get_request_id(request)

        return Response(result)


@extend_schema(
    tags=["Intelligence"],
    summary="AI-generated competitive insights",
    description=(
        "Generates an AI narrative comparing 2–5 vehicle versions using GPT-4o-mini. "
        "Requires ANALYST or ADMIN role. Subject to a daily request cap."
    ),
    request=InsightsRequestSerializer,
    responses={
        200: InsightsResponseSerializer,
        400: ErrorEnvelopeSerializer,
        401: ErrorEnvelopeSerializer,
        403: ErrorEnvelopeSerializer,
        429: ErrorEnvelopeSerializer,
        502: ErrorEnvelopeSerializer,
        503: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "XLT vs Limited+ — request",
            value={
                "vehicles": [
                    {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                    {"brand": "Ford", "model": "Ranger", "version": "Limited + 3.0L V6 26MY"},
                ],
                "attributes": ["Potência", "Torque", "Câmera 360 graus", "Polegadas"],
                "focus": "premium-experience",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Insights — success",
            value={
                "summary": "Both Ranger versions share the same 250 cv drivetrain. The Limited+ adds 360° camera and 20-inch wheels, justifying the premium positioning.",  # noqa: E501
                "key_differences": [
                    {
                        "attribute": "camera_360_graus",
                        "winner": "limited_plus_3_0l_v6_26my",
                        "values": {"xlt_3_0l_v6_at_26my": False, "limited_plus_3_0l_v6_26my": True},
                    },  # noqa: E501
                    {
                        "attribute": "polegadas",
                        "winner": "limited_plus_3_0l_v6_26my",
                        "values": {"xlt_3_0l_v6_at_26my": 17, "limited_plus_3_0l_v6_26my": 20},
                    },  # noqa: E501
                ],
                "model": "gpt-4o-mini",
                "generated_at": "2026-05-21T14:00:00Z",
                "request_id": "8a7c9f12",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "AI unavailable — 502",
            value={
                "error": {
                    "code": "UPSTREAM_UNAVAILABLE",
                    "message": "AI model is temporarily unavailable.",
                    "details": {},
                },
                "request_id": "abc123",
            },  # noqa: E501
            response_only=True,
            status_codes=["502"],
        ),
    ],
)
class InsightsView(APIView):
    permission_classes = [IsAuthenticated, HasRole.of("ANALYST", "ADMIN")]
    throttle_scope = "insights"

    def post(self, request):
        serializer = InsightsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cap = getattr(settings, "INSIGHTS_DAILY_CAP", 1000)
        if not InsightsUsage.increment_and_check(cap):
            return Response(
                {
                    "error": {
                        "code": "FEATURE_DISABLED",
                        "message": "Daily insights cap reached. Try again tomorrow.",
                        "details": {},
                    },
                    "request_id": _get_request_id(request),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        compare_result = ComparisonBuilder().build(data["vehicles"], data["attributes"])
        vehicles_data = _build_vehicles_for_prompt(compare_result)
        attr_keys = data["attributes"]
        focus = data.get("focus") or None

        key_differences = InsightsBuilder().compute_key_differences(vehicles_data, attr_keys)

        try:
            client = get_default_client()
        except InsightsFeatureDisabledError:
            return Response(
                {
                    "error": {
                        "code": "FEATURE_DISABLED",
                        "message": "AI insights feature is not configured.",
                        "details": {},
                    },
                    "request_id": _get_request_id(request),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = client.generate(vehicles_data, attr_keys, focus)
        except InsightsUpstreamError:
            return Response(
                {
                    "error": {
                        "code": "UPSTREAM_UNAVAILABLE",
                        "message": "AI model is temporarily unavailable.",
                        "details": {},
                    },
                    "request_id": _get_request_id(request),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "summary": result.summary,
                "key_differences": key_differences,
                "model": result.model,
                "generated_at": result.generated_at,
                "request_id": _get_request_id(request),
            }
        )


def _build_vehicles_for_prompt(compare_result: dict) -> list[dict]:
    vehicles = compare_result["vehicles"]
    matrix = compare_result["matrix"]
    result = []
    for i, v in enumerate(vehicles):
        attrs = []
        for row in matrix:
            attrs.append(
                {
                    "key": row["attribute"]["key"],
                    "label": row["attribute"]["label"],
                    "value": row["values"][i],
                    "unit": row["attribute"]["unit"],
                }
            )
        result.append(
            {
                "version": v["version"],
                "display_name": v["display_name"],
                "attributes": attrs,
            }
        )
    return result
