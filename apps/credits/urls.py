from django.urls import path

from .views import (
    CreditWalletDetailView,
)


app_name = "credits"


urlpatterns = [
    path(
        "wallet/",
        CreditWalletDetailView.as_view(),
        name="wallet-detail",
    ),
]