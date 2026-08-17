from django.shortcuts import get_object_or_404

from rest_framework import (
    generics,
    permissions,
    status,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product

from .models import (
    Generation,
    GenerationMode,
    SceneTemplate,
)
from .serializers import (
    GenerationCreateSerializer,
    GenerationSerializer,
    SceneTemplateSerializer,
)
from .services.generation_service import GenerationService


class SceneTemplateListView(generics.ListAPIView):
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


class GenerationCreateView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request):
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
            organization=request.user.organization,
        )

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
            )
        )

        # -----------------------------------------------------
        # MVP V1
        # Processamento ainda síncrono.
        # Futuramente isso será movido para worker/fila.
        # -----------------------------------------------------
        if created:
            try:
                generation = GenerationService.process(
                generation
                )

            except Exception as exc:
                import traceback

                print(
                "\n"
                "============================================"
                )

                print(
                "ERRO NO GENERATION SERVICE"
                )

                print(
                "============================================"
                )

                print(
                "Generation ID:",
                generation.id,
                )

                print(
                "Erro:",
                repr(exc),
                )

                traceback.print_exc()

                print(
                "============================================"
                "\n"
                )

                generation.refresh_from_db()

        # -----------------------------------------------------
        # Garante que a resposta da API reflita
        # exatamente o estado salvo no banco.
        # -----------------------------------------------------
        generation.refresh_from_db()

        output = GenerationSerializer(
            generation,
            context={
                "request": request,
            },
        )

        # -----------------------------------------------------
        # GERAÇÃO COM FALHA
        # -----------------------------------------------------
        if generation.status == "FAILED":
            return Response(
                output.data,
                status=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
            )

        # -----------------------------------------------------
        # NOVA GERAÇÃO
        # -----------------------------------------------------
        if created:
            response_status = (
                status.HTTP_201_CREATED
            )

        # -----------------------------------------------------
        # REQUISIÇÃO IDEMPOTENTE
        # Geração já existente.
        # -----------------------------------------------------
        else:
            response_status = status.HTTP_200_OK

        return Response(
            output.data,
            status=response_status,
        )


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
