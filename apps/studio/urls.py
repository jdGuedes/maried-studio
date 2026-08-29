from django.urls import path

from .dashboard_views import DashboardView
from .views import (
    GenerationCreateView,
    GenerationDetailView,
    GeneratedImageDeleteView,
    GeneratedImageDownloadView,
    SceneTemplateListView,
)


urlpatterns = [
    path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),

    path(
        "templates/",
        SceneTemplateListView.as_view(),
        name="scene-template-list",
    ),

    path(
        "generations/",
        GenerationCreateView.as_view(),
        name="generation-create",
    ),

    path(
        "generations/<uuid:pk>/",
        GenerationDetailView.as_view(),
        name="generation-detail",
    ),

    path(
        "images/<uuid:pk>/download/",
        GeneratedImageDownloadView.as_view(),
        name="generated-image-download",
    ),

    path(
        "images/<uuid:pk>/",
        GeneratedImageDeleteView.as_view(),
        name="generated-image-delete",
    ),
]
