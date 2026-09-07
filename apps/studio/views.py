import logging

from django.shortcuts import get_object_or_404

from rest_framework import (
    generics,
    permissions,
    status,
)

from rest_framework.response import Response

from rest_framework.views import APIView

from apps.billing.services import (
    BillingAccessService,
    SubscriptionRequiredError,
)
from apps.common.pagination import ClientListPagination
from apps.common.private_media import build_private_image_response
from apps.credits.services import InsufficientCredits
from apps.products.models import (
    AssetType,
    Product,
    ProductStatus,
)
from apps.products.services import VisualDataDeletionService

from .models import (
    Generation,
    GenerationMode,
    GeneratedImage,
    SceneTemplate,
)

from .serializers import (
    GenerationCreateSerializer,
    GenerationListSerializer,
    GenerationSerializer,
    SceneTemplateSerializer,
)

from .services.generation_service import (
    GenerationAlreadyInProgress,
    GenerationService,
)
from .services.generation_queue import GenerationQueueService
from .services.performance import GenerationPerformanceTracker


logger = logging.getLogger(__name__)


def get_product_generation_block_reason(product):
    if (
        product.status
        != ProductStatus.ACTIVE
    ):
        return (
            "Esta peça não está disponível "
            "para novas criações."
        )

    source_asset = (
        product.assets
        .filter(
            asset_type=AssetType.ORIGINAL
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    if (
        not source_asset
        or not source_asset.file
        or not source_asset.file.name
    ):
        return (
            "Esta peça não possui uma "
            "imagem original disponível."
        )

    try:
        exists = (
            source_asset.file.storage.exists(
                source_asset.file.name
            )
        )

    except Exception:
        exists = False

    if not exists:
        return (
            "Esta peça não possui uma "
            "imagem original disponível."
        )

    return None


class GeneratedImageDownloadView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
        pk,
    ):
        queryset = (
            GeneratedImage.objects
            .select_related(
                "generation__organization"
            )
        )

        if not request.user.is_superuser:
            organization = getattr(
                request.user,
                "organization",
                None,
            )

            queryset = queryset.filter(
                generation__organization=organization
            )

        image = get_object_or_404(
            queryset,
            pk=pk,
        )

        return build_private_image_response(
            image.file,
            mime_type=image.mime_type,
            filename_prefix=(
                "maried-generated-image"
            ),
        )


class GeneratedImageDeleteView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def delete(
        self,
        request,
        pk,
    ):
        organization = getattr(
            request.user,
            "organization",
            None,
        )

        queryset = (
            GeneratedImage.objects
            .filter(
                generation__organization=organization
            )
            .select_related(
                "generation__organization"
            )
        )

        image = get_object_or_404(
            queryset,
            pk=pk,
        )

        VisualDataDeletionService.delete_generated_image(
            image
        )

        return Response(
            status=(
                status.HTTP_204_NO_CONTENT
            ),
        )


# ==========================================================
# SCENE TEMPLATES
# ==========================================================

class SceneTemplateListView(
    generics.ListAPIView
):
    serializer_class = SceneTemplateSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        qs = SceneTemplate.objects.filter(
            is_active=True,
            generation_mode=GenerationMode.INSTAGRAM,
        )

        category = self.request.query_params.get(
            "category"
        )

        mode = self.request.query_params.get(
            "mode"
        )

        if category:
            qs = qs.filter(
                category=category
            )

        if (
            mode
            and mode != GenerationMode.INSTAGRAM
        ):
            return SceneTemplate.objects.none()

        return qs.order_by(
            "sort_order",
            "name",
        )


# ==========================================================
# GENERATIONS
#
# GET  -> Minhas Criações
# POST -> Criar nova geração
# ==========================================================

class GenerationCreateView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    # ======================================================
    # GET — MINHAS CRIAÇÕES
    # ======================================================

    def get(self, request):
        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if not organization:
            return Response(
                {
                    "detail": (
                        "Usuário não possui "
                        "organização vinculada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            Generation.objects
            .filter(
                organization=organization
            )
            .select_related(
                "product",
                "scene_template",
                "model_reference",
            )
            .order_by(
                "-created_at",
                "-id",
            )
        )

        query = request.query_params.get(
            "q"
        )

        if query:
            query = query.strip()

            if query:
                queryset = queryset.filter(
                    product__name__icontains=query
                )

        generation_mode = request.query_params.get(
            "mode"
        )

        if generation_mode:
            queryset = queryset.filter(
                mode=generation_mode
            )

        generation_status = request.query_params.get(
            "status"
        )

        if generation_status:
            queryset = queryset.filter(
                status=generation_status
            )

        start_date = request.query_params.get(
            "start_date"
        )

        if start_date:
            queryset = queryset.filter(
                created_at__date__gte=start_date
            )

        end_date = request.query_params.get(
            "end_date"
        )

        if end_date:
            queryset = queryset.filter(
                created_at__date__lte=end_date
            )

        paginator = ClientListPagination()

        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = GenerationListSerializer(
            page,
            many=True,
            context={
                "request": request,
            },
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    # ======================================================
    # POST — CRIAÇÃO EXISTENTE
    # ======================================================

    def post(self, request):
        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if not organization:
            return Response(
                {
                    "detail": (
                        "Usuário não possui "
                        "organização vinculada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not organization.is_active:
            return Response(
                {
                    "detail": (
                        "Organização inativa."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        performance_tracker = GenerationPerformanceTracker()

        with performance_tracker.measure("validation"):
            serializer = GenerationCreateSerializer(
                data=request.data
            )

            serializer.is_valid(
                raise_exception=True
            )

            data = serializer.validated_data

            product = get_object_or_404(
                Product,
                pk=data["product_id"],
                organization=organization,
            )

        try:
            BillingAccessService.ensure_operational_access(
                organization
            )

        except SubscriptionRequiredError as exc:
            return Response(
                {
                    "code": exc.code,
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        block_reason = (
            get_product_generation_block_reason(
                product
            )
        )

        if block_reason:
            return Response(
                {
                    "detail": block_reason,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generation, created = (
                GenerationService.create_request(
                    user=request.user,
                    product=product,
                    mode=data["mode"],
                    scene_template_id=data.get(
                        "scene_template_id"
                    ),
                    model_reference_id=data.get(
                        "model_reference_id"
                    ),
                    idempotency_key=data[
                        "idempotency_key"
                    ],
                    performance_tracker=performance_tracker,
                )
            )

        except SubscriptionRequiredError as exc:
            return Response(
                {
                    "code": exc.code,
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        except InsufficientCredits as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        except GenerationAlreadyInProgress as exc:
            return Response(
                {
                    "code": exc.code,
                    "detail": str(exc),
                },
                status=status.HTTP_409_CONFLICT,
            )

        if created:
            GenerationQueueService.enqueue_after_commit(
                generation
            )

        generation.refresh_from_db()

        output = GenerationSerializer(
            generation,
            context={
                "request": request,
            },
        )

        if generation.status == "FAILED":
            return Response(
                output.data,
                status=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
            )

        if generation.status in [
            "CREATED",
            "CREDIT_RESERVED",
            "PROCESSING",
        ]:
            response_status = (
                status.HTTP_202_ACCEPTED
            )
        else:
            response_status = (
                status.HTTP_200_OK
            )

        return Response(
            output.data,
            status=response_status,
        )


# ==========================================================
# DETALHE DA GERAÇÃO
# ==========================================================

class GenerationDetailView(
    generics.RetrieveAPIView
):
    serializer_class = GenerationSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        return (
            Generation.objects
            .filter(
                organization=(
                    self.request.user.organization
                )
            )
            .select_related(
                "organization",
                "product",
                "scene_template",
                "model_reference",
                "generation_rule",
            )
        )
