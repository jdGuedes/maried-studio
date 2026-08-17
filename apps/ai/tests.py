from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APITestCase

from apps.ai.models import (
    ModelReference,
)
from apps.organizations.models import (
    Organization,
)


class ModelReferenceModelTests(
    TestCase
):
    def test_create_valid_model_reference(
        self,
    ):
        reference = ModelReference.objects.create(
            code="MODEL_TEST",
            name="Modelo teste",
            slug="modelo-teste",
            description=(
                "Mulher de 25 a 28 anos, pele clara, cabelo castanho."
            ),
            prompt_instruction=(
                "Use esta descricao como referencia visual controlada."
            ),
            skin_tone="pele clara",
            hair_color="cabelo castanho",
            age_range="25 a 28 anos",
            sort_order=10,
        )

        self.assertEqual(
            str(reference),
            "MODEL_TEST - Modelo teste",
        )

        self.assertTrue(
            reference.is_active
        )


class ModelReferenceApiTests(
    APITestCase
):
    def setUp(
        self,
    ):
        organization = Organization.objects.create(
            name="Org teste",
            slug="org-teste",
        )

        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="cliente@example.com",
            password="senha-teste",
            name="Cliente",
            organization=organization,
            role="OWNER",
        )

        self.client.force_authenticate(
            self.user
        )

    def test_list_returns_only_active_model_references(
        self,
    ):
        active = ModelReference.objects.create(
            code="MODEL_ACTIVE",
            name="Modelo ativa",
            slug="modelo-ativa",
            description="Referencia ativa.",
            prompt_instruction="Use a referencia ativa.",
            sort_order=20,
            is_active=True,
        )

        ModelReference.objects.create(
            code="MODEL_INACTIVE",
            name="Modelo inativa",
            slug="modelo-inativa",
            description="Referencia inativa.",
            prompt_instruction="Use a referencia inativa.",
            sort_order=10,
            is_active=False,
        )

        response = self.client.get(
            reverse(
                "ai:model-reference-list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        codes = [
            item["code"]
            for item in response.data["results"]
        ]

        self.assertIn(
            active.code,
            codes,
        )

        self.assertNotIn(
            "MODEL_INACTIVE",
            codes,
        )

    def test_list_requires_authentication(
        self,
    ):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            reverse(
                "ai:model-reference-list"
            )
        )

        self.assertEqual(
            response.status_code,
            403,
        )
