from datetime import timedelta

from django.core.management.base import (
    BaseCommand,
)
from django.db import transaction
from django.utils import timezone

from apps.credits.models import (
    CreditTransaction,
    CreditTransactionType,
)
from apps.credits.services import (
    CreditService,
)
from apps.studio.models import (
    FailureType,
    Generation,
    GenerationStatus,
)


class Command(BaseCommand):
    help = (
        "Localiza gerações antigas presas em "
        "CREDIT_RESERVED e devolve os créditos "
        "reservados com segurança."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Executa realmente os estornos. "
                "Sem esta opção o comando apenas "
                "mostra o que seria alterado."
            ),
        )

        parser.add_argument(
            "--older-than-minutes",
            type=int,
            default=30,
            help=(
                "Considera somente gerações em "
                "CREDIT_RESERVED mais antigas que "
                "este número de minutos. Padrão: 30."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        apply_changes = (
            options["apply"]
        )

        older_than_minutes = (
            options[
                "older_than_minutes"
            ]
        )

        cutoff = (
            timezone.now()
            - timedelta(
                minutes=(
                    older_than_minutes
                )
            )
        )

        self.stdout.write("")
        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            "MARIED STUDIO"
        )

        self.stdout.write(
            "LIMPEZA DE RESERVAS ÓRFÃS"
        )

        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            f"Modo: "
            f"{'APLICAR ALTERAÇÕES' if apply_changes else 'SIMULAÇÃO'}"
        )

        self.stdout.write(
            "Considerando gerações "
            f"anteriores a: {cutoff}"
        )

        self.stdout.write("")

        generations = (
            Generation.objects
            .filter(
                status=(
                    GenerationStatus
                    .CREDIT_RESERVED
                ),
                created_at__lt=cutoff,
            )
            .select_related(
                "organization",
                "product",
            )
            .order_by(
                "created_at"
            )
        )

        total = (
            generations.count()
        )

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "Nenhuma reserva órfã "
                    "foi encontrada."
                )
            )

            return

        self.stdout.write(
            self.style.WARNING(
                f"{total} geração(ões) "
                "encontrada(s)."
            )
        )

        self.stdout.write("")

        processed = 0
        skipped = 0
        total_refunded = 0

        for generation in generations:
            self.stdout.write(
                "-" * 60
            )

            self.stdout.write(
                f"Generation ID: "
                f"{generation.id}"
            )

            self.stdout.write(
                f"Status: "
                f"{generation.status}"
            )

            self.stdout.write(
                f"Criada em: "
                f"{generation.created_at}"
            )

            self.stdout.write(
                f"Custo: "
                f"{generation.credit_cost}"
            )

            wallet = (
                generation
                .organization
                .credit_wallet
            )

            wallet.refresh_from_db()

            self.stdout.write(
                f"Saldo atual: "
                f"{wallet.balance}"
            )

            self.stdout.write(
                f"Reservado atual: "
                f"{wallet.reserved_balance}"
            )

            self.stdout.write(
                f"Disponível atual: "
                f"{wallet.available_balance}"
            )

            # =================================================
            # VERIFICA SE JÁ HOUVE CONSUMO
            # =================================================

            consumed = (
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

            if consumed:
                self.stdout.write(
                    self.style.ERROR(
                        "IGNORADA: existe "
                        "transação CONSUME "
                        "para esta geração."
                    )
                )

                skipped += 1

                continue

            # =================================================
            # VERIFICA SE JÁ EXISTE REFUND
            # =================================================

            refunded = (
                CreditTransaction.objects
                .filter(
                    wallet=wallet,
                    generation=generation,
                    type=(
                        CreditTransactionType
                        .REFUND
                    ),
                )
                .exists()
            )

            if refunded:
                self.stdout.write(
                    self.style.WARNING(
                        "IGNORADA: já existe "
                        "transação REFUND."
                    )
                )

                skipped += 1

                continue

            # =================================================
            # SOMENTE SIMULAÇÃO
            # =================================================

            if not apply_changes:
                self.stdout.write(
                    self.style.WARNING(
                        "SIMULAÇÃO: esta geração "
                        "teria sua reserva devolvida "
                        "e seria marcada como FAILED."
                    )
                )

                processed += 1

                total_refunded += (
                    generation.credit_cost
                )

                continue

            # =================================================
            # ESTORNO REAL
            # =================================================

            try:
                with transaction.atomic():
                    # Recarrega a geração
                    # bloqueando apenas sua linha.

                    locked_generation = (
                        Generation.objects
                        .select_for_update(
                            of=("self",)
                        )
                        .get(
                            pk=generation.pk
                        )
                    )

                    # Confirma novamente o status
                    # dentro da transação.

                    if (
                        locked_generation.status
                        != GenerationStatus
                        .CREDIT_RESERVED
                    ):
                        self.stdout.write(
                            self.style.WARNING(
                                "IGNORADA: status "
                                "foi alterado durante "
                                "o processamento."
                            )
                        )

                        skipped += 1

                        continue

                    wallet = (
                        locked_generation
                        .organization
                        .credit_wallet
                    )

                    amount = (
                        locked_generation
                        .credit_cost
                        or 1
                    )

                    # -----------------------------------------
                    # DEVOLVE A RESERVA PELO SERVIÇO OFICIAL
                    # -----------------------------------------

                    CreditService.refund_reservation(
                        wallet,
                        locked_generation,
                        amount,
                    )

                    # -----------------------------------------
                    # MARCA A GERAÇÃO COMO FAILED
                    # -----------------------------------------

                    locked_generation.status = (
                        GenerationStatus.FAILED
                    )

                    locked_generation.failure_type = (
                        FailureType.TECHNICAL
                    )

                    locked_generation.error_code = (
                        "STALE_CREDIT_RESERVATION"
                    )

                    locked_generation.error_message = (
                        "Reserva de crédito antiga "
                        "devolvida automaticamente "
                        "durante manutenção."
                    )

                    locked_generation.completed_at = (
                        timezone.now()
                    )

                    locked_generation.save(
                        update_fields=[
                            "status",
                            "failure_type",
                            "error_code",
                            "error_message",
                            "completed_at",
                            "updated_at",
                        ]
                    )

                    wallet.refresh_from_db()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"ESTORNADO: "
                            f"{amount} crédito(s)."
                        )
                    )

                    self.stdout.write(
                        f"Novo saldo: "
                        f"{wallet.balance}"
                    )

                    self.stdout.write(
                        f"Novo reservado: "
                        f"{wallet.reserved_balance}"
                    )

                    self.stdout.write(
                        f"Novo disponível: "
                        f"{wallet.available_balance}"
                    )

                    processed += 1

                    total_refunded += (
                        amount
                    )

            except Exception as exc:
                skipped += 1

                self.stdout.write(
                    self.style.ERROR(
                        "ERRO ao processar "
                        f"{generation.id}: "
                        f"{exc}"
                    )
                )

        # =====================================================
        # RESUMO
        # =====================================================

        self.stdout.write("")
        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            "RESUMO"
        )

        self.stdout.write(
            "=" * 60
        )

        self.stdout.write(
            f"Encontradas: {total}"
        )

        self.stdout.write(
            f"Processadas: {processed}"
        )

        self.stdout.write(
            f"Ignoradas/erros: {skipped}"
        )

        self.stdout.write(
            "Créditos a devolver/devolvidos: "
            f"{total_refunded}"
        )

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Nenhuma alteração foi "
                    "realizada porque o comando "
                    "está em modo SIMULAÇÃO."
                )
            )

            self.stdout.write(
                "Para aplicar os estornos, rode:"
            )

            self.stdout.write(
                "python manage.py "
                "refund_stale_reservations "
                "--apply"
            )

        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    "Limpeza concluída."
                )
            )