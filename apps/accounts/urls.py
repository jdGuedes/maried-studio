from django.urls import path

from .views import (
    CurrentUserProfileView,
    CsrfCookieView,
    LoginView,
    LogoutView,
)


app_name = "accounts"


urlpatterns = [
    path(
        "csrf/",
        CsrfCookieView.as_view(),
        name="csrf",
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "me/",
        CurrentUserProfileView.as_view(),
        name="me",
    ),

]
