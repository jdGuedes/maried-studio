import logging
import time

from django.core.management.base import BaseCommand

from apps.studio.services.generation_queue import (
    GenerationQueueService,
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Processa a fila duravel de geracoes MARIED STUDIO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Executa uma passagem e encerra.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1,
            help="Quantidade maxima de geracoes por passagem.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=5.0,
            help="Intervalo entre passagens quando nao usar --once.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        limit = max(
            options["limit"],
            1,
        )
        interval = max(
            options["interval"],
            1.0,
        )

        while True:
            result = GenerationQueueService.process_available(
                limit=limit
            )

            logger.info(
                "generation_queue_tick found=%s processed=%s skipped=%s failed=%s",
                result["found"],
                result["processed"],
                result["skipped"],
                result["failed"],
            )

            if once:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Generation queue processed: "
                        f"{result}"
                    )
                )
                return

            time.sleep(interval)
