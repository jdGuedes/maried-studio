from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.billing.models import BillingCycle, Plan, Subscription, SubscriptionStatus
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
