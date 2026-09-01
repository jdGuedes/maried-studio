from django.db import transaction

from .models import (
    CreditTransaction,
    CreditTransactionType,
    CreditWallet,
)


class InsufficientCredits(
    Exception
):
    pass


class CreditService:
    # ======================================================
    # HELPERS
    # ======================================================

    @staticmethod
    def _sync_totals(
        wallet: CreditWallet
    ):
        wallet.balance = (
            wallet.plan_balance
            +
            wallet.purchased_balance
        )

        wallet.reserved_balance = (
            wallet.plan_reserved_balance
            +
            wallet.purchased_reserved_balance
        )

    @staticmethod
    def _snapshot(
        wallet: CreditWallet
    ):
        return {
            "balance":
                wallet.balance,

            "reserved":
                wallet.reserved_balance,

            "plan_balance":
                wallet.plan_balance,

            "purchased_balance":
                wallet.purchased_balance,

            "plan_reserved":
                wallet.plan_reserved_balance,

            "purchased_reserved":
                wallet.purchased_reserved_balance,
        }

    @staticmethod
    def _create_transaction(
        *,
        wallet,
        transaction_type,
        amount,
        before,
        generation=None,
        actor=None,
        plan_amount=0,
        purchased_amount=0,
        description="",
        reason="",
    ):
        CreditTransaction.objects.create(
            wallet=wallet,
            generation=generation,
            actor=actor,

            type=transaction_type,

            amount=amount,

            plan_amount=(
                plan_amount
            ),

            purchased_amount=(
                purchased_amount
            ),

            balance_before=(
                before["balance"]
            ),

            balance_after=(
                wallet.balance
            ),

            reserved_before=(
                before["reserved"]
            ),

            reserved_after=(
                wallet.reserved_balance
            ),

            plan_balance_before=(
                before[
                    "plan_balance"
                ]
            ),

            plan_balance_after=(
                wallet.plan_balance
            ),

            purchased_balance_before=(
                before[
                    "purchased_balance"
                ]
            ),

            purchased_balance_after=(
                wallet.purchased_balance
            ),

            plan_reserved_before=(
                before[
                    "plan_reserved"
                ]
            ),

            plan_reserved_after=(
                wallet.plan_reserved_balance
            ),

            purchased_reserved_before=(
                before[
                    "purchased_reserved"
                ]
            ),

            purchased_reserved_after=(
                wallet
                .purchased_reserved_balance
            ),

            description=description,
            reason=reason,
        )

    # ======================================================
    # RESERVAR
    #
    # Primeiro reserva créditos do plano.
    # Depois créditos comprados.
    # ======================================================

    @staticmethod
    @transaction.atomic
    def reserve(
        wallet:
            CreditWallet,
        generation,
        amount:
            int = 1,
    ):
        existing = (
            CreditTransaction.objects
            .filter(
                wallet=wallet,
                generation=generation,
                type=(
                    CreditTransactionType
                    .RESERVE
                ),
            )
            .first()
        )

        if existing:
            return (
                CreditWallet.objects
                .get(
                    pk=wallet.pk
                )
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        if (
            wallet.available_balance
            < amount
        ):
            raise InsufficientCredits(
                "Créditos insuficientes."
            )

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        # ----------------------------------------------
        # PLANO PRIMEIRO
        # ----------------------------------------------

        plan_amount = min(
            amount,
            wallet
            .available_plan_balance,
        )

        purchased_amount = (
            amount
            - plan_amount
        )

        wallet.plan_reserved_balance += (
            plan_amount
        )

        wallet.purchased_reserved_balance += (
            purchased_amount
        )

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "reserved_balance",
                "plan_reserved_balance",
                "purchased_reserved_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,

            generation=generation,

            transaction_type=(
                CreditTransactionType
                .RESERVE
            ),

            amount=-amount,

            before=before,

            description=(
                "Crédito reservado "
                "para geração de imagem."
            ),
        )

        return wallet

    # ======================================================
    # CONSUMIR
    # ======================================================

    @staticmethod
    @transaction.atomic
    def consume(
        wallet:
            CreditWallet,
        generation,
        amount:
            int = 1,
    ):
        existing = (
            CreditTransaction.objects
            .filter(
                wallet=wallet,
                generation=generation,
                type=(
                    CreditTransactionType
                    .CONSUME
                ),
            )
            .first()
        )

        if existing:
            return (
                CreditWallet.objects
                .get(
                    pk=wallet.pk
                )
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        if (
            wallet.reserved_balance
            < amount
        ):
            raise ValueError(
                "Não há créditos "
                "reservados suficientes."
            )

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        # ----------------------------------------------
        # Consome exatamente da origem
        # que foi reservada.
        # ----------------------------------------------

        plan_amount = min(
            amount,
            wallet.plan_reserved_balance,
        )

        purchased_amount = (
            amount
            - plan_amount
        )

        if (
            purchased_amount
            >
            wallet
            .purchased_reserved_balance
        ):
            raise ValueError(
                "Reserva de créditos "
                "inconsistente."
            )

        if (
            plan_amount
            >
            wallet.plan_balance
        ):
            raise ValueError(
                "Saldo de créditos do plano "
                "inconsistente."
            )

        if (
            purchased_amount
            >
            wallet.purchased_balance
        ):
            raise ValueError(
                "Saldo de créditos comprados "
                "inconsistente."
            )

        wallet.plan_balance -= (
            plan_amount
        )

        wallet.purchased_balance -= (
            purchased_amount
        )

        wallet.plan_reserved_balance -= (
            plan_amount
        )

        wallet.purchased_reserved_balance -= (
            purchased_amount
        )

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "reserved_balance",
                "plan_balance",
                "purchased_balance",
                "plan_reserved_balance",
                "purchased_reserved_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,

            generation=generation,

            transaction_type=(
                CreditTransactionType
                .CONSUME
            ),

            amount=-amount,

            plan_amount=(
                -plan_amount
            ),

            purchased_amount=(
                -purchased_amount
            ),

            before=before,

            description=(
                "Crédito consumido após "
                "geração concluída."
            ),
        )

        return wallet

    # ======================================================
    # DEVOLVER RESERVA
    # ======================================================

    @staticmethod
    @transaction.atomic
    def refund_reservation(
        wallet:
            CreditWallet,
        generation,
        amount:
            int = 1,
    ):
        already_consumed = (
            CreditTransaction.objects
            .filter(
                wallet=wallet,
                generation=generation,
                type=(
                    CreditTransactionType
                    .CONSUME
                ),
            )
            .exists()
        )

        if already_consumed:
            return (
                CreditWallet.objects
                .get(
                    pk=wallet.pk
                )
            )

        existing_refund = (
            CreditTransaction.objects
            .filter(
                wallet=wallet,
                generation=generation,
                type=(
                    CreditTransactionType
                    .REFUND
                ),
            )
            .first()
        )

        if existing_refund:
            return (
                CreditWallet.objects
                .get(
                    pk=wallet.pk
                )
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        refundable = min(
            amount,
            wallet.reserved_balance,
        )

        if (
            refundable <= 0
        ):
            return wallet

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        plan_refund = min(
            refundable,
            wallet.plan_reserved_balance,
        )

        purchased_refund = (
            refundable
            - plan_refund
        )

        wallet.plan_reserved_balance -= (
            plan_refund
        )

        wallet.purchased_reserved_balance -= (
            purchased_refund
        )

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "reserved_balance",
                "plan_reserved_balance",
                "purchased_reserved_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,

            generation=generation,

            transaction_type=(
                CreditTransactionType
                .REFUND
            ),

            amount=refundable,

            before=before,

            description=(
                "Reserva devolvida após "
                "falha técnica ou cancelamento."
            ),
        )

        return wallet

    # ======================================================
    # NOVO CICLO DO PLANO
    #
    # Créditos antigos do plano expiram.
    # Créditos comprados permanecem.
    # ======================================================

    @staticmethod
    @transaction.atomic
    def renew_plan_credits(
        wallet:
            CreditWallet,
        amount:
            int,
        *,
        actor=None,
        description=(
            "Renovação dos créditos "
            "da assinatura."
        ),
    ):
        if amount < 0:
            raise ValueError(
                "A quantidade de créditos "
                "não pode ser negativa."
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        # Não renovamos no meio de
        # uma geração reservada.
        if (
            wallet
            .plan_reserved_balance
            > 0
        ):
            raise ValueError(
                "Existem créditos do plano "
                "reservados em processamento."
            )

        # ----------------------------------------------
        # EXPIRA SALDO ANTIGO
        # ----------------------------------------------

        if (
            wallet.plan_balance
            > 0
        ):
            before = (
                CreditService
                ._snapshot(
                    wallet
                )
            )

            expired = (
                wallet.plan_balance
            )

            wallet.plan_balance = 0

            CreditService._sync_totals(
                wallet
            )

            wallet.save(
                update_fields=[
                    "balance",
                    "plan_balance",
                    "updated_at",
                ]
            )

            CreditService._create_transaction(
                wallet=wallet,

                actor=actor,

                transaction_type=(
                    CreditTransactionType
                    .PLAN_EXPIRE
                ),

                amount=-expired,

                plan_amount=-expired,

                before=before,

                description=(
                    "Créditos restantes "
                    "do ciclo anterior expiraram."
                ),
            )

        # ----------------------------------------------
        # NOVA FRANQUIA
        # ----------------------------------------------

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        wallet.plan_balance += amount

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "plan_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,

            actor=actor,

            transaction_type=(
                CreditTransactionType
                .PLAN_GRANT
            ),

            amount=amount,

            plan_amount=amount,

            before=before,

            description=description,
        )

        return wallet

    # ======================================================
    # COMPRA DE CRÉDITOS AVULSOS
    # ======================================================

    @staticmethod
    @transaction.atomic
    def add_purchased_credits(
        wallet:
            CreditWallet,
        amount:
            int,
        *,
        actor=None,
        description=(
            "Compra de créditos avulsos."
        ),
    ):
        if (
            amount <= 0
        ):
            raise ValueError(
                "A quantidade deve "
                "ser maior que zero."
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        wallet.purchased_balance += (
            amount
        )

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "purchased_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,

            actor=actor,

            transaction_type=(
                CreditTransactionType
                .PURCHASE
            ),

            amount=amount,

            purchased_amount=amount,

            before=before,

            description=description,
        )

        return wallet

    # ======================================================
    # EXPIRAR CRÉDITOS DO PLANO
    #
    # Usado quando a assinatura deixa de ter direito
    # operacional definitivo. Créditos comprados ficam
    # preservados.
    # ======================================================

    @staticmethod
    @transaction.atomic
    def expire_plan_credits(
        wallet:
            CreditWallet,
        *,
        actor=None,
        description=(
            "Créditos do plano expirados."
        ),
    ):
        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        if (
            wallet.plan_reserved_balance
            > 0
        ):
            raise ValueError(
                "Existem créditos do plano "
                "reservados em processamento."
            )

        if (
            wallet.plan_balance
            <= 0
        ):
            return wallet

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        expired = wallet.plan_balance
        wallet.plan_balance = 0

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "plan_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,
            actor=actor,
            transaction_type=(
                CreditTransactionType
                .PLAN_EXPIRE
            ),
            amount=-expired,
            plan_amount=-expired,
            before=before,
            description=description,
        )

        return wallet

    # ======================================================
    # AJUSTE ADMINISTRATIVO
    #
    # Usado somente por SuperAdmin via camada autorizada.
    # Mantém snapshots e impede saldo negativo.
    # ======================================================

    @staticmethod
    @transaction.atomic
    def adjust_credits(
        wallet:
            CreditWallet,
        amount:
            int,
        *,
        balance_type:
            str,
        actor,
        reason:
            str,
    ):
        if amount == 0:
            raise ValueError(
                "A quantidade deve ser "
                "diferente de zero."
            )

        if not reason.strip():
            raise ValueError(
                "Informe o motivo do ajuste."
            )

        if balance_type not in [
            "PLAN",
            "PURCHASED",
        ]:
            raise ValueError(
                "Tipo de saldo inválido."
            )

        wallet = (
            CreditWallet.objects
            .select_for_update()
            .get(
                pk=wallet.pk
            )
        )

        before = (
            CreditService
            ._snapshot(
                wallet
            )
        )

        plan_amount = 0
        purchased_amount = 0

        if balance_type == "PLAN":
            new_balance = (
                wallet.plan_balance
                +
                amount
            )

            if new_balance < 0:
                raise ValueError(
                    "O ajuste deixaria o saldo "
                    "do plano negativo."
                )

            if (
                new_balance
                <
                wallet.plan_reserved_balance
            ):
                raise ValueError(
                    "O ajuste deixaria o saldo "
                    "do plano menor que a reserva."
                )

            wallet.plan_balance = (
                new_balance
            )

            plan_amount = amount

        else:
            new_balance = (
                wallet.purchased_balance
                +
                amount
            )

            if new_balance < 0:
                raise ValueError(
                    "O ajuste deixaria o saldo "
                    "avulso negativo."
                )

            if (
                new_balance
                <
                wallet.purchased_reserved_balance
            ):
                raise ValueError(
                    "O ajuste deixaria o saldo "
                    "avulso menor que a reserva."
                )

            wallet.purchased_balance = (
                new_balance
            )

            purchased_amount = amount

        CreditService._sync_totals(
            wallet
        )

        wallet.save(
            update_fields=[
                "balance",
                "plan_balance",
                "purchased_balance",
                "updated_at",
            ]
        )

        CreditService._create_transaction(
            wallet=wallet,
            actor=actor,
            transaction_type=(
                CreditTransactionType
                .ADJUSTMENT
            ),
            amount=amount,
            plan_amount=plan_amount,
            purchased_amount=purchased_amount,
            before=before,
            description=(
                "Ajuste administrativo "
                "de créditos."
            ),
            reason=reason.strip(),
        )

        return wallet
