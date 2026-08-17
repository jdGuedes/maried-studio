from django.urls import path

from .views import (
    ModelReferenceListView,
)


app_name = "ai"


urlpatterns = [
    path(
        "model-references/",
        ModelReferenceListView.as_view(),
        name="model-reference-list",
    ),
]
