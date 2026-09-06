from django.db import models
from django.utils import timezone

from apps.common.models import (
    UUIDTimeStampedModel,
)


# ==========================================================
# CICLO DO PLANO
# ==========================================================

class BillingCycle(
    models.TextChoices
):
    MONTHLY = (
        "MONTHLY",
        "Mensal",
    )


# ==========================================================
# STATUS DA ASSINATURA
# ==========================================================

class SubscriptionStatus(
    models.TextChoices
):
    PENDING = (
        "PENDING",
        "Pendente",
    )

    ACTIVE = (
        "ACTIVE",
        "Ativa",
    )

    PAST_DUE = (
        "PAST_DUE",
        "Pagamento pendente",
    )

    SUSPENDED = (
        "SUSPENDED",
        "Suspensa",
    )

    CANCELED = (
        "CANCELED",
        "Cancelada",
    )


class StripeWebhookEventStatus(
    models.TextChoices
):
    PROCESSING = (
        "PROCESSING",
        "Processando",
    )

    PROCESSED = (
        "PROCESSED",
        "Processado",
    )


class SubscriptionCheckoutAttemptStatus(
    models.TextChoices
):
    CREATING = (
        "CREATING",
        "Criando",
    )

    OPEN = (
        "OPEN",
        "Aberta",
    )

    COMPLETED = (
        "COMPLETED",
        "Concluída",
    )

    EXPIRED = (
        "EXPIRED",
        "Expirada",
    )

    FAILED = (
        "FAILED",
        "Falhou",
    )


class CreditPurchaseStatus(
    models.TextChoices
):
    PENDING = (
        "PENDING",
        "Pendente",
    )

    PAID = (
        "PAID",
        "Paga",
    )

    FAILED = (
        "FAILED",
        "Falhou",
    )

    CANCELED = (
        "CANCELED",
        "Cancelada",
    )

    EXPIRED = (
        "EXPIRED",
        "Expirada",
    )


class PaymentDisputeOriginType(
    models.TextChoices
):
    SUBSCRIPTION = (
        "SUBSCRIPTION",
        "Assinatura",
    )

    CREDIT_PURCHASE = (
        "CREDIT_PURCHASE",
        "Compra de créditos",
    )

    UNKNOWN = (
        "UNKNOWN",
        "Desconhecida",
    )


class PaymentDisputeStatus(
    models.TextChoices
):
    WARNING_NEEDS_RESPONSE = (
        "warning_needs_response",
        "Alerta exige resposta",
    )

    WARNING_UNDER_REVIEW = (
        "warning_under_review",
        "Alerta em análise",
    )

    WARNING_CLOSED = (
        "warning_closed",
        "Alerta encerrado",
    )

    NEEDS_RESPONSE = (
        "needs_response",
        "Exige resposta",
    )

    UNDER_REVIEW = (
        "under_review",
        "Em análise",
    )

    WON = (
        "won",
        "Ganha",
    )

    LOST = (
        "lost",
        "Perdida",
    )

    PREVENTED = (
        "prevented",
        "Prevenida",
    )


# ==========================================================
# PLANO
# ==========================================================

class Plan(
    UUIDTimeStampedModel
):
    name = models.CharField(
        max_length=120
    )

    slug = models.SlugField(
        max_length=140,
        unique=True,
    )

    description = models.TextField(
        blank=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )

    credits_per_cycle = (
        models.PositiveIntegerField(
            default=0
        )
    )

    extra_credit_limit_per_cycle = (
        models.PositiveIntegerField(
            default=0
        )
    )

    is_active = models.BooleanField(
        default=True
    )

    sort_order = (
        models.PositiveIntegerField(
            default=0
        )
    )

    stripe_product_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_price_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_price_signature = models.CharField(
        max_length=80,
        blank=True,
    )

    stripe_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    stripe_sync_error = models.TextField(
        blank=True,
    )

    @property
    def stripe_ready_for_checkout(self):
        return (
            self.is_active
            and bool(self.stripe_product_id)
            and bool(self.stripe_price_id)
            and not self.stripe_sync_error
        )

    def mark_stripe_sync_error(
        self,
        message,
    ):
        self.stripe_sync_error = (
            str(message)[:1000]
        )
        self.stripe_synced_at = None
        self.save(
            update_fields=[
                "stripe_sync_error",
                "stripe_synced_at",
                "updated_at",
            ]
        )

    def mark_stripe_synced(
        self,
        *,
        product_id,
        price_id,
        price_signature,
    ):
        self.stripe_product_id = product_id
        self.stripe_price_id = price_id
        self.stripe_price_signature = (
            price_signature
        )
        self.stripe_sync_error = ""
        self.stripe_synced_at = timezone.now()
        self.save(
            update_fields=[
                "stripe_product_id",
                "stripe_price_id",
                "stripe_price_signature",
                "stripe_sync_error",
                "stripe_synced_at",
                "updated_at",
            ]
        )

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.credits_per_cycle} créditos)"
        )

    class Meta:
        ordering = [
            "sort_order",
            "price",
        ]


