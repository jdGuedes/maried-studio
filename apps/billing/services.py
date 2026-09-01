import calendar
from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.credits.models import CreditWallet
from apps.credits.services import CreditService

from .models import (
    BillingCycle,
    CreditPackage,
    CreditPurchase,
    CreditPurchaseStatus,
    Plan,
    StripeInvoiceRecord,
    Subscription,
    SubscriptionStatus,
)


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


class CreditPackageUnavailableError(BillingError):
    pass


class CreditPurchaseNotAllowedError(BillingError):
    pass


class CreditPurchaseLimitExceededError(BillingError):
    pass


class CreditPurchasePaymentValidationError(BillingError):
    pass


class SubscriptionAccessStatus:
    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    BLOCKED = "BLOCKED"


class SubscriptionRequiredError(BillingError):
    code = "SUBSCRIPTION_REQUIRED"
    detail = (
        "Regularize sua assinatura para continuar usando o Studio."
    )

    def __init__(self, detail=None):
        super().__init__(
            detail or self.detail
        )


@dataclass(frozen=True)
class SubscriptionAccess:
    status: str
    subscription: Subscription | None = None
    grace_until: date | None = None
    days_remaining_in_grace: int | None = None
    can_create: bool = False
    can_purchase_credits: bool = False
    access_reason: str = "SUBSCRIPTION_REQUIRED"

    @property
    def allowed(self):
        return self.can_create


