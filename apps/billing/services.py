import calendar

from django.db import transaction
from django.utils import timezone

from apps.credits.models import CreditWallet
from apps.credits.services import CreditService

from .models import BillingCycle, Plan, Subscription, SubscriptionStatus


class BillingError(Exception):
    pass


class InactivePlanError(BillingError):
    pass


class UnsupportedBillingCycleError(BillingError):
    pass


class SubscriptionAlreadyActiveError(BillingError):
    pass


class SubscriptionNotActiveError(BillingError):
    pass


class SubscriptionService:
    @staticmethod
    def _add_month(value):
        year = value.year
        month = value.month + 1

        if month > 12:
            year += 1
            month = 1

        last_day = calendar.monthrange(
            year,
            month,
        )[1]

        day = min(
            value.day,
            last_day,
        )

        return value.replace(
            year=year,
            month=month,
            day=day,
        )

    @staticmethod
    def _calculate_monthly_period(*, starts_at):
        ends_at = SubscriptionService._add_month(
            starts_at
        )

        return (
            starts_at,
            ends_at,
            ends_at,
        )

    @staticmethod
    def _validate_plan_for_activation(plan):
        if not plan.is_active:
            raise InactivePlanError(
                "Plano inativo não pode ser vendido."
            )

        if (
            plan.billing_cycle
            != BillingCycle.MONTHLY
        ):
            raise UnsupportedBillingCycleError(
                "Somente ciclo mensal é suportado na V1."
            )

    @staticmethod
    def _wallet_for_organization(organization):
        wallet, _ = (
            CreditWallet.objects
            .get_or_create(
                organization=organization,
            )
        )

        return wallet

    @staticmethod
    @transaction.atomic
    def activate(
        *,
        organization,
        plan,
        starts_at=None,
        actor=None,
    ):
        plan = (
            Plan.objects
            .select_for_update()
            .get(
                pk=plan.pk,
            )
        )

        SubscriptionService._validate_plan_for_activation(
            plan
        )

        starts_at = starts_at or timezone.now()
        (
            current_period_start,
            current_period_end,
            next_billing_at,
        ) = SubscriptionService._calculate_monthly_period(
            starts_at=starts_at,
        )

        subscription = (
            Subscription.objects
            .select_for_update()
            .filter(
                organization=organization,
            )
            .first()
        )

        if (
            subscription
            and subscription.status == SubscriptionStatus.ACTIVE
        ):
            if (
                subscription.plan_id == plan.pk
                and subscription.current_period_start == current_period_start
                and subscription.current_period_end == current_period_end
            ):
                return subscription

            raise SubscriptionAlreadyActiveError(
                "Organização já possui assinatura ativa."
            )

        if subscription is None:
            subscription = Subscription(
                organization=organization,
            )

        subscription.plan = plan
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.price_snapshot = plan.price
        subscription.credits_snapshot = plan.credits_per_cycle
        subscription.started_at = starts_at
        subscription.current_period_start = current_period_start
        subscription.current_period_end = current_period_end
        subscription.next_billing_at = next_billing_at
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.save()

        wallet = SubscriptionService._wallet_for_organization(
            organization
        )

        CreditService.renew_plan_credits(
            wallet,
            subscription.credits_snapshot,
            actor=actor,
            description=(
                "Ativação dos créditos "
                "da assinatura."
            ),
        )

        return subscription

    @staticmethod
    @transaction.atomic
    def renew_current_cycle(
        *,
        subscription,
        actor=None,
    ):
        subscription = (
            Subscription.objects
            .select_for_update()
            .select_related(
                "organization",
                "plan",
            )
            .get(
                pk=subscription.pk,
            )
        )

        if (
            subscription.status
            != SubscriptionStatus.ACTIVE
        ):
            raise SubscriptionNotActiveError(
                "Somente assinaturas ativas podem ser renovadas."
            )

        if (
            subscription.plan.billing_cycle
            != BillingCycle.MONTHLY
        ):
            raise UnsupportedBillingCycleError(
                "Somente ciclo mensal é suportado na V1."
            )

        starts_at = (
            subscription.current_period_end
            or timezone.now()
        )

        (
            current_period_start,
            current_period_end,
            next_billing_at,
        ) = SubscriptionService._calculate_monthly_period(
            starts_at=starts_at,
        )

        subscription.current_period_start = current_period_start
        subscription.current_period_end = current_period_end
        subscription.next_billing_at = next_billing_at
        subscription.save(
            update_fields=[
                "current_period_start",
                "current_period_end",
                "next_billing_at",
                "updated_at",
            ]
        )

        wallet = SubscriptionService._wallet_for_organization(
            subscription.organization
        )

        CreditService.renew_plan_credits(
            wallet,
            subscription.credits_snapshot,
            actor=actor,
        )

        return subscription
