from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import AttributeCategory, Brand, VehicleModel, Version
from apps.catalog.serializers import (
    BrandSerializer,
    CatalogAttributesEnvelopeSerializer,
    VehicleModelSerializer,
    VersionSerializer,
)
from apps.common.serializers import ErrorEnvelopeSerializer


class NameCursorPagination(CursorPagination):
    ordering = ("name", "id")


@extend_schema(
    tags=["Catalog"],
    summary="List brands",
    description="Returns all vehicle brands in the catalog. Cursor-paginated.",
    responses={200: BrandSerializer(many=True), 401: ErrorEnvelopeSerializer},
    examples=[
        OpenApiExample(
            "Brand list",
            value={"results": [{"slug": "ford", "name": "Ford"}], "next": None, "previous": None},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class BrandListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BrandSerializer
    pagination_class = NameCursorPagination
    queryset = Brand.objects.all().order_by("name", "id")


@extend_schema(
    tags=["Catalog"],
    summary="List models for a brand",
    description="Returns vehicle models belonging to the given brand slug.",
    responses={
        200: VehicleModelSerializer(many=True),
        401: ErrorEnvelopeSerializer,
        404: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Model list",
            value={
                "results": [{"slug": "ranger", "name": "Ranger", "model_year": "26MY"}],
                "next": None,
                "previous": None,
            },  # noqa: E501
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class VehicleModelListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VehicleModelSerializer
    pagination_class = NameCursorPagination

    def get_queryset(self):
        brand_slug = self.kwargs["brand_slug"].lower()
        brand = get_object_or_404(Brand, slug=brand_slug)
        return VehicleModel.objects.filter(brand=brand).order_by("name", "id")


@extend_schema(
    tags=["Catalog"],
    summary="List versions for a model",
    description="Returns all versions (trims) for the given brand + model combination.",
    responses={
        200: VersionSerializer(many=True),
        401: ErrorEnvelopeSerializer,
        404: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Version list",
            value={
                "results": [
                    {
                        "slug": "xlt_3_0l_v6_at_26my",
                        "name": "XLT 3.0L V6 AT 26MY",
                        "model_year": "26MY",
                    },  # noqa: E501
                    {
                        "slug": "limited_3_0l_v6_26my",
                        "name": "Limited 3.0L V6 26MY",
                        "model_year": "26MY",
                    },  # noqa: E501
                ],
                "next": None,
                "previous": None,
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class VersionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VersionSerializer
    pagination_class = NameCursorPagination

    def get_queryset(self):
        brand_slug = self.kwargs["brand_slug"].lower()
        model_slug = self.kwargs["model_slug"].lower()
        brand = get_object_or_404(Brand, slug=brand_slug)
        vehicle_model = get_object_or_404(VehicleModel, brand=brand, slug=model_slug)
        return Version.objects.filter(model=vehicle_model).order_by("name", "id")


@extend_schema(
    tags=["Catalog"],
    summary="List all attributes grouped by category",
    description="Returns all known attributes. Use `?category=<slug>` to filter by category or `?search=<str>` for substring match.",  # noqa: E501
    parameters=[
        OpenApiParameter(
            name="category", description="Filter by category slug", required=False, type=str
        ),  # noqa: E501
        OpenApiParameter(
            name="search", description="Substring match on key or label", required=False, type=str
        ),  # noqa: E501
    ],
    responses={200: CatalogAttributesEnvelopeSerializer, 401: ErrorEnvelopeSerializer},
    examples=[
        OpenApiExample(
            "Attribute list",
            value={
                "categories": [
                    {
                        "slug": "engine_and_transmission",
                        "name": "Engine & Transmission",
                        "attributes": [
                            {
                                "key": "potencia",
                                "label": "Potência",
                                "value_type": "NUMERIC",
                                "unit": "cv",
                            },  # noqa: E501
                            {
                                "key": "torque",
                                "label": "Torque",
                                "value_type": "NUMERIC",
                                "unit": "Nm",
                            },  # noqa: E501
                        ],
                    }
                ]
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class AttributeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category_filter = request.query_params.get("category", "").lower()
        search_filter = request.query_params.get("search", "").lower()

        categories_qs = AttributeCategory.objects.prefetch_related("attributes").order_by(
            "display_order", "name"
        )
        if category_filter:
            categories_qs = categories_qs.filter(slug=category_filter)

        result = []
        for cat in categories_qs:
            attrs = cat.attributes.all()
            if search_filter:
                attrs = attrs.filter(
                    Q(key__icontains=search_filter) | Q(label__icontains=search_filter)
                )
            if not attrs.exists() and search_filter:
                continue
            result.append({"slug": cat.slug, "name": cat.name, "attributes": list(attrs)})

        serializer = CatalogAttributesEnvelopeSerializer({"categories": result})
        return Response(serializer.data)
