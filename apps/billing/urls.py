from django.urls import path

from .views import CurrentSubscriptionView


app_name = "billing"


urlpatterns = [
    path(
        "subscription/",
        CurrentSubscriptionView.as_view(),
        name="current-subscription",
    ),
]

