import uuid
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.billing.models import (
    BillingCycle,
    CreditPackage,
    CreditPurchase,
    CreditPurchaseStatus,
    Plan,
    SubscriptionCheckoutAttempt,
    SubscriptionCheckoutAttemptStatus,
    StripeInvoiceRecord,
    StripeWebhookEvent,
    Subscription,
    SubscriptionStatus,
)
from apps.billing.services import (
    BillingAccessService,
    CreditPurchaseLimitExceededError,
    CreditPurchaseNotAllowedError,
    CreditPurchaseService,
    InactivePlanError,
    SubscriptionDelinquencyService,
    SubscriptionAccessStatus,
    SubscriptionRequiredError,
    SubscriptionService,
)
from apps.billing.stripe_services import (
    CreditPurchaseCheckoutService,
    StripeBillingError,
    StripeBillingService,
    StripeConfigurationError,
    StripeCreditPackageService,
    StripeCreditPurchaseSessionError,
    StripeLiveModeError,
    StripePlanService,
    StripeReconciliationError,
    StripeReconciliationService,
    StripeSyncError,
    StripeWebhookService,
)
from apps.credits.models import CreditTransaction, CreditTransactionType, CreditWallet
from apps.credits.services import CreditService
from apps.organizations.models import Organization


class BillingModelsTests(TestCase):
    def create_plan(self, *, slug="pro", name="Pro"):
        return Plan.objects.create(
            name=name,
            slug=slug,
            description="Plano comercial de teste.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=150,
            is_active=True,
            sort_order=10,
        )

    def create_organization(self, *, slug="org-test", name="Organização Teste"):
        return Organization.objects.create(
            name=name,
            slug=slug,
        )

    def create_subscription(self, *, organization=None, plan=None):
        organization = organization or self.create_organization()
        plan = plan or self.create_plan()
        now = timezone.now()

        return Subscription.objects.create(
            organization=organization,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=plan.price,
            credits_snapshot=plan.credits_per_cycle,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timezone.timedelta(days=30),
            next_billing_at=now + timezone.timedelta(days=30),
        )

    def test_create_valid_plan(self):
        plan = self.create_plan()

        self.assertEqual(plan.name, "Pro")
        self.assertEqual(plan.slug, "pro")
        self.assertEqual(plan.price, Decimal("99.90"))
        self.assertEqual(plan.billing_cycle, BillingCycle.MONTHLY)
        self.assertEqual(plan.credits_per_cycle, 150)
        self.assertTrue(plan.is_active)
        self.assertEqual(str(plan), "Pro (150 créditos)")

    def test_plan_slug_is_unique(self):
        self.create_plan(slug="pro", name="Pro")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_plan(slug="pro", name="Pro Duplicado")

    def test_create_subscription_for_organization(self):
        organization = self.create_organization()
        plan = self.create_plan()

        subscription = self.create_subscription(
            organization=organization,
            plan=plan,
        )

        self.assertEqual(subscription.organization, organization)
        self.assertEqual(subscription.plan, plan)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.price_snapshot, Decimal("99.90"))
        self.assertEqual(subscription.credits_snapshot, 150)
        self.assertEqual(organization.subscription, subscription)
        self.assertEqual(str(subscription), "Organização Teste → Pro")

    def test_organization_can_have_only_one_subscription(self):
        organization = self.create_organization()
        first_plan = self.create_plan(slug="pro", name="Pro")
        second_plan = self.create_plan(slug="plus", name="Plus")

        self.create_subscription(
            organization=organization,
            plan=first_plan,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_subscription(
                    organization=organization,
                    plan=second_plan,
                )

    def test_plan_with_subscription_is_protected_from_delete(self):
        plan = self.create_plan()
        self.create_subscription(plan=plan)

        with self.assertRaises(ProtectedError):
            plan.delete()

        self.assertTrue(Plan.objects.filter(pk=plan.pk).exists())
        self.assertEqual(Subscription.objects.count(), 1)

    def test_plan_can_be_deactivated_without_destroying_subscription(self):
        plan = self.create_plan()
        subscription = self.create_subscription(plan=plan)

        plan.is_active = False
        plan.save(update_fields=["is_active", "updated_at"])

        subscription.refresh_from_db()
        plan.refresh_from_db()

        self.assertFalse(plan.is_active)
        self.assertEqual(subscription.plan, plan)


class FakeStripeObject:
    def __init__(
        self,
        object_id,
    ):
        self.id = object_id


class FakeStripeProducts:
    def __init__(
        self,
        *,
        product_id="prod_test",
    ):
        self.product_id = product_id
        self.create_calls = []
        self.update_calls = []

    def create(
        self,
        *,
        params,
        options,
    ):
        self.create_calls.append(
            {
                "params": params,
                "options": options,
            }
        )

        return FakeStripeObject(
            self.product_id
        )

    def update(
        self,
        product_id,
        *,
        params,
    ):
        self.update_calls.append(
            {
                "product_id": product_id,
                "params": params,
            }
        )

        return FakeStripeObject(
            product_id
        )


class FakeStripePrices:
    def __init__(
        self,
        *,
        ids=None,
        error=None,
    ):
        self.ids = ids or [
            "price_test",
        ]
        self.error = error
        self.create_calls = []

    def create(
        self,
        *,
        params,
        options,
    ):
        self.create_calls.append(
            {
                "params": params,
                "options": options,
            }
        )

        if self.error:
            raise self.error

        object_id = self.ids[
            min(
                len(self.create_calls) - 1,
                len(self.ids) - 1,
            )
        ]

        return FakeStripeObject(
            object_id
        )


class FakeStripeV1:
    def __init__(
        self,
        *,
        products=None,
        prices=None,
    ):
        self.products = (
            products or
            FakeStripeProducts()
        )
        self.prices = (
            prices or
            FakeStripePrices()
        )


class FakeStripeClient:
    def __init__(
        self,
        *,
        products=None,
        prices=None,
    ):
        self.v1 = FakeStripeV1(
            products=products,
            prices=prices,
        )


@override_settings(
    STRIPE_SECRET_KEY="sk_test_123",
    STRIPE_CURRENCY="brl",
    STRIPE_ALLOW_LIVE_MODE=False,
)
class StripePlanServiceTests(TestCase):
    def create_plan(
        self,
        *,
        name="START",
        slug="start",
        price=Decimal("39.90"),
        credits_per_cycle=20,
        stripe_product_id=None,
        stripe_price_id=None,
        stripe_price_signature="",
        is_active=True,
    ):
        return Plan.objects.create(
            name=name,
            slug=slug,
            description="Plano comercial.",
            price=price,
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=credits_per_cycle,
            is_active=is_active,
            sort_order=10,
            stripe_product_id=stripe_product_id,
            stripe_price_id=stripe_price_id,
            stripe_price_signature=(
                stripe_price_signature
            ),
        )

    def test_decimal_to_cents_without_float(self):
        cases = [
            (
                Decimal("39.90"),
                3990,
            ),
            (
                Decimal("39.99"),
                3999,
            ),
            (
                Decimal("0.99"),
                99,
            ),
        ]

        for amount, expected in cases:
            with self.subTest(
                amount=amount
            ):
                self.assertEqual(
                    StripePlanService.to_cents(
                        amount
                    ),
                    expected,
                )

    def test_monthly_cycle_maps_to_stripe_month_interval(self):
        self.assertEqual(
            StripePlanService.interval(
                BillingCycle.MONTHLY
            ),
            "month",
        )

    def test_sync_creates_product_and_monthly_brl_price(self):
        plan = self.create_plan()
        fake = FakeStripeClient()

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake,
        ):
            StripePlanService.sync_plan(
                plan
            )

        plan.refresh_from_db()

        self.assertEqual(
            plan.stripe_product_id,
            "prod_test",
        )
        self.assertEqual(
            plan.stripe_price_id,
            "price_test",
        )
        self.assertEqual(
            plan.stripe_price_signature,
            "brl|3990|month",
        )
        self.assertTrue(
            plan.stripe_ready_for_checkout
        )

        product_params = (
            fake.v1.products
            .create_calls[0]["params"]
        )
        price_params = (
            fake.v1.prices
            .create_calls[0]["params"]
        )

        self.assertEqual(
            product_params["name"],
            "MARIED STUDIO — START",
        )
        self.assertEqual(
            price_params["unit_amount"],
            3990,
        )
        self.assertEqual(
            price_params["currency"],
            "brl",
        )
        self.assertEqual(
            price_params["recurring"]["interval"],
            "month",
        )
        self.assertEqual(
            price_params["metadata"]["maried_plan_id"],
            str(plan.pk),
        )
        self.assertNotIn(
            "credits_per_cycle",
            price_params["metadata"],
        )

    def test_changing_only_credits_does_not_create_new_price(self):
        plan = self.create_plan(
            stripe_product_id="prod_existing",
            stripe_price_id="price_a",
            stripe_price_signature="brl|3990|month",
            credits_per_cycle=20,
        )
        plan.credits_per_cycle = 25
        plan.save(
            update_fields=[
                "credits_per_cycle",
                "updated_at",
            ]
        )
        fake = FakeStripeClient()

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake,
        ):
            StripePlanService.sync_plan(
                plan
            )

        plan.refresh_from_db()

        self.assertEqual(
            plan.stripe_price_id,
            "price_a",
        )
        self.assertEqual(
            fake.v1.prices.create_calls,
            [],
        )
        self.assertEqual(
            len(fake.v1.products.update_calls),
            1,
        )

    def test_changing_price_versions_price_without_deleting_old_price(self):
        plan = self.create_plan(
            price=Decimal("49.90"),
            stripe_product_id="prod_existing",
            stripe_price_id="price_a",
            stripe_price_signature="brl|3990|month",
        )
        fake = FakeStripeClient(
            prices=FakeStripePrices(
                ids=[
                    "price_b",
                ]
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake,
        ):
            StripePlanService.sync_plan(
                plan
            )

        plan.refresh_from_db()

        self.assertEqual(
            plan.stripe_price_id,
            "price_b",
        )
        self.assertEqual(
            plan.stripe_price_signature,
            "brl|4990|month",
        )
        self.assertEqual(
            fake.v1.prices.create_calls[0]["params"][
                "unit_amount"
            ],
            4990,
        )

    def test_retry_after_price_failure_reuses_persisted_product(self):
        plan = self.create_plan()
        failing = FakeStripeClient(
            prices=FakeStripePrices(
                error=RuntimeError(
                    "network"
                )
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=failing,
        ):
            with self.assertRaises(
                StripeSyncError
            ):
                StripePlanService.sync_plan(
                    plan
                )

        plan.refresh_from_db()
        self.assertEqual(
            plan.stripe_product_id,
            "prod_test",
        )
        self.assertFalse(
            plan.stripe_price_id
        )

        retry = FakeStripeClient()

        with patch.object(
            StripePlanService,
            "client",
            return_value=retry,
        ):
            StripePlanService.sync_plan(
                plan
            )

        self.assertEqual(
            retry.v1.products.create_calls,
            [],
        )
        self.assertEqual(
            len(retry.v1.prices.create_calls),
            1,
        )

    @override_settings(
        STRIPE_SECRET_KEY="",
    )
    def test_missing_stripe_key_fails_safely(self):
        with self.assertRaises(
            StripeConfigurationError
        ):
            StripePlanService.sync_plan(
                self.create_plan()
            )

    @override_settings(
        STRIPE_SECRET_KEY="sk_live_123",
        STRIPE_ALLOW_LIVE_MODE=False,
    )
    def test_live_mode_key_is_blocked_by_default(self):
        with self.assertRaises(
            StripeLiveModeError
        ):
            StripePlanService.sync_plan(
                self.create_plan()
            )

    def test_incomplete_stripe_response_does_not_persist_price(self):
        plan = self.create_plan()
        fake = FakeStripeClient(
            prices=FakeStripePrices(
                ids=[
                    None,
                ]
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake,
        ):
            with self.assertRaises(
                StripeSyncError
            ):
                StripePlanService.sync_plan(
                    plan
                )

        plan.refresh_from_db()
        self.assertFalse(
            plan.stripe_price_id
        )
        self.assertFalse(
            plan.stripe_ready_for_checkout
        )


class SubscriptionServiceTests(TestCase):
    def create_plan(
        self,
        *,
        slug="pro",
        name="Pro",
        price=Decimal("99.90"),
        credits_per_cycle=150,
        is_active=True,
    ):
        return Plan.objects.create(
            name=name,
            slug=slug,
            description="Plano comercial de teste.",
            price=price,
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=credits_per_cycle,
            is_active=is_active,
            sort_order=10,
        )

    def create_organization(self, *, slug="org-test", name="Organização Teste"):
        return Organization.objects.create(
            name=name,
            slug=slug,
        )

    def test_activate_creates_active_subscription_with_snapshots_and_period(self):
        organization = self.create_organization()
        plan = self.create_plan()
        starts_at = timezone.make_aware(
            timezone.datetime(
                2026,
                1,
                31,
                10,
                0,
                0,
            )
        )

        subscription = SubscriptionService.activate(
            organization=organization,
            plan=plan,
            starts_at=starts_at,
        )

        self.assertEqual(subscription.organization, organization)
        self.assertEqual(subscription.plan, plan)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.price_snapshot, Decimal("99.90"))
        self.assertEqual(subscription.credits_snapshot, 150)
        self.assertEqual(subscription.started_at, starts_at)
        self.assertEqual(subscription.current_period_start, starts_at)
        self.assertEqual(
            subscription.current_period_end,
            timezone.make_aware(
                timezone.datetime(
                    2026,
                    2,
                    28,
                    10,
                    0,
                    0,
                )
            ),
        )
        self.assertEqual(
            subscription.next_billing_at,
            subscription.current_period_end,
        )

    def test_activate_rejects_inactive_plan(self):
        organization = self.create_organization()
        plan = self.create_plan(is_active=False)

        with self.assertRaises(InactivePlanError):
            SubscriptionService.activate(
                organization=organization,
                plan=plan,
            )

        self.assertFalse(
            Subscription.objects.filter(
                organization=organization,
            ).exists()
        )

    def test_activate_keeps_snapshots_when_plan_changes_later(self):
        organization = self.create_organization()
        plan = self.create_plan(
            price=Decimal("99.90"),
            credits_per_cycle=150,
        )

        subscription = SubscriptionService.activate(
            organization=organization,
            plan=plan,
        )

        plan.price = Decimal("119.90")
        plan.credits_per_cycle = 180
        plan.save(
            update_fields=[
                "price",
                "credits_per_cycle",
                "updated_at",
            ]
        )

        subscription.refresh_from_db()

        self.assertEqual(subscription.price_snapshot, Decimal("99.90"))
        self.assertEqual(subscription.credits_snapshot, 150)

    def test_activate_applies_plan_credits_through_credit_service(self):
        organization = self.create_organization()
        plan = self.create_plan(credits_per_cycle=150)

        subscription = SubscriptionService.activate(
            organization=organization,
            plan=plan,
        )

        wallet = CreditWallet.objects.get(
            organization=organization,
        )
        self.assertEqual(wallet.plan_balance, subscription.credits_snapshot)
        self.assertEqual(wallet.purchased_balance, 0)
        self.assertEqual(wallet.balance, subscription.credits_snapshot)
        self.assertTrue(
            CreditTransaction.objects.filter(
                wallet=wallet,
                type=CreditTransactionType.PLAN_GRANT,
                amount=subscription.credits_snapshot,
            ).exists()
        )

    def test_activate_preserves_purchased_credits(self):
        organization = self.create_organization()
        plan = self.create_plan(credits_per_cycle=150)
        wallet = CreditWallet.objects.create(
            organization=organization,
        )

        CreditService.add_purchased_credits(
            wallet,
            40,
        )

        SubscriptionService.activate(
            organization=organization,
            plan=plan,
        )

        wallet.refresh_from_db()

        self.assertEqual(wallet.plan_balance, 150)
        self.assertEqual(wallet.purchased_balance, 40)
        self.assertEqual(wallet.balance, 190)

    def test_repeated_activation_does_not_duplicate_plan_credits(self):
        organization = self.create_organization()
        plan = self.create_plan(credits_per_cycle=150)
        starts_at = timezone.now()

        first = SubscriptionService.activate(
            organization=organization,
            plan=plan,
            starts_at=starts_at,
        )
        second = SubscriptionService.activate(
            organization=organization,
            plan=plan,
            starts_at=starts_at,
        )

        wallet = CreditWallet.objects.get(
            organization=organization,
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(wallet.plan_balance, 150)
        self.assertEqual(
            CreditTransaction.objects.filter(
                wallet=wallet,
                type=CreditTransactionType.PLAN_GRANT,
            ).count(),
            1,
        )

    def test_activate_rolls_back_subscription_when_credit_service_fails(self):
        organization = self.create_organization()
        plan = self.create_plan()

        with patch(
            "apps.billing.services.CreditService.renew_plan_credits",
            side_effect=RuntimeError("falha simulada"),
        ):
            with self.assertRaises(RuntimeError):
                SubscriptionService.activate(
                    organization=organization,
                    plan=plan,
                )

        self.assertFalse(
            Subscription.objects.filter(
                organization=organization,
            ).exists()
        )
        self.assertFalse(
            CreditWallet.objects.filter(
                organization=organization,
            ).exists()
        )

    def test_renew_current_cycle_expires_plan_credits_and_preserves_purchased(self):
        organization = self.create_organization()
        plan = self.create_plan(credits_per_cycle=150)
        starts_at = timezone.make_aware(
            timezone.datetime(
                2026,
                1,
                31,
                10,
                0,
                0,
            )
        )
        subscription = SubscriptionService.activate(
            organization=organization,
            plan=plan,
            starts_at=starts_at,
        )
        wallet = CreditWallet.objects.get(
            organization=organization,
        )

        CreditService.add_purchased_credits(
            wallet,
            40,
        )
        wallet.refresh_from_db()

        renewed = SubscriptionService.renew_current_cycle(
            subscription=subscription,
        )
        wallet.refresh_from_db()

        self.assertEqual(
            renewed.current_period_start,
            timezone.make_aware(
                timezone.datetime(
                    2026,
                    2,
                    28,
                    10,
                    0,
                    0,
                )
            ),
        )
        self.assertEqual(
            renewed.current_period_end,
            timezone.make_aware(
                timezone.datetime(
                    2026,
                    3,
                    28,
                    10,
                    0,
                    0,
                )
            ),
        )
        self.assertEqual(wallet.plan_balance, 150)
        self.assertEqual(wallet.purchased_balance, 40)
        self.assertEqual(wallet.balance, 190)
        self.assertTrue(
            CreditTransaction.objects.filter(
                wallet=wallet,
                type=CreditTransactionType.PLAN_EXPIRE,
            ).exists()
        )


class BillingAccessServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Organização Access",
            slug="org-access-billing",
        )

        self.plan = Plan.objects.create(
            name="Plano Access",
            slug="plano-access-billing",
            description="Plano usado em testes de acesso.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
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
        status=SubscriptionStatus.ACTIVE,
        period_end=None,
    ):
        period_start = self.at(
            2026,
            7,
            25,
        )

        period_end = period_end or self.at(
            2026,
            8,
            25,
        )

        return Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=status,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=period_start,
            current_period_start=period_start,
            current_period_end=period_end,
            next_billing_at=period_end,
        )

    def evaluate(self, subscription, year, month, day):
        return BillingAccessService.evaluate_subscription(
            subscription,
            now=self.at(
                year,
                month,
                day,
            ),
        )

    def test_active_subscription_before_due_date_is_allowed(self):
        subscription = self.create_subscription()

        access = self.evaluate(
            subscription,
            2026,
            8,
            24,
        )

        self.assertEqual(
            access.status,
            SubscriptionAccessStatus.ACTIVE,
        )

        self.assertTrue(
            access.allowed
        )

    def test_due_date_is_still_active(self):
        subscription = self.create_subscription()

        access = self.evaluate(
            subscription,
            2026,
            8,
            25,
        )

        self.assertEqual(
            access.status,
            SubscriptionAccessStatus.ACTIVE,
        )

    def test_three_calendar_grace_days_are_allowed(self):
        subscription = self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
        )

        for day in (
            26,
            27,
            28,
        ):
            with self.subTest(day=day):
                access = self.evaluate(
                    subscription,
                    2026,
                    8,
                    day,
                )

                self.assertEqual(
                    access.status,
                    SubscriptionAccessStatus.GRACE,
                )

                self.assertTrue(
                    access.allowed
                )

    def test_fourth_day_after_due_date_is_blocked(self):
        subscription = self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
        )

        access = self.evaluate(
            subscription,
            2026,
            8,
            29,
        )

        self.assertEqual(
            access.status,
            SubscriptionAccessStatus.BLOCKED,
        )

        self.assertFalse(
            access.allowed
        )

    def test_grace_crossing_month_boundary(self):
        subscription = self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                8,
                30,
            ),
        )

        for year, month, day in (
            (2026, 8, 31),
            (2026, 9, 1),
            (2026, 9, 2),
        ):
            with self.subTest(day=day):
                access = self.evaluate(
                    subscription,
                    year,
                    month,
                    day,
                )

                self.assertEqual(
                    access.status,
                    SubscriptionAccessStatus.GRACE,
                )

        blocked = self.evaluate(
            subscription,
            2026,
            9,
            3,
        )

        self.assertEqual(
            blocked.status,
            SubscriptionAccessStatus.BLOCKED,
        )

    def test_grace_crossing_year_boundary(self):
        subscription = self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
            period_end=self.at(
                2026,
                12,
                30,
            ),
        )

        for year, month, day in (
            (2026, 12, 31),
            (2027, 1, 1),
            (2027, 1, 2),
        ):
            with self.subTest(day=day):
                access = self.evaluate(
                    subscription,
                    year,
                    month,
                    day,
                )

                self.assertEqual(
                    access.status,
                    SubscriptionAccessStatus.GRACE,
                )

        blocked = self.evaluate(
            subscription,
            2027,
            1,
            3,
        )

        self.assertEqual(
            blocked.status,
            SubscriptionAccessStatus.BLOCKED,
        )

    def test_missing_subscription_is_blocked(self):
        access = BillingAccessService.evaluate_subscription(
            None,
            now=self.at(
                2026,
                8,
                25,
            ),
        )

        self.assertEqual(
            access.status,
            SubscriptionAccessStatus.BLOCKED,
        )

    def test_non_operational_statuses_are_blocked(self):
        for subscription_status in (
            SubscriptionStatus.PENDING,
            SubscriptionStatus.SUSPENDED,
            SubscriptionStatus.CANCELED,
        ):
            with self.subTest(status=subscription_status):
                subscription = self.create_subscription(
                    status=subscription_status,
                    period_end=self.at(
                        2026,
                        9,
                        25,
                    ),
                )

                access = self.evaluate(
                    subscription,
                    2026,
                    8,
                    25,
                )

                self.assertEqual(
                    access.status,
                    SubscriptionAccessStatus.BLOCKED,
                )

                subscription.delete()

    def test_ensure_operational_access_raises_for_blocked_subscription(self):
        self.create_subscription(
            status=SubscriptionStatus.PAST_DUE,
        )

        with self.assertRaises(
            SubscriptionRequiredError
        ):
            BillingAccessService.ensure_operational_access(
                self.organization,
                now=self.at(
                    2026,
                    8,
                    29,
                ),
            )

    def test_renewal_restores_active_access_and_preserves_purchased_credits(self):
        subscription = self.create_subscription(
            status=SubscriptionStatus.ACTIVE,
        )

        wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=8,
            purchased_balance=17,
            balance=25,
        )

        renewed = SubscriptionService.renew_current_cycle(
            subscription=subscription,
        )

        wallet.refresh_from_db()

        access = BillingAccessService.evaluate_subscription(
            renewed,
            now=self.at(
                2026,
                8,
                29,
            ),
        )

        self.assertEqual(
            access.status,
            SubscriptionAccessStatus.ACTIVE,
        )

        self.assertEqual(
            wallet.plan_balance,
            50,
        )

        self.assertEqual(
            wallet.purchased_balance,
            17,
        )


class CurrentSubscriptionApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()

        self.organization = Organization.objects.create(
            name="Organização Assinatura",
            slug="org-assinatura-api",
        )

        self.user = User.objects.create_user(
            email="assinatura-api@example.com",
            password="senha-teste",
            name="Cliente Assinatura",
            organization=self.organization,
            role="OWNER",
        )

        self.other_organization = Organization.objects.create(
            name="Outra Organização Assinatura",
            slug="outra-org-assinatura-api",
        )

        self.plan = Plan.objects.create(
            name="Plano API",
            slug="plano-api-billing",
            description="Plano usado em teste de API.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=50,
            is_active=True,
        )

        self.other_plan = Plan.objects.create(
            name="Plano Outro Cliente",
            slug="plano-outro-cliente-billing",
            description="Plano de outra organização.",
            price=Decimal("199.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=999,
            is_active=True,
        )

        self.period_end = timezone.make_aware(
            timezone.datetime(
                2026,
                8,
                25,
                10,
                0,
                0,
            )
        )

        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.PAST_DUE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=self.period_end - timezone.timedelta(days=30),
            current_period_start=self.period_end - timezone.timedelta(days=30),
            current_period_end=self.period_end,
            next_billing_at=self.period_end,
        )

        Subscription.objects.create(
            organization=self.other_organization,
            plan=self.other_plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.other_plan.price,
            credits_snapshot=self.other_plan.credits_per_cycle,
            started_at=self.period_end - timezone.timedelta(days=30),
            current_period_start=self.period_end - timezone.timedelta(days=30),
            current_period_end=self.period_end,
            next_billing_at=self.period_end,
        )

    def test_current_subscription_returns_operational_status(self):
        self.client.force_authenticate(
            self.user
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=timezone.make_aware(
                timezone.datetime(
                    2026,
                    8,
                    28,
                    10,
                    0,
                    0,
                )
            ),
        ):
            response = self.client.get(
                reverse(
                    "billing:current-subscription"
                )
            )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["operational_status"],
            SubscriptionAccessStatus.GRACE,
        )

        self.assertEqual(
            response.data["grace_until"],
            "2026-08-28",
        )

        self.assertEqual(
            response.data["plan_name"],
            "Plano API",
        )
        self.assertEqual(
            response.data["plan"]["id"],
            str(self.plan.pk),
        )
        self.assertEqual(
            response.data["plan"]["credits_per_cycle"],
            50,
        )
        self.assertEqual(
            response.data["billing_cycle"],
            BillingCycle.MONTHLY,
        )
        self.assertEqual(
            response.data["credits_per_cycle"],
            50,
        )
        self.assertIsNotNone(
            response.data["current_period_start"],
        )
        self.assertIsNotNone(
            response.data["current_period_end"],
        )
        self.assertIsNotNone(
            response.data["next_billing_at"],
        )

    def test_current_subscription_ignores_arbitrary_organization_id(self):
        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            (
                reverse("billing:current-subscription")
                + f"?organization_id={self.other_organization.pk}"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["plan_name"],
            "Plano API",
        )
        self.assertNotEqual(
            response.data["plan_name"],
            "Plano Outro Cliente",
        )

    def test_anonymous_user_cannot_access_current_subscription(self):
        response = self.client.get(
            reverse(
                "billing:current-subscription"
            )
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

    def test_active_subscription_returns_active_status(self):
        self.subscription.status = SubscriptionStatus.ACTIVE
        self.subscription.current_period_end = self.period_end
        self.subscription.next_billing_at = self.period_end
        self.subscription.save(
            update_fields=[
                "status",
                "current_period_end",
                "next_billing_at",
                "updated_at",
            ]
        )
        self.client.force_authenticate(
            self.user
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=timezone.make_aware(
                timezone.datetime(
                    2026,
                    8,
                    24,
                    10,
                    0,
                    0,
                )
            ),
        ):
            response = self.client.get(
                reverse(
                    "billing:current-subscription"
                )
            )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["operational_status"],
            SubscriptionAccessStatus.ACTIVE,
        )

    def test_blocked_subscription_is_still_readable(self):
        self.client.force_authenticate(
            self.user
        )

        with patch(
            "apps.billing.services.timezone.now",
            return_value=timezone.make_aware(
                timezone.datetime(
                    2026,
                    8,
                    29,
                    10,
                    0,
                    0,
                )
            ),
        ):
            response = self.client.get(
                reverse(
                    "billing:current-subscription"
                )
            )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["operational_status"],
            SubscriptionAccessStatus.BLOCKED,
        )
        self.assertEqual(
            response.data["plan_name"],
            "Plano API",
        )

    def test_without_subscription_returns_safe_empty_payload(self):
        self.subscription.delete()
        self.client.force_authenticate(
            self.user
        )

        response = self.client.get(
            reverse(
                "billing:current-subscription"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.data["operational_status"],
            SubscriptionAccessStatus.BLOCKED,
        )
        self.assertIsNone(
            response.data["status"],
        )
        self.assertIsNone(
            response.data["plan"],
        )


class FakeStripeCustomers:
    def __init__(self):
        self.create_calls = []

    def create(self, *, params, options):
        self.create_calls.append({"params": params, "options": options})
        return FakeStripeObject("cus_test_123")


class FakeStripeCheckoutSessions:
    def __init__(
        self,
        *,
        side_effect=None,
        retrieve_response=None,
        retrieve_side_effect=None,
        expire_response=None,
        expire_side_effect=None,
    ):
        self.create_calls = []
        self.retrieve_calls = []
        self.expire_calls = []
        self.side_effect = side_effect
        self.retrieve_response = retrieve_response
        self.retrieve_side_effect = retrieve_side_effect
        self.expire_response = expire_response
        self.expire_side_effect = expire_side_effect

    def create(self, *, params, options):
        self.create_calls.append({"params": params, "options": options})
        if self.side_effect:
            raise self.side_effect

        session_id = f"cs_test_{len(self.create_calls)}"
        session = FakeStripeObject(session_id)
        session.url = f"https://checkout.stripe.com/c/pay/{session_id}"
        session.expires_at = int(
            (
                timezone.now() +
                timezone.timedelta(hours=24)
            ).timestamp()
        )
        return session

    def retrieve(self, session_id):
        self.retrieve_calls.append(session_id)

        if self.retrieve_side_effect:
            raise self.retrieve_side_effect

        if self.retrieve_response is not None:
            return self.retrieve_response

        session = FakeStripeObject(session_id)
        session.status = "open"
        session.payment_status = "unpaid"
        return session

    def expire(self, session_id):
        self.expire_calls.append(session_id)

        if self.expire_side_effect:
            raise self.expire_side_effect

        if self.expire_response is not None:
            return self.expire_response

        session = FakeStripeObject(session_id)
        session.status = "expired"
        session.payment_status = "unpaid"
        return session


class FakeStripeCheckoutNamespace:
    def __init__(
        self,
        *,
        side_effect=None,
        retrieve_response=None,
        retrieve_side_effect=None,
        expire_response=None,
        expire_side_effect=None,
    ):
        self.sessions = FakeStripeCheckoutSessions(
            side_effect=side_effect,
            retrieve_response=retrieve_response,
            retrieve_side_effect=retrieve_side_effect,
            expire_response=expire_response,
            expire_side_effect=expire_side_effect,
        )


class FakeStripeInvoices:
    def __init__(
        self,
        *,
        invoice=None,
        invoices=None,
        side_effect=None,
        list_side_effect=None,
    ):
        self.invoice = invoice
        self.invoices = invoices or []
        self.side_effect = side_effect
        self.list_side_effect = list_side_effect
        self.retrieve_calls = []
        self.list_calls = []

    def retrieve(self, invoice_id, *, params=None):
        self.retrieve_calls.append(
            {
                "invoice_id": invoice_id,
                "params": params,
            }
        )

        if self.side_effect:
            raise self.side_effect

        return self.invoice

    def list(self, *, params=None):
        self.list_calls.append(
            {
                "params": params,
            }
        )

        if self.list_side_effect:
            raise self.list_side_effect

        return {
            "data": self.invoices,
        }


class FakeStripeSubscriptions:
    def __init__(
        self,
        *,
        subscription=None,
        subscriptions=None,
        retrieve_side_effect=None,
        list_side_effect=None,
    ):
        self.subscription = subscription
        self.subscriptions = subscriptions or []
        self.retrieve_side_effect = retrieve_side_effect
        self.list_side_effect = list_side_effect
        self.retrieve_calls = []
        self.list_calls = []

    def retrieve(self, subscription_id, *, params=None):
        self.retrieve_calls.append(
            {
                "subscription_id": subscription_id,
                "params": params,
            }
        )

        if self.retrieve_side_effect:
            raise self.retrieve_side_effect

        return self.subscription

    def list(self, *, params=None):
        self.list_calls.append(
            {
                "params": params,
            }
        )

        if self.list_side_effect:
            raise self.list_side_effect

        return {
            "data": self.subscriptions,
        }


class FakeStripeV1Billing:
    def __init__(
        self,
        *,
        checkout_side_effect=None,
        invoice=None,
        invoices=None,
        invoice_side_effect=None,
        invoice_list_side_effect=None,
        subscription=None,
        subscriptions=None,
        subscription_retrieve_side_effect=None,
        subscription_list_side_effect=None,
        checkout_retrieve_response=None,
        checkout_retrieve_side_effect=None,
        checkout_expire_response=None,
        checkout_expire_side_effect=None,
    ):
        self.customers = FakeStripeCustomers()
        self.checkout = FakeStripeCheckoutNamespace(
            side_effect=checkout_side_effect,
            retrieve_response=checkout_retrieve_response,
            retrieve_side_effect=checkout_retrieve_side_effect,
            expire_response=checkout_expire_response,
            expire_side_effect=checkout_expire_side_effect,
        )
        self.invoices = FakeStripeInvoices(
            invoice=invoice,
            invoices=invoices,
            side_effect=invoice_side_effect,
            list_side_effect=invoice_list_side_effect,
        )
        self.subscriptions = FakeStripeSubscriptions(
            subscription=subscription,
            subscriptions=subscriptions,
            retrieve_side_effect=subscription_retrieve_side_effect,
            list_side_effect=subscription_list_side_effect,
        )


class FakeStripeBillingClient:
    def __init__(
        self,
        *,
        checkout_side_effect=None,
        invoice=None,
        invoices=None,
        invoice_side_effect=None,
        invoice_list_side_effect=None,
        subscription=None,
        subscriptions=None,
        subscription_retrieve_side_effect=None,
        subscription_list_side_effect=None,
        checkout_retrieve_response=None,
        checkout_retrieve_side_effect=None,
        checkout_expire_response=None,
        checkout_expire_side_effect=None,
    ):
        self.v1 = FakeStripeV1Billing(
            checkout_side_effect=checkout_side_effect,
            invoice=invoice,
            invoices=invoices,
            invoice_side_effect=invoice_side_effect,
            invoice_list_side_effect=invoice_list_side_effect,
            subscription=subscription,
            subscriptions=subscriptions,
            subscription_retrieve_side_effect=(
                subscription_retrieve_side_effect
            ),
            subscription_list_side_effect=(
                subscription_list_side_effect
            ),
            checkout_retrieve_response=checkout_retrieve_response,
            checkout_retrieve_side_effect=checkout_retrieve_side_effect,
            checkout_expire_response=checkout_expire_response,
            checkout_expire_side_effect=checkout_expire_side_effect,
        )


class IdempotencyError(Exception):
    pass


class StripeCheckoutApiTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Checkout",
            slug="cliente-checkout",
        )
        self.user = get_user_model().objects.create_user(
            email="checkout@example.com",
            password="senha-teste",
            name="Cliente Checkout",
            organization=self.organization,
        )
        self.plan = Plan.objects.create(
            name="Start",
            slug="start-checkout",
            description="Plano Start",
            price=Decimal("39.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=20,
            is_active=True,
            stripe_product_id="prod_start",
            stripe_price_id="price_start",
            stripe_price_signature="brl|3990|month",
            stripe_sync_error="",
        )
        self.url = reverse("billing:subscription-checkout")
        self.client.force_authenticate(self.user)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_create_subscription_checkout_creates_customer_once(self):
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.stripe_customer_id, "cus_test_123")
        self.assertEqual(len(fake_client.v1.customers.create_calls), 1)
        self.assertEqual(response.data["checkout_session_id"], "cs_test_1")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_uses_plan_price_and_customer(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(fake_client.v1.customers.create_calls, [])
        checkout_call = fake_client.v1.checkout.sessions.create_calls[0]
        params = checkout_call["params"]
        self.assertEqual(params["mode"], "subscription")
        self.assertEqual(params["customer"], "cus_existing")
        self.assertEqual(
            params["line_items"],
            [{"price": "price_start", "quantity": 1}],
        )
        self.assertNotIn("payment_method_types", params)
        self.assertIn("/assinatura/sucesso", params["success_url"])
        self.assertIn("/assinatura?checkout=cancelled", params["cancel_url"])

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_persists_attempt_idempotency_key(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt = SubscriptionCheckoutAttempt.objects.get()
        checkout_call = fake_client.v1.checkout.sessions.create_calls[0]
        self.assertEqual(
            checkout_call["options"]["idempotency_key"],
            f"maried-checkout-{attempt.pk}",
        )
        self.assertEqual(
            checkout_call["params"]["metadata"]["maried_checkout_attempt_id"],
            str(attempt.pk),
        )
        self.assertEqual(
            attempt.status,
            SubscriptionCheckoutAttemptStatus.OPEN,
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_reuses_open_attempt(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            first_response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )
            second_response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            first_response.data,
            second_response.data,
        )
        self.assertEqual(
            len(fake_client.v1.checkout.sessions.create_calls),
            1,
        )
        self.assertEqual(
            SubscriptionCheckoutAttempt.objects.count(),
            1,
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_creates_new_attempt_after_expiration(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )
            attempt = SubscriptionCheckoutAttempt.objects.get()
            attempt.expires_at = timezone.now() - timezone.timedelta(minutes=1)
            attempt.save(update_fields=["expires_at", "updated_at"])

            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attempt.refresh_from_db()
        self.assertEqual(
            attempt.status,
            SubscriptionCheckoutAttemptStatus.EXPIRED,
        )
        self.assertEqual(
            len(fake_client.v1.checkout.sessions.create_calls),
            2,
        )
        self.assertEqual(
            SubscriptionCheckoutAttempt.objects.count(),
            2,
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_idempotency_error_returns_safe_response(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient(
            checkout_side_effect=IdempotencyError("raw stripe conflict")
        )

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["code"],
            "CHECKOUT_RETRY_REQUIRED",
        )
        self.assertNotIn(
            "raw stripe conflict",
            response.data["detail"],
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_subscription_checkout_provider_error_returns_safe_response(self):
        self.organization.stripe_customer_id = "cus_existing"
        self.organization.save(
            update_fields=["stripe_customer_id", "updated_at"]
        )
        fake_client = FakeStripeBillingClient(
            checkout_side_effect=RuntimeError("provider secret detail")
        )

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertEqual(
            response.data["code"],
            "CHECKOUT_UNAVAILABLE",
        )
        self.assertNotIn(
            "provider secret detail",
            response.data["detail"],
        )

    def test_checkout_rejects_unsynced_plan(self):
        self.plan.stripe_price_id = None
        self.plan.save(update_fields=["stripe_price_id", "updated_at"])

        response = self.client.post(
            self.url,
            {"plan_id": str(self.plan.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(
            SubscriptionCheckoutAttempt.objects.exists()
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_pending_subscription_allows_checkout_for_intended_plan(self):
        SubscriptionService.create_pending(
            organization=self.organization,
            plan=self.plan,
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(StripeBillingService, "client", return_value=fake_client):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            len(fake_client.v1.checkout.sessions.create_calls),
            1,
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_pending_subscription_rejects_checkout_for_other_plan(self):
        SubscriptionService.create_pending(
            organization=self.organization,
            plan=self.plan,
        )
        other_plan = Plan.objects.create(
            name="Bronze Checkout",
            slug="bronze-checkout",
            description="Outro plano",
            price=Decimal("79.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=40,
            is_active=True,
            stripe_product_id="prod_bronze",
            stripe_price_id="price_bronze",
            stripe_price_signature="brl|7990|month",
            stripe_sync_error="",
        )

        with patch.object(
            StripeBillingService,
            "client",
            return_value=FakeStripeBillingClient(),
        ):
            response = self.client.post(
                self.url,
                {"plan_id": str(other_plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            SubscriptionCheckoutAttempt.objects.exists()
        )

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_past_due_subscription_blocks_checkout_attempt(self):
        now = timezone.now()
        Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.PAST_DUE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=now - timezone.timedelta(days=31),
            current_period_start=now - timezone.timedelta(days=31),
            current_period_end=now - timezone.timedelta(days=1),
            next_billing_at=now - timezone.timedelta(days=1),
            stripe_subscription_id="sub_past_due",
        )

        with patch.object(
            StripeBillingService,
            "client",
            return_value=FakeStripeBillingClient(),
        ):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            SubscriptionCheckoutAttempt.objects.exists()
        )


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Webhook",
            slug="cliente-webhook",
            stripe_customer_id="cus_webhook",
        )
        self.plan = Plan.objects.create(
            name="Start Webhook",
            slug="start-webhook",
            description="Plano para webhook",
            price=Decimal("39.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=25,
            is_active=True,
            stripe_product_id="prod_webhook",
            stripe_price_id="price_webhook",
            stripe_price_signature="brl|3990|month",
            stripe_sync_error="",
        )

    def at(self, year, month, day):
        return timezone.make_aware(
            timezone.datetime(year, month, day, 10, 0, 0)
        )

    def timestamp(self, value):
        return int(value.timestamp())

    def test_checkout_completed_marks_attempt_without_granting_credits(self):
        attempt = SubscriptionCheckoutAttempt.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionCheckoutAttemptStatus.OPEN,
            stripe_customer_id="cus_webhook",
            stripe_price_id="price_webhook",
            stripe_checkout_session_id="cs_checkout_done",
            stripe_checkout_url=(
                "https://checkout.stripe.com/c/pay/cs_checkout_done"
            ),
            stripe_idempotency_key="maried-checkout-test",
            request_signature="cus_webhook|price_webhook|success|cancel",
        )
        event = {
            "id": "evt_checkout_done",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_checkout_done",
                    "customer": "cus_webhook",
                    "subscription": "sub_checkout_done",
                    "metadata": {
                        "maried_checkout_attempt_id": str(attempt.pk),
                    },
                },
            },
        }

        result = StripeWebhookService.process_event(event)

        attempt.refresh_from_db()
        self.assertTrue(result["processed"])
        self.assertEqual(
            attempt.status,
            SubscriptionCheckoutAttemptStatus.COMPLETED,
        )
        self.assertFalse(
            Subscription.objects.filter(
                organization=self.organization
            ).exists()
        )
        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def invoice_event(
        self,
        *,
        event_id="evt_paid_1",
        invoice_id="in_paid_1",
        subscription_id="sub_webhook",
        customer_id="cus_webhook",
        price_id="price_webhook",
        period_start=None,
        period_end=None,
        event_type="invoice.paid",
    ):
        period_start = period_start or self.at(2026, 1, 1)
        period_end = period_end or self.at(2026, 2, 1)

        return {
            "id": event_id,
            "type": event_type,
            "data": {
                "object": {
                    "id": invoice_id,
                    "customer": customer_id,
                    "subscription": subscription_id,
                    "status": "paid",
                    "subscription_details": {
                        "metadata": {
                            "maried_organization_id": str(self.organization.pk),
                            "maried_plan_id": str(self.plan.pk),
                        },
                    },
                    "lines": {
                        "data": [
                            {
                                "period": {
                                    "start": self.timestamp(period_start),
                                    "end": self.timestamp(period_end),
                                },
                                "pricing": {
                                    "price_details": {
                                        "price": price_id,
                                    }
                                },
                            }
                        ]
                    },
                }
            },
        }

    def invoice_payment_event(
        self,
        *,
        event_id="evt_invoice_payment_paid",
        invoice=None,
        invoice_id="in_paid_1",
    ):
        return {
            "id": event_id,
            "type": "invoice_payment.paid",
            "data": {
                "object": {
                    "id": "inpay_paid_1",
                    "object": "invoice_payment",
                    "status": "paid",
                    "amount_paid": 3990,
                    "currency": "brl",
                    "invoice": invoice or invoice_id,
                    "payment": {
                        "type": "payment_intent",
                        "payment_intent": "pi_paid_1",
                    },
                },
            },
        }

    def test_first_invoice_paid_activates_subscription_and_grants_credits(self):
        result = StripeWebhookService.process_event(self.invoice_event())

        self.assertTrue(result["processed"])
        self.assertEqual(result["cycle_type"], "FIRST")
        subscription = Subscription.objects.get(organization=self.organization)
        wallet = CreditWallet.objects.get(organization=self.organization)
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(subscription.stripe_subscription_id, "sub_webhook")
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(wallet.purchased_balance, 0)

    def test_invoice_payment_paid_with_expanded_invoice_activates_once(self):
        invoice = self.invoice_event(
            invoice_id="in_invoice_payment"
        )["data"]["object"]
        event = self.invoice_payment_event(
            invoice=invoice
        )

        result = StripeWebhookService.process_event(event)

        subscription = Subscription.objects.get(
            organization=self.organization
        )
        wallet = CreditWallet.objects.get(
            organization=self.organization
        )
        self.assertTrue(result["processed"])
        self.assertEqual(result["cycle_type"], "FIRST")
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(wallet.purchased_balance, 0)

    def test_invoice_payment_paid_retrieves_invoice_when_not_expanded(self):
        invoice = self.invoice_event(
            invoice_id="in_retrieved"
        )["data"]["object"]
        fake_client = FakeStripeBillingClient(
            invoice=invoice
        )

        with patch.object(
            StripeBillingService,
            "client",
            return_value=fake_client,
        ):
            result = StripeWebhookService.process_event(
                self.invoice_payment_event(
                    invoice_id="in_retrieved"
                )
            )

        wallet = CreditWallet.objects.get(
            organization=self.organization
        )
        self.assertTrue(result["processed"])
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(
            fake_client.v1.invoices.retrieve_calls[0]["invoice_id"],
            "in_retrieved",
        )
        self.assertEqual(
            fake_client.v1.invoices.retrieve_calls[0]["params"]["expand"],
            [
                "lines.data.price",
                "lines.data.pricing.price_details",
            ],
        )

    def test_different_paid_events_for_same_invoice_do_not_duplicate_credits(self):
        invoice = self.invoice_event(
            invoice_id="in_same_paid"
        )["data"]["object"]

        first = StripeWebhookService.process_event(
            self.invoice_payment_event(
                event_id="evt_inpay_same",
                invoice=invoice,
            )
        )
        second = StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_invoice_succeeded_same",
                invoice_id="in_same_paid",
                event_type="invoice.payment_succeeded",
            )
        )

        wallet = CreditWallet.objects.get(
            organization=self.organization
        )
        self.assertTrue(first["applied"])
        self.assertFalse(second["applied"])
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(StripeInvoiceRecord.objects.count(), 1)

    def test_duplicate_event_does_not_duplicate_credits(self):
        event = self.invoice_event()

        StripeWebhookService.process_event(event)
        result = StripeWebhookService.process_event(event)

        wallet = CreditWallet.objects.get(organization=self.organization)
        self.assertTrue(result["duplicate"])
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

    def test_duplicate_invoice_with_new_event_does_not_duplicate_credits(self):
        StripeWebhookService.process_event(
            self.invoice_event(event_id="evt_paid_1", invoice_id="in_same")
        )
        result = StripeWebhookService.process_event(
            self.invoice_event(event_id="evt_paid_2", invoice_id="in_same")
        )

        wallet = CreditWallet.objects.get(organization=self.organization)
        self.assertFalse(result["applied"])
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(StripeInvoiceRecord.objects.count(), 1)

    def test_subscription_created_does_not_grant_credits(self):
        result = StripeWebhookService.process_event(
            {
                "id": "evt_subscription_created",
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_created_only",
                        "object": "subscription",
                        "customer": "cus_webhook",
                        "status": "active",
                    },
                },
            }
        )

        self.assertTrue(result["processed"])
        self.assertFalse(
            Subscription.objects.filter(
                organization=self.organization
            ).exists()
        )
        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_unknown_event_is_acknowledged_without_financial_effect(self):
        result = StripeWebhookService.process_event(
            {
                "id": "evt_unknown_billing",
                "type": "customer.updated",
                "data": {
                    "object": {
                        "id": "cus_webhook",
                    },
                },
            }
        )

        self.assertFalse(result["processed"])
        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_invoice_retrieve_failure_rolls_back_webhook_event(self):
        fake_client = FakeStripeBillingClient(
            invoice_side_effect=RuntimeError("stripe unavailable")
        )

        with patch.object(
            StripeBillingService,
            "client",
            return_value=fake_client,
        ):
            with self.assertRaises(StripeBillingError):
                StripeWebhookService.process_event(
                    self.invoice_payment_event(
                        event_id="evt_retrieve_failure",
                        invoice_id="in_missing",
                    )
                )

        self.assertFalse(
            StripeWebhookEvent.objects.filter(
                stripe_event_id="evt_retrieve_failure"
            ).exists()
        )
        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_incomplete_invoice_does_not_grant_credits(self):
        invoice = self.invoice_event()["data"]["object"]
        invoice.pop("customer")

        with self.assertRaises(StripeBillingError):
            StripeWebhookService.process_event(
                self.invoice_payment_event(
                    event_id="evt_incomplete_invoice",
                    invoice=invoice,
                )
            )

        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_customer_mismatch_does_not_grant_credits(self):
        invoice = self.invoice_event(
            customer_id="cus_other"
        )["data"]["object"]

        with self.assertRaises(StripeBillingError):
            StripeWebhookService.process_event(
                self.invoice_payment_event(
                    event_id="evt_customer_mismatch",
                    invoice=invoice,
                )
            )

        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_unknown_price_does_not_grant_credits(self):
        invoice = self.invoice_event(
            price_id="price_unknown"
        )["data"]["object"]

        with self.assertRaises(Plan.DoesNotExist):
            StripeWebhookService.process_event(
                self.invoice_payment_event(
                    event_id="evt_price_unknown",
                    invoice=invoice,
                )
            )

        self.assertFalse(
            CreditWallet.objects.filter(
                organization=self.organization
            ).exists()
        )

    def test_invoice_payment_paid_preserves_purchased_credits(self):
        CreditWallet.objects.create(
            organization=self.organization,
            balance=7,
            plan_balance=0,
            purchased_balance=7,
        )
        invoice = self.invoice_event(
            invoice_id="in_preserve_purchased"
        )["data"]["object"]

        StripeWebhookService.process_event(
            self.invoice_payment_event(
                event_id="evt_preserve_purchased",
                invoice=invoice,
            )
        )

        wallet = CreditWallet.objects.get(
            organization=self.organization
        )
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(wallet.purchased_balance, 7)
        self.assertEqual(wallet.balance, 32)

    def test_renewal_resets_plan_balance_and_preserves_purchased(self):
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_first",
                invoice_id="in_first",
                period_start=self.at(2026, 1, 1),
                period_end=self.at(2026, 2, 1),
            )
        )
        wallet = CreditWallet.objects.get(organization=self.organization)
        wallet.plan_balance = 7
        wallet.purchased_balance = 13
        wallet.balance = 20
        wallet.save()

        result = StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_second",
                invoice_id="in_second",
                period_start=self.at(2026, 2, 1),
                period_end=self.at(2026, 3, 1),
            )
        )

        wallet.refresh_from_db()
        self.assertEqual(result["cycle_type"], "RENEWAL")
        self.assertEqual(wallet.plan_balance, 25)
        self.assertEqual(wallet.purchased_balance, 13)

    def test_payment_failed_first_cycle_does_not_grant_or_grace(self):
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_failed_first",
                invoice_id="in_failed_first",
                event_type="invoice.payment_failed",
            )
        )

        self.assertFalse(
            Subscription.objects.filter(organization=self.organization).exists()
        )
        self.assertFalse(
            CreditWallet.objects.filter(organization=self.organization).exists()
        )

    def test_payment_failed_renewal_enters_grace_then_blocked(self):
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_first",
                invoice_id="in_first",
                period_start=self.at(2026, 1, 1),
                period_end=self.at(2026, 2, 1),
            )
        )
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_failed_renewal",
                invoice_id="in_failed_renewal",
                event_type="invoice.payment_failed",
            )
        )

        subscription = Subscription.objects.get(organization=self.organization)
        grace = BillingAccessService.evaluate_subscription(
            subscription,
            now=self.at(2026, 2, 2),
        )
        blocked = BillingAccessService.evaluate_subscription(
            subscription,
            now=self.at(2026, 2, 5),
        )
        self.assertEqual(subscription.status, SubscriptionStatus.PAST_DUE)
        self.assertEqual(grace.status, SubscriptionAccessStatus.GRACE)
        self.assertEqual(blocked.status, SubscriptionAccessStatus.BLOCKED)

    def test_regularization_restores_active(self):
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_first",
                invoice_id="in_first",
                period_start=self.at(2026, 1, 1),
                period_end=self.at(2026, 2, 1),
            )
        )
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_failed",
                invoice_id="in_failed",
                event_type="invoice.payment_failed",
            )
        )
        StripeWebhookService.process_event(
            self.invoice_event(
                event_id="evt_regularized",
                invoice_id="in_regularized",
                period_start=self.at(2026, 2, 1),
                period_end=self.at(2026, 3, 1),
            )
        )

        subscription = Subscription.objects.get(organization=self.organization)
        access = BillingAccessService.evaluate_subscription(
            subscription,
            now=self.at(2026, 2, 5),
        )
        self.assertEqual(subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(access.status, SubscriptionAccessStatus.ACTIVE)


@override_settings(
    STRIPE_SECRET_KEY="sk_test_reconcile",
    STRIPE_ALLOW_LIVE_MODE=False,
)
class StripeReconciliationServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Reconcile",
            slug="cliente-reconcile",
            stripe_customer_id="cus_reconcile",
        )
        self.plan = Plan.objects.create(
            name="START",
            slug="start-reconcile",
            description="Plano START.",
            price=Decimal("39.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=25,
            is_active=True,
            stripe_product_id="prod_reconcile",
            stripe_price_id="price_reconcile",
            stripe_price_signature="brl|3990|month",
            stripe_sync_error="",
        )
        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.PENDING,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
        )
        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=0,
            purchased_balance=0,
            balance=0,
        )

    def at(self, year, month, day):
        return timezone.make_aware(
            timezone.datetime(year, month, day, 10, 0, 0)
        )

    def timestamp(self, value):
        return int(value.timestamp())

    def stripe_subscription(
        self,
        *,
        subscription_id="sub_reconcile",
        customer_id="cus_reconcile",
        price_id="price_reconcile",
        status="active",
        metadata=None,
    ):
        return {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "status": status,
            "metadata": metadata
            if metadata is not None
            else {
                "integration": "maried-studio-v1",
                "maried_organization_id": str(self.organization.pk),
                "maried_plan_id": str(self.plan.pk),
            },
            "items": {
                "data": [
                    {
                        "price": {
                            "id": price_id,
                        },
                    }
                ],
            },
        }

    def invoice(
        self,
        *,
        invoice_id="in_reconcile",
        subscription_id="sub_reconcile",
        customer_id="cus_reconcile",
        price_id="price_reconcile",
        status="paid",
        period_start=None,
        period_end=None,
        organization_id=None,
        plan_id=None,
    ):
        period_start = period_start or self.at(2026, 9, 1)
        period_end = period_end or self.at(2026, 10, 1)

        return {
            "id": invoice_id,
            "object": "invoice",
            "customer": customer_id,
            "subscription": subscription_id,
            "status": status,
            "subscription_details": {
                "metadata": {
                    "maried_organization_id": str(
                        organization_id or self.organization.pk
                    ),
                    "maried_plan_id": str(plan_id or self.plan.pk),
                },
            },
            "lines": {
                "data": [
                    {
                        "period": {
                            "start": self.timestamp(period_start),
                            "end": self.timestamp(period_end),
                        },
                        "pricing": {
                            "price_details": {
                                "price": price_id,
                            },
                        },
                    },
                ],
            },
        }

    def fake_client(
        self,
        *,
        subscription=None,
        subscriptions=None,
        invoices=None,
        **kwargs,
    ):
        if subscription is None and subscriptions:
            subscription = subscriptions[0]

        return FakeStripeBillingClient(
            subscription=subscription,
            subscriptions=subscriptions,
            invoices=invoices,
            **kwargs,
        )

    def reconcile(self, fake_client):
        with patch.object(
            StripeBillingService,
            "client",
            return_value=fake_client,
        ):
            return StripeReconciliationService.reconcile(
                organization=self.organization,
            )

    def test_active_subscription_paid_invoice_activates_and_grants_credits(self):
        result = self.reconcile(
            self.fake_client(
                subscriptions=[self.stripe_subscription()],
                invoices=[self.invoice()],
            )
        )

        self.subscription.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertTrue(result.reconciled)
        self.assertTrue(result.applied)
        self.assertEqual(result.cycle_type, "FIRST")
        self.assertEqual(
            self.subscription.status,
            SubscriptionStatus.ACTIVE,
        )
        self.assertEqual(
            self.subscription.stripe_subscription_id,
            "sub_reconcile",
        )
        self.assertEqual(self.wallet.plan_balance, 25)
        self.assertEqual(self.wallet.purchased_balance, 0)

    def test_reconcile_twice_does_not_duplicate_credits(self):
        fake_client = self.fake_client(
            subscriptions=[self.stripe_subscription()],
            invoices=[self.invoice()],
        )

        first = self.reconcile(fake_client)
        second = self.reconcile(fake_client)

        self.wallet.refresh_from_db()
        self.assertTrue(first.applied)
        self.assertFalse(second.applied)
        self.assertEqual(self.wallet.plan_balance, 25)
        self.assertEqual(StripeInvoiceRecord.objects.count(), 1)

    def test_reconcile_preserves_purchased_credits(self):
        self.wallet.purchased_balance = 10
        self.wallet.balance = 10
        self.wallet.save()

        self.reconcile(
            self.fake_client(
                subscriptions=[self.stripe_subscription()],
                invoices=[self.invoice()],
            )
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 25)
        self.assertEqual(self.wallet.purchased_balance, 10)
        self.assertEqual(self.wallet.balance, 35)

    def test_without_customer_returns_stable_error(self):
        self.organization.stripe_customer_id = ""
        self.organization.save(update_fields=["stripe_customer_id", "updated_at"])

        with self.assertRaises(StripeReconciliationError) as context:
            StripeReconciliationService.reconcile(
                organization=self.organization,
            )

        self.assertEqual(
            context.exception.code,
            "STRIPE_CUSTOMER_NOT_FOUND",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_customer_without_subscription_returns_stable_error(self):
        with self.assertRaises(StripeReconciliationError) as context:
            self.reconcile(
                self.fake_client(subscriptions=[])
            )

        self.assertEqual(
            context.exception.code,
            "STRIPE_SUBSCRIPTION_NOT_FOUND",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_multiple_subscriptions_are_ambiguous(self):
        with self.assertRaises(StripeReconciliationError) as context:
            self.reconcile(
                self.fake_client(
                    subscriptions=[
                        self.stripe_subscription(
                            subscription_id="sub_a",
                        ),
                        self.stripe_subscription(
                            subscription_id="sub_b",
                        ),
                    ],
                )
            )

        self.assertEqual(
            context.exception.code,
            "STRIPE_SUBSCRIPTION_AMBIGUOUS",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_active_subscription_without_paid_invoice_does_not_grant(self):
        with self.assertRaises(StripeReconciliationError) as context:
            self.reconcile(
                self.fake_client(
                    subscriptions=[self.stripe_subscription()],
                    invoices=[],
                )
            )

        self.assertEqual(
            context.exception.code,
            "STRIPE_PAID_INVOICE_NOT_FOUND",
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_open_invoice_does_not_grant_credits(self):
        with self.assertRaises(StripeReconciliationError):
            self.reconcile(
                self.fake_client(
                    subscriptions=[
                        {
                            **self.stripe_subscription(),
                            "latest_invoice": self.invoice(
                                status="open",
                            ),
                        }
                    ],
                    invoices=[],
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_customer_mismatch_does_not_grant_credits(self):
        with self.assertRaises(StripeReconciliationError):
            self.reconcile(
                self.fake_client(
                    subscriptions=[
                        self.stripe_subscription(
                            customer_id="cus_other",
                        )
                    ],
                    invoices=[self.invoice()],
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_price_mismatch_does_not_grant_credits(self):
        other_plan = Plan.objects.create(
            name="PRO",
            slug="pro-reconcile",
            description="Plano PRO.",
            price=Decimal("99.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=80,
            is_active=True,
            stripe_product_id="prod_pro_reconcile",
            stripe_price_id="price_other",
            stripe_price_signature="brl|9990|month",
        )

        with self.assertRaises(StripeReconciliationError):
            self.reconcile(
                self.fake_client(
                    subscriptions=[
                        self.stripe_subscription(
                            price_id=other_plan.stripe_price_id,
                            metadata={
                                "maried_organization_id": str(
                                    self.organization.pk
                                ),
                                "maried_plan_id": str(other_plan.pk),
                            },
                        )
                    ],
                    invoices=[
                        self.invoice(
                            price_id=other_plan.stripe_price_id,
                            plan_id=other_plan.pk,
                        )
                    ],
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_organization_mismatch_does_not_grant_credits(self):
        other_organization = Organization.objects.create(
            name="Outra Reconcile",
            slug="outra-reconcile",
        )

        with self.assertRaises(StripeReconciliationError):
            self.reconcile(
                self.fake_client(
                    subscriptions=[self.stripe_subscription()],
                    invoices=[
                        self.invoice(
                            organization_id=other_organization.pk,
                        )
                    ],
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_stripe_api_failure_does_not_grant_credits(self):
        with self.assertRaises(StripeReconciliationError):
            self.reconcile(
                self.fake_client(
                    subscription_list_side_effect=RuntimeError(
                        "stripe unavailable"
                    ),
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.plan_balance, 0)

    def test_reconcile_then_webhook_does_not_duplicate_credits(self):
        invoice = self.invoice()

        self.reconcile(
            self.fake_client(
                subscriptions=[self.stripe_subscription()],
                invoices=[invoice],
            )
        )
        result = StripeWebhookService.process_event(
            {
                "id": "evt_after_reconcile",
                "type": "invoice.paid",
                "data": {
                    "object": invoice,
                },
            }
        )

        self.wallet.refresh_from_db()
        self.assertFalse(result["applied"])
        self.assertEqual(self.wallet.plan_balance, 25)

    def test_webhook_then_reconcile_does_not_duplicate_credits(self):
        invoice = self.invoice()
        StripeWebhookService.process_event(
            {
                "id": "evt_before_reconcile",
                "type": "invoice.paid",
                "data": {
                    "object": invoice,
                },
            }
        )

        result = self.reconcile(
            self.fake_client(
                subscriptions=[self.stripe_subscription()],
                invoices=[invoice],
            )
        )

        self.wallet.refresh_from_db()
        self.assertFalse(result.applied)
        self.assertEqual(self.wallet.plan_balance, 25)


class StripeWebhookApiTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Checkout API",
            slug="cliente-checkout-api",
        )
        self.user = get_user_model().objects.create_user(
            email="checkout-api@example.com",
            password="senha-teste",
            name="Cliente Checkout API",
            organization=self.organization,
        )
        self.plan = Plan.objects.create(
            name="Start API",
            slug="start-checkout-api",
            description="Plano Start API",
            price=Decimal("39.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=20,
            is_active=True,
            stripe_product_id="prod_start_api",
            stripe_price_id="price_start_api",
            stripe_price_signature="brl|3990|month",
            stripe_sync_error="",
        )
        self.url = reverse("billing:subscription-checkout")
        self.client.force_authenticate(self.user)

    def test_webhook_without_signature_returns_400(self):
        response = self.client.post(
            reverse("billing:stripe-webhook"),
            b"{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    def test_webhook_invalid_signature_returns_400(self):
        with patch.object(
            StripeWebhookService,
            "construct_event",
            side_effect=ValueError("assinatura invalida"),
        ):
            response = self.client.post(
                reverse("billing:stripe-webhook"),
                b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="bad",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    def test_webhook_valid_signature_processes_event(self):
        event = {
            "id": "evt_unknown",
            "type": "customer.created",
            "data": {
                "object": {},
            },
        }

        with patch.object(
            StripeWebhookService,
            "construct_event",
            return_value=event,
        ):
            response = self.client.post(
                reverse("billing:stripe-webhook"),
                b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="good",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(StripeWebhookEvent.objects.count(), 1)

    def test_checkout_rejects_inactive_plan(self):
        self.plan.is_active = False
        self.plan.save(update_fields=["is_active", "updated_at"])

        response = self.client.post(
            self.url,
            {"plan_id": str(self.plan.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_rejects_superadmin(self):
        superadmin = get_user_model().objects.create_superuser(
            email="root@example.com",
            password="senha-teste",
            name="Root",
        )
        self.client.force_authenticate(superadmin)

        response = self.client.post(
            self.url,
            {"plan_id": str(self.plan.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_active_stripe_subscription_blocks_duplicate_checkout(self):
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
            stripe_subscription_id="sub_existing",
        )

        with patch.object(
            StripeBillingService,
            "client",
            return_value=FakeStripeBillingClient(),
        ):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test_checkout",
        FRONTEND_URL="http://localhost:3000",
    )
    def test_active_local_subscription_blocks_duplicate_checkout(self):
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

        with patch.object(
            StripeBillingService,
            "client",
            return_value=FakeStripeBillingClient(),
        ):
            response = self.client.post(
                self.url,
                {"plan_id": str(self.plan.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    STRIPE_SECRET_KEY="sk_test_123",
    STRIPE_CURRENCY="brl",
    STRIPE_ALLOW_LIVE_MODE=False,
)
class CreditPackagePurchaseTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Extras",
            slug="cliente-extras",
        )
        self.plan = Plan.objects.create(
            name="Pro",
            slug="pro-extras",
            description="Plano com extras.",
            price=Decimal("79.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=30,
            extra_credit_limit_per_cycle=25,
            is_active=True,
        )
        self.period_start = timezone.make_aware(
            timezone.datetime(2026, 8, 1, 10, 0, 0)
        )
        self.period_end = timezone.make_aware(
            timezone.datetime(2026, 9, 1, 10, 0, 0)
        )
        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=self.period_start,
            current_period_start=self.period_start,
            current_period_end=self.period_end,
            next_billing_at=self.period_end,
            stripe_customer_id="cus_test",
        )
        self.wallet = CreditWallet.objects.create(
            organization=self.organization,
            plan_balance=30,
            balance=30,
        )
        self.package = CreditPackage.objects.create(
            name="10 extras",
            slug="10-extras",
            description="Pacote teste.",
            credits=10,
            price=Decimal("19.90"),
            currency="BRL",
            is_active=True,
            stripe_product_id="prod_extra",
            stripe_price_id="price_extra_10",
            stripe_price_signature="brl|1990|10",
        )

    def create_purchase(self, **overrides):
        data = {
            "organization": self.organization,
            "package": self.package,
            "subscription": self.subscription,
            "plan": self.plan,
            "status": CreditPurchaseStatus.PENDING,
            "credits_snapshot": self.package.credits,
            "price_snapshot": self.package.price,
            "currency_snapshot": self.package.currency,
            "stripe_price_id_snapshot": self.package.stripe_price_id,
            "extra_credit_limit_snapshot": (
                self.plan.extra_credit_limit_per_cycle
            ),
            "cycle_start": self.period_start,
            "cycle_end": self.period_end,
            "stripe_customer_id": "cus_test",
            "stripe_checkout_session_id": f"cs_{uuid.uuid4()}",
            "stripe_checkout_url": "https://checkout.stripe.test/session",
            "stripe_idempotency_key": f"key-{uuid.uuid4()}",
            "request_signature": "signature",
            "expires_at": timezone.now() + timezone.timedelta(hours=1),
        }
        data.update(overrides)
        return CreditPurchase.objects.create(**data)

    def stripe_checkout_session(
        self,
        session_id="cs_test",
        *,
        session_status="open",
        payment_status="unpaid",
        payment_intent="",
    ):
        session = FakeStripeObject(session_id)
        session.status = session_status
        session.payment_status = payment_status
        session.customer = "cus_test"
        session.payment_intent = payment_intent
        session.amount_total = 1990
        session.currency = "brl"
        return session

    def test_plan_extra_credit_limit_defaults_to_zero(self):
        plan = Plan.objects.create(
            name="Essencial",
            slug="essencial-default-limit",
            description="Plano sem limite configurado.",
            price=Decimal("49.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=15,
        )

        self.assertEqual(plan.extra_credit_limit_per_cycle, 0)

    def test_package_stripe_sync_creates_one_time_price(self):
        package = CreditPackage.objects.create(
            name="25 extras",
            slug="25-extras-sync",
            description="Pacote sync.",
            credits=25,
            price=Decimal("39.90"),
            currency="BRL",
        )
        fake = FakeStripeClient()

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake,
        ):
            StripeCreditPackageService.sync_package(package)

        price_params = fake.v1.prices.create_calls[0]["params"]

        self.assertEqual(price_params["unit_amount"], 3990)
        self.assertEqual(price_params["currency"], "brl")
        self.assertNotIn("recurring", price_params)
        self.assertEqual(
            price_params["metadata"]["maried_credit_package_id"],
            str(package.pk),
        )

    def test_active_subscription_can_purchase_within_limit(self):
        purchase, created = CreditPurchaseService.create_pending_purchase(
            organization=self.organization,
            package=self.package,
            subscription=self.subscription,
            stripe_customer_id="cus_test",
            request_signature="sig-active",
        )

        self.assertTrue(created)
        self.assertEqual(purchase.status, CreditPurchaseStatus.PENDING)
        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(allowance["pending_credits_this_cycle"], 10)

    def test_credit_checkout_uses_one_time_payment_mode(self):
        user = get_user_model().objects.create_user(
            email="extras@example.com",
            password="senha-teste",
            name="Cliente Extras",
            organization=self.organization,
            role="OWNER",
        )
        fake_client = FakeStripeBillingClient()

        with patch.object(
            StripeBillingService,
            "client",
            return_value=fake_client,
        ):
            checkout = StripeBillingService.create_credit_checkout(
                user=user,
                package=self.package,
            )

        checkout_call = fake_client.v1.checkout.sessions.create_calls[0]
        params = checkout_call["params"]
        purchase = CreditPurchase.objects.get(
            stripe_checkout_session_id=checkout["checkout_session_id"]
        )

        self.assertEqual(params["mode"], "payment")
        self.assertEqual(params["line_items"][0]["price"], "price_extra_10")
        self.assertEqual(params["line_items"][0]["quantity"], 1)
        self.assertNotIn("payment_method_types", params)
        self.assertEqual(
            params["metadata"]["maried_credit_purchase_id"],
            str(purchase.pk),
        )

    def test_open_pending_purchase_reuses_checkout_without_new_session(self):
        self.organization.stripe_customer_id = "cus_test"
        self.organization.save(
            update_fields=[
                "stripe_customer_id",
                "updated_at",
            ]
        )
        user = get_user_model().objects.create_user(
            email="retry-extras@example.com",
            password="senha-teste",
            name="Cliente Retry",
            organization=self.organization,
            role="OWNER",
        )
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_pending_open",
            stripe_checkout_url="https://checkout.stripe.test/open",
            request_signature=(
                StripeBillingService.checkout_request_signature(
                    customer_id="cus_test",
                    price_id="price_extra_10",
                    success_url=(
                        "http://localhost:3000/creditos/sucesso"
                        "?session_id={CHECKOUT_SESSION_ID}"
                    ),
                    cancel_url=(
                        "http://localhost:3000/creditos?checkout=cancelled"
                    ),
                )
            ),
        )
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_response=self.stripe_checkout_session(
                "cs_pending_open",
                session_status="open",
                payment_status="unpaid",
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            checkout = StripeBillingService.create_credit_checkout(
                user=user,
                package=self.package,
            )

        purchase.refresh_from_db()
        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(checkout["purchase_id"], str(purchase.pk))
        self.assertEqual(
            checkout["checkout_session_id"],
            "cs_pending_open",
        )
        self.assertEqual(
            checkout["url"],
            "https://checkout.stripe.test/open",
        )
        self.assertEqual(
            fake_client.v1.checkout.sessions.create_calls,
            [],
        )
        self.assertEqual(
            fake_client.v1.checkout.sessions.retrieve_calls,
            ["cs_pending_open"],
        )
        self.assertEqual(
            CreditPurchase.objects.count(),
            1,
        )
        self.assertEqual(
            purchase.status,
            CreditPurchaseStatus.PENDING,
        )
        self.assertEqual(
            allowance["pending_credits_this_cycle"],
            10,
        )

    def test_expired_stripe_session_marks_purchase_expired_and_releases_limit(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_expired_remote"
        )
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_response=self.stripe_checkout_session(
                "cs_expired_remote",
                session_status="expired",
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            synced = (
                CreditPurchaseCheckoutService
                .sync_purchase_from_session(
                    purchase=purchase,
                )
            )

        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(
            synced.status,
            CreditPurchaseStatus.EXPIRED,
        )
        self.assertEqual(
            allowance["pending_credits_this_cycle"],
            0,
        )
        self.assertEqual(
            allowance["remaining_extra_credits"],
            25,
        )

    def test_complete_paid_stripe_session_applies_credits_once(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_paid_remote"
        )
        session = self.stripe_checkout_session(
            "cs_paid_remote",
            session_status="complete",
            payment_status="paid",
            payment_intent="pi_paid_remote",
        )

        synced = (
            CreditPurchaseCheckoutService
            .sync_purchase_from_session(
                purchase=purchase,
                session=session,
                event_id="evt_checkout_remote",
            )
        )
        synced_again = (
            CreditPurchaseCheckoutService
            .sync_purchase_from_session(
                purchase=synced,
                session=session,
                event_id="evt_checkout_remote_again",
            )
        )

        self.wallet.refresh_from_db()
        self.assertEqual(
            synced.status,
            CreditPurchaseStatus.PAID,
        )
        self.assertEqual(
            synced_again.status,
            CreditPurchaseStatus.PAID,
        )
        self.assertEqual(
            self.wallet.purchased_balance,
            10,
        )

    def test_cancel_pending_open_session_expires_stripe_and_releases_limit(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_cancel_open"
        )
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_response=self.stripe_checkout_session(
                "cs_cancel_open",
                session_status="open",
            )
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            canceled = (
                CreditPurchaseCheckoutService
                .cancel_pending_purchase(
                    purchase=purchase,
                )
            )

        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(
            canceled.status,
            CreditPurchaseStatus.EXPIRED,
        )
        self.assertEqual(
            fake_client.v1.checkout.sessions.retrieve_calls,
            ["cs_cancel_open"],
        )
        self.assertEqual(
            fake_client.v1.checkout.sessions.expire_calls,
            ["cs_cancel_open"],
        )
        self.assertEqual(
            allowance["pending_credits_this_cycle"],
            0,
        )

    def test_stripe_sync_failure_keeps_pending_reservation(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_sync_failure"
        )
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_side_effect=RuntimeError("stripe unavailable")
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            synced = (
                CreditPurchaseCheckoutService
                .sync_pending_for_subscription(
                    self.subscription,
                )
            )

        purchase.refresh_from_db()
        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(synced, 0)
        self.assertEqual(
            purchase.status,
            CreditPurchaseStatus.PENDING,
        )
        self.assertEqual(
            allowance["pending_credits_this_cycle"],
            10,
        )

    def test_cancel_stripe_failure_keeps_pending_reservation(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_cancel_failure"
        )
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_response=self.stripe_checkout_session(
                "cs_cancel_failure",
                session_status="open",
            ),
            checkout_expire_side_effect=RuntimeError("stripe unavailable"),
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            with self.assertRaises(StripeCreditPurchaseSessionError):
                (
                    CreditPurchaseCheckoutService
                    .cancel_pending_purchase(
                        purchase=purchase,
                    )
                )

        purchase.refresh_from_db()
        allowance = CreditPurchaseService.allowance_for_subscription(
            self.subscription
        )
        self.assertEqual(
            purchase.status,
            CreditPurchaseStatus.PENDING,
        )
        self.assertEqual(
            allowance["pending_credits_this_cycle"],
            10,
        )

    def test_grace_subscription_cannot_purchase_extras(self):
        self.subscription.status = SubscriptionStatus.PAST_DUE
        self.subscription.current_period_end = (
            timezone.now() - timezone.timedelta(days=1)
        )
        self.subscription.next_billing_at = self.subscription.current_period_end
        self.subscription.save()

        with self.assertRaises(CreditPurchaseNotAllowedError):
            CreditPurchaseService.create_pending_purchase(
                organization=self.organization,
                package=self.package,
                subscription=self.subscription,
                stripe_customer_id="cus_test",
                request_signature="sig-grace",
            )

    def test_limit_counts_paid_and_pending_without_reopening_after_consumption(self):
        self.create_purchase(
            status=CreditPurchaseStatus.PAID,
            credits_snapshot=20,
            stripe_checkout_session_id="cs_paid",
            stripe_payment_intent_id="pi_paid",
        )

        with self.assertRaises(CreditPurchaseLimitExceededError):
            CreditPurchaseService.create_pending_purchase(
                organization=self.organization,
                package=self.package,
                subscription=self.subscription,
                stripe_customer_id="cus_test",
                request_signature="sig-limit",
            )

    def test_expired_pending_purchase_releases_cycle_limit(self):
        self.create_purchase(
            credits_snapshot=20,
            stripe_checkout_session_id="cs_expired",
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )

        purchase, created = CreditPurchaseService.create_pending_purchase(
            organization=self.organization,
            package=self.package,
            subscription=self.subscription,
            stripe_customer_id="cus_test",
            request_signature="sig-after-expire",
        )

        self.assertTrue(created)
        self.assertEqual(purchase.credits_snapshot, 10)

    def test_paid_purchase_adds_purchased_credits_once(self):
        purchase = self.create_purchase()

        first, applied = CreditPurchaseService.apply_paid_purchase(
            purchase=purchase,
            stripe_customer_id="cus_test",
            stripe_payment_intent_id="pi_paid_once",
            amount_received=1990,
            currency="brl",
            event_id="evt_1",
        )
        second, applied_again = CreditPurchaseService.apply_paid_purchase(
            purchase=first,
            stripe_customer_id="cus_test",
            stripe_payment_intent_id="pi_paid_once",
            amount_received=1990,
            currency="brl",
            event_id="evt_2",
        )

        self.wallet.refresh_from_db()
        self.assertTrue(applied)
        self.assertFalse(applied_again)
        self.assertEqual(second.status, CreditPurchaseStatus.PAID)
        self.assertEqual(self.wallet.purchased_balance, 10)

    def test_checkout_and_payment_intent_events_do_not_duplicate_credits(self):
        purchase = self.create_purchase(
            stripe_checkout_session_id="cs_both_events"
        )
        event = {
            "id": "evt_checkout_paid",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": purchase.stripe_checkout_session_id,
                    "payment_status": "paid",
                    "customer": "cus_test",
                    "payment_intent": "pi_both_events",
                    "amount_total": 1990,
                    "currency": "brl",
                    "metadata": {
                        "maried_credit_purchase_id": str(purchase.pk),
                    },
                }
            },
        }
        intent_event = {
            "id": "evt_payment_intent_paid",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_both_events",
                    "customer": "cus_test",
                    "amount_received": 1990,
                    "currency": "brl",
                    "metadata": {
                        "maried_credit_purchase_id": str(purchase.pk),
                    },
                }
            },
        }

        StripeWebhookService.process_event(event)
        StripeWebhookService.process_event(intent_event)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.purchased_balance, 10)

    def test_canceled_subscription_with_purchased_balance_can_create_but_not_buy(self):
        self.subscription.status = SubscriptionStatus.CANCELED
        self.subscription.canceled_at = timezone.now()
        self.subscription.save()
        self.wallet.purchased_balance = 3
        self.wallet.balance = 33
        self.wallet.save()

        access = BillingAccessService.evaluate_organization(
            self.organization
        )

        self.assertTrue(access.can_create)
        self.assertFalse(access.can_purchase_credits)

    def test_finalize_expired_grace_cancels_and_expires_plan_credits(self):
        self.subscription.status = SubscriptionStatus.PAST_DUE
        self.subscription.current_period_end = (
            timezone.now() - timezone.timedelta(days=4)
        )
        self.subscription.next_billing_at = self.subscription.current_period_end
        self.subscription.save()
        self.wallet.purchased_balance = 7
        self.wallet.balance = 37
        self.wallet.save()

        processed = SubscriptionDelinquencyService.finalize_expired_grace()

        self.subscription.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(processed, 1)
        self.assertEqual(self.subscription.status, SubscriptionStatus.CANCELED)
        self.assertEqual(self.wallet.plan_balance, 0)
        self.assertEqual(self.wallet.purchased_balance, 7)


@override_settings(
    STRIPE_SECRET_KEY="sk_test_123",
    STRIPE_CURRENCY="brl",
    STRIPE_ALLOW_LIVE_MODE=False,
)
class CreditPurchaseCancelApiTests(APITestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Cliente Cancelamento",
            slug="cliente-cancelamento",
        )
        self.other_organization = Organization.objects.create(
            name="Outro Cliente Cancelamento",
            slug="outro-cliente-cancelamento",
        )
        self.user = get_user_model().objects.create_user(
            email="cancelamento@example.com",
            password="senha-teste",
            name="Cliente Cancelamento",
            organization=self.organization,
            role="OWNER",
        )
        self.plan = Plan.objects.create(
            name="Pro Cancelamento",
            slug="pro-cancelamento",
            description="Plano com extras.",
            price=Decimal("79.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=30,
            extra_credit_limit_per_cycle=25,
            is_active=True,
        )
        self.other_plan = Plan.objects.create(
            name="Pro Outro Cancelamento",
            slug="pro-outro-cancelamento",
            description="Plano de outro cliente.",
            price=Decimal("79.90"),
            billing_cycle=BillingCycle.MONTHLY,
            credits_per_cycle=30,
            extra_credit_limit_per_cycle=25,
            is_active=True,
        )
        self.period_start = timezone.make_aware(
            timezone.datetime(2026, 8, 1, 10, 0, 0)
        )
        self.period_end = timezone.make_aware(
            timezone.datetime(2026, 9, 1, 10, 0, 0)
        )
        self.subscription = Subscription.objects.create(
            organization=self.organization,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.plan.price,
            credits_snapshot=self.plan.credits_per_cycle,
            started_at=self.period_start,
            current_period_start=self.period_start,
            current_period_end=self.period_end,
            next_billing_at=self.period_end,
            stripe_customer_id="cus_cancel",
        )
        self.other_subscription = Subscription.objects.create(
            organization=self.other_organization,
            plan=self.other_plan,
            status=SubscriptionStatus.ACTIVE,
            price_snapshot=self.other_plan.price,
            credits_snapshot=self.other_plan.credits_per_cycle,
            started_at=self.period_start,
            current_period_start=self.period_start,
            current_period_end=self.period_end,
            next_billing_at=self.period_end,
            stripe_customer_id="cus_other_cancel",
        )
        self.package = CreditPackage.objects.create(
            name="10 extras cancelamento",
            slug="10-extras-cancelamento",
            description="Pacote teste.",
            credits=10,
            price=Decimal("19.90"),
            currency="BRL",
            is_active=True,
            stripe_product_id="prod_cancel",
            stripe_price_id="price_cancel_10",
            stripe_price_signature="brl|1990|10",
        )
        self.client.force_authenticate(self.user)

    def create_purchase(self, organization, subscription):
        return CreditPurchase.objects.create(
            organization=organization,
            package=self.package,
            subscription=subscription,
            plan=subscription.plan,
            status=CreditPurchaseStatus.PENDING,
            credits_snapshot=self.package.credits,
            price_snapshot=self.package.price,
            currency_snapshot=self.package.currency,
            stripe_price_id_snapshot=self.package.stripe_price_id,
            extra_credit_limit_snapshot=(
                subscription.plan.extra_credit_limit_per_cycle
            ),
            cycle_start=self.period_start,
            cycle_end=self.period_end,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_checkout_session_id=f"cs_{uuid.uuid4()}",
            stripe_checkout_url="https://checkout.stripe.test/session",
            stripe_idempotency_key=f"key-{uuid.uuid4()}",
            request_signature=f"sig-{uuid.uuid4()}",
            expires_at=timezone.now() + timezone.timedelta(hours=1),
        )

    def test_user_cannot_cancel_other_organization_credit_purchase(self):
        purchase = self.create_purchase(
            self.other_organization,
            self.other_subscription,
        )

        response = self.client.post(
            reverse(
                "billing:credit-purchase-cancel",
                args=[purchase.pk],
            ),
            {},
            format="json",
        )

        purchase.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            purchase.status,
            CreditPurchaseStatus.PENDING,
        )

    def test_cancel_endpoint_expires_own_open_credit_purchase(self):
        purchase = self.create_purchase(
            self.organization,
            self.subscription,
        )
        session = FakeStripeObject(
            purchase.stripe_checkout_session_id
        )
        session.status = "open"
        session.payment_status = "unpaid"
        fake_client = FakeStripeBillingClient(
            checkout_retrieve_response=session,
        )

        with patch.object(
            StripePlanService,
            "client",
            return_value=fake_client,
        ):
            response = self.client.post(
                reverse(
                    "billing:credit-purchase-cancel",
                    args=[purchase.pk],
                ),
                {},
                format="json",
            )

        purchase.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["status"],
            CreditPurchaseStatus.EXPIRED,
        )
        self.assertEqual(
            purchase.status,
            CreditPurchaseStatus.EXPIRED,
        )
