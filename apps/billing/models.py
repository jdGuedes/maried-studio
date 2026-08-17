from django.db import models

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

    is_active = models.BooleanField(
        default=True
    )

    sort_order = (
        models.PositiveIntegerField(
            default=0
        )
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