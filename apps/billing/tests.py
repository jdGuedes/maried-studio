from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
from apps.billing.services import InactivePlanError, SubscriptionService
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
