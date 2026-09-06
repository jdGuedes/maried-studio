from decimal import Decimal
from io import BytesIO
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image

from rest_framework.test import APITestCase, APITransactionTestCase

from apps.billing.models import (
    BillingCycle,
    PaymentDispute,
    PaymentDisputeOriginType,
    PaymentDisputeStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from apps.billing.services import SubscriptionService
from apps.credits.models import CreditTransaction, CreditTransactionType, CreditWallet
from apps.organizations.models import Organization
from apps.studio.models import Generation, GeneratedImage, GenerationMode, GenerationStatus

from .models import AssetType, Product, ProductAsset, ProductCategory


class ProductSubscriptionAccessTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Produtos",
            slug="empresa-produtos-subscription",
        )

        self.user = User.objects.create_user(
            email="produtos-subscription@example.com",
            password="senha-teste",
            name="Cliente Produtos",
            organization=self.organization,
            role="OWNER",
        )

        self.plan = Plan.objects.create(
            name="Plano Produtos",
            slug="plano-produtos-subscription",
            description="Plano de testes.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=10,
            balance=10,
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

    def image_file(self, name="produto.png"):
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
            format="PNG",
        )

        buffer.seek(0)

        return SimpleUploadedFile(
            name,
            buffer.read(),
            content_type="image/png",
        )

    def post_product(self):
        return self.client.post(
            reverse(
                "product-list"
            ),
            {
                "name": "Produto Teste",
                "category": ProductCategory.EARRING,
                "original_image": self.image_file(),
            },
            format="multipart",
        )

    def test_active_subscription_allows_product_creation(self):
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
            response = self.post_product()

        self.assertEqual(
            response.status_code,
            201,
        )

    def test_grace_day_one_allows_product_creation(self):
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
                26,
            ),
        ):
            response = self.post_product()

        self.assertEqual(
            response.status_code,
            201,
        )

    def test_grace_day_three_allows_product_creation(self):
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
            response = self.post_product()

        self.assertEqual(
            response.status_code,
            201,
        )

    def test_blocked_subscription_rejects_product_creation(self):
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
            response = self.post_product()

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["code"],
            "SUBSCRIPTION_REQUIRED",
        )

        self.assertFalse(
            Product.objects.filter(
                organization=self.organization,
                name="Produto Teste",
            ).exists()
        )

    def test_pending_subscription_rejects_product_creation(self):
        SubscriptionService.create_pending(
            organization=self.organization,
            plan=self.plan,
        )

        response = self.post_product()

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["code"],
            "SUBSCRIPTION_REQUIRED",
        )

        self.assertFalse(
            Product.objects.filter(
                organization=self.organization,
                name="Produto Teste",
            ).exists()
        )

    def test_financial_block_rejects_product_creation(self):
        self.create_subscription(
            status=SubscriptionStatus.ACTIVE,
            period_end=self.at(
                2026,
                9,
                25,
            ),
        )
        PaymentDispute.objects.create(
            organization=self.organization,
            stripe_dispute_id="du_product_block",
            status=PaymentDisputeStatus.NEEDS_RESPONSE,
            origin_type=PaymentDisputeOriginType.SUBSCRIPTION,
            amount=9990,
            currency="BRL",
        )

        response = self.post_product()

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            response.data["code"],
            "SUBSCRIPTION_REQUIRED",
        )

        self.assertFalse(
            Product.objects.filter(
                organization=self.organization,
                name="Produto Teste",
            ).exists()
        )

    def test_blocked_subscription_still_allows_product_list(self):
        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                25,
            ),
        )

        Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Produto Existente",
            category=ProductCategory.EARRING,
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=self.at(
                2026,
                8,
                29,
            ),
        ):
            response = self.client.get(
                reverse(
                    "product-list"
                )
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            1,
        )

    def test_user_cannot_access_product_from_other_organization(self):
        other_organization = Organization.objects.create(
            name="Outra Empresa",
            slug="outra-empresa-produtos-subscription",
        )

        other_user = get_user_model().objects.create_user(
            email="outro-produtos@example.com",
            password="senha-teste",
            name="Outro Cliente",
            organization=other_organization,
            role="OWNER",
        )

        other_product = Product.objects.create(
            organization=other_organization,
            created_by=other_user,
            name="Produto de Outra Organização",
            category=ProductCategory.EARRING,
        )

        response = self.client.get(
            reverse(
                "product-detail",
                kwargs={
                    "pk": other_product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class ProductPrivateMediaDownloadTests(
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
            name="Empresa Mídia A",
            slug="empresa-midia-a",
        )

        self.other_organization = Organization.objects.create(
            name="Empresa Mídia B",
            slug="empresa-midia-b",
        )

        self.user = User.objects.create_user(
            email="midia-a@example.com",
            password="senha-teste",
            name="Cliente Mídia A",
            organization=self.organization,
            role="OWNER",
        )

        self.other_user = User.objects.create_user(
            email="midia-b@example.com",
            password="senha-teste",
            name="Cliente Mídia B",
            organization=self.other_organization,
            role="OWNER",
        )

        self.staff_user = User.objects.create_user(
            email="staff-midia@example.com",
            password="senha-teste",
            name="Staff sem SuperAdmin",
            organization=self.other_organization,
            role="OWNER",
            is_staff=True,
        )

        self.superuser = User.objects.create_superuser(
            email="super-midia@example.com",
            password="senha-teste",
            name="SuperAdmin Mídia",
        )

        self.product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Brinco Privado",
            category=ProductCategory.EARRING,
        )

        self.other_product = Product.objects.create(
            organization=self.other_organization,
            created_by=self.other_user,
            name="Brinco de Outra Org",
            category=ProductCategory.EARRING,
        )

        self.asset_bytes = self.image_bytes(
            color="white"
        )

        self.asset = ProductAsset.objects.create(
            product=self.product,
            asset_type=AssetType.ORIGINAL,
            mime_type="image/png",
            width=600,
            height=600,
            file_size=len(
                self.asset_bytes
            ),
        )

        self.asset.file.save(
            "original-privado.png",
            ContentFile(
                self.asset_bytes
            ),
            save=True,
        )

        self.asset.file.close()

    def image_bytes(
        self,
        *,
        color,
    ):
        buffer = BytesIO()

        image = Image.new(
            "RGB",
            (
                600,
                600,
            ),
            color,
        )

        image.save(
            buffer,
            format="PNG",
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
            name="Plano Mídia",
            slug="plano-midia-privada",
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
            "product-asset-download",
            kwargs={
                "pk": self.asset.pk,
            },
        )

    def test_owner_can_download_own_product_asset(self):
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
            "image/png",
        )

        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )

        self.assertNotIn(
            "products/originals",
            response["Content-Disposition"],
        )

        self.assertEqual(
            self.response_content(
                response
            ),
            self.asset_bytes,
        )

    def test_other_tenant_cannot_download_product_asset(self):
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

    def test_anonymous_cannot_download_product_asset(self):
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

    def test_staff_without_superuser_has_no_global_product_asset_access(self):
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

    def test_superadmin_can_download_product_asset_globally(self):
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
            self.asset_bytes,
        )

    def test_blocked_subscription_can_download_existing_product_asset(self):
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

    def test_product_serializer_uses_authorized_url_without_storage_path(self):
        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            reverse(
                "product-detail",
                kwargs={
                    "pk": self.product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            f"/api/products/assets/{self.asset.pk}/download/",
            response.data["original_image_url"],
        )

        self.assertNotIn(
            "/media/",
            response.data["original_image_url"],
        )

        self.assertNotIn(
            "products/originals",
            response.data["original_image_url"],
        )

        self.assertNotIn(
            "file",
            response.data["assets"][0],
        )

        self.assertIn(
            f"/api/products/assets/{self.asset.pk}/download/",
            response.data["assets"][0]["file_url"],
        )

    def test_missing_product_asset_file_returns_safe_404(self):
        missing_asset = ProductAsset.objects.create(
            product=self.product,
            asset_type=AssetType.ORIGINAL,
            file="products/originals/2099/01/missing.png",
            mime_type="image/png",
            width=600,
            height=600,
            file_size=1,
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            reverse(
                "product-asset-download",
                kwargs={
                    "pk": missing_asset.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertNotIn(
            "products/originals",
            str(response.content),
        )


class ProductPermanentDeletionTests(
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
            name="Empresa Delete A",
            slug="empresa-delete-a",
        )

        self.other_organization = Organization.objects.create(
            name="Empresa Delete B",
            slug="empresa-delete-b",
        )

        self.user = User.objects.create_user(
            email="delete-a@example.com",
            password="senha-teste",
            name="Cliente Delete A",
            organization=self.organization,
            role="OWNER",
        )

        self.other_user = User.objects.create_user(
            email="delete-b@example.com",
            password="senha-teste",
            name="Cliente Delete B",
            organization=self.other_organization,
            role="OWNER",
        )

        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=8,
            purchased_balance=3,
            balance=11,
        )

    def image_bytes(
        self,
        *,
        image_format="PNG",
    ):
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
            format=image_format,
        )

        return buffer.getvalue()

    def create_product_with_asset(
        self,
    ):
        product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Produto Delete",
            category=ProductCategory.EARRING,
        )

        content = self.image_bytes()

        asset = ProductAsset.objects.create(
            product=product,
            asset_type=AssetType.ORIGINAL,
            mime_type="image/png",
            width=600,
            height=600,
            file_size=len(
                content
            ),
        )

        asset.file.save(
            "original-delete.png",
            ContentFile(
                content
            ),
            save=True,
        )

        asset.file.close()

        return product, asset

    def add_generation_with_image(
        self,
        product,
        key,
    ):
        generation = Generation.objects.create(
            organization=self.organization,
            user=self.user,
            product=product,
            mode=GenerationMode.STILL,
            status=GenerationStatus.COMPLETED,
            idempotency_key=key,
            credit_cost=1,
        )

        content = self.image_bytes(
            image_format="JPEG"
        )

        image = GeneratedImage.objects.create(
            generation=generation,
            mime_type="image/jpeg",
            width=600,
            height=600,
            file_size=len(
                content
            ),
        )

        image.file.save(
            f"{key}.jpg",
            ContentFile(
                content
            ),
            save=True,
        )

        image.file.close()

        CreditTransaction.objects.create(
            wallet=self.wallet,
            generation=generation,
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

        return generation, image

    def create_blocked_subscription(self):
        plan = Plan.objects.create(
            name="Plano Delete",
            slug="plano-delete-product",
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

    def test_delete_product_without_generation_removes_asset_and_file(self):
        product, asset = self.create_product_with_asset()
        asset_name = asset.file.name
        storage = asset.file.storage

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertFalse(
            ProductAsset.objects.filter(
                pk=asset.pk
            ).exists()
        )

        self.assertFalse(
            storage.exists(
                asset_name
            )
        )

    def test_delete_product_with_generations_removes_visual_data_and_files(self):
        product, asset = self.create_product_with_asset()
        first_generation, first_image = self.add_generation_with_image(
            product,
            "generated-delete-one",
        )
        second_generation, second_image = self.add_generation_with_image(
            product,
            "generated-delete-two",
        )

        storage = asset.file.storage
        names = [
            asset.file.name,
            first_image.file.name,
            second_image.file.name,
        ]

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertFalse(
            ProductAsset.objects.filter(
                product_id=product.pk
            ).exists()
        )

        self.assertFalse(
            Generation.objects.filter(
                pk__in=[
                    first_generation.pk,
                    second_generation.pk,
                ]
            ).exists()
        )

        self.assertFalse(
            GeneratedImage.objects.filter(
                pk__in=[
                    first_image.pk,
                    second_image.pk,
                ]
            ).exists()
        )

        for name in names:
            with self.subTest(
                name=name
            ):
                self.assertFalse(
                    storage.exists(
                        name
                    )
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
            2,
        )

        self.assertEqual(
            CreditTransaction.objects.filter(
                type=CreditTransactionType.REFUND
            ).count(),
            0,
        )

    def test_other_tenant_cannot_delete_product_or_file(self):
        product, asset = self.create_product_with_asset()
        asset_name = asset.file.name
        storage = asset.file.storage

        self.client.force_authenticate(
            self.other_user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertTrue(
            storage.exists(
                asset_name
            )
        )

    def test_anonymous_cannot_delete_product(self):
        product, asset = self.create_product_with_asset()
        asset_name = asset.file.name
        storage = asset.file.storage

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
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
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertTrue(
            storage.exists(
                asset_name
            )
        )

    def test_blocked_subscription_can_delete_own_product(self):
        self.create_blocked_subscription()
        product, asset = self.create_product_with_asset()
        asset_name = asset.file.name
        storage = asset.file.storage

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertFalse(
            storage.exists(
                asset_name
            )
        )

    def test_product_assets_are_not_available_after_product_delete(self):
        product, asset = self.create_product_with_asset()
        asset_download_url = reverse(
            "product-asset-download",
            kwargs={
                "pk": asset.pk,
            },
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        response = self.client.get(
            asset_download_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_missing_product_file_does_not_block_database_delete(self):
        product = Product.objects.create(
            organization=self.organization,
            created_by=self.user,
            name="Produto Arquivo Ausente",
            category=ProductCategory.EARRING,
        )

        asset = ProductAsset.objects.create(
            product=product,
            asset_type=AssetType.ORIGINAL,
            file="products/originals/2099/01/missing.png",
            mime_type="image/png",
            width=600,
            height=600,
            file_size=1,
        )

        self.client.force_authenticate(
            self.user
        )

        response = self.client.delete(
            reverse(
                "product-detail",
                kwargs={
                    "pk": product.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            204,
        )

        self.assertFalse(
            Product.objects.filter(
                pk=product.pk
            ).exists()
        )

        self.assertFalse(
            ProductAsset.objects.filter(
                pk=asset.pk
            ).exists()
        )

class ProductPaginationTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Empresa Paginação Produtos A",
            slug="empresa-paginacao-produtos-a",
        )

        self.other_organization = Organization.objects.create(
            name="Empresa Paginação Produtos B",
            slug="empresa-paginacao-produtos-b",
        )

        self.user = User.objects.create_user(
            email="produtos-paginacao-a@example.com",
            password="senha-teste",
            name="Cliente Paginação A",
            organization=self.organization,
            role="OWNER",
        )

        self.other_user = User.objects.create_user(
            email="produtos-paginacao-b@example.com",
            password="senha-teste",
            name="Cliente Paginação B",
            organization=self.other_organization,
            role="OWNER",
        )

        self.client.force_authenticate(
            self.user
        )

    def create_product(
        self,
        *,
        organization,
        user,
        index,
        category=ProductCategory.EARRING,
    ):
        product = Product.objects.create(
            organization=organization,
            created_by=user,
            name=f"Produto Página {index:02d}",
            category=category,
        )

        created_at = (
            timezone.now()
            + timezone.timedelta(
                minutes=index
            )
        )

        Product.objects.filter(
            pk=product.pk
        ).update(
            created_at=created_at
        )

        product.refresh_from_db()

        return product

    def create_dataset(self):
        for index in range(25):
            category = (
                ProductCategory.RING
                if index < 13
                else ProductCategory.EARRING
            )

            self.create_product(
                organization=self.organization,
                user=self.user,
                index=index,
                category=category,
            )

        for index in range(10):
            self.create_product(
                organization=self.other_organization,
                user=self.other_user,
                index=index,
            )

    def test_product_list_is_paginated_by_twelve_and_tenant_scoped(self):
        self.create_dataset()

        response = self.client.get(
            reverse(
                "product-list"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            25,
        )

        self.assertEqual(
            len(response.data["results"]),
            12,
        )

        self.assertEqual(
            response.data["results"][0]["name"],
            "Produto Página 24",
        )

        names = {
            product["name"]
            for product in response.data["results"]
        }

        self.assertNotIn(
            "Produto Página 09",
            names,
        )

        response = self.client.get(
            reverse(
                "product-list"
            ),
            {
                "page": 3,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

    def test_product_list_filters_before_count_and_pagination(self):
        self.create_dataset()

        response = self.client.get(
            reverse(
                "product-list"
            ),
            {
                "category": ProductCategory.RING,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["count"],
            13,
        )

        self.assertEqual(
            len(response.data["results"]),
            12,
        )

        response = self.client.get(
            reverse(
                "product-list"
            ),
            {
                "category": ProductCategory.RING,
                "page": 2,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            len(response.data["results"]),
            1,
        )

    def test_invalid_product_page_returns_not_found(self):
        self.create_dataset()

        response = self.client.get(
            reverse(
                "product-list"
            ),
            {
                "page": 999,
            },
        )

        self.assertEqual(
            response.status_code,
            404,
        )
