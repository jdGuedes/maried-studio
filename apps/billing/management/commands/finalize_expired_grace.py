from django.core.management.base import BaseCommand

from apps.billing.services import SubscriptionDelinquencyService


class Command(BaseCommand):
    help = (
        "Cancela assinaturas PAST_DUE apÃ³s o fim do perÃ­odo de tolerÃ¢ncia."
    )

    def handle(self, *args, **options):
        processed = (
            SubscriptionDelinquencyService
            .finalize_expired_grace()
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Assinaturas finalizadas: {processed}"
            )
        )
