import hashlib
import logging
import random
import string
import uuid
from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.organizations.models import Organization

from .models import (
    BillingCycle,
    CreditPackage,
    CreditPurchase,
    CreditPurchaseStatus,
    PaymentDisputeStatus,
    Plan,
    SubscriptionCheckoutAttempt,
    SubscriptionCheckoutAttemptStatus,
    StripeWebhookEvent,
    StripeWebhookEventStatus,
    Subscription,
    SubscriptionStatus,
)
from .services import (
    BillingAccessService,
    CreditPurchaseService,
    PaymentDisputeService,
    SubscriptionService,
)


logger = logging.getLogger(__name__)


class StripePlanError(Exception):
    pass


class StripeConfigurationError(StripePlanError):
    pass


class StripeLiveModeError(StripePlanError):
    pass


class StripeSyncError(StripePlanError):
    pass


class StripePlanService:
    INTEGRATION = "maried-studio-v1"

    @classmethod
    def sync_plan(
        cls,
        plan,
    ):
        try:
            return cls._sync_plan(
                plan
            )

        except StripePlanError:
            raise

        except Exception as exc:
            raise StripeSyncError(
                "Não foi possível sincronizar este plano com o Stripe."
            ) from exc

    @classmethod
    def _sync_plan(
        cls,
        plan,
    ):
        cls.validate_key()

        product_id = cls.ensure_product(
            plan
        )

        if (
            product_id
            and not plan.stripe_product_id
        ):
            plan.stripe_product_id = product_id
            plan.save(
                update_fields=[
                    "stripe_product_id",
                    "updated_at",
                ]
            )

        price_signature = (
            cls.price_signature(
                plan
            )
        )

        price_id = plan.stripe_price_id

        if (
            not price_id
            or plan.stripe_price_signature
            != price_signature
        ):
            price_id = cls.create_price(
                plan,
                product_id=product_id,
                price_signature=(
                    price_signature
                ),
            )

        cls.update_product(
            plan,
            product_id=product_id,
        )

        plan.mark_stripe_synced(
            product_id=product_id,
            price_id=price_id,
            price_signature=price_signature,
        )

        return plan

    @classmethod
    def ensure_product(
        cls,
        plan,
    ):
        if plan.stripe_product_id:
            return plan.stripe_product_id

        product = cls.client().v1.products.create(
            params={
                "name": cls.product_name(
                    plan
                ),
                "description": (
                    plan.description or None
                ),
                "active": plan.is_active,
                "metadata": cls.metadata(
                    plan
                ),
            },
            options={
                "idempotency_key": (
                    cls.idempotency_key(
                        plan,
                        "product"
                    )
                ),
            },
        )

        product_id = getattr(
            product,
            "id",
            None,
        )

        if not product_id:
            raise StripeSyncError(
                "Stripe não retornou o Product ID."
            )

        return product_id

    @classmethod
    def update_product(
        cls,
        plan,
        *,
        product_id,
    ):
        cls.client().v1.products.update(
            product_id,
            params={
                "name": cls.product_name(
                    plan
                ),
                "description": (
                    plan.description or None
                ),
                "active": plan.is_active,
                "metadata": cls.metadata(
                    plan
                ),
            },
        )

    @classmethod
    def create_price(
        cls,
        plan,
        *,
        product_id,
        price_signature,
    ):
        price = cls.client().v1.prices.create(
            params={
                "product": product_id,
                "currency": cls.currency(),
                "unit_amount": cls.to_cents(
                    plan.price
                ),
                "recurring": {
                    "interval": cls.interval(
                        plan.billing_cycle
                    ),
                },
                "active": plan.is_active,
                "metadata": {
                    **cls.metadata(plan),
                    "maried_price_signature": (
                        price_signature
                    ),
                },
            },
            options={
                "idempotency_key": (
                    cls.idempotency_key(
                        plan,
                        f"price-{price_signature}"
                    )
                ),
            },
        )

        price_id = getattr(
            price,
            "id",
            None,
        )

        if not price_id:
            raise StripeSyncError(
                "Stripe não retornou o Price ID."
            )

        return price_id

    @staticmethod
    def to_cents(
        amount,
    ):
        cents = (
            Decimal(amount)
            .quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            * 100
        )

        return int(cents)

    @classmethod
    def price_signature(
        cls,
        plan,
    ):
        return "|".join(
            [
                cls.currency(),
                str(
                    cls.to_cents(
                        plan.price
                    )
                ),
                cls.interval(
                    plan.billing_cycle
                ),
            ]
        )

    @staticmethod
    def interval(
        billing_cycle,
    ):
        if (
            billing_cycle
            == BillingCycle.MONTHLY
        ):
            return "month"

        raise StripeSyncError(
            "Ciclo de cobrança não suportado pelo Stripe."
        )

    @staticmethod
    def currency():
        return settings.STRIPE_CURRENCY.lower()

    @staticmethod
    def product_name(
        plan,
    ):
        name = (
            plan.name or
            plan.slug or
            "Plano"
        )

        return f"MARIED STUDIO — {name}"

    @classmethod
    def metadata(
        cls,
        plan,
    ):
        return {
            "integration": cls.INTEGRATION,
            "maried_plan_id": str(plan.pk),
            "maried_plan_slug": plan.slug,
        }

    @classmethod
    def idempotency_key(
        cls,
        plan,
        operation,
    ):
        slug = (
            slugify(operation) or
            "sync"
        )

        return (
            f"maried-plan-{plan.pk}-{slug}"
        )

    @classmethod
    def validate_key(
        cls,
    ):
        secret_key = settings.STRIPE_SECRET_KEY

        if not secret_key:
            raise StripeConfigurationError(
                "STRIPE_SECRET_KEY não configurada."
            )

        if (
            secret_key.startswith("sk_live_")
            or secret_key.startswith("rk_live_")
        ) and not settings.STRIPE_ALLOW_LIVE_MODE:
            raise StripeLiveModeError(
                "Stripe test mode necessário para continuar."
            )

    @classmethod
    def client(
        cls,
    ):
        cls.validate_key()

        try:
            from stripe import StripeClient

        except ImportError as exc:
            raise StripeConfigurationError(
                "Stripe SDK não instalado."
            ) from exc

        return StripeClient(
            api_key=settings.STRIPE_SECRET_KEY,
            stripe_version=(
                settings.STRIPE_API_VERSION
            ),
        )


class StripeCreditPackageService:
    INTEGRATION = StripePlanService.INTEGRATION

    @classmethod
    def sync_package(cls, package):
        try:
            return cls._sync_package(
                package
            )

        except StripePlanError:
            raise

        except Exception as exc:
            raise StripeSyncError(
                "Não foi possível sincronizar este pacote com o Stripe."
            ) from exc

    @classmethod
    def _sync_package(cls, package):
        StripePlanService.validate_key()

        product_id = cls.ensure_product(
            package
        )

        if (
            product_id
            and not package.stripe_product_id
        ):
            package.stripe_product_id = product_id
            package.save(
                update_fields=[
                    "stripe_product_id",
                    "updated_at",
                ]
            )

        price_signature = cls.price_signature(
            package
        )
        price_id = package.stripe_price_id

        if (
            not price_id
            or package.stripe_price_signature
            != price_signature
        ):
            price_id = cls.create_price(
                package,
                product_id=product_id,
                price_signature=price_signature,
            )

        cls.update_product(
            package,
            product_id=product_id,
        )

        package.mark_stripe_synced(
            product_id=product_id,
            price_id=price_id,
            price_signature=price_signature,
        )

        return package

    @classmethod
    def ensure_product(cls, package):
        if package.stripe_product_id:
            return package.stripe_product_id

        product = StripePlanService.client().v1.products.create(
            params={
                "name": cls.product_name(
                    package
                ),
                "description": (
                    package.description or None
                ),
                "active": package.is_active,
                "metadata": cls.metadata(
                    package
                ),
            },
            options={
                "idempotency_key": (
                    cls.idempotency_key(
                        package,
                        "product",
                    )
                ),
            },
        )

        product_id = _stripe_value(
            product,
            "id",
        )

        if not product_id:
            raise StripeSyncError(
                "Stripe não retornou o Product ID."
            )

        return product_id

    @classmethod
    def update_product(
        cls,
        package,
        *,
        product_id,
    ):
        StripePlanService.client().v1.products.update(
            product_id,
            params={
                "name": cls.product_name(
                    package
                ),
                "description": (
                    package.description or None
                ),
                "active": package.is_active,
                "metadata": cls.metadata(
                    package
                ),
            },
        )

    @classmethod
    def create_price(
        cls,
        package,
        *,
        product_id,
        price_signature,
    ):
        price = StripePlanService.client().v1.prices.create(
            params={
                "product": product_id,
                "currency": package.currency.lower(),
                "unit_amount": StripePlanService.to_cents(
                    package.price
                ),
                "active": package.is_active,
                "metadata": {
                    **cls.metadata(package),
                    "maried_price_signature": price_signature,
                },
            },
            options={
                "idempotency_key": (
                    cls.idempotency_key(
                        package,
                        f"price-{price_signature}",
                    )
                ),
            },
        )

        price_id = _stripe_value(
            price,
            "id",
        )

        if not price_id:
            raise StripeSyncError(
                "Stripe não retornou o Price ID."
            )

        return price_id

    @staticmethod
    def product_name(package):
        name = (
            package.name
            or package.slug
            or "Pacote de créditos"
        )

        return f"MARIED STUDIO - {name}"

    @classmethod
    def metadata(cls, package):
        return {
            "integration": cls.INTEGRATION,
            "maried_credit_package_id": str(package.pk),
            "maried_credit_package_slug": package.slug,
            "maried_credit_package_credits": str(package.credits),
        }

    @staticmethod
    def price_signature(package):
        return "|".join(
            [
                package.currency.lower(),
                str(
                    StripePlanService.to_cents(
                        package.price
                    )
                ),
                str(package.credits),
            ]
        )

    @staticmethod
    def idempotency_key(package, operation):
        slug = slugify(operation) or "sync"

        return (
            f"maried-credit-package-{package.pk}-{slug}"
        )


class StripeBillingError(StripePlanError):
    pass


class StripeCheckoutUnavailableError(StripeBillingError):
    pass


class StripeSubscriptionAlreadyActiveError(StripeBillingError):
    pass


class StripeCheckoutRetryRequiredError(StripeBillingError):
    pass


class StripeCheckoutProviderError(StripeBillingError):
    pass


