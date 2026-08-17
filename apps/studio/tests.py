from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.ai.models import ModelReference
from apps.credits.models import CreditWallet
from apps.organizations.models import Organization
from apps.products.models import Product, ProductCategory
from apps.ai.services.prompt_engine import PromptEngine
from apps.studio.models import (
    GenerationMode,
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
