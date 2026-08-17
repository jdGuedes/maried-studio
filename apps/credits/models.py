from django.db import models

from apps.common.models import (
    UUIDTimeStampedModel,
)


# ==========================================================
# TIPOS DE TRANSAÇÃO
# ==========================================================

class CreditTransactionType(
    models.TextChoices
):
    PLAN_GRANT = (
        "PLAN_GRANT",
        "Créditos do plano",
    )

    PLAN_EXPIRE = (
        "PLAN_EXPIRE",
        "Expiração do plano",
    )

    PURCHASE = (
        "PURCHASE",
        "Compra avulsa",
    )

    BONUS = (
        "BONUS",
        "Bônus",
    )

    RESERVE = (
        "RESERVE",
        "Reserva",
    )

    CONSUME = (
        "CONSUME",
        "Consumo",
    )

    REFUND = (
        "REFUND",
        "Estorno",
    )

    ADJUSTMENT = (
        "ADJUSTMENT",
        "Ajuste administrativo",
    )


# ==========================================================
# CARTEIRA
# ==========================================================

class CreditWallet(
    UUIDTimeStampedModel
):
    organization = (
        models.OneToOneField(
            "organizations.Organization",
            on_delete=models.CASCADE,
            related_name="credit_wallet",
        )
    )

    # ======================================================
    # COMPATIBILIDADE
    #
    # Mantemos balance durante a transição.
    # Ele será sempre sincronizado com:
    #
    # plan_balance + purchased_balance
    # ======================================================

    balance = models.PositiveIntegerField(
        default=0
    )

    reserved_balance = (
        models.PositiveIntegerField(
            default=0
        )
    )

    # ======================================================
    # NOVOS SALDOS
    # ======================================================

    plan_balance = (
        models.PositiveIntegerField(
            default=0
        )
    )

    purchased_balance = (
        models.PositiveIntegerField(
            default=0
        )
    )

    # ======================================================
    # RESERVAS POR ORIGEM
    # ======================================================

    plan_reserved_balance = (
        models.PositiveIntegerField(
            default=0
        )
    )

    purchased_reserved_balance = (
        models.PositiveIntegerField(
            default=0
        )
    )

    # ======================================================
    # PROPRIEDADES
    # ======================================================

    @property
    def available_plan_balance(
        self,
    ):
        return max(
            self.plan_balance
            - self.plan_reserved_balance,
            0,
        )

    @property
    def available_purchased_balance(
        self,
    ):
        return max(
            self.purchased_balance
            - self.purchased_reserved_balance,
            0,
        )

    @property
    def available_balance(
        self,
    ):
        return (
            self.available_plan_balance
            +
            self.available_purchased_balance
        )

    @property
    def total_balance(
        self,
    ):
        return (
            self.plan_balance
            +
            self.purchased_balance
        )

    def __str__(self):
        return (
            f"{self.organization} "
            f"→ {self.available_balance} créditos"
        )


# ==========================================================
# TRANSAÇÃO
# ==========================================================

class CreditTransaction(
    UUIDTimeStampedModel
):
    wallet = models.ForeignKey(
        CreditWallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    generation = models.ForeignKey(
        "studio.Generation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=(
            "credit_transactions"
        ),
    )

    # Usuário responsável por uma ação administrativa.
    # Em operações automáticas pode ficar vazio.

    actor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=(
            "credit_adjustments"
        ),
    )

    type = models.CharField(
        max_length=30,
        choices=(
            CreditTransactionType
            .choices
        ),
    )

    # Variação total.
    amount = models.IntegerField()

    # Quanto alterou créditos do plano.
    plan_amount = models.IntegerField(
        default=0
    )

    # Quanto alterou créditos comprados.
    purchased_amount = (
        models.IntegerField(
            default=0
        )
    )

    # ======================================================
    # SNAPSHOT TOTAL
    # ======================================================

    balance_before = (
        models.IntegerField()
    )

    balance_after = (
        models.IntegerField()
    )

    reserved_before = (
        models.IntegerField(
            default=0
        )
    )

    reserved_after = (
        models.IntegerField(
            default=0
        )
    )

    # ======================================================
    # SNAPSHOT POR ORIGEM
    # ======================================================

    plan_balance_before = (
        models.IntegerField(
            default=0
        )
    )

    plan_balance_after = (
        models.IntegerField(
            default=0
        )
    )

    purchased_balance_before = (
        models.IntegerField(
            default=0
        )
    )

    purchased_balance_after = (
        models.IntegerField(
            default=0
        )
    )

    plan_reserved_before = (
        models.IntegerField(
            default=0
        )
    )

    plan_reserved_after = (
        models.IntegerField(
            default=0
        )
    )

    purchased_reserved_before = (
        models.IntegerField(
            default=0
        )
    )

    purchased_reserved_after = (
        models.IntegerField(
            default=0
        )
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    reason = models.CharField(
        max_length=255,
        blank=True,
    )