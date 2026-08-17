from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.credits.models import CreditTransaction, CreditTransactionType, CreditWallet
from apps.organizations.models import Organization


class SuperAdminApiTests(
    APITestCase
):
    def setUp(
        self,
    ):
        user_model = get_user_model()

        self.organization = (
            Organization.objects.create(
                name="Cliente Teste",
                slug="cliente-teste",
            )
        )

        self.wallet = (
            CreditWallet.objects.create(
                organization=self.organization,
                plan_balance=10,
                purchased_balance=5,
                balance=15,
            )
        )

        self.admin_user = (
            user_model.objects.create_user(
                email="admin@example.com",
                password="senha-teste",
                name="SrGuedes",
                organization=self.organization,
                role="OWNER",
                is_staff=True,
                is_superuser=True,
            )
        )

        self.common_user = (
            user_model.objects.create_user(
                email="cliente@example.com",
                password="senha-teste",
                name="Cliente",
                organization=self.organization,
                role="OWNER",
            )
        )

        self.plan = Plan.objects.create(
            name="Plano Teste",
            slug="plano-teste",
            description="Plano usado em teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=100,
            is_active=True,
            sort_order=10,
        )

        self.subscription = (
            Subscription.objects.create(
                organization=self.organization,
                plan=self.plan,
                status=SubscriptionStatus.ACTIVE,
                price_snapshot=self.plan.price,
                credits_snapshot=(
                    self.plan.credits_per_cycle
                ),
            )
        )

    def test_common_user_cannot_access_superadmin_summary(
        self,
    ):
        self.client.force_authenticate(
            self.common_user
        )

        response = self.client.get(
            reverse(
                "superadmin:summary"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_superadmin_can_access_summary(
        self,
    ):
        self.client.force_authenticate(
            self.admin_user
        )

        response = self.client.get(
            reverse(
                "superadmin:summary"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["organizations"],
            1,
        )

        self.assertEqual(
            response.data["subscriptions"],
            1,
        )

        self.assertEqual(
            response.data["credit_wallets"],
            1,
        )

    def test_superadmin_can_list_core_resources(
        self,
    ):
        self.client.force_authenticate(
            self.admin_user
        )

        route_names = [
            "organizations",
            "accounts",
            "plans",
            "subscriptions",
            "credit-wallets",
            "generations",
        ]

        for route_name in route_names:
            with self.subTest(
                route_name=route_name
            ):
                response = self.client.get(
                    reverse(
                        f"superadmin:{route_name}"
                    )
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )

    def test_superadmin_credit_adjustment_uses_service_and_audit(
        self,
    ):
        self.client.force_authenticate(
            self.admin_user
        )

        response = self.client.post(
            reverse(
                "superadmin:credit-adjustments"
            ),
            {
                "organization_id": str(
                    self.organization.id
                ),
                "amount": 7,
                "balance_type": "PURCHASED",
                "reason": "Ajuste operacional",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.purchased_balance,
            12,
        )

        self.assertEqual(
            self.wallet.balance,
            22,
        )

        transaction = (
            CreditTransaction.objects.get(
                wallet=self.wallet,
                type=(
                    CreditTransactionType
                    .ADJUSTMENT
                ),
            )
        )

        self.assertEqual(
            transaction.actor,
            self.admin_user,
        )

        self.assertEqual(
            transaction.reason,
            "Ajuste operacional",
        )

        self.assertEqual(
            transaction.balance_before,
            15,
        )

        self.assertEqual(
            transaction.balance_after,
            22,
        )

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                user=self.admin_user,
                action=(
                    "SUPERADMIN_CREDIT_ADJUSTMENT"
                ),
            ).exists()
        )

    def test_credit_adjustment_rejects_negative_result(
        self,
    ):
        self.client.force_authenticate(
            self.admin_user
        )

        response = self.client.post(
            reverse(
                "superadmin:credit-adjustments"
            ),
            {
                "organization_id": str(
                    self.organization.id
                ),
                "amount": -6,
                "balance_type": "PURCHASED",
                "reason": "Correção operacional",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.purchased_balance,
            5,
        )
