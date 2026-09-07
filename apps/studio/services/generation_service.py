import mimetypes
import logging
import sys
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.ai.models import ModelReference
from apps.ai.providers.openai import OpenAIImageProvider
from apps.ai.services.prompt_engine import PromptEngine
from apps.billing.services import BillingAccessService
from apps.credits.services import CreditService
from apps.products.models import AssetType
from apps.studio.models import (
    FailureType,
    GeneratedImage,
    Generation,
    GenerationRule,
    GenerationStatus,
    SceneTemplate,
)
from apps.studio.services.performance import GenerationPerformanceTracker


logger = logging.getLogger(__name__)


ACTIVE_GENERATION_STATUSES = (
    GenerationStatus.CREDIT_RESERVED,
    GenerationStatus.PROCESSING,
)


class GenerationAlreadyInProgress(Exception):
    code = "GENERATION_ALREADY_IN_PROGRESS"

    def __init__(self, generation):
        self.generation = generation

        super().__init__(
            "Já existe uma criação em andamento. "
            "Aguarde ela ficar pronta antes de iniciar uma nova."
        )


class GenerationService:
    # =========================================================
    # CRIAÇÃO DA SOLICITAÇÃO
    # =========================================================

    @staticmethod
    @transaction.atomic
    def create_request(
        *,
        user,
        product,
        mode,
        scene_template_id,
        model_reference_id=None,
        idempotency_key,
        performance_tracker=None,
    ):
        tracker = performance_tracker
        # -----------------------------------------------------
        # 0. ISOLAMENTO MULTI-TENANT
        # -----------------------------------------------------

        if not user.is_active:
            raise PermissionError(
                "Usuário inativo."
            )

        if not user.organization_id:
            raise PermissionError(
                "Usuário não pertence a uma organização."
            )

        if not product.organization_id:
            raise PermissionError(
                "Produto não pertence a uma organização."
            )

        if (
            user.organization_id
            != product.organization_id
        ):
            raise PermissionError(
                "O produto não pertence à organização "
                "do usuário."
            )

        locked_organization = (
            product.organization.__class__.objects
            .select_for_update(
                of=("self",)
            )
            .get(
                pk=product.organization_id,
            )
        )

        if not locked_organization.is_active:
            raise PermissionError(
                "Organização inativa."
            )

        BillingAccessService.ensure_operational_access(
            locked_organization
        )

        # -----------------------------------------------------
        # 1. IDEMPOTÊNCIA
        # -----------------------------------------------------

        existing = Generation.objects.filter(
            organization=locked_organization,
            idempotency_key=idempotency_key,
        ).first()

        if existing:
            return existing, False

        active_generation = (
            Generation.objects
            .filter(
                organization=locked_organization,
                status__in=ACTIVE_GENERATION_STATUSES,
            )
            .order_by(
                "created_at",
                "id",
            )
            .first()
        )

        if active_generation:
            raise GenerationAlreadyInProgress(
                active_generation
            )

        # -----------------------------------------------------
        # 2. REGRA DA GERAÇÃO
        # -----------------------------------------------------

        rule = GenerationRule.objects.get(
            category=product.category,
            generation_mode=mode,
            is_active=True,
        )

        # -----------------------------------------------------
        # 3. TEMPLATE / MODELREFERENCE
        # -----------------------------------------------------

        template = None
        model_reference = None

        if scene_template_id:
            template = SceneTemplate.objects.get(
                pk=scene_template_id,
                category=product.category,
                generation_mode=mode,
                is_active=True,
            )

        if model_reference_id:
            model_reference = (
                ModelReference.objects
                .filter(
                    pk=model_reference_id,
                    is_active=True,
                )
                .first()
            )

            if model_reference is None:
                raise ValueError(
                    "ModelReference ativo "
                    "não encontrado."
                )

        if mode == "STILL" and (
            template
            or model_reference
        ):
            raise ValueError(
                "Still não usa cenário ou modelo."
            )

        if mode == "BODY_DETAIL":
            if template:
                raise ValueError(
                    "Detalhe no Corpo usa "
                    "ModelReference, não cenário."
                )

            if not model_reference:
                raise ValueError(
                    "Detalhe no Corpo exige "
                    "uma modelo."
                )

        if mode == "INSTAGRAM":
            if not template:
                raise ValueError(
                    "Instagramável exige "
                    "um cenário."
                )

            if model_reference:
                raise ValueError(
                    "Instagramável não usa modelo."
                )

        if mode == "MODEL":
            if template:
                raise ValueError(
                    "Na Modelo usa "
                    "ModelReference, não cenário."
                )

            if not model_reference:
                raise ValueError(
                    "Na Modelo exige "
                    "uma modelo."
                )

        # -----------------------------------------------------
        # 4. CRIA A GENERATION
        # -----------------------------------------------------

        generation = Generation.objects.create(
            organization=locked_organization,
            user=user,
            product=product,
            mode=mode,
            scene_template=template,
            model_reference=model_reference,
            generation_rule=rule,
            status=GenerationStatus.CREATED,
            idempotency_key=idempotency_key,
            credit_cost=1,
        )

        # -----------------------------------------------------
        # 5. RESERVA DO CRÉDITO
        # -----------------------------------------------------

        wallet = locked_organization.credit_wallet

        if tracker:
            with tracker.measure("credit"):
                CreditService.reserve(
                    wallet,
                    generation,
                    1,
                )
        else:
            CreditService.reserve(
                wallet,
                generation,
                1,
            )

        generation.status = (
            GenerationStatus.CREDIT_RESERVED
        )

        generation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return generation, True

    # =========================================================
    # PROCESSAMENTO
    # =========================================================

    @staticmethod
    def process(
        generation: Generation,
        performance_tracker=None,
        allow_claimed_processing=False,
    ):
        tracker = (
            performance_tracker
            or GenerationPerformanceTracker()
        )
        input_metadata = {}
        output_metadata = {}

        db_context = tracker.measure("db_finalize")
        db_context.__enter__()
        transaction_context = transaction.atomic()
        transaction_context.__enter__()
        try:
            locked_generation = (
                Generation.objects
                .select_for_update(
                    of=("self",)
                )
                .select_related(
                    "organization",
                    "user",
                    "product",
                    "scene_template",
                    "model_reference",
                    "generation_rule",
                )
                .get(
                    pk=generation.pk
                )
            )

            # -------------------------------------------------
            # CONSISTÊNCIA MULTI-TENANT
            # -------------------------------------------------

            if (
                locked_generation.user.organization_id
                != locked_generation.organization_id
            ):
                raise PermissionError(
                    "Usuário e geração pertencem a "
                    "organizações diferentes."
                )

            if (
                locked_generation.product.organization_id
                != locked_generation.organization_id
            ):
                raise PermissionError(
                    "Produto e geração pertencem a "
                    "organizações diferentes."
                )

            if not locked_generation.organization.is_active:
                raise PermissionError(
                    "Organização inativa."
                )

            if not locked_generation.user.is_active:
                raise PermissionError(
                    "Usuário inativo."
                )

            if (
                locked_generation.status
                == GenerationStatus.COMPLETED
            ):
                transaction_context.__exit__(None, None, None)
                db_context.__exit__(None, None, None)
                tracker.log(
                    generation=locked_generation,
                    success=True,
                    provider=locked_generation.provider,
                    model=locked_generation.model,
                )
                return locked_generation

            if locked_generation.status == (
                GenerationStatus.PROCESSING
            ):
                if not allow_claimed_processing:
                    raise ValueError(
                        "Geração não pode ser processada "
                        f"no status {locked_generation.status}."
                    )

                if locked_generation.started_at:
                    tracker.mark_claimed_at(
                        locked_generation.started_at
                    )

                transaction_context.__exit__(None, None, None)
                db_context.__exit__(None, None, None)

            elif locked_generation.status != (
                GenerationStatus.CREDIT_RESERVED
            ):
                raise ValueError(
                    "Geração não pode ser processada "
                    f"no status {locked_generation.status}."
                )

            else:
                locked_generation.status = (
                    GenerationStatus.PROCESSING
                )

                locked_generation.started_at = (
                    timezone.now()
                )

                tracker.mark_claimed_at(
                    locked_generation.started_at
                )

                locked_generation.provider = (
                    "OPENAI"
                )

                locked_generation.model = (
                    settings.OPENAI_IMAGE_MODEL
                )

                locked_generation.save(
                    update_fields=[
                        "status",
                        "started_at",
                        "provider",
                        "model",
                        "updated_at",
                    ]
                )
                transaction_context.__exit__(None, None, None)
                db_context.__exit__(None, None, None)
        except Exception:
            transaction_context.__exit__(*sys.exc_info())
            db_context.__exit__(*sys.exc_info())
            raise

        generation = locked_generation

        wallet = (
            generation.organization.credit_wallet
        )

        try:
            current_stage = "prompt"
            prompt_timer = tracker.start_stage()
            prompt = PromptEngine.build(
                product=generation.product,
                mode=generation.mode,
                scene_template=(
                    generation.scene_template
                ),
                model_reference=(
                    generation.model_reference
                ),
                generation_rule=(
                    generation.generation_rule
                ),
            )

            generation.final_prompt = prompt

            generation.configuration_snapshot = {
                "category": (
                    generation.product.category
                ),
                "mode": (
                    generation.mode
                ),
                "template_id": (
                    str(
                        generation.scene_template_id
                    )
                    if generation.scene_template_id
                    else None
                ),
                "template_version": (
                    generation.scene_template.version
                    if generation.scene_template
                    else None
                ),
                "model_reference_id": (
                    str(
                        generation.model_reference_id
                    )
                    if generation.model_reference_id
                    else None
                ),
                "model_reference_code": (
                    generation.model_reference.code
                    if generation.model_reference
                    else None
                ),
                "framing": (
                    generation.generation_rule.framing
                ),
                "body_area": (
                    generation.generation_rule.body_area
                ),
                "provider": (
                    "OPENAI"
                ),
                "model": (
                    settings.OPENAI_IMAGE_MODEL
                ),
            }

            generation.save(
                update_fields=[
                    "final_prompt",
                    "configuration_snapshot",
                    "updated_at",
                ]
            )
            tracker.stop_stage("prompt", prompt_timer)
            current_stage = ""

            current_stage = "asset_preparation"
            asset_timer = tracker.start_stage()
            source = (
                generation.product.assets
                .filter(
                    asset_type=AssetType.ORIGINAL
                )
                .order_by(
                    "created_at"
                )
                .first()
            )

            if not source:
                raise ValueError(
                    "Produto não possui imagem original."
                )

            if not source.file:
                raise ValueError(
                    "O arquivo original do produto "
                    "não está disponível."
                )

            provider = (
                OpenAIImageProvider()
            )

            source.file.open(
                "rb"
            )

            try:
                reference_bytes = (
                    source.file.read()
                )

                filename = Path(
                    source.file.name
                ).name

                mime_type = (
                    source.mime_type
                    or mimetypes.guess_type(
                        filename
                    )[0]
                )

                allowed_mime_types = {
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                }

                if (
                    mime_type
                    not in allowed_mime_types
                ):
                    raise ValueError(
                        "Formato de imagem não "
                        f"suportado: {mime_type}. "
                        "Use JPEG, PNG ou WEBP."
                    )

                reference_upload = (
                    filename,
                    reference_bytes,
                    mime_type,
                )
                input_metadata = {
                    "input_file_size_bytes": (
                        source.file_size
                        or len(reference_bytes)
                    ),
                    "input_width": source.width,
                    "input_height": source.height,
                }

                tracker.stop_stage(
                    "asset_preparation",
                    asset_timer,
                )
                current_stage = ""

                with tracker.measure("provider"):
                    asset = provider.generate(
                        prompt=prompt,
                        reference_file=(
                            reference_upload
                        ),
                    )

            finally:
                source.file.close()

            with tracker.measure("result_processing"):
                output_metadata = {
                    "output_size_bytes": len(
                        asset.content
                    ),
                    "output_width": None,
                    "output_height": None,
                }

            with tracker.measure("storage"):
                result = GeneratedImage(
                    generation=generation,
                    mime_type=asset.mime_type,
                    file_size=output_metadata[
                        "output_size_bytes"
                    ],
                )

                result.file.save(
                    f"{generation.id}.png",
                    ContentFile(
                        asset.content
                    ),
                    save=True,
                )

            with tracker.measure("credit"):
                CreditService.consume(
                    wallet,
                    generation,
                    1,
                )

            with tracker.measure("db_finalize"):
                generation.status = (
                    GenerationStatus.COMPLETED
                )

                generation.completed_at = (
                    timezone.now()
                )

                generation.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "updated_at",
                    ]
                )

            tracker.log(
                generation=generation,
                success=True,
                provider=generation.provider,
                model=generation.model,
                input_metadata=input_metadata,
                output_metadata=output_metadata,
            )

            return generation

        except Exception as exc:
            if current_stage:
                tracker.mark_failure(current_stage)

            try:
                with tracker.measure("credit"):
                    CreditService.refund_reservation(
                        wallet,
                        generation,
                        1,
                    )

            except Exception as refund_exc:
                logger.exception(
                    "generation_credit_refund_failed",
                    extra={
                        "generation_id": str(generation.pk),
                        "organization_id": str(
                            generation.organization_id
                        ),
                        "exception_class": (
                            refund_exc.__class__.__name__
                        ),
                    },
                )

            with tracker.measure("db_finalize"):
                generation.status = (
                    GenerationStatus.FAILED
                )

                generation.failure_type = (
                    FailureType.TECHNICAL
                )

                generation.error_code = (
                    exc.__class__.__name__
                )

                generation.error_message = (
                    str(exc)[:2000]
                )

                generation.completed_at = (
                    timezone.now()
                )

                generation.save(
                    update_fields=[
                        "status",
                        "failure_type",
                        "error_code",
                        "error_message",
                        "completed_at",
                        "updated_at",
                    ]
                )

            tracker.log(
                generation=generation,
                success=False,
                provider=generation.provider,
                model=generation.model,
                input_metadata=input_metadata,
                output_metadata=output_metadata,
            )

            raise
