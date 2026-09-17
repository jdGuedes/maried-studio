from django.urls import path

from .views import (
    ModelReferenceListView,
    ModelReferencePreviewDownloadView,
)


app_name = "ai"


urlpatterns = [
    path(
        "model-references/",
        ModelReferenceListView.as_view(),
        name="model-reference-list",
    ),
    path(
        "model-references/<uuid:pk>/preview/",
        ModelReferencePreviewDownloadView.as_view(),
        name="model-reference-preview-download",
    ),
]
