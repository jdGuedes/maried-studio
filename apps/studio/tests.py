from decimal import Decimal
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image

from rest_framework.test import APITestCase, APITransactionTestCase

from apps.ai.models import ModelReference
from apps.ai.services.prompt_engine import PromptEngine
from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.billing.services import SubscriptionRequiredError
from apps.credits.models import CreditTransaction, CreditTransactionType
from apps.credits.models import CreditWallet
from apps.organizations.models import Organization
from apps.products.models import Product, ProductCategory
from apps.studio.models import (
    Generation,
    GenerationMode,
    GeneratedImage,
    GenerationRule,
    GenerationStatus,
    SceneTemplate,
)
from apps.studio.serializers import GenerationCreateSerializer
from apps.studio.services.generation_service import GenerationService


class GenerationModeContractTests(
    TestCase
):
    def test_model_mode_label_is_na_modelo(
        self,
    ):
        self.assertEqual(
            GenerationMode.MODEL.label,
            "Na Modelo",
        )


class GenerationCreateSerializerTests(
    TestCase
):
    def test_body_detail_requires_model_reference(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.BODY_DETAIL,
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "model_reference_id",
            serializer.errors,
        )

    def test_body_detail_rejects_scene_template(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.BODY_DETAIL,
                "scene_template_id": (
                    "22222222-2222-2222-2222-222222222222"
                ),
                "model_reference_id": (
                    "33333333-3333-3333-3333-333333333333"
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "scene_template_id",
            serializer.errors,
        )

    def test_still_rejects_extra_visual_reference(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.STILL,
                "model_reference_id": (
                    "33333333-3333-3333-3333-333333333333"
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "model_reference_id",
            serializer.errors,
        )

    def test_instagram_requires_scene_template(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.INSTAGRAM,
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "scene_template_id",
            serializer.errors,
        )

    def test_model_requires_model_reference(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.MODEL,
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "model_reference_id",
            serializer.errors,
        )

    def test_model_rejects_scene_template(
        self,
    ):
        serializer = GenerationCreateSerializer(
            data={
                "product_id": (
                    "11111111-1111-1111-1111-111111111111"
                ),
                "mode": GenerationMode.MODEL,
                "scene_template_id": (
                    "22222222-2222-2222-2222-222222222222"
                ),
                "model_reference_id": (
                    "33333333-3333-3333-3333-333333333333"
                ),
            }
        )

        self.assertFalse(
            serializer.is_valid()
        )

        self.assertIn(
            "scene_template_id",
            serializer.errors,
        )


class GenerationServiceModelReferenceTests(
    TestCase
):
    def setUp(
        self,
    ):
        user_model = get_user_model()

        self.organization = (
            Organization.objects.create(
                name="Org Teste",
                slug="org-teste-studio",
            )
        )

        self.user = (
            user_model.objects.create_user(
                email="cliente-studio@example.com",
                password="senha-teste",
                name="Cliente",
                organization=self.organization,
                role="OWNER",
            )
        )

        self.wallet = (
            CreditWallet.objects.create(
                organization=self.organization,
                plan_balance=3,
                balance=3,
            )
        )

        self.plan = Plan.objects.create(
            name="Plano Studio",
            slug="plano-studio-model-reference",
            description="Plano de teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        now = timezone.now()

        Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timezone.timedelta(days=30),
            next_billing_at=now + timezone.timedelta(days=30),
        )

        self.product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Brinco Teste",
            category=ProductCategory.EARRING,
        )

        self.rule = GenerationRule.objects.create(
            category=ProductCategory.EARRING,
            generation_mode=GenerationMode.BODY_DETAIL,
            framing="CLOSE_UP",
            body_area="ear and side of face",
            placement_instruction=(
                "Hair must not cover the jewelry."
            ),
        )

        self.model_reference = (
            ModelReference.objects.create(
                code="MODEL_TEST",
                name="Modelo Teste",
                slug="modelo-teste-studio",
                description="Modelo para teste.",
                prompt_instruction=(
                    "Use a controlled test model reference."
                ),
                is_active=True,
                sort_order=10,
            )
        )

        self.model_rule = (
            GenerationRule.objects.create(
                category=ProductCategory.EARRING,
                generation_mode=GenerationMode.MODEL,
                framing="PORTRAIT_BUST",
                body_area="ears and face",
                placement_instruction=(
                    "Place the earrings naturally "
                    "on the model's ears."
                ),
            )
        )

    def test_body_detail_request_stores_model_reference_and_reserves_credit(
        self,
    ):
        generation, created = (
            GenerationService.create_request(
                user=self.user,
                product=self.product,
                mode=GenerationMode.BODY_DETAIL,
                scene_template_id=None,
                model_reference_id=(
                    self.model_reference.id
                ),
                idempotency_key=(
                    "body-detail-model-reference"
                ),
            )
        )

        self.assertTrue(
            created
        )

        self.assertEqual(
            generation.model_reference,
            self.model_reference,
        )

        self.assertEqual(
            generation.status,
            GenerationStatus.CREDIT_RESERVED,
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.reserved_balance,
            1,
        )

    def test_prompt_uses_selected_model_reference_instruction(
        self,
    ):
        prompt = PromptEngine.build(
            product=self.product,
            mode=GenerationMode.BODY_DETAIL,
            scene_template=None,
            model_reference=self.model_reference,
            generation_rule=self.rule,
        )

        self.assertIn(
            "Use a controlled test model reference.",
            prompt,
        )

        self.assertNotIn(
            "medium-brown",
            prompt,
        )

    def test_model_request_stores_model_reference_and_reserves_credit(
        self,
    ):
        generation, created = (
            GenerationService.create_request(
                user=self.user,
                product=self.product,
                mode=GenerationMode.MODEL,
                scene_template_id=None,
                model_reference_id=(
                    self.model_reference.id
                ),
                idempotency_key=(
                    "on-model-model-reference"
                ),
            )
        )

        self.assertTrue(
            created
        )

        self.assertEqual(
            generation.model_reference,
            self.model_reference,
        )

        self.assertEqual(
            generation.generation_rule,
            self.model_rule,
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.reserved_balance,
            1,
        )

    def test_model_prompt_uses_selected_model_reference_instruction(
        self,
    ):
        prompt = PromptEngine.build(
            product=self.product,
            mode=GenerationMode.MODEL,
            scene_template=None,
            model_reference=self.model_reference,
            generation_rule=self.model_rule,
        )

        self.assertIn(
            "GENERATION MODE: MODEL",
            prompt,
        )

        self.assertIn(
            "Use a controlled test model reference.",
            prompt,
        )


class SceneTemplateContractTests(
    APITestCase
):
    def setUp(
        self,
    ):
        user_model = get_user_model()

        self.organization = (
            Organization.objects.create(
                name="Org API",
                slug="org-api-studio",
            )
        )

        self.user = (
            user_model.objects.create_user(
                email="api-studio@example.com",
                password="senha-teste",
                name="Cliente API",
                organization=self.organization,
                role="OWNER",
            )
        )

        self.client.force_authenticate(
            self.user
        )

        SceneTemplate.objects.create(
            name="Body Natural",
            slug="body-natural-test",
            generation_mode=GenerationMode.BODY_DETAIL,
            category=ProductCategory.EARRING,
            prompt_template="Template legado de corpo.",
            is_active=True,
        )

        SceneTemplate.objects.create(
            name="Instagram Comercial",
            slug="instagram-comercial-test",
            generation_mode=GenerationMode.INSTAGRAM,
            category=ProductCategory.EARRING,
            prompt_template="Template Instagram ativo.",
            is_active=True,
            sort_order=10,
        )

    def test_body_detail_does_not_list_scene_templates(
        self,
    ):
        response = self.client.get(
            reverse(
                "scene-template-list"
            ),
            {
                "category": ProductCategory.EARRING,
                "mode": GenerationMode.BODY_DETAIL,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["results"],
            [],
        )

    def test_scene_template_list_returns_only_instagram_templates(
        self,
    ):
        response = self.client.get(
            reverse(
                "scene-template-list"
            ),
            {
                "category": ProductCategory.EARRING,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        slugs = [
            item["slug"]
            for item in response.data["results"]
        ]

        self.assertEqual(
            slugs,
            [
                "instagram-comercial-test",
            ],
        )


class SeedStudioCommandTests(
    TestCase
):
    def test_seed_studio_creates_only_instagram_scene_templates(
        self,
    ):
        call_command(
            "seed_studio",
        )

        self.assertTrue(
            SceneTemplate.objects.exists()
        )

        self.assertFalse(
            SceneTemplate.objects
            .exclude(
                generation_mode=GenerationMode.INSTAGRAM
            )
            .exists()
        )

    def test_seed_studio_creates_model_generation_rules_for_all_categories(
        self,
    ):
        call_command(
            "seed_studio",
        )

        categories = [
            value
            for value, _label in ProductCategory.choices
        ]

        for category in categories:
            with self.subTest(
                category=category
            ):
                self.assertTrue(
                    GenerationRule.objects.filter(
                        category=category,
                        generation_mode=GenerationMode.MODEL,
                        is_active=True,
                    )
                    .exclude(
                        framing=""
                    )
                    .exists()
                )


class MultiTenantIsolationTests(
    APITestCase
):
    def setUp(
        self,
    ):
        user_model = get_user_model()

        self.org_a = Organization.objects.create(
            name="Organização A",
            slug="org-a-multitenant",
        )

        self.org_b = Organization.objects.create(
            name="Organização B",
            slug="org-b-multitenant",
        )

        self.user_a = user_model.objects.create_user(
            email="owner-a@example.com",
            password="senha-teste",
            name="Owner A",
            organization=self.org_a,
            role="OWNER",
        )

        self.user_b = user_model.objects.create_user(
            email="owner-b@example.com",
            password="senha-teste",
            name="Owner B",
            organization=self.org_b,
            role="OWNER",
        )

        self.wallet_a = CreditWallet.objects.create(
            organization=self.org_a,
            plan_balance=10,
            balance=10,
        )

        self.wallet_b = CreditWallet.objects.create(
            organization=self.org_b,
            plan_balance=10,
            balance=10,
        )

        self.plan = Plan.objects.create(
            name="Plano MultiTenant",
            slug="plano-multitenant-studio",
            description="Plano de teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        now = timezone.now()

        for organization in (
            self.org_a,
            self.org_b,
        ):
            Subscription.objects.create(
                organization=organization,
                plan=self.plan,
                status=SubscriptionStatus.ACTIVE,
                price_snapshot=self.plan.price,
                credits_snapshot=self.plan.credits_per_cycle,
                started_at=now,
                current_period_start=now,
                current_period_end=now + timezone.timedelta(days=30),
                next_billing_at=now + timezone.timedelta(days=30),
            )

        self.product_a = Product.objects.create(
            organization=self.org_a,
            created_by=self.user_a,
            name="Produto A",
            category=ProductCategory.EARRING,
        )

        self.product_b = Product.objects.create(
            organization=self.org_b,
            created_by=self.user_b,
            name="Produto B",
            category=ProductCategory.EARRING,
        )

        self.still_rule = GenerationRule.objects.create(
            category=ProductCategory.EARRING,
            generation_mode=GenerationMode.STILL,
            framing="PRODUCT",
            body_area="",
            placement_instruction="",
        )

        self.generation_a = Generation.objects.create(
            organization=self.org_a,
            user=self.user_a,
            product=self.product_a,
            mode=GenerationMode.STILL,
            generation_rule=self.still_rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="completed-a",
            credit_cost=1,
        )

        self.generation_b = Generation.objects.create(
            organization=self.org_b,
            user=self.user_b,
            product=self.product_b,
            mode=GenerationMode.STILL,
            generation_rule=self.still_rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="completed-b",
            credit_cost=1,
        )

    def test_service_allows_user_to_create_request_for_own_product(
        self,
    ):
        generation, created = (
            GenerationService.create_request(
                user=self.user_a,
                product=self.product_a,
                mode=GenerationMode.STILL,
                scene_template_id=None,
                model_reference_id=None,
                idempotency_key="own-product-request",
            )
        )

        self.assertTrue(
            created
        )

        self.assertEqual(
            generation.organization,
            self.org_a,
        )

        self.assertEqual(
            generation.user,
            self.user_a,
        )

        self.assertEqual(
            generation.product,
            self.product_a,
        )

        self.wallet_a.refresh_from_db()

        self.assertEqual(
            self.wallet_a.reserved_balance,
            1,
        )

    def test_service_blocks_user_from_other_organization_product(
        self,
    ):
        with self.assertRaises(
            PermissionError
        ):
            GenerationService.create_request(
                user=self.user_a,
                product=self.product_b,
                mode=GenerationMode.STILL,
                scene_template_id=None,
                model_reference_id=None,
                idempotency_key="cross-tenant-service",
            )

    def test_cross_tenant_service_attempt_does_not_touch_other_wallet(
        self,
    ):
        before_total = (
            self.wallet_b.total_balance
        )
        before_available = (
            self.wallet_b.available_balance
        )
        before_reserved = (
            self.wallet_b.reserved_balance
        )

        with self.assertRaises(
            PermissionError
        ):
            GenerationService.create_request(
                user=self.user_a,
                product=self.product_b,
                mode=GenerationMode.STILL,
                scene_template_id=None,
                model_reference_id=None,
                idempotency_key="cross-tenant-credit",
            )

        self.wallet_b.refresh_from_db()

        self.assertEqual(
            self.wallet_b.total_balance,
            before_total,
        )

        self.assertEqual(
            self.wallet_b.available_balance,
            before_available,
        )

        self.assertEqual(
            self.wallet_b.reserved_balance,
            before_reserved,
        )

    def test_api_post_cannot_use_product_from_other_organization(
        self,
    ):
        self.client.force_authenticate(
            self.user_a
        )

        response = self.client.post(
            reverse(
                "generation-create"
            ),
            {
                "product_id": str(
                    self.product_b.id
                ),
                "mode": GenerationMode.STILL,
                "idempotency_key": "cross-tenant-api",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertFalse(
            Generation.objects.filter(
                organization=self.org_b,
                idempotency_key="cross-tenant-api",
            ).exists()
        )

    def test_generation_list_exposes_only_authenticated_organization(
        self,
    ):
        self.client.force_authenticate(
            self.user_a
        )

        response = self.client.get(
            reverse(
                "generation-create"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        ids = {
            str(item["id"])
            for item in response.data[
                "results"
            ]
        }

        self.assertIn(
            str(self.generation_a.id),
            ids,
        )

        self.assertNotIn(
            str(self.generation_b.id),
            ids,
        )

    def test_generation_detail_does_not_expose_other_organization(
        self,
    ):
        self.client.force_authenticate(
            self.user_a
        )

        response = self.client.get(
            reverse(
                "generation-detail",
                kwargs={
                    "pk": self.generation_b.id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_dashboard_counts_only_authenticated_organization(
        self,
    ):
        self.client.force_authenticate(
            self.user_a
        )

        response = self.client.get(
            reverse(
                "dashboard"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data[
                "products"
            ]["count"],
            1,
        )

        self.assertEqual(
            response.data[
                "generations"
            ]["count"],
            1,
        )

        recent_ids = {
            str(item["id"])
            for item in response.data[
                "recent_generations"
            ]
        }

        self.assertIn(
            str(self.generation_a.id),
            recent_ids,
        )

        self.assertNotIn(
            str(self.generation_b.id),
            recent_ids,
        )

    def test_post_rejects_user_without_organization(
        self,
    ):
        user_model = get_user_model()

        user_without_org = (
            user_model.objects.create_user(
                email="sem-org@example.com",
                password="senha-teste",
                name="Sem Organização",
                organization=None,
                role="OWNER",
            )
        )

        self.client.force_authenticate(
            user_without_org
        )

        response = self.client.post(
            reverse(
                "generation-create"
            ),
            {
                "product_id": str(
                    self.product_a.id
                ),
                "mode": GenerationMode.STILL,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_post_rejects_inactive_organization(
        self,
    ):
        self.org_a.is_active = False
        self.org_a.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        self.client.force_authenticate(
            self.user_a
        )

        response = self.client.post(
            reverse(
                "generation-create"
            ),
            {
                "product_id": str(
                    self.product_a.id
                ),
                "mode": GenerationMode.STILL,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )


class GenerationSubscriptionAccessTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Organização Geração",
            slug="org-geracao-subscription",
        )

        self.user = User.objects.create_user(
            email="geracao-subscription@example.com",
            password="senha-teste",
            name="Cliente Geração",
            organization=self.organization,
            role="OWNER",
        )

        self.plan = Plan.objects.create(
            name="Plano Geração",
            slug="plano-geracao-subscription",
            description="Plano de teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=10,
            balance=10,
        )

        self.product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Produto Geração",
            category=ProductCategory.EARRING,
        )

        self.rule = GenerationRule.objects.create(
            category=ProductCategory.EARRING,
            generation_mode=GenerationMode.STILL,
            framing="PRODUCT",
            body_area="",
            placement_instruction="",
        )

        self.client.force_authenticate(
            self.user
        )

    def at(self, year, month, day):
        return timezone.make_aware(
            timezone.datetime(
                year,
                month,
                day,
                10,
                0,
                0,
            )
        )

    def create_subscription(
        self,
        *,
        status,
        period_end,
    ):
        return Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=status,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=period_end - timezone.timedelta(days=30),
            current_period_start=period_end - timezone.timedelta(days=30),
            current_period_end=period_end,
            next_billing_at=period_end,
        )

    def create_request(self, key):
        return GenerationService.create_request(
            user=self.user,
            product=self.product,
            mode=GenerationMode.STILL,
            scene_template_id=None,
            model_reference_id=None,
            idempotency_key=key,
        )

    def test_active_subscription_allows_generation_request(self):
        self.create_subscription(
            status=SubscriptionStatus.ACTIVE,
            period_end=self.at(
                2026,
                9,
                25,
            ),
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                25,
            ),
        ):
            generation, created = self.create_request(
                "generation-active-subscription"
            )

        self.assertTrue(
            created
        )

        self.assertEqual(
            generation.status,
            GenerationStatus.CREDIT_RESERVED,
        )

    def test_grace_subscription_allows_generation_request(self):
        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                25,
            ),
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                28,
            ),
        ):
            generation, created = self.create_request(
                "generation-grace-subscription"
            )

        self.assertTrue(
            created
        )

        self.assertEqual(
            generation.status,
            GenerationStatus.CREDIT_RESERVED,
        )

    def test_blocked_subscription_with_plan_credits_rejects_generation(self):
        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                25,
            ),
        )

        before_reserved = self.wallet.reserved_balance

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                29,
            ),
        ):
            with self.assertRaises(
                SubscriptionRequiredError
            ):
                self.create_request(
                    "generation-blocked-plan-credits"
                )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.reserved_balance,
            before_reserved,
        )

        self.assertFalse(
            Generation.objects.filter(
                idempotency_key="generation-blocked-plan-credits",
            ).exists()
        )

        self.assertFalse(
            CreditTransaction.objects.filter(
                wallet=self.wallet,
            ).exists()
        )

    def test_blocked_subscription_with_purchased_credits_rejects_generation(self):
        self.wallet.plan_balance = 0
        self.wallet.purchased_balance = 100
        self.wallet.balance = 100
        self.wallet.save(
            update_fields=[
                "plan_balance",
                "purchased_balance",
                "balance",
                "updated_at",
            ]
        )

        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                25,
            ),
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                29,
            ),
        ):
            with self.assertRaises(
                SubscriptionRequiredError
            ):
                self.create_request(
                    "generation-blocked-purchased-credits"
                )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.purchased_balance,
            100,
        )

        self.assertEqual(
            self.wallet.reserved_balance,
            0,
        )

        self.assertFalse(
            Generation.objects.filter(
                idempotency_key="generation-blocked-purchased-credits",
            ).exists()
        )

        self.assertFalse(
            CreditTransaction.objects.filter(
                wallet=self.wallet,
            ).exists()
        )

    def test_api_blocks_generation_before_provider_call(self):
        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                25,
            ),
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                29,
            ),
        ):
            with patch(
                "apps.ai.providers.openai.OpenAIImageProvider.generate"
            ) as generate:
                response = self.client.post(
                    reverse(
                        "generation-create"
                    ),
                    {
                        "product_id": str(
                            self.product.id
                        ),
                        "mode": GenerationMode.STILL,
                        "idempotency_key": "api-blocked-subscription",
                    },
                    format="json",
                )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["code"],
            "SUBSCRIPTION_REQUIRED",
        )

        generate.assert_not_called()

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.reserved_balance,
            0,
        )


