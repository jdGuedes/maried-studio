from django.urls import path

from .views import (
    AccountRecoveryChangeQuestionsView,
    AccountRecoveryPasswordResetView,
    AccountRecoveryQuestionsVerifyView,
    AccountRecoveryQuestionsView,
    AccountRecoveryRotateKeyView,
    AccountRecoverySetupView,
    AccountRecoveryStatusView,
    AccountRecoveryVerifyKeyView,
    AuthenticatedPasswordChangeView,
    CurrentUserProfileView,
    CsrfCookieView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
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
        "password/change/",
        AuthenticatedPasswordChangeView.as_view(),
        name="password-change",
    ),

    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),

    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),

    path(
        "recovery/status/",
        AccountRecoveryStatusView.as_view(),
        name="recovery-status",
    ),

    path(
        "recovery/setup/",
        AccountRecoverySetupView.as_view(),
        name="recovery-setup",
    ),

    path(
        "recovery/rotate-key/",
        AccountRecoveryRotateKeyView.as_view(),
        name="recovery-rotate-key",
    ),

    path(
        "recovery/change-questions/",
        AccountRecoveryChangeQuestionsView.as_view(),
        name="recovery-change-questions",
    ),

    path(
        "recovery/verify-key/",
        AccountRecoveryVerifyKeyView.as_view(),
        name="recovery-verify-key",
    ),

    path(
        "recovery/questions/",
        AccountRecoveryQuestionsView.as_view(),
        name="recovery-questions",
    ),

    path(
        "recovery/questions/verify/",
        AccountRecoveryQuestionsVerifyView.as_view(),
        name="recovery-questions-verify",
    ),

    path(
        "recovery/reset-password/",
        AccountRecoveryPasswordResetView.as_view(),
        name="recovery-reset-password",
    ),

    path(
        "me/",
        CurrentUserProfileView.as_view(),
        name="me",
    ),

]
