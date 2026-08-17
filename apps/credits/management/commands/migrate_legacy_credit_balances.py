from django.core.management.base import (
    BaseCommand,
)

from django.db import transaction

from apps.credits.models import (
    CreditWallet,
)


class Command(
    BaseCommand
):
    help = (
        "Migra os saldos antigos da carteira "
        "para purchased_balance."
    )

    @transaction.atomic
    def handle(
        self,
        *args,
        **options,
    ):
        wallets = (
            CreditWallet.objects
            .select_for_update()
            .all()
        )

        migrated = 0
        skipped = 0

        for wallet in wallets:
            # Já migrada.
            if (
                wallet.plan_balance > 0
                or
                wallet.purchased_balance > 0
                or
                wallet.plan_reserved_balance > 0
                or
                wallet.purchased_reserved_balance > 0
            ):
                skipped += 1

                continue

            legacy_balance = (
                wallet.balance
            )

            legacy_reserved = (
                wallet.reserved_balance
            )

            if (
                legacy_balance == 0
                and
                legacy_reserved == 0
            ):
                skipped += 1

                continue

            # O saldo antigo será tratado
            # como crédito avulso/administrativo.
            #
            # Portanto não expirará na renovação
            # de uma futura assinatura.

            wallet.purchased_balance = (
                legacy_balance
            )

            wallet.purchased_reserved_balance = (
                legacy_reserved
            )

            wallet.save(
                update_fields=[
                    "purchased_balance",
                    "purchased_reserved_balance",
                    "updated_at",
                ]
            )

            migrated += 1

            self.stdout.write(
                self.style.SUCCESS(
                    (
                        f"{wallet.organization}: "
                        f"{legacy_balance} crédito(s) migrado(s)."
                    )
                )
            )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Migradas: {migrated}"
            )
        )

        self.stdout.write(
            f"Ignoradas: {skipped}"
        )