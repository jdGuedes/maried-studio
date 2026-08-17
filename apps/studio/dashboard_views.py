from calendar import monthrange
from datetime import date

from django.utils import timezone

from rest_framework import (
    permissions,
    status,
)

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import (
    Product,
    ProductStatus,
)

from apps.studio.models import (
    Generation,
    GenerationStatus,
)

from .dashboard_serializers import (
    DashboardSerializer,
)


# ==========================================================
# UTILITÁRIOS DE DATA
# ==========================================================

def get_current_month_period():
    today = timezone.localdate()

    start_date = today.replace(
        day=1
    )

    last_day = monthrange(
        today.year,
        today.month,
    )[1]

    end_date = today.replace(
        day=last_day
    )

    return (
        start_date,
        end_date,
    )


def parse_date_param(
    value,
):
    if not value:
        return None

    try:
        return date.fromisoformat(
            value
        )

    except ValueError:
        return None


def resolve_period(
    request,
    *,
    start_param,
    end_param,
):
    """
    Se nenhuma data for informada,
    usa o mês atual.

    Se apenas uma das datas for
    informada, retorna erro.
    """

    raw_start = (
        request.query_params.get(
            start_param
        )
    )

    raw_end = (
        request.query_params.get(
            end_param
        )
    )

    # ======================================================
    # PADRÃO
    # ======================================================

    if (
        not raw_start
        and not raw_end
    ):
        return (
            *get_current_month_period(),
            None,
        )

    # ======================================================
    # PRECISA TER INÍCIO E FIM
    # ======================================================

    if (
        not raw_start
        or not raw_end
    ):
        return (
            None,
            None,
            (
                "Informe a data inicial "
                "e a data final."
            ),
        )

    start_date = (
        parse_date_param(
            raw_start
        )
    )

    end_date = (
        parse_date_param(
            raw_end
        )
    )

    if (
        not start_date
        or not end_date
    ):
        return (
            None,
            None,
            (
                "Formato de data inválido. "
                "Use YYYY-MM-DD."
            ),
        )

    if (
        start_date >
        end_date
    ):
        return (
            None,
            None,
            (
                "A data inicial não pode "
                "ser maior que a data final."
            ),
        )

    return (
        start_date,
        end_date,
        None,
    )


# ==========================================================
# DASHBOARD
# ==========================================================

class DashboardView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
    ):
        # ==================================================
        # ORGANIZAÇÃO
        # ==================================================

        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if organization is None:
            return Response(
                {
                    "detail": (
                        "Usuário não possui "
                        "organização vinculada."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        # ==================================================
        # PERÍODO DAS GERAÇÕES
        # ==================================================

        (
            generation_start,
            generation_end,
            generation_error,
        ) = resolve_period(
            request,
            start_param=(
                "generation_start_date"
            ),
            end_param=(
                "generation_end_date"
            ),
        )

        if generation_error:
            return Response(
                {
                    "detail": (
                        generation_error
                    ),
                    "filter": (
                        "generations"
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        # ==================================================
        # PERÍODO DOS PRODUTOS
        # ==================================================

        (
            product_start,
            product_end,
            product_error,
        ) = resolve_period(
            request,
            start_param=(
                "product_start_date"
            ),
            end_param=(
                "product_end_date"
            ),
        )

        if product_error:
            return Response(
                {
                    "detail": (
                        product_error
                    ),
                    "filter": (
                        "products"
                    ),
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        # ==================================================
        # PEÇAS CADASTRADAS
        #
        # Contamos apenas peças ACTIVE.
        # Peças ARCHIVED continuam preservadas no banco
        # e no histórico, mas não aparecem no Dashboard.
        # ==================================================

        products_count = (
            Product.objects
            .filter(
                organization=(
                    organization
                ),

                status=(
                    ProductStatus.ACTIVE
                ),

                created_at__date__gte=(
                    product_start
                ),

                created_at__date__lte=(
                    product_end
                ),
            )
            .count()
        )

        # ==================================================
        # CRIAÇÕES CONCLUÍDAS
        #
        # Não contamos FAILED,
        # CANCELLED ou PROCESSING.
        # ==================================================

        generations_count = (
            Generation.objects
            .filter(
                organization=(
                    organization
                ),

                status=(
                    GenerationStatus
                    .COMPLETED
                ),

                created_at__date__gte=(
                    generation_start
                ),

                created_at__date__lte=(
                    generation_end
                ),
            )
            .count()
        )

        # ==================================================
        # CARTEIRA
        # ==================================================

        wallet = (
            organization
            .credit_wallet
        )

        available_credits = (
            wallet.available_balance
        )

        # ==================================================
        # ÚLTIMAS CRIAÇÕES
        #
        # Acompanha o mesmo período do card "Criações".
        # ==================================================

        recent_queryset = (
            Generation.objects
            .filter(
                organization=(
                    organization
                ),

                status=(
                    GenerationStatus
                    .COMPLETED
                ),

                created_at__date__gte=(
                    generation_start
                ),

                created_at__date__lte=(
                    generation_end
                ),
            )
            .select_related(
                "product",
                "scene_template",
            )
            .order_by(
                "-created_at"
            )[:8]
        )

        recent_generations = []

        for generation in (
            recent_queryset
        ):
            image_url = None

            # ==============================================
            # IMAGEM GERADA
            # ==============================================

            try:
                result_image = (
                    generation
                    .result_image
                )

                if (
                    result_image
                    and result_image.file
                ):
                    image_url = (
                        request
                        .build_absolute_uri(
                            result_image
                            .file
                            .url
                        )
                    )

            except Exception:
                image_url = None

            # ==============================================
            # ESTILO
            # ==============================================

            style_name = None

            if (
                generation
                .scene_template
            ):
                style_name = (
                    generation
                    .scene_template
                    .name
                )

            # ==============================================
            # NOME DA PEÇA
            # ==============================================

            product_name = (
                generation
                .product
                .name
                or "Peça sem nome"
            )

            # ==============================================
            # RESULTADO
            # ==============================================

            recent_generations.append(
                {
                    "id": (
                        generation.id
                    ),

                    "product_id": (
                        generation
                        .product_id
                    ),

                    "product_name": (
                        product_name
                    ),

                    "category": (
                        generation
                        .product
                        .category
                    ),

                    "mode": (
                        generation.mode
                    ),

                    "mode_label": (
                        generation
                        .get_mode_display()
                    ),

                    "style_name": (
                        style_name
                    ),

                    "image_url": (
                        image_url
                    ),

                    "created_at": (
                        generation
                        .created_at
                    ),
                }
            )

        # ==================================================
        # RESPOSTA
        # ==================================================

        data = {
            "available_credits": (
                available_credits
            ),

            "products": {
                "count": (
                    products_count
                ),

                "start_date": (
                    product_start
                ),

                "end_date": (
                    product_end
                ),
            },

            "generations": {
                "count": (
                    generations_count
                ),

                "start_date": (
                    generation_start
                ),

                "end_date": (
                    generation_end
                ),
            },

            "recent_generations": (
                recent_generations
            ),
        }

        serializer = (
            DashboardSerializer(
                data
            )
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_200_OK
            ),
        )