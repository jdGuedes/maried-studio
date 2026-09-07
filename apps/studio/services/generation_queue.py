import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.studio.models import (
    Generation,
    GenerationStatus,
)
from apps.studio.services.generation_service import (
    GenerationService,
)
from apps.studio.services.performance import (
    GenerationPerformanceTracker,
)


logger = logging.getLogger(__name__)


class GenerationQueueService:
    SELECT_RELATED_FIELDS = (
        "organization",
        "user",
        "product",
        "scene_template",
        "model_reference",
        "generation_rule",
    )

    @staticmethod
    def enqueue_after_commit(generation):
        transaction.on_commit(
            lambda: logger.info(
                "generation_queued",
                extra={
                    "generation_id": str(generation.pk),
                    "organization_id": str(
                        generation.organization_id
                    ),
                    "status": generation.status,
                },
            )
        )

    @staticmethod
    def _claim_generation(generation_id):
        with transaction.atomic():
            generation = (
                Generation.objects
                .select_for_update(
                    skip_locked=True,
                    of=("self",),
                )
                .filter(
                    pk=generation_id,
                    status=GenerationStatus.CREDIT_RESERVED,
                )
                .select_related(
                    *GenerationQueueService.SELECT_RELATED_FIELDS
                )
                .first()
            )

            if not generation:
                return None

            claimed_at = timezone.now()

            generation.status = (
                GenerationStatus.PROCESSING
            )
            generation.started_at = claimed_at
            generation.provider = "OPENAI"
            generation.model = (
                settings.OPENAI_IMAGE_MODEL
            )
            generation.save(
                update_fields=[
                    "status",
                    "started_at",
                    "provider",
                    "model",
                    "updated_at",
                ]
            )

        queue_wait_ms = (
            claimed_at - generation.created_at
        ).total_seconds() * 1000

        logger.info(
            "generation_queue_claimed",
            extra={
                "generation_id": str(generation.pk),
                "organization_id": str(
                    generation.organization_id
                ),
                "status": generation.status,
                "worker_action": "claimed",
                "queue_wait_ms": round(
                    queue_wait_ms,
                    3,
                ),
            },
        )

        return generation

    @staticmethod
    def process_generation(generation_id):
        claimed_generation = (
            GenerationQueueService._claim_generation(
                generation_id
            )
        )

        if claimed_generation:
            tracker = GenerationPerformanceTracker(
                queued_at=claimed_generation.created_at,
                claimed_at=claimed_generation.started_at,
            )

            return (
                GenerationService.process(
                    claimed_generation,
                    performance_tracker=tracker,
                    allow_claimed_processing=True,
                ),
                True,
            )

        generation = (
            Generation.objects
            .select_related(
                *GenerationQueueService.SELECT_RELATED_FIELDS
            )
            .get(
                pk=generation_id,
            )
        )

        logger.info(
            "generation_queue_skip",
            extra={
                "generation_id": str(generation.pk),
                "organization_id": str(
                    generation.organization_id
                ),
                "status": generation.status,
            },
        )

        return generation, False

    @staticmethod
    def process_available(*, limit=1):
        with transaction.atomic():
            generation_ids = list(
                Generation.objects
                .select_for_update(
                    skip_locked=True,
                    of=("self",),
                )
                .filter(
                    status=GenerationStatus.CREDIT_RESERVED,
                )
                .order_by(
                    "created_at",
                    "id",
                )
                .values_list(
                    "id",
                    flat=True,
                )[:limit]
            )

            claimed_at = timezone.now()

            if generation_ids:
                Generation.objects.filter(
                    id__in=generation_ids,
                    status=GenerationStatus.CREDIT_RESERVED,
                ).update(
                    status=GenerationStatus.PROCESSING,
                    started_at=claimed_at,
                    provider="OPENAI",
                    model=settings.OPENAI_IMAGE_MODEL,
                    updated_at=claimed_at,
                )

        generations_by_id = {
            generation.id: generation
            for generation in (
                Generation.objects
                .filter(
                    id__in=generation_ids,
                )
                .select_related(
                    *GenerationQueueService.SELECT_RELATED_FIELDS
                )
            )
        }

        claimed_generations = [
            generations_by_id[generation_id]
            for generation_id in generation_ids
            if generation_id in generations_by_id
        ]

        for generation in claimed_generations:
            queue_wait_ms = (
                generation.started_at -
                generation.created_at
            ).total_seconds() * 1000

            logger.info(
                "generation_queue_claimed",
                extra={
                    "generation_id": str(generation.pk),
                    "organization_id": str(
                        generation.organization_id
                    ),
                    "status": generation.status,
                    "worker_action": "claimed",
                    "queue_wait_ms": round(
                        queue_wait_ms,
                        3,
                    ),
                },
            )

        processed = 0
        skipped = 0
        failed = 0

        for generation in claimed_generations:
            try:
                tracker = GenerationPerformanceTracker(
                    queued_at=generation.created_at,
                    claimed_at=generation.started_at,
                )

                GenerationService.process(
                    generation,
                    performance_tracker=tracker,
                    allow_claimed_processing=True,
                )

                did_process = True

                if did_process:
                    processed += 1
                else:
                    skipped += 1

            except Exception:
                failed += 1
                logger.exception(
                    "generation_queue_job_failed",
                    extra={
                        "generation_id": str(generation.id),
                    },
                )

        return {
            "found": len(claimed_generations),
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
        }
