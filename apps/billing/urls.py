from django.urls import path

from .views import (
    AvailablePlanListView,
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
        "checkout/subscription/",
        SubscriptionCheckoutView.as_view(),
        name="subscription-checkout",
    ),
    path(
        "stripe/webhook/",
        StripeWebhookView.as_view(),
        name="stripe-webhook",
    ),
]