class StripeCreditPurchaseSessionError(StripeBillingError):
    pass


class StripeSubscriptionCancellationError(StripeBillingError):
    pass


class StripeReconciliationError(StripeBillingError):
    code = "STRIPE_RECONCILIATION_FAILED"

    def __init__(
        self,
        detail=None,
    ):
        self.detail = detail or "Não foi possível sincronizar com o Stripe."
        super().__init__(self.detail)


class StripeCustomerNotFoundError(StripeReconciliationError):
    code = "STRIPE_CUSTOMER_NOT_FOUND"


class StripeSubscriptionNotFoundError(StripeReconciliationError):
    code = "STRIPE_SUBSCRIPTION_NOT_FOUND"


class StripeSubscriptionAmbiguousError(StripeReconciliationError):
    code = "STRIPE_SUBSCRIPTION_AMBIGUOUS"


class StripePaidInvoiceNotFoundError(StripeReconciliationError):
    code = "STRIPE_PAID_INVOICE_NOT_FOUND"


class StripeReconciliationValidationError(StripeReconciliationError):
    code = "STRIPE_RECONCILIATION_FAILED"


@dataclass(frozen=True)
class StripeReconciliationResult:
    reconciled: bool
    applied: bool
    subscription: Subscription | None
    plan: Plan | None
    stripe_subscription_id: str
    stripe_subscription_status: str
    stripe_invoice_id: str
    stripe_customer_id: str
    stripe_price_id: str
    cycle_type: str | None = None
    disputes_reconciled: int = 0
    financial_blocked: bool = False


def _stripe_value(
    data,
    key,
    default=None,
):
    if isinstance(data, dict):
        return data.get(
            key,
            default,
        )

    return getattr(
        data,
        key,
        default,
    )


def _stripe_path(
    data,
    *keys,
    default=None,
):
    current = data

    for key in keys:
        current = _stripe_value(
            current,
            key,
        )

        if current is None:
            return default

    return current


def _stripe_timestamp(
    value,
):
    if value is None:
        return None

    return timezone.datetime.fromtimestamp(
        int(value),
        tz=datetime_timezone.utc,
    )


def _stripe_id(
    value,
):
    if isinstance(value, str):
        return value

    return _stripe_value(
        value,
        "id",
        "",
    )


def get_credit_purchase_for_payment(
    *,
    purchase_id,
    checkout_session_id="",
    payment_intent_id="",
):
    query = (
        CreditPurchase.objects
        .select_related(
            "organization",
            "subscription",
            "package",
        )
        .filter(
            pk=purchase_id,
        )
    )

    if checkout_session_id:
        query = query.filter(
            stripe_checkout_session_id=checkout_session_id,
        )

    purchase = query.first()

    if not purchase:
        raise StripeBillingError(
            "Compra de créditos não encontrada para pagamento Stripe."
        )

    if (
        payment_intent_id
        and purchase.stripe_payment_intent_id
        and purchase.stripe_payment_intent_id != payment_intent_id
    ):
        raise StripeBillingError(
            "PaymentIntent Stripe divergente para compra de créditos."
        )

    return purchase


class CreditPurchaseCheckoutService:
    @classmethod
    def client(cls):
        return StripePlanService.client()

    @classmethod
    def retrieve_session(cls, session_id):
        try:
            return (
                cls.client()
                .v1
                .checkout
                .sessions
                .retrieve(session_id)
            )

        except Exception as exc:
            raise StripeCreditPurchaseSessionError(
                "Não foi possível consultar a sessão Stripe."
            ) from exc

    @classmethod
    def expire_session(cls, session_id):
        try:
            return (
                cls.client()
                .v1
                .checkout
                .sessions
                .expire(session_id)
            )

        except Exception as exc:
            raise StripeCreditPurchaseSessionError(
                "Não foi possível cancelar a tentativa no Stripe."
            ) from exc

    @classmethod
    def sync_purchase_from_session(
        cls,
        *,
        purchase,
        session=None,
        event_id="",
    ):
        if purchase.status != CreditPurchaseStatus.PENDING:
            return purchase

        if not purchase.stripe_checkout_session_id:
            return purchase

        session = session or cls.retrieve_session(
            purchase.stripe_checkout_session_id
        )

        session_status = _stripe_value(
            session,
            "status",
            "",
        )
        payment_status = _stripe_value(
            session,
            "payment_status",
            "",
        )

        if (
            session_status == "complete"
            and payment_status == "paid"
        ):
            purchase, _applied = (
                CreditPurchaseService
                .apply_paid_purchase(
                    purchase=purchase,
                    stripe_customer_id=_stripe_id(
                        _stripe_value(
                            session,
                            "customer",
                            "",
                        )
                    ),
                    stripe_payment_intent_id=_stripe_id(
                        _stripe_value(
                            session,
                            "payment_intent",
                            "",
                        )
                    ),
                    amount_received=_stripe_value(
                        session,
                        "amount_total",
                        None,
                    ),
                    currency=_stripe_value(
                        session,
                        "currency",
                        "",
                    ),
                    event_id=event_id,
                )
            )

            return purchase

        if session_status == "expired":
            with transaction.atomic():
                purchase = (
                    CreditPurchase.objects
                    .select_for_update()
                    .get(pk=purchase.pk)
                )

                if purchase.status == CreditPurchaseStatus.PENDING:
                    purchase.status = CreditPurchaseStatus.EXPIRED
                    purchase.error_message = ""
                    purchase.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "updated_at",
                        ]
                    )

            return purchase

        return purchase

    @classmethod
    def sync_pending_for_subscription(
        cls,
        subscription,
        *,
        limit=5,
    ):
        if not subscription:
            return 0

        purchases = (
            CreditPurchase.objects
            .filter(
                subscription=subscription,
                status=CreditPurchaseStatus.PENDING,
                stripe_checkout_session_id__isnull=False,
            )
            .exclude(
                stripe_checkout_session_id="",
            )
            .order_by("-created_at")[:limit]
        )

        synced = 0

        for purchase in purchases:
            try:
                cls.sync_purchase_from_session(
                    purchase=purchase
                )
                synced += 1

            except StripeCreditPurchaseSessionError:
                logger.info(
                    "Credit purchase session sync skipped",
                    extra={
                        "credit_purchase_id": str(purchase.pk),
                    },
                )

        return synced

    @classmethod
    def cancel_pending_purchase(
        cls,
        *,
        purchase,
    ):
        if purchase.status == CreditPurchaseStatus.PAID:
            return purchase

        if purchase.status != CreditPurchaseStatus.PENDING:
            return purchase

        if not purchase.stripe_checkout_session_id:
            return CreditPurchaseService.cancel_purchase_session(
                purchase=purchase,
                status=CreditPurchaseStatus.EXPIRED,
            )

        session = cls.retrieve_session(
            purchase.stripe_checkout_session_id
        )
        session_status = _stripe_value(
            session,
            "status",
            "",
        )
        payment_status = _stripe_value(
            session,
            "payment_status",
            "",
        )

        if (
            session_status == "complete"
            and payment_status == "paid"
        ):
            return cls.sync_purchase_from_session(
                purchase=purchase,
                session=session,
            )

        if session_status == "open":
            session = cls.expire_session(
                purchase.stripe_checkout_session_id
            )

        return cls.sync_purchase_from_session(
            purchase=purchase,
            session=session,
        )


class StripeSubscriptionCancellationService:
    @classmethod
    def client(cls):
        return StripePlanService.client()

    @classmethod
    def _subscription_for_organization(
        cls,
        organization,
    ):
        subscription = (
            Subscription.objects
            .select_related(
                "organization",
                "plan",
            )
            .filter(
                organization=organization,
            )
            .first()
        )

        if (
            not subscription
            or not subscription.stripe_subscription_id
        ):
            raise StripeSubscriptionCancellationError(
                "Assinatura Stripe não encontrada."
            )

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise StripeSubscriptionCancellationError(
                "Somente assinatura ativa pode alterar renovação."
            )

        return subscription

    @classmethod
    def cancel_at_period_end(
        cls,
        *,
        organization,
    ):
        subscription = cls._subscription_for_organization(
            organization
        )

        try:
            stripe_subscription = (
                cls.client()
                .v1
                .subscriptions
                .update(
                    subscription.stripe_subscription_id,
                    params={
                        "cancel_at_period_end": True,
                    },
                )
            )

        except Exception as exc:
            raise StripeSubscriptionCancellationError(
                "Não foi possível cancelar a renovação no Stripe."
            ) from exc

        return StripeWebhookService.sync_subscription_object(
            stripe_subscription,
            fallback_subscription=subscription,
        )

    @classmethod
    def resume(
        cls,
        *,
        organization,
    ):
        subscription = cls._subscription_for_organization(
            organization
        )

        access = BillingAccessService.evaluate_organization(
            organization
        )

        if access.financial_blocked:
            raise StripeSubscriptionCancellationError(
                "Não é possível manter a assinatura durante bloqueio financeiro."
            )

        try:
            stripe_subscription = (
                cls.client()
                .v1
                .subscriptions
                .update(
                    subscription.stripe_subscription_id,
                    params={
                        "cancel_at_period_end": False,
                    },
                )
            )

        except Exception as exc:
            raise StripeSubscriptionCancellationError(
                "Não foi possível manter a assinatura no Stripe."
            ) from exc

        return StripeWebhookService.sync_subscription_object(
            stripe_subscription,
            fallback_subscription=subscription,
        )


