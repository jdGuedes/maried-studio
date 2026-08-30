from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APITestCase

from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.billing.services import (
    BillingAccessService,
    InactivePlanError,
    SubscriptionAccessStatus,
    SubscriptionRequiredError,
    SubscriptionService,
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
