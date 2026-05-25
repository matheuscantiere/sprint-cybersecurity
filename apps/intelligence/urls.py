from django.urls import path

from apps.intelligence.views import CompareView, InsightsView, LookupView

urlpatterns = [
    path("lookup/", LookupView.as_view(), name="intelligence-lookup"),
    path("compare/", CompareView.as_view(), name="intelligence-compare"),
    path("insights/", InsightsView.as_view(), name="intelligence-insights"),
]