class GeneratedImagePrivateDownloadTests(
    APITransactionTestCase
):
    def setUp(self):
        self.media_root = tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        )

        self.override_settings = override_settings(
            MEDIA_ROOT=self.media_root.name
        )

        self.override_settings.enable()

        self.addCleanup(
            self.override_settings.disable
        )

        self.addCleanup(
            self.media_root.cleanup
        )

        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Org Imagem A",
            slug="org-imagem-a",
        )

        self.other_organization = Organization.objects.create(
            name="Org Imagem B",
            slug="org-imagem-b",
        )

        self.user = User.objects.create_user(
            email="imagem-a@example.com",
            password="senha-teste",
            name="Cliente Imagem A",
            organization=self.organization,
            role="OWNER",
        )

        self.other_user = User.objects.create_user(
            email="imagem-b@example.com",
            password="senha-teste",
            name="Cliente Imagem B",
            organization=self.other_organization,
            role="OWNER",
        )

        self.staff_user = User.objects.create_user(
            email="staff-imagem@example.com",
            password="senha-teste",
            name="Staff sem SuperAdmin",
            organization=self.other_organization,
            role="OWNER",
            is_staff=True,
        )

        self.superuser = User.objects.create_superuser(
            email="super-imagem@example.com",
            password="senha-teste",
            name="SuperAdmin Imagem",
        )

        self.product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Produto Imagem",
            category=ProductCategory.EARRING,
        )

        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=8,
            purchased_balance=3,
            balance=11,
        )

        self.other_product = Product.objects.create(
            organization=self.other_organization,
            created_by=self.other_user,
            name="Outro Produto Imagem",
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
            user=self.user,
            product=self.product,
            mode=GenerationMode.STILL,
            generation_rule=self.rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="private-generated-image-a",
            credit_cost=1,
        )

        self.image_bytes = self.jpeg_bytes()

        self.generated_image = GeneratedImage.objects.create(
            generation=self.generation,
            mime_type="image/jpeg",
            width=600,
            height=600,
            file_size=len(
                self.image_bytes
            ),
        )

        self.generated_image.file.save(
            "resultado-privado.jpg",
            ContentFile(
                self.image_bytes
            ),
            save=True,
        )

        self.generated_image.file.close()

    def jpeg_bytes(self):
        buffer = BytesIO()

        image = Image.new(
            "RGB",
            (
                600,
                600,
            ),
            "white",
        )

        image.save(
            buffer,
            format="JPEG",
        )

        return buffer.getvalue()

    def response_content(
        self,
        response,
    ):
        return b"".join(
            response.streaming_content
        )

    def create_blocked_subscription(self):
        plan = Plan.objects.create(
            name="Plano Imagem",
            slug="plano-imagem-privada",
            description="Plano de teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        period_end = timezone.now() - timezone.timedelta(
            days=4
        )

        return Subscription.objects.create(
            organization=self.organization,
            plan=plan,
            status=SubscriptionStatus.PAST_DUE,
            price_snapshot=plan.price,
            credits_snapshot=plan.credits_per_cycle,
            started_at=period_end - timezone.timedelta(
                days=30
            ),
            current_period_start=period_end - timezone.timedelta(
                days=30
            ),
            current_period_end=period_end,
            next_billing_at=period_end,
        )

    def download_url(self):
        return reverse(
            "generated-image-download",
            kwargs={
                "pk": self.generated_image.pk,
            },
        )

    def test_owner_can_download_own_generated_image(self):
        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            self.download_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response["Content-Type"],
            "image/jpeg",
        )

        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )

        self.assertNotIn(
            "generations/",
            response["Content-Disposition"],
        )

        self.assertEqual(
            self.response_content(
                response
            ),
            self.image_bytes,
        )

    def test_other_tenant_cannot_download_generated_image(self):
        self.client.force_authenticate(
            self.other_user
        )

        response = self.client.get(
            self.download_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_anonymous_cannot_download_generated_image(self):
        response = self.client.get(
            self.download_url()
        )

        self.assertIn(
            response.status_code,
            [
                401,
                403,
            ],
        )

    def test_staff_without_superuser_has_no_global_generated_image_access(self):
        self.client.force_authenticate(
            self.staff_user
        )

        response = self.client.get(
            self.download_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_superadmin_can_download_generated_image_globally(self):
        self.client.force_authenticate(
            self.superuser
        )

        response = self.client.get(
            self.download_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.response_content(
                response
            ),
            self.image_bytes,
        )

    def test_blocked_subscription_can_download_existing_generated_image(self):
        self.create_blocked_subscription()

        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            self.download_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.response_content(
            response
        )

    def test_generation_serializer_uses_authorized_url_without_storage_path(self):
        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            reverse(
                "generation-create"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        image_url = response.data["results"][0]["image_url"]

        self.assertIn(
            f"/api/studio/images/{self.generated_image.pk}/download/",
            image_url,
        )

        self.assertNotIn(
            "/media/",
            image_url,
        )

        self.assertNotIn(
            "generations/",
            image_url,
        )

    def test_missing_generated_image_file_returns_safe_404(self):
        missing_generation = Generation.objects.create(
            organization=self.organization,
            user=self.user,
            product=self.product,
            mode=GenerationMode.STILL,
            generation_rule=self.rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="missing-generated-image",
            credit_cost=1,
        )

        missing_image = GeneratedImage.objects.create(
            generation=missing_generation,
            file="generations/2099/01/missing.jpg",
            mime_type="image/jpeg",
            width=600,
            height=600,
            file_size=1,
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            reverse(
                "generated-image-download",
                kwargs={
                    "pk": missing_image.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertNotIn(
            "generations/",
            str(response.content),
        )

    def test_delete_own_generated_image_removes_record_and_file_only(self):
        image_id = self.generated_image.pk
        file_name = self.generated_image.file.name
        storage = self.generated_image.file.storage

        CreditTransaction.objects.create(
            wallet=self.wallet,
            generation=self.generation,
            type=CreditTransactionType.CONSUME,
            amount=-1,
            plan_amount=-1,
            purchased_amount=0,
            balance_before=11,
            balance_after=10,
            reserved_before=1,
            reserved_after=0,
            plan_balance_before=8,
            plan_balance_after=7,
            purchased_balance_before=3,
            purchased_balance_after=3,
            plan_reserved_before=1,
            plan_reserved_after=0,
            purchased_reserved_before=0,
            purchased_reserved_after=0,
            description="Consumo de teste.",
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )

        self.assertFalse(
            storage.exists(
                file_name
            )
        )

        self.assertTrue(
            Product.objects.filter(
                pk=self.product.pk
            ).exists()
        )

        self.assertTrue(
            Generation.objects.filter(
                pk=self.generation.pk
            ).exists()
        )

        self.wallet.refresh_from_db()

        self.assertEqual(
            self.wallet.plan_balance,
            8,
        )

        self.assertEqual(
            self.wallet.purchased_balance,
            3,
        )

        self.assertEqual(
            self.wallet.reserved_balance,
            0,
        )

        self.assertEqual(
            CreditTransaction.objects.count(),
            1,
        )

        self.assertEqual(
            CreditTransaction.objects.filter(
                type=CreditTransactionType.REFUND
            ).count(),
            0,
        )

    def test_other_tenant_cannot_delete_generated_image_or_file(self):
        image_id = self.generated_image.pk
        file_name = self.generated_image.file.name
        storage = self.generated_image.file.storage

        self.client.force_authenticate(
            self.other_user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )

        self.assertTrue(
            storage.exists(
                file_name
            )
        )

    def test_anonymous_cannot_delete_generated_image(self):
        image_id = self.generated_image.pk
        file_name = self.generated_image.file.name
        storage = self.generated_image.file.storage

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertIn(
            response.status_code,
            [
                401,
                403,
            ],
        )

        self.assertTrue(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )

        self.assertTrue(
            storage.exists(
                file_name
            )
        )

    def test_blocked_subscription_can_delete_own_generated_image(self):
        self.create_blocked_subscription()

        image_id = self.generated_image.pk
        file_name = self.generated_image.file.name
        storage = self.generated_image.file.storage

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )

        self.assertFalse(
            storage.exists(
                file_name
            )
        )

    def test_download_after_generated_image_delete_returns_404(self):
        image_id = self.generated_image.pk
        download_url = self.download_url()

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        response = self.client.get(
            download_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_staff_without_superuser_has_no_global_generated_image_delete_access(self):
        image_id = self.generated_image.pk
        file_name = self.generated_image.file.name
        storage = self.generated_image.file.storage

        self.client.force_authenticate(
            self.staff_user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": image_id,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )

        self.assertTrue(
            storage.exists(
                file_name
            )
        )

    def test_delete_generated_image_with_missing_file_removes_record(self):
        missing_generation = Generation.objects.create(
            organization=self.organization,
            user=self.user,
            product=self.product,
            mode=GenerationMode.STILL,
            generation_rule=self.rule,
            status=GenerationStatus.COMPLETED,
            idempotency_key="delete-missing-generated-image",
            credit_cost=1,
        )

        missing_image = GeneratedImage.objects.create(
            generation=missing_generation,
            file="generations/2099/01/missing-delete.jpg",
            mime_type="image/jpeg",
            width=600,
            height=600,
            file_size=1,
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "generated-image-delete",
                kwargs={
                    "pk": missing_image.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            GeneratedImage.objects.filter(
                pk=missing_image.pk
            ).exists()
        )

    def test_storage_delete_failure_does_not_restore_database_record(self):
        image_id = self.generated_image.pk
        storage = self.generated_image.file.storage

        self.client.force_authenticate(
            self.user
        )

        with self.assertLogs(
            "apps.products.services",
            level="ERROR",
        ):
            with patch.object(
                storage,
                "delete",
                side_effect=RuntimeError(
                    "storage indisponível"
                ),
            ):
                response = self.client.delete(
                    reverse(
                        "generated-image-delete",
                        kwargs={
                            "pk": image_id,
                        },
                    )
                )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            GeneratedImage.objects.filter(
                pk=image_id
            ).exists()
        )