class CreditPackage(
    UUIDTimeStampedModel
):
    name = models.CharField(
        max_length=120
    )

    slug = models.SlugField(
        max_length=140,
        unique=True,
    )

    description = models.TextField(
        blank=True
    )

    credits = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="BRL",
    )

    is_active = models.BooleanField(
        default=True
    )

    sort_order = (
        models.PositiveIntegerField(
            default=0
        )
    )

    stripe_product_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_price_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_price_signature = models.CharField(
        max_length=80,
        blank=True,
    )

    stripe_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    stripe_sync_error = models.TextField(
        blank=True,
    )

    @property
    def stripe_ready_for_checkout(self):
        return (
            self.is_active
            and bool(self.stripe_product_id)
            and bool(self.stripe_price_id)
            and not self.stripe_sync_error
        )

    def mark_stripe_sync_error(
        self,
        message,
    ):
        self.stripe_sync_error = (
            str(message)[:1000]
        )
        self.stripe_synced_at = None
        self.save(
            update_fields=[
                "stripe_sync_error",
                "stripe_synced_at",
                "updated_at",
            ]
        )

    def mark_stripe_synced(
        self,
        *,
        product_id,
        price_id,
        price_signature,
    ):
        self.stripe_product_id = product_id
        self.stripe_price_id = price_id
        self.stripe_price_signature = price_signature
        self.stripe_sync_error = ""
        self.stripe_synced_at = timezone.now()
        self.save(
            update_fields=[
                "stripe_product_id",
                "stripe_price_id",
                "stripe_price_signature",
                "stripe_sync_error",
                "stripe_synced_at",
                "updated_at",
            ]
        )

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.credits} créditos)"
        )

    class Meta:
        ordering = [
            "sort_order",
            "price",
        ]


# ==========================================================
# ASSINATURA
# ==========================================================

class Subscription(
    UUIDTimeStampedModel
):
    organization = (
        models.OneToOneField(
            "organizations.Organization",
            on_delete=models.CASCADE,
            related_name="subscription",
        )
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    status = models.CharField(
        max_length=20,
        choices=(
            SubscriptionStatus
            .choices
        ),
        default=(
            SubscriptionStatus
            .PENDING
        ),
    )

    # ------------------------------------------------------
    # SNAPSHOT COMERCIAL
    #
    # Mantemos o que foi contratado, mesmo se o plano
    # for alterado posteriormente.
    # ------------------------------------------------------

    price_snapshot = (
        models.DecimalField(
            max_digits=10,
            decimal_places=2,
        )
    )

    credits_snapshot = (
        models.PositiveIntegerField()
    )

    started_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    current_period_start = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    current_period_end = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    next_billing_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    cancel_at_period_end = (
        models.BooleanField(
            default=False
        )
    )

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_status = models.CharField(
        max_length=50,
        blank=True,
    )

    last_processed_stripe_invoice_id = (
        models.CharField(
            max_length=255,
            unique=True,
            null=True,
            blank=True,
        )
    )

    canceled_at = (
        models.DateTimeField(
            null=True,
            blank=True,
        )
    )

    def __str__(self):
        return (
            f"{self.organization} "
            f"→ {self.plan.name}"
        )

class CreditPurchase(
    UUIDTimeStampedModel
):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="credit_purchases",
    )

    package = models.ForeignKey(
        CreditPackage,
        on_delete=models.PROTECT,
        related_name="purchases",
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="credit_purchases",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="credit_purchases",
    )

    status = models.CharField(
        max_length=20,
        choices=CreditPurchaseStatus.choices,
        default=CreditPurchaseStatus.PENDING,
    )

    credits_snapshot = models.PositiveIntegerField()

    price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    currency_snapshot = models.CharField(
        max_length=3,
    )

    stripe_price_id_snapshot = models.CharField(
        max_length=255,
    )

    extra_credit_limit_snapshot = (
        models.PositiveIntegerField(
            default=0
        )
    )

    cycle_start = models.DateTimeField()

    cycle_end = models.DateTimeField()

    stripe_customer_id = models.CharField(
        max_length=255,
    )

    stripe_checkout_session_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_checkout_url = models.TextField(
        blank=True,
    )

    stripe_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    stripe_idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    request_signature = models.CharField(
        max_length=255,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    processed_event_id = models.CharField(
        max_length=255,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    @property
    def is_pending_reservation(self):
        return (
            self.status == CreditPurchaseStatus.PENDING
            and (
                self.expires_at is None
                or self.expires_at > timezone.now()
            )
        )

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "subscription",
                    "status",
                    "cycle_start",
                    "cycle_end",
                ],
                name="billing_purchase_cycle",
            ),
            models.Index(
                fields=[
                    "stripe_checkout_session_id",
                ],
                name="billing_purchase_session",
            ),
            models.Index(
                fields=[
                    "stripe_payment_intent_id",
                ],
                name="billing_purchase_pi",
            ),
        ]