class StripeBillingService:
    INTEGRATION = StripePlanService.INTEGRATION

    @classmethod
    def client(cls):
        return StripePlanService.client()

    @classmethod
    def validate_key(cls):
        return StripePlanService.validate_key()

    @staticmethod
    def frontend_url():
        return (
            getattr(
                settings,
                "FRONTEND_URL",
                "http://localhost:3000",
            )
            .rstrip("/")
        )

    @classmethod
    def ensure_customer(
        cls,
        *,
        organization,
        user,
    ):
        with transaction.atomic():
            organization = (
                Organization.objects
                .select_for_update()
                .get(
                    pk=organization.pk,
                )
            )

            if organization.stripe_customer_id:
                return organization.stripe_customer_id

            customer = cls.client().v1.customers.create(
                params={
                    "email": user.email,
                    "name": organization.name,
                    "metadata": {
                        "integration": cls.INTEGRATION,
                        "maried_organization_id": str(
                            organization.pk
                        ),
                        "maried_user_id": str(user.pk),
                    },
                },
                options={
                    "idempotency_key": (
                        f"maried-customer-{organization.pk}"
                    ),
                },
            )

            customer_id = _stripe_value(
                customer,
                "id",
            )

            if not customer_id:
                raise StripeBillingError(
                    "Stripe não retornou Customer ID."
                )

            organization.stripe_customer_id = customer_id
            organization.save(
                update_fields=[
                    "stripe_customer_id",
                    "updated_at",
                ]
            )

            return customer_id

    @classmethod
    def integration_identifier(cls):
        suffix = "".join(
            random.choice(
                string.ascii_lowercase
            )
            for _ in range(8)
        )

        return f"maried_studio_v1_{suffix}"

    @classmethod
    def create_subscription_checkout(
        cls,
        *,
        user,
        plan,
    ):
        if user.is_superuser:
            raise StripeCheckoutUnavailableError(
                "SuperAdmin não utiliza checkout de cliente."
            )

        organization = getattr(
            user,
            "organization",
            None,
        )

        if organization is None:
            raise StripeCheckoutUnavailableError(
                "Usuário não possui organização vinculada."
            )

        access = BillingAccessService.evaluate_organization(
            organization
        )

        if access.financial_blocked:
            raise StripeCheckoutUnavailableError(
                "Conta bloqueada por contestação financeira."
            )

        plan = Plan.objects.get(
            pk=plan.pk,
        )

        if not plan.stripe_ready_for_checkout:
            raise StripeCheckoutUnavailableError(
                "Plano indisponível para pagamento no momento."
            )

        existing = (
            Subscription.objects
            .filter(
                organization=organization,
                status__in=[
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PAST_DUE,
                ],
            )
            .first()
        )

        if existing:
            raise StripeSubscriptionAlreadyActiveError(
                "Organização já possui assinatura Stripe."
            )

        pending = (
            Subscription.objects
            .filter(
                organization=organization,
                status=SubscriptionStatus.PENDING,
            )
            .first()
        )

        if (
            pending
            and pending.plan_id != plan.pk
        ):
            raise StripeCheckoutUnavailableError(
                "Checkout permitido somente para o plano pendente."
            )

        customer_id = cls.ensure_customer(
            organization=organization,
            user=user,
        )
        success_url = (
            f"{cls.frontend_url()}"
            "/assinatura/sucesso"
            "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = (
            f"{cls.frontend_url()}"
            "/assinatura?checkout=cancelled"
        )
        request_signature = cls.checkout_request_signature(
            customer_id=customer_id,
            price_id=plan.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        with transaction.atomic():
            organization = (
                Organization.objects
                .select_for_update()
                .get(
                    pk=organization.pk,
                )
            )
            subscription = (
                Subscription.objects
                .select_for_update()
                .filter(
                    organization=organization,
                    status=SubscriptionStatus.PENDING,
                )
                .first()
            )

            attempt = cls.reusable_checkout_attempt(
                organization=organization,
                plan=plan,
                customer_id=customer_id,
                price_id=plan.stripe_price_id,
                request_signature=request_signature,
            )

            if attempt and cls.checkout_attempt_is_reusable(
                attempt
            ):
                return cls.checkout_attempt_response(
                    attempt
                )

            attempt = SubscriptionCheckoutAttempt(
                organization=organization,
                plan=plan,
                subscription=subscription,
                stripe_customer_id=customer_id,
                stripe_price_id=plan.stripe_price_id,
                request_signature=request_signature,
            )
            attempt.stripe_idempotency_key = (
                cls.checkout_idempotency_key(
                    attempt=attempt,
                )
            )
            attempt.save()

        session = cls.create_checkout_session(
            attempt=attempt,
            organization=organization,
            plan=plan,
            customer_id=customer_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        cls.update_checkout_attempt_from_session(
            attempt,
            session,
        )

        return cls.checkout_attempt_response(
            attempt
        )

    @classmethod
    def create_credit_checkout(
        cls,
        *,
        user,
        package,
    ):
        if user.is_superuser:
            raise StripeCheckoutUnavailableError(
                "SuperAdmin não utiliza checkout de cliente."
            )

        organization = getattr(
            user,
            "organization",
            None,
        )

        if organization is None:
            raise StripeCheckoutUnavailableError(
                "Usuário não possui organização vinculada."
            )

        access = BillingAccessService.evaluate_organization(
            organization
        )

        if access.financial_blocked:
            raise StripeCheckoutUnavailableError(
                "Conta bloqueada por contestação financeira."
            )

        package = CreditPackage.objects.get(
            pk=package.pk,
        )

        if not package.stripe_ready_for_checkout:
            raise StripeCheckoutUnavailableError(
                "Pacote indisponível para pagamento no momento."
            )

        subscription = (
            Subscription.objects
            .select_related("plan")
            .filter(
                organization=organization,
            )
            .first()
        )

        if not subscription:
            raise StripeCheckoutUnavailableError(
                "Assinatura ativa necessária para comprar créditos extras."
            )

        customer_id = cls.ensure_customer(
            organization=organization,
            user=user,
        )
        success_url = (
            f"{cls.frontend_url()}"
            "/creditos/sucesso"
            "?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = (
            f"{cls.frontend_url()}"
            "/creditos?checkout=cancelled"
        )
        request_signature = cls.checkout_request_signature(
            customer_id=customer_id,
            price_id=package.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        purchase, created = cls.create_or_reuse_credit_purchase(
            organization=organization,
            package=package,
            subscription=subscription,
            customer_id=customer_id,
            request_signature=request_signature,
        )

        if not created:
            return cls.credit_purchase_response(
                purchase
            )

        session = cls.create_credit_checkout_session(
            purchase=purchase,
            organization=organization,
            package=package,
            customer_id=customer_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        cls.update_credit_purchase_from_session(
            purchase,
            session,
        )

        return cls.credit_purchase_response(
            purchase
        )

    @classmethod
    def create_or_reuse_credit_purchase(
        cls,
        *,
        organization,
        package,
        subscription,
        customer_id,
        request_signature,
    ):
        purchase, created = (
            CreditPurchaseService
            .create_pending_purchase(
                organization=organization,
                package=package,
                subscription=subscription,
                stripe_customer_id=customer_id,
                request_signature=request_signature,
            )
        )

        if created:
            return purchase, created

        synced_purchase = (
            CreditPurchaseCheckoutService
            .sync_purchase_from_session(
                purchase=purchase
            )
        )

        if (
            synced_purchase.status
            == CreditPurchaseStatus.PENDING
        ):
            return synced_purchase, False

        return (
            CreditPurchaseService
            .create_pending_purchase(
                organization=organization,
                package=package,
                subscription=subscription,
                stripe_customer_id=customer_id,
                request_signature=request_signature,
            )
        )

    @classmethod
    def create_checkout_session(
        cls,
        *,
        attempt,
        organization,
        plan,
        customer_id,
        success_url,
        cancel_url,
    ):
        try:
            return cls.client().v1.checkout.sessions.create(
                params={
                    "mode": "subscription",
                    "customer": customer_id,
                    "line_items": [
                        {
                            "price": plan.stripe_price_id,
                            "quantity": 1,
                        },
                    ],
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                    "metadata": cls.checkout_metadata(
                        organization=organization,
                        plan=plan,
                        attempt=attempt,
                    ),
                    "subscription_data": {
                        "metadata": cls.checkout_metadata(
                            organization=organization,
                            plan=plan,
                            attempt=attempt,
                        ),
                    },
                    "integration_identifier": (
                        cls.integration_identifier()
                    ),
                },
                options={
                    "idempotency_key": (
                        attempt.stripe_idempotency_key
                    ),
                },
            )

        except Exception as exc:
            if cls.is_stripe_idempotency_error(
                exc
            ):
                raise StripeCheckoutRetryRequiredError(
                    "Não foi possível iniciar o pagamento. Tente novamente."
                ) from exc

            raise StripeCheckoutProviderError(
                "Não foi possível iniciar o pagamento. Tente novamente."
            ) from exc

    @classmethod
    def update_checkout_attempt_from_session(
        cls,
        attempt,
        session,
    ):
        url = _stripe_value(
            session,
            "url",
        )
        session_id = _stripe_value(
            session,
            "id",
        )

        if not url or not session_id:
            raise StripeBillingError(
                "Stripe não retornou Checkout Session válida."
            )

        attempt.stripe_checkout_session_id = session_id
        attempt.stripe_checkout_url = url
        attempt.status = SubscriptionCheckoutAttemptStatus.OPEN
        attempt.expires_at = _stripe_timestamp(
            _stripe_value(
                session,
                "expires_at",
            )
        )
        attempt.error_message = ""
        attempt.save(
            update_fields=[
                "stripe_checkout_session_id",
                "stripe_checkout_url",
                "status",
                "expires_at",
                "error_message",
                "updated_at",
            ]
        )

    @classmethod
    def create_credit_checkout_session(
        cls,
        *,
        purchase,
        organization,
        package,
        customer_id,
        success_url,
        cancel_url,
    ):
        try:
            return cls.client().v1.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "customer": customer_id,
                    "line_items": [
                        {
                            "price": package.stripe_price_id,
                            "quantity": 1,
                        },
                    ],
                    "success_url": success_url,
                    "cancel_url": cancel_url,
                    "metadata": cls.credit_checkout_metadata(
                        organization=organization,
                        package=package,
                        purchase=purchase,
                    ),
                    "payment_intent_data": {
                        "metadata": cls.credit_checkout_metadata(
                            organization=organization,
                            package=package,
                            purchase=purchase,
                        ),
                    },
                    "integration_identifier": (
                        cls.integration_identifier()
                    ),
                },
                options={
                    "idempotency_key": (
                        purchase.stripe_idempotency_key
                    ),
                },
            )

        except Exception as exc:
            if cls.is_stripe_idempotency_error(
                exc
            ):
                raise StripeCheckoutRetryRequiredError(
                    "Não foi possível iniciar o pagamento. Tente novamente."
                ) from exc

            raise StripeCheckoutProviderError(
                "Não foi possível iniciar o pagamento. Tente novamente."
            ) from exc

    @classmethod
    def update_credit_purchase_from_session(
        cls,
        purchase,
        session,
    ):
        url = _stripe_value(
            session,
            "url",
        )
        session_id = _stripe_value(
            session,
            "id",
        )
        payment_intent_id = _stripe_id(
            _stripe_value(
                session,
                "payment_intent",
                "",
            )
        )

        if not url or not session_id:
            raise StripeBillingError(
                "Stripe não retornou Checkout Session válida."
            )

        purchase.stripe_checkout_session_id = session_id
        purchase.stripe_checkout_url = url
        purchase.stripe_payment_intent_id = (
            payment_intent_id
            or purchase.stripe_payment_intent_id
        )
        purchase.expires_at = _stripe_timestamp(
            _stripe_value(
                session,
                "expires_at",
            )
        )
        purchase.error_message = ""
        purchase.save(
            update_fields=[
                "stripe_checkout_session_id",
                "stripe_checkout_url",
                "stripe_payment_intent_id",
                "expires_at",
                "error_message",
                "updated_at",
            ]
        )

    @classmethod
    def credit_purchase_response(
        cls,
        purchase,
    ):
        return {
            "purchase_id": str(purchase.pk),
            "checkout_session_id": (
                purchase.stripe_checkout_session_id
            ),
            "url": purchase.stripe_checkout_url,
            "status": purchase.status,
        }

    @classmethod
    def checkout_attempt_response(
        cls,
        attempt,
    ):
        return {
            "checkout_session_id": (
                attempt.stripe_checkout_session_id
            ),
            "url": attempt.stripe_checkout_url,
        }

    @classmethod
    def reusable_checkout_attempt(
        cls,
        *,
        organization,
        plan,
        customer_id,
        price_id,
        request_signature,
    ):
        return (
            SubscriptionCheckoutAttempt.objects
            .select_for_update()
            .filter(
                organization=organization,
                plan=plan,
                stripe_customer_id=customer_id,
                stripe_price_id=price_id,
                request_signature=request_signature,
                status__in=[
                    SubscriptionCheckoutAttemptStatus.CREATING,
                    SubscriptionCheckoutAttemptStatus.OPEN,
                ],
            )
            .order_by(
                "-created_at",
            )
            .first()
        )

    @classmethod
    def checkout_attempt_is_reusable(
        cls,
        attempt,
    ):
        if (
            attempt.status
            == SubscriptionCheckoutAttemptStatus.CREATING
        ):
            return False

        if not (
            attempt.stripe_checkout_session_id
            and attempt.stripe_checkout_url
        ):
            return False

        if (
            attempt.expires_at
            and attempt.expires_at <= timezone.now()
        ):
            attempt.status = (
                SubscriptionCheckoutAttemptStatus.EXPIRED
            )
            attempt.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )
            return False

        return True

    @classmethod
    def checkout_metadata(
        cls,
        *,
        organization,
        plan,
        attempt=None,
    ):
        metadata = {
            "integration": cls.INTEGRATION,
            "maried_organization_id": str(organization.pk),
            "maried_plan_id": str(plan.pk),
        }

        if attempt is not None:
            metadata["maried_checkout_attempt_id"] = (
                str(attempt.pk)
            )

        return metadata

    @classmethod
    def credit_checkout_metadata(
        cls,
        *,
        organization,
        package,
        purchase,
    ):
        return {
            "integration": cls.INTEGRATION,
            "maried_organization_id": str(organization.pk),
            "maried_credit_package_id": str(package.pk),
            "maried_credit_purchase_id": str(purchase.pk),
        }

    @classmethod
    def checkout_idempotency_key(
        cls,
        *,
        attempt,
    ):
        return (
            f"maried-checkout-{attempt.pk}"
        )

    @classmethod
    def checkout_request_signature(
        cls,
        *,
        customer_id,
        price_id,
        success_url,
        cancel_url,
    ):
        raw_signature = "|".join(
            [
                customer_id,
                price_id,
                success_url,
                cancel_url,
            ]
        )

        return hashlib.sha256(
            raw_signature.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def is_stripe_idempotency_error(exc):
        return (
            exc.__class__.__name__
            == "IdempotencyError"
        )


class StripeWebhookService:
    HANDLED_EVENTS = {
        "checkout.session.completed",
        "customer.subscription.created",
        "invoice.paid",
        "invoice.payment_succeeded",
        "invoice_payment.paid",
        "invoice.payment_failed",
        "payment_intent.succeeded",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "charge.dispute.created",
        "charge.dispute.updated",
        "charge.dispute.closed",
        "charge.dispute.funds_withdrawn",
        "charge.dispute.funds_reinstated",
    }

    @classmethod
    def construct_event(
        cls,
        *,
        payload,
        signature,
    ):
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise StripeConfigurationError(
                "STRIPE_WEBHOOK_SECRET não configurada."
            )

        try:
            from stripe import Webhook

            return Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )

        except ImportError as exc:
            raise StripeConfigurationError(
                "Stripe SDK não instalado."
            ) from exc

    @classmethod
    def process_event(
        cls,
        event,
    ):
        event_id = _stripe_value(
            event,
            "id",
        )
        event_type = _stripe_value(
            event,
            "type",
            "",
        )

        if not event_id:
            raise StripeBillingError(
                "Evento Stripe sem ID."
            )

        with transaction.atomic():
            webhook_event, created = (
                StripeWebhookEvent.objects
                .select_for_update()
                .get_or_create(
                    stripe_event_id=event_id,
                    defaults={
                        "event_type": event_type,
                    },
                )
            )

            if not created:
                return {
                    "duplicate": True,
                    "event_type": event_type,
                }

            data_object = _stripe_path(
                event,
                "data",
                "object",
                default={},
            )

            if event_type not in cls.HANDLED_EVENTS:
                cls._mark_processed(
                    webhook_event
                )

                return {
                    "processed": False,
                    "event_type": event_type,
                }

            handler = {
                "checkout.session.completed": (
                    cls._handle_checkout_completed
                ),
                "customer.subscription.created": (
                    cls._handle_subscription_created
                ),
                "invoice.paid": cls._handle_invoice_paid,
                "invoice.payment_succeeded": cls._handle_invoice_paid,
                "invoice_payment.paid": (
                    cls._handle_invoice_payment_paid
                ),
                "invoice.payment_failed": (
                    cls._handle_invoice_payment_failed
                ),
                "payment_intent.succeeded": (
                    cls._handle_payment_intent_succeeded
                ),
                "customer.subscription.updated": (
                    cls._handle_subscription_updated
                ),
                "customer.subscription.deleted": (
                    cls._handle_subscription_deleted
                ),
                "charge.dispute.created": cls._handle_dispute_event,
                "charge.dispute.updated": cls._handle_dispute_event,
                "charge.dispute.closed": cls._handle_dispute_event,
                "charge.dispute.funds_withdrawn": (
                    cls._handle_dispute_event
                ),
                "charge.dispute.funds_reinstated": (
                    cls._handle_dispute_event
                ),
            }[event_type]

            result = handler(
                data_object,
                webhook_event=webhook_event,
            )

            cls._mark_processed(
                webhook_event,
                organization=result.get("organization"),
                subscription=result.get("subscription"),
                stripe_customer_id=result.get(
                    "stripe_customer_id",
                    "",
                ),
                stripe_subscription_id=result.get(
                    "stripe_subscription_id",
                    "",
                ),
                stripe_invoice_id=result.get(
                    "stripe_invoice_id",
                    "",
                ),
            )

            return {
                "processed": True,
                "event_type": event_type,
                "cycle_type": result.get("cycle_type"),
                "applied": result.get("applied"),
            }

    @classmethod
    def _mark_processed(
        cls,
        webhook_event,
        *,
        organization=None,
        subscription=None,
        stripe_customer_id="",
        stripe_subscription_id="",
        stripe_invoice_id="",
    ):
        webhook_event.status = (
            StripeWebhookEventStatus.PROCESSED
        )
        webhook_event.organization = organization
        webhook_event.subscription = subscription
        webhook_event.stripe_customer_id = (
            stripe_customer_id or ""
        )
        webhook_event.stripe_subscription_id = (
            stripe_subscription_id or ""
        )
        webhook_event.stripe_invoice_id = (
            stripe_invoice_id or ""
        )
        webhook_event.processed_at = timezone.now()
        webhook_event.save()

    @classmethod
    def _handle_checkout_completed(
        cls,
        checkout_session,
        *,
        webhook_event,
    ):
        stripe_subscription_id = _stripe_value(
            checkout_session,
            "subscription",
            "",
        )
        stripe_customer_id = _stripe_value(
            checkout_session,
            "customer",
            "",
        )
        attempt_id = _stripe_path(
            checkout_session,
            "metadata",
            "maried_checkout_attempt_id",
        )
        purchase_id = _stripe_path(
            checkout_session,
            "metadata",
            "maried_credit_purchase_id",
        )

        if purchase_id:
            return cls._handle_credit_checkout_completed(
                checkout_session,
                webhook_event=webhook_event,
            )

        subscription = None

        if stripe_subscription_id:
            subscription = (
                Subscription.objects
                .filter(
                    stripe_subscription_id=(
                        stripe_subscription_id
                    )
                )
                .first()
            )

        if attempt_id:
            (
                SubscriptionCheckoutAttempt.objects
                .filter(
                    pk=attempt_id,
                )
                .update(
                    status=(
                        SubscriptionCheckoutAttemptStatus
                        .COMPLETED
                    ),
                    updated_at=timezone.now(),
                )
            )

        return {
            "subscription": subscription,
            "organization": (
                subscription.organization
                if subscription
                else None
            ),
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": (
                stripe_subscription_id
            ),
        }

    @classmethod
    def _handle_invoice_paid(
        cls,
        invoice,
        *,
        webhook_event,
    ):
        invoice = cls._invoice_with_financial_details(
            invoice
        )
        invoice_id = _stripe_id(
            invoice
        )
        stripe_customer_id = _stripe_id(
            _stripe_value(
                invoice,
                "customer",
                "",
            )
        )
        stripe_subscription_id = (
            cls._invoice_subscription_id(
                invoice
            )
        )
        stripe_price_id = cls._invoice_price_id(
            invoice
        )
        period_start = cls._invoice_period_start(
            invoice
        )
        period_end = cls._invoice_period_end(
            invoice
        )

        if not all(
            [
                invoice_id,
                stripe_customer_id,
                stripe_subscription_id,
                stripe_price_id,
                period_start,
                period_end,
            ]
        ):
            raise StripeBillingError(
                "Invoice paga sem dados financeiros mínimos."
            )

        organization = cls._organization_for_invoice(
            invoice,
            stripe_customer_id=stripe_customer_id,
        )
        plan = cls._plan_for_price(
            stripe_price_id
        )

        (
            subscription,
            cycle_type,
            applied,
        ) = SubscriptionService.apply_paid_stripe_invoice(
            organization=organization,
            plan=plan,
            stripe_invoice_id=invoice_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=stripe_price_id,
            stripe_status=(
                _stripe_value(
                    invoice,
                    "status",
                    "",
                )
            ),
            period_start=period_start,
            period_end=period_end,
            event_id=webhook_event.stripe_event_id,
        )

        if (
            organization.stripe_customer_id
            != stripe_customer_id
        ):
            organization.stripe_customer_id = (
                stripe_customer_id
            )
            organization.save(
                update_fields=[
                    "stripe_customer_id",
                    "updated_at",
                ]
            )

        return {
            "organization": organization,
            "subscription": subscription,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
            "stripe_invoice_id": invoice_id,
            "cycle_type": cycle_type,
            "applied": applied,
        }

    @classmethod
    def _handle_credit_checkout_completed(
        cls,
        checkout_session,
        *,
        webhook_event,
    ):
        if (
            _stripe_value(
                checkout_session,
                "payment_status",
                "",
            )
            != "paid"
        ):
            raise StripeBillingError(
                "Checkout de créditos concluído sem pagamento confirmado."
            )

        purchase_id = _stripe_path(
            checkout_session,
            "metadata",
            "maried_credit_purchase_id",
        )
        stripe_customer_id = _stripe_id(
            _stripe_value(
                checkout_session,
                "customer",
                "",
            )
        )
        payment_intent_id = _stripe_id(
            _stripe_value(
                checkout_session,
                "payment_intent",
                "",
            )
        )

        if not purchase_id:
            raise StripeBillingError(
                "Checkout de créditos sem compra vinculada."
            )

        purchase = get_credit_purchase_for_payment(
            purchase_id=purchase_id,
            checkout_session_id=_stripe_id(
                checkout_session
            ),
        )

        purchase, applied = (
            CreditPurchaseService
            .apply_paid_purchase(
                purchase=purchase,
                stripe_customer_id=stripe_customer_id,
                stripe_payment_intent_id=payment_intent_id,
                amount_received=_stripe_value(
                    checkout_session,
                    "amount_total",
                    None,
                ),
                currency=_stripe_value(
                    checkout_session,
                    "currency",
                    "",
                ),
                event_id=webhook_event.stripe_event_id,
            )
        )

        return {
            "organization": purchase.organization,
            "subscription": purchase.subscription,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": "",
            "stripe_invoice_id": "",
            "cycle_type": "CREDIT_PURCHASE",
            "applied": applied,
        }

    @classmethod
    def _handle_payment_intent_succeeded(
        cls,
        payment_intent,
        *,
        webhook_event,
    ):
        purchase_id = _stripe_path(
            payment_intent,
            "metadata",
            "maried_credit_purchase_id",
        )
        payment_intent_id = _stripe_id(
            payment_intent
        )

        if purchase_id:
            purchase = get_credit_purchase_for_payment(
                purchase_id=purchase_id,
                payment_intent_id=payment_intent_id,
            )
        else:
            purchase = (
                CreditPurchase.objects
                .select_related(
                    "organization",
                    "subscription",
                )
                .filter(
                    stripe_payment_intent_id=payment_intent_id,
                )
                .first()
            )

        if not purchase:
            raise StripeBillingError(
                "PaymentIntent pago sem compra de créditos vinculada."
            )

        purchase, applied = (
            CreditPurchaseService
            .apply_paid_purchase(
                purchase=purchase,
                stripe_customer_id=_stripe_id(
                    _stripe_value(
                        payment_intent,
                        "customer",
                        "",
                    )
                ),
                stripe_payment_intent_id=payment_intent_id,
                amount_received=_stripe_value(
                    payment_intent,
                    "amount_received",
                    None,
                ),
                currency=_stripe_value(
                    payment_intent,
                    "currency",
                    "",
                ),
                event_id=webhook_event.stripe_event_id,
            )
        )

        return {
            "organization": purchase.organization,
            "subscription": purchase.subscription,
            "stripe_customer_id": purchase.stripe_customer_id,
            "stripe_subscription_id": "",
            "stripe_invoice_id": "",
            "cycle_type": "CREDIT_PURCHASE",
            "applied": applied,
        }

    @classmethod
    def _handle_invoice_payment_paid(
        cls,
        invoice_payment,
        *,
        webhook_event,
    ):
        if (
            _stripe_value(
                invoice_payment,
                "status",
                "",
            )
            != "paid"
        ):
            raise StripeBillingError(
                "InvoicePayment recebido sem status paid."
            )

        invoice = cls._invoice_from_invoice_payment(
            invoice_payment
        )

        return cls._handle_invoice_paid(
            invoice,
            webhook_event=webhook_event,
        )

    @classmethod
    def _invoice_from_invoice_payment(
        cls,
        invoice_payment,
    ):
        invoice = _stripe_value(
            invoice_payment,
            "invoice",
        )

        if cls._is_invoice_object(
            invoice
        ):
            return invoice

        invoice_id = (
            invoice
            if isinstance(
                invoice,
                str,
            )
            else _stripe_value(
                invoice,
                "id",
            )
        )

        if not invoice_id:
            raise StripeBillingError(
                "InvoicePayment pago sem Invoice vinculada."
            )

        return cls.retrieve_invoice(
            invoice_id
        )

    @staticmethod
    def _is_invoice_object(
        invoice,
    ):
        if not invoice:
            return False

        object_type = _stripe_value(
            invoice,
            "object",
            "invoice",
        )

        return (
            object_type == "invoice"
            and bool(
                _stripe_value(
                    invoice,
                    "id",
                )
            )
        )

    @classmethod
    def retrieve_invoice(
        cls,
        invoice_id,
    ):
        try:
            return StripeBillingService.client().v1.invoices.retrieve(
                invoice_id,
                params={
                    "expand": [
                        "lines.data.price",
                        "lines.data.pricing.price_details",
                    ],
                },
            )

        except Exception as exc:
            raise StripeBillingError(
                "Invoice paga não pôde ser recuperada do Stripe."
            ) from exc

    @classmethod
    def _invoice_with_financial_details(
        cls,
        invoice,
    ):
        invoice_id = _stripe_id(
            invoice
        )

        if not invoice_id:
            return invoice

        if all(
            [
                cls._invoice_subscription_id(
                    invoice
                ),
                cls._invoice_price_id(
                    invoice
                ),
                cls._invoice_period_start(
                    invoice
                ),
                cls._invoice_period_end(
                    invoice
                ),
            ]
        ):
            return invoice

        return cls.retrieve_invoice(
            invoice_id
        )

    @classmethod
    def _handle_subscription_created(
        cls,
        stripe_subscription,
        *,
        webhook_event,
    ):
        return cls._sync_subscription_status(
            stripe_subscription
        )

    @classmethod
    def _handle_invoice_payment_failed(
        cls,
        invoice,
        *,
        webhook_event,
    ):
        stripe_subscription_id = (
            cls._invoice_subscription_id(
                invoice
            )
        )
        stripe_customer_id = _stripe_value(
            invoice,
            "customer",
            "",
        )

        subscription = None

        if stripe_subscription_id:
            subscription = (
                SubscriptionService
                .mark_stripe_payment_failed(
                    stripe_subscription_id=(
                        stripe_subscription_id
                    ),
                    stripe_customer_id=stripe_customer_id,
                )
            )

        return {
            "organization": (
                subscription.organization
                if subscription
                else None
            ),
            "subscription": subscription,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": (
                stripe_subscription_id
            ),
            "stripe_invoice_id": _stripe_value(
                invoice,
                "id",
                "",
            ),
        }

    @classmethod
    def _handle_subscription_updated(
        cls,
        stripe_subscription,
        *,
        webhook_event,
    ):
        return cls._sync_subscription_status(
            stripe_subscription
        )

    @classmethod
    def _handle_subscription_deleted(
        cls,
        stripe_subscription,
        *,
        webhook_event,
    ):
        result = cls._sync_subscription_status(
            stripe_subscription,
            deleted=True,
        )

        return result

    @classmethod
    def _handle_dispute_event(
        cls,
        dispute_object,
        *,
        webhook_event,
    ):
        dispute_id = _stripe_id(
            dispute_object
        )
        payment_intent_id = _stripe_id(
            _stripe_value(
                dispute_object,
                "payment_intent",
                "",
            )
        )
        charge_id = _stripe_id(
            _stripe_value(
                dispute_object,
                "charge",
                "",
            )
        )
        customer_id = cls._dispute_customer_id(
            dispute_object
        )
        dispute_status = _stripe_value(
            dispute_object,
            "status",
            "",
        )

        if not dispute_id or not dispute_status:
            raise StripeBillingError(
                "Disputa Stripe sem dados mínimos."
            )

        organization = cls._organization_for_dispute(
            dispute_object,
            stripe_customer_id=customer_id,
            payment_intent_id=payment_intent_id,
        )

        dispute = (
            PaymentDisputeService
            .upsert_from_stripe_dispute(
                organization=organization,
                stripe_dispute_id=dispute_id,
                stripe_payment_intent_id=payment_intent_id,
                stripe_charge_id=charge_id,
                stripe_customer_id=customer_id,
                amount=_stripe_value(
                    dispute_object,
                    "amount",
                    0,
                ) or 0,
                currency=_stripe_value(
                    dispute_object,
                    "currency",
                    "",
                ),
                status=dispute_status,
                reason=_stripe_value(
                    dispute_object,
                    "reason",
                    "",
                ),
                evidence_due_by=_stripe_timestamp(
                    _stripe_path(
                        dispute_object,
                        "evidence_details",
                        "due_by",
                    )
                ),
                event_id=webhook_event.stripe_event_id,
            )
        )

        return {
            "organization": organization,
            "subscription": dispute.related_subscription,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": (
                dispute.related_subscription.stripe_subscription_id
                if dispute.related_subscription
                else ""
            ),
            "stripe_invoice_id": "",
            "cycle_type": "DISPUTE",
            "applied": dispute.is_blocking,
        }

    @classmethod
    def _normalize_dispute(
        cls,
        dispute_object,
    ):
        dispute_id = _stripe_id(
            dispute_object
        )
        dispute_status = _stripe_value(
            dispute_object,
            "status",
            "",
        )

        if not dispute_id or not dispute_status:
            raise StripeBillingError(
                "Stripe dispute missing required data."
            )

        return {
            "stripe_dispute_id": dispute_id,
            "stripe_payment_intent_id": _stripe_id(
                _stripe_value(
                    dispute_object,
                    "payment_intent",
                    "",
                )
            ),
            "stripe_charge_id": _stripe_id(
                _stripe_value(
                    dispute_object,
                    "charge",
                    "",
                )
            ),
            "stripe_customer_id": cls._dispute_customer_id(
                dispute_object
            ),
            "amount": (
                _stripe_value(
                    dispute_object,
                    "amount",
                    0,
                )
                or 0
            ),
            "currency": _stripe_value(
                dispute_object,
                "currency",
                "",
            ),
            "status": dispute_status,
            "reason": _stripe_value(
                dispute_object,
                "reason",
                "",
            ),
            "evidence_due_by": _stripe_timestamp(
                _stripe_path(
                    dispute_object,
                    "evidence_details",
                    "due_by",
                )
            ),
        }

    @classmethod
    def _dispute_customer_id(
        cls,
        dispute_object,
    ):
        direct_customer = _stripe_id(
            _stripe_value(
                dispute_object,
                "customer",
                "",
            )
        )

        if direct_customer:
            return direct_customer

        payment_intent_customer = _stripe_id(
            _stripe_path(
                dispute_object,
                "payment_intent",
                "customer",
                default="",
            )
        )

        if payment_intent_customer:
            return payment_intent_customer

        return _stripe_id(
            _stripe_path(
                dispute_object,
                "charge",
                "customer",
                default="",
            )
        )

    @classmethod
    def _organization_for_dispute(
        cls,
        dispute_object,
        *,
        stripe_customer_id,
        payment_intent_id,
    ):
        if payment_intent_id:
            purchase = (
                CreditPurchase.objects
                .select_related(
                    "organization",
                )
                .filter(
                    stripe_payment_intent_id=payment_intent_id,
                )
                .first()
            )

            if purchase:
                if (
                    stripe_customer_id
                    and purchase.stripe_customer_id
                    and purchase.stripe_customer_id != stripe_customer_id
                ):
                    raise StripeBillingError(
                        "Disputa Stripe possui Customer divergente."
                    )

                return purchase.organization

        if stripe_customer_id:
            organization = (
                Organization.objects
                .filter(
                    stripe_customer_id=stripe_customer_id,
                )
                .first()
            )

            if organization:
                return organization

        organization_id = _stripe_path(
            dispute_object,
            "metadata",
            "maried_organization_id",
        )

        if organization_id:
            organization = Organization.objects.get(
                pk=organization_id,
            )

            if (
                stripe_customer_id
                and organization.stripe_customer_id
                and organization.stripe_customer_id != stripe_customer_id
            ):
                raise StripeBillingError(
                    "Disputa Stripe não corresponde à Organization."
                )

            return organization

        raise StripeBillingError(
            "Disputa Stripe sem Organization segura."
        )

    @classmethod
    def sync_subscription_object(
        cls,
        stripe_subscription,
        *,
        fallback_subscription=None,
    ):
        return cls._sync_subscription_status(
            stripe_subscription,
            fallback_subscription=fallback_subscription,
        )["subscription"]

    @classmethod
    def _sync_subscription_status(
        cls,
        stripe_subscription,
        *,
        deleted=False,
        fallback_subscription=None,
    ):
        stripe_subscription_id = _stripe_value(
            stripe_subscription,
            "id",
            "",
        )
        stripe_customer_id = _stripe_value(
            stripe_subscription,
            "customer",
            "",
        )
        stripe_status = _stripe_value(
            stripe_subscription,
            "status",
            "",
        )

        subscription = None

        if stripe_subscription_id:
            subscription = (
                Subscription.objects
                .filter(
                    stripe_subscription_id=(
                        stripe_subscription_id
                    )
                )
                .select_related(
                    "organization",
                )
                .first()
            )

        if subscription is None:
            subscription = fallback_subscription

        if not subscription:
            return {
                "stripe_customer_id": stripe_customer_id,
                "stripe_subscription_id": stripe_subscription_id,
            }

        if deleted:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = timezone.now()
        elif stripe_status == "past_due":
            subscription.status = SubscriptionStatus.PAST_DUE
        elif stripe_status == "canceled":
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = timezone.now()
        elif (
            stripe_status == "active"
            and subscription.current_period_end
        ):
            subscription.status = SubscriptionStatus.ACTIVE

        subscription.cancel_at_period_end = bool(
            _stripe_value(
                stripe_subscription,
                "cancel_at_period_end",
                False,
            )
        )
        subscription.stripe_customer_id = (
            stripe_customer_id
            or subscription.stripe_customer_id
        )
        subscription.stripe_status = stripe_status
        subscription.save(
            update_fields=[
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "stripe_customer_id",
                "stripe_status",
                "updated_at",
            ]
        )

        return {
            "organization": subscription.organization,
            "subscription": subscription,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
        }

    @classmethod
    def _organization_for_invoice(
        cls,
        invoice,
        *,
        stripe_customer_id,
    ):
        organization_id = _stripe_path(
            invoice,
            "subscription_details",
            "metadata",
            "maried_organization_id",
        )

        if organization_id:
            organization = Organization.objects.get(
                pk=organization_id,
            )
            if (
                organization.stripe_customer_id
                and organization.stripe_customer_id
                != stripe_customer_id
            ):
                raise StripeBillingError(
                    "Customer Stripe não corresponde à Organization."
                )

            return organization

        return Organization.objects.get(
            stripe_customer_id=stripe_customer_id,
        )

    @classmethod
    def _plan_for_price(
        cls,
        stripe_price_id,
    ):
        return Plan.objects.get(
            stripe_price_id=stripe_price_id,
        )

    @classmethod
    def _invoice_subscription_id(
        cls,
        invoice,
    ):
        subscription = (
            _stripe_value(
                invoice,
                "subscription",
            )
            or _stripe_path(
                invoice,
                "parent",
                "subscription_details",
                "subscription",
            )
            or _stripe_path(
                invoice,
                "subscription_details",
                "subscription",
            )
        )

        return _stripe_id(
            subscription
        )

    @classmethod
    def _invoice_price_id(
        cls,
        invoice,
    ):
        lines = _stripe_path(
            invoice,
            "lines",
            "data",
            default=[],
        )

        if not lines:
            return ""

        line = lines[0]

        price = (
            _stripe_path(
                line,
                "pricing",
                "price_details",
                "price",
            )
            or _stripe_value(
                line,
                "price",
            )
        )

        return _stripe_id(
            price
        )

    @classmethod
    def _invoice_period_start(
        cls,
        invoice,
    ):
        lines = _stripe_path(
            invoice,
            "lines",
            "data",
            default=[],
        )

        if lines:
            value = _stripe_path(
                lines[0],
                "period",
                "start",
            )

            if value:
                return _stripe_timestamp(
                    value
                )

        return _stripe_timestamp(
            _stripe_value(
                invoice,
                "period_start",
            )
        )

    @classmethod
    def _invoice_period_end(
        cls,
        invoice,
    ):
        lines = _stripe_path(
            invoice,
            "lines",
            "data",
            default=[],
        )

        if lines:
            value = _stripe_path(
                lines[0],
                "period",
                "end",
            )

            if value:
                return _stripe_timestamp(
                    value
                )

        return _stripe_timestamp(
            _stripe_value(
                invoice,
                "period_end",
            )
        )


