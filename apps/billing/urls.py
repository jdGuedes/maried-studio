from django.urls import path

from .views import (
    AvailablePlanListView,
    CreditCheckoutView,
    CreditPackageListView,
    CreditPurchaseCancelView,
    CreditPurchaseBySessionView,
    CurrentSubscriptionView,
    StripeWebhookView,
    SubscriptionCheckoutView,
)


app_name = "billing"


urlpatterns = [
    path(
        "plans/",
        AvailablePlanListView.as_view(),
        name="available-plans",
    ),
    path(
        "subscription/",
        CurrentSubscriptionView.as_view(),
        name="current-subscription",
    ),
    path(
        "credit-packages/",
        CreditPackageListView.as_view(),
        name="credit-packages",
    ),
    path(
        "checkout/subscription/",
        SubscriptionCheckoutView.as_view(),
        name="subscription-checkout",
    ),
    path(
        "checkout/credits/",
        CreditCheckoutView.as_view(),
        name="credit-checkout",
    ),
    path(
        "credit-purchases/by-session/<str:session_id>/",
        CreditPurchaseBySessionView.as_view(),
        name="credit-purchase-by-session",
    ),
    path(
        "credit-purchases/<uuid:pk>/cancel/",
        CreditPurchaseCancelView.as_view(),
        name="credit-purchase-cancel",
    ),
    path(
        "stripe/webhook/",
        StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
]
