from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase

from apps.credits.models import CreditWallet
from apps.organizations.models import Organization


class CreditWalletApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Cliente Legado",
            slug="cliente-legado-wallet",
        )
        self.other_organization = Organization.objects.create(
            name="Outro Cliente",
            slug="outro-cliente-wallet",
        )
        self.user = User.objects.create_user(
            email="cliente-legado@example.com",
            password="senha-teste",
            name="Cliente Legado",
            organization=self.organization,
            role="OWNER",
        )
        self.other_wallet = CreditWallet.objects.create(
            organization=self.other_organization,
            plan_balance=100,
            purchased_balance=25,
            balance=125,
        )

    def test_wallet_endpoint_creates_empty_wallet_for_legacy_organization(self):
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/credits/wallet/")

        self.assertEqual(response.status_code, 200)

        wallet = CreditWallet.objects.get(
            organization=self.organization
        )
        self.assertEqual(wallet.plan_balance, 0)
        self.assertEqual(wallet.purchased_balance, 0)
        self.assertEqual(wallet.available_balance, 0)
        self.assertEqual(response.data["available_balance"], 0)

    def test_wallet_endpoint_ignores_arbitrary_organization_id(self):
        wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=3,
            purchased_balance=2,
            plan_reserved_balance=1,
            balance=5,
            reserved_balance=1,
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(
            f"/api/credits/wallet/?organization_id={self.other_organization.pk}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(wallet.pk))
        self.assertNotEqual(
            str(response.data["id"]),
            str(self.other_wallet.pk),
        )
        self.assertEqual(response.data["plan_balance"], 3)
        self.assertEqual(response.data["purchased_balance"], 2)
        self.assertEqual(response.data["reserved_balance"], 1)
        self.assertEqual(response.data["available_plan_balance"], 2)
        self.assertEqual(response.data["available_purchased_balance"], 2)
        self.assertEqual(response.data["available_balance"], 4)
        self.assertEqual(response.data["total_balance"], 5)

    def test_anonymous_user_cannot_access_wallet(self):
        response = self.client.get("/api/credits/wallet/")

        self.assertIn(
            response.status_code,
            [401, 403],
        )
