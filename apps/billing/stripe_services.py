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
    Plan,
    SubscriptionCheckoutAttempt,
    SubscriptionCheckoutAttemptStatus,
    StripeWebhookEvent,
    StripeWebhookEventStatus,
    Subscription,
    SubscriptionStatus,
)
from .services import SubscriptionService


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
        "customer.subscription.updated",
        "customer.subscription.deleted",
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
                "customer.subscription.updated": (
                    cls._handle_subscription_updated
                ),
                "customer.subscription.deleted": (
                    cls._handle_subscription_deleted
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
    def _sync_subscription_status(
        cls,
        stripe_subscription,
        *,
        deleted=False,
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
            return cls._apply_invoice(
                organization=organization,
                local_subscription=local_subscription,
                stripe_subscription=stripe_subscription,
                invoice=invoice,
                actor=actor,
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
