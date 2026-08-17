from django.urls import path

from .views import (
    CurrentUserProfileView,
)


app_name = "accounts"


urlpatterns = [
    path(
        "me/",
        CurrentUserProfileView.as_view(),
        name="me",
    ),
]