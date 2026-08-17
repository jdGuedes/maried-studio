import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.ai.providers.openai import OpenAIImageProvider
from apps.ai.services.prompt_engine import PromptEngine
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
        idempotency_key,
    ):
        # -----------------------------------------------------
        # 1. IDEMPOTÊNCIA
        #
        # Se a mesma solicitação já existir dentro da
        # organização, retornamos a Generation existente.
        # -----------------------------------------------------

        existing = Generation.objects.filter(
            organization=product.organization,
            idempotency_key=idempotency_key,
        ).first()

        if existing:
            return existing, False

        # -----------------------------------------------------
        # 2. REGRA DA GERAÇÃO
        # -----------------------------------------------------

        rule = GenerationRule.objects.get(
            category=product.category,
            generation_mode=mode,
            is_active=True,
        )

        # -----------------------------------------------------
        # 3. TEMPLATE
        #
        # STILL pode trabalhar sem SceneTemplate.
        # -----------------------------------------------------

        template = None

        if scene_template_id:
            template = SceneTemplate.objects.get(
                pk=scene_template_id,
                category=product.category,
                generation_mode=mode,
                is_active=True,
            )

        # -----------------------------------------------------
        # 4. CRIA A GENERATION
        # -----------------------------------------------------

        generation = Generation.objects.create(
            organization=product.organization,
            user=user,
            product=product,
            mode=mode,
            scene_template=template,
            generation_rule=rule,
            status=GenerationStatus.CREATED,
            idempotency_key=idempotency_key,
            credit_cost=1,
        )

        # -----------------------------------------------------
        # 5. RESERVA DO CRÉDITO
        # -----------------------------------------------------

        wallet = product.organization.credit_wallet

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
        generation: Generation
    ):
        # -----------------------------------------------------
        # 1. TRAVA DE PROCESSAMENTO
        #
        # IMPORTANTE:
        #
        # Bloqueamos SOMENTE a linha da tabela Generation.
        #
        # scene_template pode ser NULL, principalmente no STILL.
        # select_related() cria LEFT OUTER JOIN nesse cenário.
        #
        # Um select_for_update() genérico faria o PostgreSQL
        # tentar aplicar FOR UPDATE também no lado nullable
        # desse JOIN.
        #
        # Isso causava:
        #
        # FOR UPDATE cannot be applied to the nullable side
        # of an outer join
        #
        # of=("self",) mantém a proteção contra concorrência
        # sem tentar bloquear as relações opcionais.
        # -----------------------------------------------------

        with transaction.atomic():
            locked_generation = (
                Generation.objects
                .select_for_update(
                    of=("self",)
                )
                .select_related(
                    "organization",
                    "product",
                    "scene_template",
                    "generation_rule",
                )
                .get(
                    pk=generation.pk
                )
            )

            # -------------------------------------------------
            # JÁ CONCLUÍDA
            # -------------------------------------------------

            if (
                locked_generation.status
                == GenerationStatus.COMPLETED
            ):
                return locked_generation

            # -------------------------------------------------
            # STATUS INVÁLIDO
            # -------------------------------------------------

            if (
                locked_generation.status
                != GenerationStatus.CREDIT_RESERVED
            ):
                raise ValueError(
                    "Geração não pode ser processada "
                    f"no status {locked_generation.status}."
                )

            # -------------------------------------------------
            # MARCA COMO PROCESSANDO
            # -------------------------------------------------

            locked_generation.status = (
                GenerationStatus.PROCESSING
            )

            locked_generation.started_at = (
                timezone.now()
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

        # =====================================================
        # DAQUI PARA FRENTE A GENERATION ESTÁ EM PROCESSING
        # =====================================================

        generation = locked_generation

        wallet = (
            generation.organization.credit_wallet
        )

        try:
            # -------------------------------------------------
            # 2. MONTA O PROMPT
            # -------------------------------------------------

            prompt = PromptEngine.build(
                product=generation.product,
                mode=generation.mode,
                scene_template=(
                    generation.scene_template
                ),
                generation_rule=(
                    generation.generation_rule
                ),
            )

            generation.final_prompt = prompt

            # -------------------------------------------------
            # SNAPSHOT
            #
            # Guarda as configurações usadas naquela geração.
            # Isso é importante para auditoria e reprodução.
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 3. LOCALIZA A IMAGEM ORIGINAL
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 4. PREPARA O PROVIDER OPENAI
            # -------------------------------------------------

            provider = (
                OpenAIImageProvider()
            )

            source.file.open(
                "rb"
            )

            try:
                # ---------------------------------------------
                # LÊ O ARQUIVO
                # ---------------------------------------------

                reference_bytes = (
                    source.file.read()
                )

                filename = Path(
                    source.file.name
                ).name

                # ---------------------------------------------
                # MIME TYPE
                # ---------------------------------------------

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

                # ---------------------------------------------
                # ARQUIVO DE REFERÊNCIA PARA OPENAI
                # ---------------------------------------------

                reference_upload = (
                    filename,
                    reference_bytes,
                    mime_type,
                )

                # ---------------------------------------------
                # CHAMADA REAL À OPENAI
                # ---------------------------------------------

                asset = provider.generate(
                    prompt=prompt,
                    reference_file=(
                        reference_upload
                    ),
                )

            finally:
                source.file.close()

            # -------------------------------------------------
            # 5. SALVA A IMAGEM GERADA
            # -------------------------------------------------

            result = GeneratedImage(
                generation=generation,
                mime_type=asset.mime_type,
            )

            result.file.save(
                f"{generation.id}.png",
                ContentFile(
                    asset.content
                ),
                save=True,
            )

            # -------------------------------------------------
            # 6. CONSOME O CRÉDITO
            #
            # A reserva só é consumida depois de a imagem
            # ter sido efetivamente gerada e salva.
            # -------------------------------------------------

            CreditService.consume(
                wallet,
                generation,
                1,
            )

            # -------------------------------------------------
            # 7. MARCA COMO CONCLUÍDA
            # -------------------------------------------------

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

            return generation

        except Exception as exc:
            # -------------------------------------------------
            # 8. FALHA
            #
            # Se alguma etapa falhar:
            #
            # - devolvemos a reserva;
            # - marcamos FAILED;
            # - registramos tipo e mensagem;
            # - propagamos a exceção para a camada superior.
            # -------------------------------------------------

            try:
                CreditService.refund_reservation(
                    wallet,
                    generation,
                    1,
                )

            except Exception as refund_exc:
                # Não escondemos o erro original da geração
                # caso o estorno também tenha algum problema.

                print(
                    "ERRO AO DEVOLVER RESERVA "
                    "DE CRÉDITO:",
                    repr(refund_exc),
                )

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

            raise