class StripeReconciliationService:
    @classmethod
    def reconcile(
        cls,
        *,
        organization,
        actor=None,
    ):
        organization = Organization.objects.get(
            pk=organization.pk,
        )

        if not organization.stripe_customer_id:
            raise StripeCustomerNotFoundError(
                "Organization sem Customer Stripe vinculado."
            )

        local_subscription = (
            Subscription.objects
            .select_related("plan")
            .filter(organization=organization)
            .first()
        )

        try:
            stripe_subscription = cls._find_stripe_subscription(
                organization=organization,
                local_subscription=local_subscription,
            )
            invoice = cls._find_relevant_paid_invoice(
                organization=organization,
                stripe_subscription=stripe_subscription,
            )
            dispute_objects = cls._find_relevant_disputes(
                organization=organization,
                invoice=invoice,
            )

            with transaction.atomic():
                result = cls._apply_invoice(
                    organization=organization,
                    local_subscription=local_subscription,
                    stripe_subscription=stripe_subscription,
                    invoice=invoice,
                    actor=actor,
                )
                disputes_reconciled = cls._apply_disputes(
                    organization=organization,
                    dispute_objects=dispute_objects,
                    validated_reconciliation_organization=organization,
                )

            access = BillingAccessService.evaluate_organization(
                organization
            )

            return StripeReconciliationResult(
                reconciled=result.reconciled,
                applied=result.applied,
                subscription=result.subscription,
                plan=result.plan,
                stripe_subscription_id=result.stripe_subscription_id,
                stripe_subscription_status=(
                    result.stripe_subscription_status
                ),
                stripe_invoice_id=result.stripe_invoice_id,
                stripe_customer_id=result.stripe_customer_id,
                stripe_price_id=result.stripe_price_id,
                cycle_type=result.cycle_type,
                disputes_reconciled=disputes_reconciled,
                financial_blocked=access.financial_blocked,
            )

        except StripeReconciliationError:
            raise

        except Exception as exc:
            logger.exception(
                "Stripe reconciliation failed",
                extra={
                    "organization_id": str(organization.pk),
                    "stripe_customer_id": (
                        organization.stripe_customer_id
                    ),
                    "exception_class": exc.__class__.__name__,
                },
            )
            raise StripeReconciliationError() from exc

    @classmethod
    def _find_stripe_subscription(
        cls,
        *,
        organization,
        local_subscription,
    ):
        if (
            local_subscription
            and local_subscription.stripe_subscription_id
        ):
            stripe_subscription = cls.retrieve_subscription(
                local_subscription.stripe_subscription_id
            )
            cls._validate_subscription_candidate(
                stripe_subscription,
                organization=organization,
                local_subscription=local_subscription,
            )
            return stripe_subscription

        subscriptions = cls.list_subscriptions(
            organization.stripe_customer_id
        )
        candidates = []

        for stripe_subscription in subscriptions:
            try:
                plan = cls._plan_for_subscription(
                    stripe_subscription
                )
                cls._validate_subscription_candidate(
                    stripe_subscription,
                    organization=organization,
                    local_subscription=local_subscription,
                    plan=plan,
                )
            except Plan.DoesNotExist:
                continue

            candidates.append(stripe_subscription)

        if not candidates:
            raise StripeSubscriptionNotFoundError(
                "Nenhuma Subscription Stripe compatível foi encontrada."
            )

        if len(candidates) > 1:
            raise StripeSubscriptionAmbiguousError(
                "Mais de uma Subscription Stripe compatível foi encontrada."
            )

        return candidates[0]

    @classmethod
    def retrieve_subscription(
        cls,
        stripe_subscription_id,
    ):
        try:
            return StripeBillingService.client().v1.subscriptions.retrieve(
                stripe_subscription_id,
                params={
                    "expand": [
                        "items.data.price",
                        "latest_invoice",
                    ],
                },
            )

        except Exception as exc:
            raise StripeSubscriptionNotFoundError(
                "Subscription Stripe não pôde ser consultada."
            ) from exc

    @classmethod
    def list_subscriptions(
        cls,
        stripe_customer_id,
    ):
        try:
            response = StripeBillingService.client().v1.subscriptions.list(
                params={
                    "customer": stripe_customer_id,
                    "status": "all",
                    "limit": 10,
                    "expand": [
                        "data.items.data.price",
                        "data.latest_invoice",
                    ],
                },
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "Subscriptions Stripe não puderam ser consultadas."
            ) from exc

        return _stripe_value(
            response,
            "data",
            [],
        ) or []

    @classmethod
    def _validate_subscription_candidate(
        cls,
        stripe_subscription,
        *,
        organization,
        local_subscription,
        plan=None,
    ):
        stripe_customer_id = _stripe_id(
            _stripe_value(
                stripe_subscription,
                "customer",
                "",
            )
        )

        if stripe_customer_id != organization.stripe_customer_id:
            raise StripeReconciliationValidationError(
                "Customer Stripe não corresponde à Organization."
            )

        metadata_organization_id = _stripe_path(
            stripe_subscription,
            "metadata",
            "maried_organization_id",
        )

        if (
            metadata_organization_id
            and metadata_organization_id != str(organization.pk)
        ):
            raise StripeReconciliationValidationError(
                "Metadata da Subscription aponta para outra Organization."
            )

        plan = plan or cls._plan_for_subscription(
            stripe_subscription
        )

        metadata_plan_id = _stripe_path(
            stripe_subscription,
            "metadata",
            "maried_plan_id",
        )

        if (
            metadata_plan_id
            and metadata_plan_id != str(plan.pk)
        ):
            raise StripeReconciliationValidationError(
                "Metadata da Subscription aponta para outro Plan."
            )

        if (
            local_subscription
            and local_subscription.plan_id
            and local_subscription.plan_id != plan.pk
        ):
            raise StripeReconciliationValidationError(
                "Price Stripe não corresponde ao Plan local."
            )

    @classmethod
    def _find_relevant_paid_invoice(
        cls,
        *,
        organization,
        stripe_subscription,
    ):
        if (
            _stripe_value(
                stripe_subscription,
                "status",
                "",
            )
            != "active"
        ):
            raise StripePaidInvoiceNotFoundError(
                "Subscription Stripe não possui pagamento ativo aplicável."
            )

        stripe_subscription_id = _stripe_id(
            stripe_subscription
        )

        invoices = cls.list_paid_invoices(
            stripe_customer_id=organization.stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )

        for invoice in invoices:
            if cls._invoice_is_applicable(
                invoice,
                organization=organization,
                stripe_subscription_id=stripe_subscription_id,
            ):
                return invoice

        latest_invoice = _stripe_value(
            stripe_subscription,
            "latest_invoice",
        )

        if StripeWebhookService._is_invoice_object(
            latest_invoice
        ) and cls._invoice_is_applicable(
            latest_invoice,
            organization=organization,
            stripe_subscription_id=stripe_subscription_id,
        ):
            return latest_invoice

        raise StripePaidInvoiceNotFoundError(
            "Nenhuma Invoice paga aplicável foi encontrada no Stripe."
        )

    @classmethod
    def list_paid_invoices(
        cls,
        *,
        stripe_customer_id,
        stripe_subscription_id,
    ):
        try:
            response = StripeBillingService.client().v1.invoices.list(
                params={
                    "customer": stripe_customer_id,
                    "subscription": stripe_subscription_id,
                    "status": "paid",
                    "limit": 10,
                    "expand": [
                        "data.lines.data.price",
                        "data.lines.data.pricing.price_details",
                    ],
                },
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "Invoices Stripe não puderam ser consultadas."
            ) from exc

        return _stripe_value(
            response,
            "data",
            [],
        ) or []

    @classmethod
    def _invoice_is_applicable(
        cls,
        invoice,
        *,
        organization,
        stripe_subscription_id,
    ):
        if _stripe_value(invoice, "status", "") != "paid":
            return False

        stripe_customer_id = _stripe_id(
            _stripe_value(invoice, "customer", "")
        )

        if stripe_customer_id != organization.stripe_customer_id:
            raise StripeReconciliationValidationError(
                "Customer da Invoice não corresponde à Organization."
            )

        invoice_subscription_id = (
            StripeWebhookService._invoice_subscription_id(invoice)
        )

        if invoice_subscription_id != stripe_subscription_id:
            raise StripeReconciliationValidationError(
                "Invoice não pertence à Subscription reconciliada."
            )

        return True

    @classmethod
    def _find_relevant_disputes(
        cls,
        *,
        organization,
        invoice,
    ):
        (
            payment_intent_ids,
            charge_ids,
            direct_disputes_by_id,
        ) = (
            cls._payment_references_for_disputes(
                organization=organization,
                invoice=invoice,
            )
        )
        disputes_by_id = dict(direct_disputes_by_id)

        for dispute_object in list(disputes_by_id.values()):
            cls._validate_dispute_candidate(
                dispute_object,
                organization=organization,
            )

        for payment_intent_id in sorted(payment_intent_ids):
            for dispute_object in cls.list_disputes(
                payment_intent_id=payment_intent_id,
            ):
                cls._validate_dispute_candidate(
                    dispute_object,
                    organization=organization,
                )
                disputes_by_id[
                    _stripe_id(dispute_object)
                ] = dispute_object

        for charge_id in sorted(charge_ids):
            for dispute_object in cls.list_disputes(
                charge_id=charge_id,
            ):
                cls._validate_dispute_candidate(
                    dispute_object,
                    organization=organization,
                )
                disputes_by_id[
                    _stripe_id(dispute_object)
                ] = dispute_object

        return list(
            disputes_by_id.values()
        )

    @classmethod
    def _payment_references_for_disputes(
        cls,
        *,
        organization,
        invoice,
    ):
        payment_intent_ids = set()
        charge_ids = set()
        dispute_ids = set()
        payment_intents_by_id = {}
        charges_by_id = {}
        disputes_by_id = {}

        cls._add_payment_reference(
            payment_intent_ids,
            _stripe_value(
                invoice,
                "payment_intent",
                "",
            ),
            payment_intents_by_id,
            expected_object="payment_intent",
        )
        cls._add_payment_reference(
            charge_ids,
            _stripe_value(
                invoice,
                "charge",
                "",
            ),
            charges_by_id,
            expected_object="charge",
        )

        for payment_record in cls._invoice_payment_records(
            invoice=invoice,
            has_financial_reference=bool(
                payment_intent_ids
                or charge_ids
            ),
        ):
            payment_record_status = _stripe_value(
                payment_record,
                "status",
                "",
            )

            if (
                payment_record_status
                and payment_record_status != "paid"
            ):
                continue

            payment = _stripe_value(
                payment_record,
                "payment",
                {},
            )
            payment_type = _stripe_value(
                payment,
                "type",
                "",
            )

            if payment_type and payment_type != "payment_intent":
                continue

            payment_object_type = _stripe_value(
                payment,
                "object",
                "",
            )

            if payment_object_type == "payment_intent":
                cls._add_payment_reference(
                    payment_intent_ids,
                    payment,
                    payment_intents_by_id,
                    expected_object="payment_intent",
                )
            elif payment_object_type == "charge":
                cls._add_payment_reference(
                    charge_ids,
                    payment,
                    charges_by_id,
                    expected_object="charge",
                )

            cls._add_payment_reference(
                payment_intent_ids,
                _stripe_path(
                    payment,
                    "payment_intent",
                    default="",
                ),
                payment_intents_by_id,
                expected_object="payment_intent",
            )
            cls._add_payment_reference(
                charge_ids,
                _stripe_path(
                    payment,
                    "charge",
                    default="",
                ),
                charges_by_id,
                expected_object="charge",
            )

        for payment_intent_id in list(payment_intent_ids):
            payment_intent = payment_intents_by_id.get(
                payment_intent_id
            ) or cls.retrieve_payment_intent(
                payment_intent_id
            )
            payment_intents_by_id[payment_intent_id] = payment_intent
            cls._validate_payment_intent_candidate(
                payment_intent,
                organization=organization,
                payment_intent_id=payment_intent_id,
            )
            cls._add_payment_reference(
                charge_ids,
                _stripe_value(
                    payment_intent,
                    "latest_charge",
                    "",
                ),
                charges_by_id,
                expected_object="charge",
            )

            for charge in _stripe_path(
                payment_intent,
                "charges",
                "data",
                default=[],
            ) or []:
                cls._add_payment_reference(
                    charge_ids,
                    charge,
                    charges_by_id,
                    expected_object="charge",
                )

        for charge_id in list(charge_ids):
            charge = charges_by_id.get(
                charge_id
            ) or cls.retrieve_charge(
                charge_id
            )
            charges_by_id[charge_id] = charge
            cls._validate_charge_candidate(
                charge,
                organization=organization,
                charge_id=charge_id,
                payment_intent_ids=payment_intent_ids,
            )
            cls._add_payment_reference(
                payment_intent_ids,
                _stripe_value(
                    charge,
                    "payment_intent",
                    "",
                ),
                payment_intents_by_id,
                expected_object="payment_intent",
            )
            cls._add_payment_reference(
                dispute_ids,
                (
                    _stripe_value(
                        charge,
                        "dispute",
                        "",
                    )
                    if _stripe_value(
                        charge,
                        "disputed",
                        None,
                    ) is not False
                    else ""
                ),
                disputes_by_id,
                expected_object="dispute",
            )

        for purchase in (
            CreditPurchase.objects
            .filter(
                organization=organization,
            )
            .exclude(
                stripe_payment_intent_id__isnull=True,
            )
            .exclude(
                stripe_payment_intent_id="",
            )
        ):
            payment_intent_ids.add(
                purchase.stripe_payment_intent_id
            )

        for dispute_id in list(dispute_ids):
            if dispute_id not in disputes_by_id:
                disputes_by_id[dispute_id] = cls.retrieve_dispute(
                    dispute_id
                )

        return payment_intent_ids, charge_ids, disputes_by_id

    @classmethod
    def _invoice_payment_records(
        cls,
        *,
        invoice,
        has_financial_reference,
    ):
        invoice_payments = _stripe_path(
            invoice,
            "payments",
            "data",
            default=None,
        )

        if invoice_payments:
            return invoice_payments

        if has_financial_reference:
            return []

        invoice_id = _stripe_id(
            invoice
        )

        if not invoice_id:
            return []

        return cls.list_invoice_payments(
            invoice_id
        )

    @classmethod
    def list_invoice_payments(
        cls,
        invoice_id,
    ):
        try:
            response = StripeBillingService.client().v1.invoice_payments.list(
                params={
                    "invoice": invoice_id,
                    "limit": 10,
                },
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "InvoicePayments Stripe nao puderam ser consultados."
            ) from exc

        return _stripe_value(
            response,
            "data",
            [],
        ) or []

    @staticmethod
    def _add_payment_reference(
        target,
        value,
        objects_by_id=None,
        *,
        expected_object="",
    ):
        reference_id = _stripe_id(
            value
        )

        if reference_id:
            target.add(
                reference_id
            )

        if (
            reference_id
            and objects_by_id is not None
            and expected_object
            and _stripe_value(value, "object", "") == expected_object
        ):
            objects_by_id[reference_id] = value

    @classmethod
    def retrieve_payment_intent(
        cls,
        payment_intent_id,
    ):
        try:
            return StripeBillingService.client().v1.payment_intents.retrieve(
                payment_intent_id,
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "PaymentIntent Stripe nao pode ser consultado."
            ) from exc

    @classmethod
    def retrieve_charge(
        cls,
        charge_id,
    ):
        try:
            return StripeBillingService.client().v1.charges.retrieve(
                charge_id,
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "Charge Stripe nao pode ser consultada."
            ) from exc

    @classmethod
    def retrieve_dispute(
        cls,
        dispute_id,
    ):
        try:
            return StripeBillingService.client().v1.disputes.retrieve(
                dispute_id,
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "Stripe dispute could not be retrieved."
            ) from exc

    @classmethod
    def _validate_payment_intent_candidate(
        cls,
        payment_intent,
        *,
        organization,
        payment_intent_id,
    ):
        if _stripe_id(payment_intent) != payment_intent_id:
            raise StripeReconciliationValidationError(
                "PaymentIntent Stripe nao corresponde ao ID consultado."
            )

        customer_id = _stripe_id(
            _stripe_value(
                payment_intent,
                "customer",
                "",
            )
        )

        if customer_id and customer_id != organization.stripe_customer_id:
            logger.warning(
                "Stripe PaymentIntent customer mismatch during reconciliation",
                extra={
                    "organization_id": str(organization.pk),
                    "stripe_payment_intent_id": payment_intent_id,
                },
            )
            raise StripeReconciliationValidationError(
                "PaymentIntent Stripe pertence a outro Customer."
            )

    @classmethod
    def _validate_charge_candidate(
        cls,
        charge,
        *,
        organization,
        charge_id,
        payment_intent_ids,
    ):
        if _stripe_id(charge) != charge_id:
            raise StripeReconciliationValidationError(
                "Charge Stripe nao corresponde ao ID consultado."
            )

        customer_id = _stripe_id(
            _stripe_value(
                charge,
                "customer",
                "",
            )
        )

        if customer_id and customer_id != organization.stripe_customer_id:
            logger.warning(
                "Stripe charge customer mismatch during reconciliation",
                extra={
                    "organization_id": str(organization.pk),
                    "stripe_charge_id": charge_id,
                },
            )
            raise StripeReconciliationValidationError(
                "Charge Stripe pertence a outro Customer."
            )

        payment_intent_id = _stripe_id(
            _stripe_value(
                charge,
                "payment_intent",
                "",
            )
        )

        if (
            payment_intent_id
            and payment_intent_ids
            and payment_intent_id not in payment_intent_ids
        ):
            raise StripeReconciliationValidationError(
                "Charge Stripe nao pertence ao PaymentIntent reconciliado."
            )

    @classmethod
    def list_disputes(
        cls,
        *,
        payment_intent_id="",
        charge_id="",
    ):
        params = {
            "limit": 100,
        }

        if payment_intent_id:
            params["payment_intent"] = payment_intent_id
        elif charge_id:
            params["charge"] = charge_id
        else:
            return []

        try:
            response = StripeBillingService.client().v1.disputes.list(
                params=params,
            )

        except Exception as exc:
            raise StripeReconciliationError(
                "Stripe disputes could not be consulted."
            ) from exc

        return _stripe_value(
            response,
            "data",
            [],
        ) or []

    @classmethod
    def _validate_dispute_candidate(
        cls,
        dispute_object,
        *,
        organization,
    ):
        customer_id = StripeWebhookService._dispute_customer_id(
            dispute_object
        )

        if (
            customer_id
            and customer_id != organization.stripe_customer_id
        ):
            logger.warning(
                "Stripe dispute customer mismatch during reconciliation",
                extra={
                    "organization_id": str(organization.pk),
                    "stripe_dispute_id": _stripe_id(dispute_object),
                },
            )
            raise StripeReconciliationValidationError(
                "Stripe dispute belongs to another Customer."
            )

    @classmethod
    def _apply_disputes(
        cls,
        *,
        organization,
        dispute_objects,
        validated_reconciliation_organization=None,
    ):
        count = 0

        for dispute_object in dispute_objects:
            dispute_data = StripeWebhookService._normalize_dispute(
                dispute_object
            )
            if validated_reconciliation_organization is not None:
                if validated_reconciliation_organization.pk != organization.pk:
                    raise StripeReconciliationValidationError(
                        "Trusted reconciliation Organization mismatch."
                    )

                if (
                    dispute_data["stripe_customer_id"]
                    and dispute_data["stripe_customer_id"]
                    != validated_reconciliation_organization.stripe_customer_id
                ):
                    logger.warning(
                        "Trusted Stripe dispute customer mismatch",
                        extra={
                            "organization_id": str(organization.pk),
                            "stripe_dispute_id": dispute_data[
                                "stripe_dispute_id"
                            ],
                        },
                    )
                    raise StripeReconciliationValidationError(
                        "Stripe dispute belongs to another Customer."
                    )

                logger.info(
                    "Applying Stripe dispute with validated reconciliation organization",
                    extra={
                        "organization_id": str(organization.pk),
                        "stripe_dispute_id": dispute_data[
                            "stripe_dispute_id"
                        ],
                    },
                )
                dispute_organization = validated_reconciliation_organization
                dispute_data["stripe_customer_id"] = (
                    dispute_data["stripe_customer_id"]
                    or validated_reconciliation_organization.stripe_customer_id
                )
            else:
                dispute_organization = StripeWebhookService._organization_for_dispute(
                    dispute_object,
                    stripe_customer_id=dispute_data[
                        "stripe_customer_id"
                    ],
                    payment_intent_id=dispute_data[
                        "stripe_payment_intent_id"
                    ],
                )

            if dispute_organization.pk != organization.pk:
                raise StripeReconciliationValidationError(
                    "Stripe dispute points to another Organization."
                )

            PaymentDisputeService.upsert_from_stripe_dispute(
                organization=organization,
                **dispute_data,
                event_id="",
                source="RECONCILIATION",
            )
            count += 1

        return count

    @classmethod
    def _apply_invoice(
        cls,
        *,
        organization,
        local_subscription,
        stripe_subscription,
        invoice,
        actor=None,
    ):
        invoice_id = _stripe_id(invoice)
        stripe_customer_id = _stripe_id(
            _stripe_value(invoice, "customer", "")
        )
        stripe_subscription_id = (
            StripeWebhookService._invoice_subscription_id(invoice)
        )
        stripe_price_id = (
            StripeWebhookService._invoice_price_id(invoice)
        )
        period_start = (
            StripeWebhookService._invoice_period_start(invoice)
        )
        period_end = (
            StripeWebhookService._invoice_period_end(invoice)
        )

        if not all(
            [
                invoice_id,
                stripe_customer_id,
                stripe_subscription_id,
                stripe_price_id,
                period_start,
                period_end,
            ]
        ):
            raise StripeReconciliationValidationError(
                "Invoice paga sem dados financeiros mínimos."
            )

        plan = StripeWebhookService._plan_for_price(
            stripe_price_id
        )

        if (
            local_subscription
            and local_subscription.plan_id
            and local_subscription.plan_id != plan.pk
        ):
            raise StripeReconciliationValidationError(
                "Price da Invoice não corresponde ao Plan local."
            )

        invoice_organization = StripeWebhookService._organization_for_invoice(
            invoice,
            stripe_customer_id=stripe_customer_id,
        )

        if invoice_organization.pk != organization.pk:
            raise StripeReconciliationValidationError(
                "Invoice aponta para outra Organization."
            )

        stripe_status = _stripe_value(
            stripe_subscription,
            "status",
            "",
        )

        (
            subscription,
            cycle_type,
            applied,
        ) = SubscriptionService.apply_paid_stripe_invoice(
            organization=organization,
            plan=plan,
            stripe_invoice_id=invoice_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=stripe_price_id,
            stripe_status=stripe_status,
            period_start=period_start,
            period_end=period_end,
            event_id=(
                f"reconciliation:{uuid.uuid4()}"
            ),
        )

        return StripeReconciliationResult(
            reconciled=True,
            applied=applied,
            subscription=subscription,
            plan=plan,
            stripe_subscription_id=stripe_subscription_id,
            stripe_subscription_status=stripe_status,
            stripe_invoice_id=invoice_id,
            stripe_customer_id=stripe_customer_id,
            stripe_price_id=stripe_price_id,
            cycle_type=cycle_type,
        )

    @classmethod
    def _plan_for_subscription(
        cls,
        stripe_subscription,
    ):
        stripe_price_id = cls._subscription_price_id(
            stripe_subscription
        )

        if not stripe_price_id:
            raise Plan.DoesNotExist()

        return Plan.objects.get(
            stripe_price_id=stripe_price_id,
        )

    @staticmethod
    def _subscription_price_id(
        stripe_subscription,
    ):
        items = _stripe_path(
            stripe_subscription,
            "items",
            "data",
            default=[],
        )

        if not items:
            return ""

        price = _stripe_value(
            items[0],
            "price",
        )

        return _stripe_id(
            price
        )
