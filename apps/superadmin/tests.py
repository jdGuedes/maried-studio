from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.audit.models import AuditLog
from apps.billing.services import BillingError
from apps.billing.models import (
    BillingCycle,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from apps.credits.models import (
    CreditTransaction,
    CreditTransactionType,
    CreditWallet,
)
from apps.organizations.models import Organization
from apps.products.models import Product, ProductCategory
from apps.studio.models import (
    Generation,
    GenerationMode,
    GenerationRule,
    GenerationStatus,
    SceneTemplate,
)


class SuperAdminApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Cliente Teste",
            slug="cliente-teste-superadmin",
        )

        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=10,
            purchased_balance=5,
            balance=15,
        )

        self.superadmin = User.objects.create_user(
            email="superadmin@example.com",
            password="senha-teste",
            name="SuperAdmin",
            organization=None,
            is_staff=True,
            is_superuser=True,
        )

        self.common_user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-teste",
            name="Cliente",
            organization=self.organization,
            role="OWNER",
        )

        self.plan = Plan.objects.create(
            name="Plano Teste",
            slug="plano-teste-superadmin",
            description="Plano usado em teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=100,
            is_active=True,
            sort_order=10,
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
        )

        self.product = Product.objects.create(
            organization=self.organization,
            created_by=self.common_user,
            name="Produto SuperAdmin",
            category=ProductCategory.EARRING,
        )

        self.rule = GenerationRule.objects.create(
            category=ProductCategory.EARRING,
            generation_mode=GenerationMode.STILL,
            framing="PRODUCT",
            body_area="",
            placement_instruction="",
        )

        self.generation = Generation.objects.create(
            organization=self.organization,
            user=self.common_user,
            product=self.product,
            mode=GenerationMode.STILL,
            generation_rule=self.rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="superadmin-generation-test",
            credit_cost=1,
        )

    def auth_superadmin(self):
        self.client.force_authenticate(self.superadmin)

    def _client_payload(self, **overrides):
        payload = {
            "name": "Cliente Operacional",
            "email": "cliente-operacional@example.com",
            "initial_password": "senha-inicial-segura",
            "plan_id": str(self.plan.pk),
        }
        payload.update(overrides)
        return payload

    def test_common_user_cannot_access_superadmin(self):
        self.client.force_authenticate(self.common_user)
        response = self.client.get(reverse("superadmin:summary"))
        self.assertEqual(response.status_code, 403)

    def test_common_user_cannot_create_client(self):
        self.client.force_authenticate(self.common_user)

        response = self.client.post(
            reverse("superadmin:clients"),
            self._client_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_without_superuser_cannot_create_client(self):
        User = get_user_model()
        staff_user = User.objects.create_user(
            email="staff@example.com",
            password="senha-teste",
            name="Staff",
            organization=None,
            is_staff=True,
            is_superuser=False,
        )

        self.client.force_authenticate(staff_user)

        response = self.client.post(
            reverse("superadmin:clients"),
            self._client_payload(
                email="cliente-staff@example.com",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_superadmin_without_organization_can_access_summary(self):
        self.assertIsNone(self.superadmin.organization)
        self.auth_superadmin()

        response = self.client.get(reverse("superadmin:summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["organizations"], 1)
        self.assertEqual(response.data["subscriptions"], 1)
        self.assertEqual(response.data["credit_wallets"], 1)
        self.assertIn(
            "operational_active_subscriptions",
            response.data,
        )
        self.assertIn(
            "operational_grace_subscriptions",
            response.data,
        )
        self.assertIn(
            "operational_blocked_subscriptions",
            response.data,
        )

    def test_superadmin_can_list_audit_logs_read_only(self):
        AuditLog.objects.create(
            organization=self.organization,
            user=self.superadmin,
            action="SUPERADMIN_TEST_ACTION",
            entity_type="Organization",
            entity_id=str(self.organization.pk),
            metadata={
                "reason": "Teste",
            },
        )
        self.auth_superadmin()

        response = self.client.get(
            reverse("superadmin:audit-logs")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        item = response.data["results"][0]
        self.assertEqual(item["action"], "SUPERADMIN_TEST_ACTION")
        self.assertEqual(item["organization_name"], self.organization.name)
        self.assertEqual(item["metadata"]["reason"], "Teste")

    def test_common_user_cannot_list_audit_logs(self):
        self.client.force_authenticate(self.common_user)

        response = self.client.get(
            reverse("superadmin:audit-logs")
        )

        self.assertEqual(response.status_code, 403)

    def test_superadmin_can_create_complete_client_with_active_plan(self):
        self.auth_superadmin()

        plan = Plan.objects.create(
            name="Plano Cliente V1",
            slug="plano-cliente-v1",
            description="Plano operacional.",
            price=Decimal("199.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        response = self.client.post(
            reverse("superadmin:clients"),
            self._client_payload(
                plan_id=str(plan.pk),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        organization = Organization.objects.get(
            name="Cliente Operacional"
        )
        user = organization.users.get()
        wallet = organization.credit_wallet
        subscription = organization.subscription

        self.assertEqual(user.email, "cliente-operacional@example.com")
        self.assertEqual(user.role, "OWNER")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("senha-inicial-segura"))
        self.assertNotEqual(user.password, "senha-inicial-segura")

        self.assertEqual(wallet.plan_balance, 50)
        self.assertEqual(wallet.purchased_balance, 0)
        self.assertEqual(wallet.available_balance, 50)

        self.assertEqual(subscription.plan, plan)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.credits_snapshot, 50)
        self.assertIsNotNone(subscription.current_period_start)
        self.assertIsNotNone(subscription.current_period_end)

        self.assertEqual(response.data["user"]["email"], user.email)
        self.assertEqual(response.data["wallet"]["available_balance"], 50)
        self.assertEqual(
            response.data["subscription"]["operational_status"],
            "ACTIVE",
        )

        self.assertTrue(
            CreditTransaction.objects.filter(
                wallet=wallet,
                type=CreditTransactionType.PLAN_GRANT,
                actor=self.superadmin,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                organization=organization,
                user=self.superadmin,
                action="SUPERADMIN_CLIENT_CREATED",
            ).exists()
        )

    def test_client_creation_rejects_duplicate_email_without_orphan_org(self):
        self.auth_superadmin()

        organization_count = Organization.objects.count()
        user_count = get_user_model().objects.count()

        response = self.client.post(
            reverse("superadmin:clients"),
            self._client_payload(
                email=self.common_user.email,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Organization.objects.count(), organization_count)
        self.assertEqual(get_user_model().objects.count(), user_count)

    def test_client_creation_rejects_inactive_plan_without_partial_client(self):
        self.auth_superadmin()

        inactive_plan = Plan.objects.create(
            name="Plano Inativo V1",
            slug="plano-inativo-v1",
            description="Plano inativo.",
            price=Decimal("49.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=25,
            is_active=False,
        )
        organization_count = Organization.objects.count()
        user_count = get_user_model().objects.count()

        response = self.client.post(
            reverse("superadmin:clients"),
            self._client_payload(
                email="plano-inativo@example.com",
                plan_id=str(inactive_plan.pk),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Organization.objects.count(), organization_count)
        self.assertEqual(get_user_model().objects.count(), user_count)

    def test_client_creation_rolls_back_subscription_activation_failure(self):
        self.auth_superadmin()

        organization_count = Organization.objects.count()
        user_count = get_user_model().objects.count()

        with patch(
            "apps.superadmin.views.SubscriptionService.activate",
            side_effect=BillingError("Falha operacional."),
        ):
            response = self.client.post(
                reverse("superadmin:clients"),
                self._client_payload(
                    email="rollback@example.com",
                ),
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Organization.objects.count(), organization_count)
        self.assertEqual(get_user_model().objects.count(), user_count)

    def test_superadmin_can_read_client_detail_with_operational_data(self):
        self.auth_superadmin()

        now = timezone.now()
        self.subscription.current_period_start = now
        self.subscription.current_period_end = (
            now + timezone.timedelta(days=30)
        )
        self.subscription.next_billing_at = (
            now + timezone.timedelta(days=30)
        )
        self.subscription.save(
            update_fields=[
                "current_period_start",
                "current_period_end",
                "next_billing_at",
                "updated_at",
            ]
        )

        response = self.client.get(
            reverse(
                "superadmin:client-detail",
                kwargs={"pk": self.organization.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], self.common_user.email)
        self.assertEqual(response.data["wallet"]["available_balance"], 15)
        self.assertEqual(response.data["usage"]["products_count"], 1)
        self.assertEqual(response.data["usage"]["generations_count"], 1)
        self.assertEqual(
            response.data["subscription"]["operational_status"],
            "ACTIVE",
        )

    def test_superadmin_can_list_core_resources(self):
        self.auth_superadmin()

        for name in [
            "organizations",
            "accounts",
            "plans",
            "subscriptions",
            "credit-wallets",
            "generations",
            "scene-templates",
        ]:
            with self.subTest(name=name):
                response = self.client.get(
                    reverse(f"superadmin:{name}")
                )
                self.assertEqual(response.status_code, 200)

    def test_superadmin_can_suspend_and_reactivate_organization(self):
        self.auth_superadmin()
        url = reverse(
            "superadmin:organization-detail",
            kwargs={"pk": self.organization.pk},
        )

        response = self.client.patch(
            url,
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.organization.refresh_from_db()
        self.assertFalse(self.organization.is_active)

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                user=self.superadmin,
                action="SUPERADMIN_ORGANIZATION_STATUS_CHANGED",
            ).exists()
        )

        response = self.client.patch(
            url,
            {"is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.organization.refresh_from_db()
        self.assertTrue(self.organization.is_active)

    def test_superadmin_can_block_and_reactivate_user(self):
        self.auth_superadmin()
        url = reverse(
            "superadmin:account-detail",
            kwargs={"pk": self.common_user.pk},
        )

        response = self.client.patch(
            url,
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.common_user.refresh_from_db()
        self.assertFalse(self.common_user.is_active)

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                user=self.superadmin,
                action="SUPERADMIN_USER_STATUS_CHANGED",
            ).exists()
        )

        response = self.client.patch(
            url,
            {"is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.common_user.refresh_from_db()
        self.assertTrue(self.common_user.is_active)

    def test_user_detail_cannot_change_privileges_or_organization(self):
        other_org = Organization.objects.create(
            name="Outra Organização",
            slug="outra-org-superadmin",
        )

        self.auth_superadmin()

        response = self.client.patch(
            reverse(
                "superadmin:account-detail",
                kwargs={"pk": self.common_user.pk},
            ),
            {
                "organization": str(other_org.pk),
                "is_staff": True,
                "is_superuser": True,
                "role": "ADMIN",
                "name": "Nome Permitido",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.common_user.refresh_from_db()

        self.assertEqual(
            self.common_user.name,
            "Nome Permitido",
        )
        self.assertEqual(
            self.common_user.organization,
            self.organization,
        )
        self.assertFalse(self.common_user.is_staff)
        self.assertFalse(self.common_user.is_superuser)
        self.assertEqual(self.common_user.role, "OWNER")

    def test_superadmin_can_create_and_update_plan_with_audit(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:plans"),
            {
                "name": "Plano Novo",
                "slug": "plano-novo-superadmin",
                "description": "Plano novo.",
                "price": "149.90",
                "billing_cycle": BillingCycle.MONTHLY,
                "credits_per_cycle": 250,
                "is_active": True,
                "sort_order": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        new_plan = Plan.objects.get(
            slug="plano-novo-superadmin"
        )

        self.assertTrue(
            AuditLog.objects.filter(
                user=self.superadmin,
                action="SUPERADMIN_PLAN_CREATED",
                entity_id=str(new_plan.pk),
            ).exists()
        )

        response = self.client.patch(
            reverse(
                "superadmin:plan-detail",
                kwargs={"pk": new_plan.pk},
            ),
            {
                "price": "159.90",
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        new_plan.refresh_from_db()
        self.assertEqual(
            new_plan.price,
            Decimal("159.90"),
        )
        self.assertFalse(new_plan.is_active)

        self.assertTrue(
            AuditLog.objects.filter(
                user=self.superadmin,
                action="SUPERADMIN_PLAN_UPDATED",
                entity_id=str(new_plan.pk),
            ).exists()
        )

    def test_superadmin_can_read_subscription_detail(self):
        self.auth_superadmin()

        response = self.client.get(
            reverse(
                "superadmin:subscription-detail",
                kwargs={"pk": self.subscription.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            str(response.data["organization"]),
            str(self.organization.pk),
        )

    def test_superadmin_can_read_generation_detail(self):
        self.auth_superadmin()

        response = self.client.get(
            reverse(
                "superadmin:generation-detail",
                kwargs={"pk": self.generation.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            str(response.data["id"]),
            str(self.generation.pk),
        )

    def test_delete_not_allowed_on_mutable_details(self):
        self.auth_superadmin()

        urls = [
            reverse(
                "superadmin:organization-detail",
                kwargs={"pk": self.organization.pk},
            ),
            reverse(
                "superadmin:account-detail",
                kwargs={"pk": self.common_user.pk},
            ),
            reverse(
                "superadmin:plan-detail",
                kwargs={"pk": self.plan.pk},
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.delete(url)
                self.assertEqual(response.status_code, 405)

    def test_raw_subscription_patch_is_not_available(self):
        self.auth_superadmin()

        response = self.client.patch(
            reverse(
                "superadmin:subscription-detail",
                kwargs={"pk": self.subscription.pk},
            ),
            {
                "status": SubscriptionStatus.CANCELED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 405)

    def test_superadmin_can_activate_subscription_for_client(self):
        self.auth_superadmin()

        organization = Organization.objects.create(
            name="Cliente Sem Assinatura",
            slug="cliente-sem-assinatura",
        )
        CreditWallet.objects.create(
            organization=organization
        )

        response = self.client.post(
            reverse(
                "superadmin:client-activate-subscription",
                kwargs={"pk": organization.pk},
            ),
            {
                "plan_id": str(self.plan.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        organization.refresh_from_db()
        self.assertEqual(
            organization.subscription.status,
            SubscriptionStatus.ACTIVE,
        )
        self.assertEqual(
            organization.credit_wallet.plan_balance,
            self.plan.credits_per_cycle,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                organization=organization,
                user=self.superadmin,
                action="SUPERADMIN_SUBSCRIPTION_ACTIVATED",
            ).exists()
        )

    def test_superadmin_can_renew_subscription_preserving_purchased_credits(self):
        self.auth_superadmin()

        now = timezone.now()
        self.subscription.current_period_start = (
            now - timezone.timedelta(days=30)
        )
        self.subscription.current_period_end = now
        self.subscription.next_billing_at = now
        self.subscription.save(
            update_fields=[
                "current_period_start",
                "current_period_end",
                "next_billing_at",
                "updated_at",
            ]
        )

        self.wallet.plan_balance = 20
        self.wallet.purchased_balance = 12
        self.wallet.balance = 32
        self.wallet.save(
            update_fields=[
                "plan_balance",
                "purchased_balance",
                "balance",
                "updated_at",
            ]
        )

        response = self.client.post(
            reverse(
                "superadmin:subscription-renew",
                kwargs={"pk": self.subscription.pk},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.wallet.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(
            self.wallet.plan_balance,
            self.subscription.credits_snapshot,
        )
        self.assertEqual(self.wallet.purchased_balance, 12)
        self.assertEqual(self.wallet.balance, 112)
        self.assertGreater(
            self.subscription.current_period_end,
            now,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                user=self.superadmin,
                action="SUPERADMIN_SUBSCRIPTION_RENEWED",
            ).exists()
        )

    def test_superadmin_credit_adjustment_uses_service_and_audit(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": 7,
                "balance_type": "PURCHASED",
                "reason": "Ajuste operacional",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.purchased_balance, 12)
        self.assertEqual(self.wallet.balance, 22)

        transaction = CreditTransaction.objects.get(
            wallet=self.wallet,
            type=CreditTransactionType.ADJUSTMENT,
        )

        self.assertEqual(transaction.actor, self.superadmin)
        self.assertEqual(
            transaction.reason,
            "Ajuste operacional",
        )
        self.assertEqual(transaction.balance_before, 15)
        self.assertEqual(transaction.balance_after, 22)

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                user=self.superadmin,
                action="SUPERADMIN_CREDIT_ADJUSTMENT",
            ).exists()
        )

    def test_superadmin_can_add_and_remove_plan_credits(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": 4,
                "balance_type": "PLAN",
                "reason": "Bônus operacional",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 14)

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": -3,
                "balance_type": "PLAN",
                "reason": "Correção operacional",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 11)
        self.assertEqual(self.wallet.balance, 16)

    def test_superadmin_can_remove_purchased_credits_when_balance_allows(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": -2,
                "balance_type": "PURCHASED",
                "reason": "Correção operacional",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.purchased_balance, 3)
        self.assertEqual(self.wallet.balance, 13)

    def test_credit_adjustment_requires_reason(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": 1,
                "balance_type": "PLAN",
                "reason": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("reason", response.data)

    def test_credit_adjustment_rejects_negative_result(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:credit-adjustments"),
            {
                "organization_id": str(self.organization.id),
                "amount": -6,
                "balance_type": "PURCHASED",
                "reason": "Correção operacional",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.purchased_balance, 5)

    def test_members_endpoint_remains_unavailable_for_common_user(self):
        self.client.force_authenticate(self.common_user)

        response = self.client.get("/api/accounts/members/")

        self.assertEqual(response.status_code, 404)

    def test_superadmin_can_create_instagram_scene_template(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:scene-templates"),
            {
                "name": "Cenario Comercial",
                "slug": "cenario-comercial-superadmin",
                "generation_mode": GenerationMode.INSTAGRAM,
                "category": ProductCategory.EARRING,
                "prompt_template": "Use um cenario comercial de teste.",
                "version": 1,
                "is_active": True,
                "sort_order": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            SceneTemplate.objects.filter(
                slug="cenario-comercial-superadmin",
                generation_mode=GenerationMode.INSTAGRAM,
            ).exists()
        )

    def test_superadmin_rejects_non_instagram_scene_template(self):
        self.auth_superadmin()

        response = self.client.post(
            reverse("superadmin:scene-templates"),
            {
                "name": "Body Legado",
                "slug": "body-legado-superadmin",
                "generation_mode": GenerationMode.BODY_DETAIL,
                "category": ProductCategory.EARRING,
                "prompt_template": "Template invalido para V1.",
                "version": 1,
                "is_active": True,
                "sort_order": 10,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("generation_mode", response.data)

    def test_superadmin_can_update_scene_template_status_and_order(self):
        self.auth_superadmin()

        template = SceneTemplate.objects.create(
            name="Cenario Teste",
            slug="cenario-teste-superadmin",
            generation_mode=GenerationMode.INSTAGRAM,
            category=ProductCategory.EARRING,
            prompt_template="Cenario inicial.",
            version=1,
            is_active=True,
            sort_order=10,
        )

        response = self.client.patch(
            reverse(
                "superadmin:scene-template-detail",
                kwargs={"pk": template.pk},
            ),
            {
                "is_active": False,
                "sort_order": 30,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        template.refresh_from_db()
        self.assertFalse(template.is_active)
        self.assertEqual(template.sort_order, 30)