class PaymentDispute(
    UUIDTimeStampedModel
):
    BLOCKING_STATUSES = {
        PaymentDisputeStatus.WARNING_NEEDS_RESPONSE,
        PaymentDisputeStatus.WARNING_UNDER_REVIEW,
        PaymentDisputeStatus.NEEDS_RESPONSE,
        PaymentDisputeStatus.UNDER_REVIEW,
        PaymentDisputeStatus.LOST,
    }

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="payment_disputes",
    )

    stripe_dispute_id = models.CharField(
        max_length=255,
        unique=True,
    )

    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_charge_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
    )

    related_subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_disputes",
    )

    related_credit_purchase = models.ForeignKey(
        CreditPurchase,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_disputes",
    )

    origin_type = models.CharField(
        max_length=30,
        choices=PaymentDisputeOriginType.choices,
        default=PaymentDisputeOriginType.UNKNOWN,
    )

    amount = models.IntegerField(
        default=0,
    )

    currency = models.CharField(
        max_length=3,
        blank=True,
    )

    status = models.CharField(
        max_length=40,
        choices=PaymentDisputeStatus.choices,
    )

    reason = models.CharField(
        max_length=120,
        blank=True,
    )

    evidence_due_by = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_event_id = models.CharField(
        max_length=255,
        blank=True,
    )

    @property
    def is_blocking(self):
        return self.status in self.BLOCKING_STATUSES

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "status",
                ],
                name="billing_dispute_org_status",
            ),
            models.Index(
                fields=[
                    "stripe_payment_intent_id",
                ],
                name="billing_dispute_pi",
            ),
            models.Index(
                fields=[
                    "stripe_charge_id",
                ],
                name="billing_dispute_charge",
            ),
        ]


class StripeWebhookEvent(
    UUIDTimeStampedModel
):
    stripe_event_id = models.CharField(
        max_length=255,
        unique=True,
    )

    event_type = models.CharField(
        max_length=120,
    )

    status = models.CharField(
        max_length=20,
        choices=StripeWebhookEventStatus.choices,
        default=StripeWebhookEventStatus.PROCESSING,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stripe_webhook_events",
    )

    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stripe_webhook_events",
    )

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_invoice_id = models.CharField(
        max_length=255,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]


class StripeInvoiceRecord(
    UUIDTimeStampedModel
):
    stripe_invoice_id = models.CharField(
        max_length=255,
        unique=True,
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="stripe_invoice_records",
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="stripe_invoice_records",
    )

    stripe_subscription_id = models.CharField(
        max_length=255,
    )

    stripe_customer_id = models.CharField(
        max_length=255,
    )

    stripe_price_id = models.CharField(
        max_length=255,
    )

    period_start = models.DateTimeField()

    period_end = models.DateTimeField()

    processed_event_id = models.CharField(
        max_length=255,
    )

    cycle_type = models.CharField(
        max_length=20,
    )

    class Meta:
        ordering = [
            "-period_start",
        ]


class SubscriptionCheckoutAttempt(
    UUIDTimeStampedModel
):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscription_checkout_attempts",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscription_checkout_attempts",
    )

    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="checkout_attempts",
    )

    status = models.CharField(
        max_length=20,
        choices=SubscriptionCheckoutAttemptStatus.choices,
        default=SubscriptionCheckoutAttemptStatus.CREATING,
    )

    stripe_customer_id = models.CharField(
        max_length=255,
    )

    stripe_price_id = models.CharField(
        max_length=255,
    )

    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
    )

    stripe_checkout_url = models.TextField(
        blank=True,
    )

    stripe_idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    request_signature = models.CharField(
        max_length=255,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "plan",
                    "status",
                ],
                name="billing_co_attempt_lookup",
            ),
            models.Index(
                fields=[
                    "stripe_checkout_session_id",
                ],
                name="billing_co_session_lookup",
            ),
        ]
