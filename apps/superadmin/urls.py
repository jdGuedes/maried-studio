from django.urls import path

from .views import (
    CreditAdjustmentView,
    SuperAdminCreditWalletListView,
    SuperAdminGenerationListView,
    SuperAdminOrganizationListView,
    SuperAdminPlanListView,
    SuperAdminSubscriptionListView,
    SuperAdminSummaryView,
    SuperAdminUserListView,
)


app_name = "superadmin"


urlpatterns = [
    path(
        "summary/",
        SuperAdminSummaryView.as_view(),
        name="summary",
    ),
    path(
        "organizations/",
        SuperAdminOrganizationListView.as_view(),
        name="organizations",
    ),
    path(
        "accounts/",
        SuperAdminUserListView.as_view(),
        name="accounts",
    ),
    path(
        "plans/",
        SuperAdminPlanListView.as_view(),
        name="plans",
    ),
    path(
        "subscriptions/",
        SuperAdminSubscriptionListView.as_view(),
        name="subscriptions",
    ),
    path(
        "credit-wallets/",
        SuperAdminCreditWalletListView.as_view(),
        name="credit-wallets",
    ),
    path(
        "generations/",
        SuperAdminGenerationListView.as_view(),
        name="generations",
    ),
    path(
        "credit-adjustments/",
        CreditAdjustmentView.as_view(),
        name="credit-adjustments",
    ),
]