class BillingAccessService:
    GRACE_DAYS = 3

    @staticmethod
    def _local_date(value):
        if value is None:
            return None

        if timezone.is_naive(value):
            value = timezone.make_aware(value)

        return timezone.localtime(value).date()

    @staticmethod
    def evaluate_subscription(
        subscription,
        *,
        now=None,
        wallet=None,
    ):
        now = now or timezone.now()
        today = BillingAccessService._local_date(
            now
        )

        if subscription is None:
            return SubscriptionAccess(
                status=SubscriptionAccessStatus.BLOCKED,
                subscription=None,
                access_reason="SUBSCRIPTION_REQUIRED",
            )

        period_end = BillingAccessService._local_date(
            subscription.current_period_end
        )

        if period_end is None:
            return SubscriptionAccess(
                status=SubscriptionAccessStatus.BLOCKED,
                subscription=subscription,
                access_reason="SUBSCRIPTION_PERIOD_MISSING",
            )

        grace_until = (
            period_end
            +
            timezone.timedelta(
                days=BillingAccessService.GRACE_DAYS
            )
        )

        status = subscription.status

        if (
            status == SubscriptionStatus.ACTIVE
            and today <= period_end
        ):
            return SubscriptionAccess(
                status=SubscriptionAccessStatus.ACTIVE,
                subscription=subscription,
                grace_until=grace_until,
                can_create=True,
                can_purchase_credits=True,
                access_reason="ACTIVE",
            )

        if status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
        }:
            if period_end < today <= grace_until:
                return SubscriptionAccess(
                    status=SubscriptionAccessStatus.GRACE,
                    subscription=subscription,
                    grace_until=grace_until,
                    days_remaining_in_grace=(
                        grace_until - today
                    ).days,
                    can_create=True,
                    can_purchase_credits=False,
                    access_reason="GRACE",
                )

        if (
            status == SubscriptionStatus.CANCELED
            and wallet is None
        ):
            wallet = (
                CreditWallet.objects
                .filter(
                    organization=subscription.organization,
                )
                .first()
            )

        if (
            status == SubscriptionStatus.CANCELED
            and wallet is not None
            and wallet.available_purchased_balance > 0
        ):
            return SubscriptionAccess(
                status=SubscriptionAccessStatus.BLOCKED,
                subscription=subscription,
                grace_until=grace_until,
                can_create=True,
                can_purchase_credits=False,
                access_reason="CANCELED_WITH_PURCHASED_CREDITS",
            )

        return SubscriptionAccess(
            status=SubscriptionAccessStatus.BLOCKED,
            subscription=subscription,
            grace_until=grace_until,
            can_create=False,
            can_purchase_credits=False,
            access_reason="SUBSCRIPTION_BLOCKED",
        )

    @staticmethod
    def evaluate_organization(
        organization,
        *,
        now=None,
    ):
        subscription = (
            Subscription.objects
            .select_related(
                "plan",
                "organization",
            )
            .filter(
                organization=organization,
            )
            .first()
        )

        wallet = (
            CreditWallet.objects
            .filter(
                organization=organization,
            )
            .first()
        )

        return BillingAccessService.evaluate_subscription(
            subscription,
            now=now,
            wallet=wallet,
        )

    @staticmethod
    def ensure_operational_access(
        organization,
        *,
        now=None,
    ):
        access = BillingAccessService.evaluate_organization(
            organization,
            now=now,
        )

        if not access.allowed:
            raise SubscriptionRequiredError()

        return access


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
    def create_pending(
        *,
        organization,
        plan,
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
            raise SubscriptionAlreadyActiveError(
                "Organização já possui assinatura ativa."
            )

        if subscription is None:
            subscription = Subscription(
                organization=organization,
            )

        subscription.plan = plan
        subscription.status = SubscriptionStatus.PENDING
        subscription.price_snapshot = plan.price
        subscription.credits_snapshot = plan.credits_per_cycle
        subscription.started_at = None
        subscription.current_period_start = None
        subscription.current_period_end = None
        subscription.next_billing_at = None
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.save()

        SubscriptionService._wallet_for_organization(
            organization
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

    @staticmethod
    @transaction.atomic
    def apply_paid_stripe_invoice(
        *,
        organization,
        plan,
        stripe_invoice_id,
        stripe_customer_id,
        stripe_subscription_id,
        stripe_price_id,
        stripe_status,
        period_start,
        period_end,
        event_id,
    ):
        existing_invoice = (
            StripeInvoiceRecord.objects
            .select_related(
                "subscription",
            )
            .filter(
                stripe_invoice_id=stripe_invoice_id,
            )
            .first()
        )

        if existing_invoice:
            return (
                existing_invoice.subscription,
                existing_invoice.cycle_type,
                False,
            )

        plan = (
            Plan.objects
            .select_for_update()
            .get(
                pk=plan.pk,
            )
        )

        subscription = (
            Subscription.objects
            .select_for_update()
            .filter(
                organization=organization,
            )
            .first()
        )

        is_first_cycle = (
            subscription is None
            or not subscription.last_processed_stripe_invoice_id
        )

        if is_first_cycle:
            SubscriptionService._validate_plan_for_activation(
                plan
            )
        elif (
            plan.billing_cycle
            != BillingCycle.MONTHLY
        ):
            raise UnsupportedBillingCycleError(
                "Somente ciclo mensal é suportado na V1."
            )

        if subscription is None:
            subscription = Subscription(
                organization=organization,
                started_at=period_start,
            )

        subscription.plan = plan
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.price_snapshot = plan.price
        subscription.credits_snapshot = plan.credits_per_cycle

        if is_first_cycle:
            subscription.started_at = (
                subscription.started_at
                or period_start
            )

        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.next_billing_at = period_end
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.stripe_customer_id = stripe_customer_id
        subscription.stripe_subscription_id = (
            stripe_subscription_id
        )
        subscription.stripe_price_id = stripe_price_id
        subscription.stripe_status = stripe_status
        subscription.last_processed_stripe_invoice_id = (
            stripe_invoice_id
        )
        subscription.save()

        wallet = SubscriptionService._wallet_for_organization(
            organization
        )

        CreditService.renew_plan_credits(
            wallet,
            subscription.credits_snapshot,
            description=(
                "Créditos do ciclo pago via Stripe."
            ),
        )

        cycle_type = (
            "FIRST"
            if is_first_cycle
            else "RENEWAL"
        )

        StripeInvoiceRecord.objects.create(
            stripe_invoice_id=stripe_invoice_id,
            organization=organization,
            subscription=subscription,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            stripe_price_id=stripe_price_id,
            period_start=period_start,
            period_end=period_end,
            processed_event_id=event_id,
            cycle_type=cycle_type,
        )

        return (
            subscription,
            cycle_type,
            True,
        )

    @staticmethod
    @transaction.atomic
    def mark_stripe_payment_failed(
        *,
        stripe_subscription_id,
        stripe_customer_id="",
        stripe_status="past_due",
    ):
        subscription = (
            Subscription.objects
            .select_for_update()
            .filter(
                stripe_subscription_id=stripe_subscription_id,
            )
            .first()
        )

        if not subscription:
            return None

        if subscription.last_processed_stripe_invoice_id:
            subscription.status = SubscriptionStatus.PAST_DUE
        else:
            subscription.status = SubscriptionStatus.PENDING

        subscription.stripe_customer_id = (
            stripe_customer_id
            or subscription.stripe_customer_id
        )
        subscription.stripe_status = stripe_status
        subscription.save(
            update_fields=[
                "status",
                "stripe_customer_id",
                "stripe_status",
                "updated_at",
            ]
        )

        return subscription


class CreditPurchaseService:
    @staticmethod
    def active_cycle_purchases_query(subscription):
        return CreditPurchase.objects.filter(
            subscription=subscription,
            cycle_start=subscription.current_period_start,
            cycle_end=subscription.current_period_end,
        )

    @staticmethod
    def expire_stale_pending_purchases(*, now=None):
        now = now or timezone.now()

        return (
            CreditPurchase.objects
            .filter(
                status=CreditPurchaseStatus.PENDING,
                expires_at__isnull=False,
                expires_at__lte=now,
            )
            .update(
                status=CreditPurchaseStatus.EXPIRED,
                updated_at=now,
            )
        )

    @classmethod
    def allowance_for_subscription(
        cls,
        subscription,
        *,
        now=None,
    ):
        now = now or timezone.now()
        cls.expire_stale_pending_purchases(
            now=now
        )

        if (
            not subscription
            or not subscription.current_period_start
            or not subscription.current_period_end
        ):
            return {
                "extra_credit_limit_per_cycle": 0,
                "paid_credits_this_cycle": 0,
                "pending_credits_this_cycle": 0,
                "remaining_extra_credits": 0,
            }

        queryset = cls.active_cycle_purchases_query(
            subscription
        )

        paid = (
            queryset
            .filter(
                status=CreditPurchaseStatus.PAID,
            )
            .aggregate(total=Sum("credits_snapshot"))
            ["total"]
            or 0
        )

        pending = (
            queryset
            .filter(
                status=CreditPurchaseStatus.PENDING,
            )
            .filter(
                expires_at__isnull=True,
            )
            .aggregate(total=Sum("credits_snapshot"))
            ["total"]
            or 0
        )

        pending += (
            queryset
            .filter(
                status=CreditPurchaseStatus.PENDING,
                expires_at__gt=now,
            )
            .aggregate(total=Sum("credits_snapshot"))
            ["total"]
            or 0
        )

        limit = (
            subscription
            .plan
            .extra_credit_limit_per_cycle
        )

        return {
            "extra_credit_limit_per_cycle": limit,
            "paid_credits_this_cycle": paid,
            "pending_credits_this_cycle": pending,
            "remaining_extra_credits": max(
                0,
                limit - paid - pending,
            ),
        }

    @classmethod
    @transaction.atomic
    def create_pending_purchase(
        cls,
        *,
        organization,
        package,
        subscription,
        stripe_customer_id,
        request_signature,
    ):
        cls.expire_stale_pending_purchases()

        subscription = (
            Subscription.objects
            .select_for_update()
            .select_related("plan")
            .get(
                pk=subscription.pk,
            )
        )

        access = BillingAccessService.evaluate_subscription(
            subscription,
            wallet=(
                CreditWallet.objects
                .filter(
                    organization=organization,
                )
                .first()
            ),
        )

        if not access.can_purchase_credits:
            raise CreditPurchaseNotAllowedError(
                "Compra de créditos disponível apenas para assinatura ativa."
            )

        if not package.stripe_ready_for_checkout:
            raise CreditPackageUnavailableError(
                "Pacote indisponível para pagamento no momento."
            )

        existing = (
            CreditPurchase.objects
            .select_for_update()
            .filter(
                organization=organization,
                package=package,
                subscription=subscription,
                status=CreditPurchaseStatus.PENDING,
                request_signature=request_signature,
            )
            .order_by("-created_at")
            .first()
        )

        if (
            existing
            and existing.is_pending_reservation
            and existing.stripe_checkout_session_id
            and existing.stripe_checkout_url
        ):
            return existing, False

        allowance = cls.allowance_for_subscription(
            subscription
        )

        if (
            package.credits
            > allowance["remaining_extra_credits"]
        ):
            raise CreditPurchaseLimitExceededError(
                "Pacote excede o limite de créditos extras deste ciclo."
            )

        purchase = CreditPurchase(
            organization=organization,
            package=package,
            subscription=subscription,
            plan=subscription.plan,
            credits_snapshot=package.credits,
            price_snapshot=package.price,
            currency_snapshot=package.currency.upper(),
            stripe_price_id_snapshot=package.stripe_price_id,
            extra_credit_limit_snapshot=(
                subscription.plan.extra_credit_limit_per_cycle
            ),
            cycle_start=subscription.current_period_start,
            cycle_end=subscription.current_period_end,
            stripe_customer_id=stripe_customer_id,
            request_signature=request_signature,
        )
        purchase.stripe_idempotency_key = (
            f"maried-credit-checkout-{purchase.pk}"
        )
        purchase.save()

        return purchase, True

    @staticmethod
    def _validate_payment(
        *,
        purchase,
        stripe_customer_id,
        stripe_payment_intent_id,
        amount_received,
        currency,
    ):
        if (
            stripe_customer_id
            and stripe_customer_id
            != purchase.stripe_customer_id
        ):
            raise CreditPurchasePaymentValidationError(
                "Customer Stripe divergente para compra de créditos."
            )

        if (
            amount_received is not None
            and int(amount_received)
            != int(purchase.price_snapshot * 100)
        ):
            raise CreditPurchasePaymentValidationError(
                "Valor pago divergente para compra de créditos."
            )

        if (
            currency
            and currency.upper()
            != purchase.currency_snapshot.upper()
        ):
            raise CreditPurchasePaymentValidationError(
                "Moeda divergente para compra de créditos."
            )

        if stripe_payment_intent_id:
            other = (
                CreditPurchase.objects
                .filter(
                    stripe_payment_intent_id=(
                        stripe_payment_intent_id
                    ),
                )
                .exclude(
                    pk=purchase.pk,
                )
                .first()
            )

            if other:
                raise CreditPurchasePaymentValidationError(
                    "PaymentIntent Stripe já vinculado a outra compra."
                )

    @classmethod
    @transaction.atomic
    def apply_paid_purchase(
        cls,
        *,
        purchase,
        stripe_customer_id="",
        stripe_payment_intent_id="",
        amount_received=None,
        currency="",
        event_id="",
    ):
        purchase = (
            CreditPurchase.objects
            .select_for_update()
            .select_related(
                "organization",
                "package",
                "subscription",
            )
            .get(
                pk=purchase.pk,
            )
        )

        if purchase.status == CreditPurchaseStatus.PAID:
            return purchase, False

        cls._validate_payment(
            purchase=purchase,
            stripe_customer_id=stripe_customer_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            amount_received=amount_received,
            currency=currency,
        )

        wallet, _ = (
            CreditWallet.objects
            .get_or_create(
                organization=purchase.organization,
            )
        )

        CreditService.add_purchased_credits(
            wallet,
            purchase.credits_snapshot,
            description=(
                "Compra de créditos avulsos via Stripe."
            ),
        )

        purchase.status = CreditPurchaseStatus.PAID
        purchase.stripe_payment_intent_id = (
            stripe_payment_intent_id
            or purchase.stripe_payment_intent_id
        )
        purchase.processed_event_id = event_id
        purchase.paid_at = timezone.now()
        purchase.error_message = ""
        purchase.save(
            update_fields=[
                "status",
                "stripe_payment_intent_id",
                "processed_event_id",
                "paid_at",
                "error_message",
                "updated_at",
            ]
        )

        return purchase, True

    @staticmethod
    @transaction.atomic
    def cancel_purchase_session(
        *,
        purchase,
        status=CreditPurchaseStatus.CANCELED,
    ):
        purchase = (
            CreditPurchase.objects
            .select_for_update()
            .get(
                pk=purchase.pk,
            )
        )

        if purchase.status == CreditPurchaseStatus.PENDING:
            purchase.status = status
            purchase.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return purchase


class SubscriptionDelinquencyService:
    @classmethod
    def finalize_expired_grace(
        cls,
        *,
        now=None,
    ):
        now = now or timezone.now()
        processed = 0

        subscriptions = (
            Subscription.objects
            .select_related(
                "organization",
                "plan",
            )
            .filter(
                status=SubscriptionStatus.PAST_DUE,
            )
        )

        for subscription in subscriptions:
            access = BillingAccessService.evaluate_subscription(
                subscription,
                now=now,
            )

            if access.status != SubscriptionAccessStatus.BLOCKED:
                continue

            cls.cancel_after_grace(
                subscription=subscription,
                now=now,
            )
            processed += 1

        return processed

    @staticmethod
    @transaction.atomic
    def cancel_after_grace(
        *,
        subscription,
        now=None,
    ):
        now = now or timezone.now()

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

        wallet, _ = (
            CreditWallet.objects
            .get_or_create(
                organization=subscription.organization,
            )
        )

        CreditService.expire_plan_credits(
            wallet,
            description=(
                "Créditos do plano expirados após fim do período de tolerância."
            ),
        )

        subscription.status = SubscriptionStatus.CANCELED
        subscription.cancel_at_period_end = False
        subscription.canceled_at = now
        subscription.save(
            update_fields=[
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "updated_at",
            ]
        )

        return subscription
