from datetime import date

from rest_framework import (
    permissions,
    status,
    viewsets,
)

from rest_framework.decorators import action

from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)

from rest_framework.response import Response

from apps.studio.models import (
    GenerationStatus,
)

from .models import (
    Product,
    ProductStatus,
)

from .serializers import (
    OriginalAssetUploadSerializer,
    ProductAssetSerializer,
    ProductSerializer,
)


class ProductViewSet(
    viewsets.ModelViewSet
):
    serializer_class = (
        ProductSerializer
    )

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]


    # ======================================================
    # QUERYSET
    # ======================================================

    def get_queryset(
        self,
    ):
        queryset = (
            Product.objects
            .filter(
                organization=(
                    self.request
                    .user
                    .organization
                )
            )
            .prefetch_related(
                "assets",
            )
        )

        # ==================================================
        # LISTAGEM
        #
        # Por padrão, "Minhas peças"
        # mostra somente peças ativas.
        # ==================================================

        if (
            self.action
            == "list"
        ):
            queryset = (
                queryset.filter(
                    status=(
                        ProductStatus
                        .ACTIVE
                    )
                )
            )

        # ==================================================
        # BUSCA POR NOME
        # ==================================================

        search = (
            self.request
            .query_params
            .get(
                "q",
                ""
            )
            .strip()
        )

        if search:
            queryset = (
                queryset.filter(
                    name__icontains=(
                        search
                    )
                )
            )

        # ==================================================
        # CATEGORIA
        # ==================================================

        category = (
            self.request
            .query_params
            .get(
                "category"
            )
        )

        if category:
            queryset = (
                queryset.filter(
                    category=category
                )
            )

        # ==================================================
        # DATA INICIAL
        # ==================================================

        start_date = (
            self.request
            .query_params
            .get(
                "start_date"
            )
        )

        if start_date:
            try:
                parsed_start = (
                    date.fromisoformat(
                        start_date
                    )
                )

                queryset = (
                    queryset.filter(
                        created_at__date__gte=(
                            parsed_start
                        )
                    )
                )

            except ValueError:
                pass

        # ==================================================
        # DATA FINAL
        # ==================================================

        end_date = (
            self.request
            .query_params
            .get(
                "end_date"
            )
        )

        if end_date:
            try:
                parsed_end = (
                    date.fromisoformat(
                        end_date
                    )
                )

                queryset = (
                    queryset.filter(
                        created_at__date__lte=(
                            parsed_end
                        )
                    )
                )

            except ValueError:
                pass

        return (
            queryset.order_by(
                "-created_at"
            )
        )


    # ======================================================
    # CREATE
    # ======================================================

    def perform_create(
        self,
        serializer,
    ):
        serializer.save(
            organization=(
                self.request
                .user
                .organization
            ),

            created_by=(
                self.request.user
            ),

            status=(
                ProductStatus.ACTIVE
            ),
        )


    # ======================================================
    # DELETE SEGURO
    #
    # Não removemos fisicamente.
    # Arquivamos a peça.
    # ======================================================

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):
        product = (
            self.get_object()
        )

        if (
            product.status
            == ProductStatus.ARCHIVED
        ):
            return Response(
                {
                    "detail": (
                        "Esta peça já está arquivada."
                    )
                },
                status=(
                    status.HTTP_200_OK
                ),
            )

        product.status = (
            ProductStatus.ARCHIVED
        )

        product.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return Response(
            {
                "detail": (
                    "Peça excluída com sucesso."
                ),

                "id": str(
                    product.id
                ),

                "status": (
                    product.status
                ),
            },
            status=(
                status.HTTP_200_OK
            ),
        )


    # ======================================================
    # RENOMEAR
    #
    # Endpoint opcional mais semântico:
    #
    # PATCH
    # /api/products/<id>/rename/
    #
    # {"name": "Novo nome"}
    #
    # O PATCH normal do ModelViewSet
    # também continua funcionando.
    # ======================================================

    @action(
        detail=True,
        methods=[
            "patch",
        ],
        url_path="rename",
        parser_classes=[
            JSONParser,
        ],
    )
    def rename(
        self,
        request,
        pk=None,
    ):
        product = (
            self.get_object()
        )

        name = (
            request.data
            .get(
                "name",
                ""
            )
            .strip()
        )

        if not name:
            return Response(
                {
                    "detail": (
                        "Informe um nome "
                        "para a peça."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        if len(name) > 160:
            return Response(
                {
                    "detail": (
                        "O nome pode ter "
                        "no máximo 160 caracteres."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )

        product.name = name

        product.save(
            update_fields=[
                "name",
                "updated_at",
            ]
        )

        serializer = (
            self.get_serializer(
                product
            )
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_200_OK
            ),
        )


    # ======================================================
    # RESULTADOS DE UMA PEÇA
    #
    # GET
    # /api/products/<id>/results/
    # ======================================================

    @action(
        detail=True,
        methods=[
            "get",
        ],
        url_path="results",
    )
    def results(
        self,
        request,
        pk=None,
    ):
        product = (
            self.get_object()
        )

        generations = (
            product.generations
            .filter(
                status=(
                    GenerationStatus
                    .COMPLETED
                )
            )
            .select_related(
                "scene_template",
                "result_image",
            )
            .order_by(
                "-created_at"
            )
        )

        results = []

        for generation in (
            generations
        ):
            image_url = None

            try:
                result_image = (
                    generation
                    .result_image
                )

                if (
                    result_image
                    and
                    result_image.file
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

            results.append(
                {
                    "id": str(
                        generation.id
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
                        generation.created_at
                    ),

                    "completed_at": (
                        generation.completed_at
                    ),
                }
            )

        return Response(
            {
                "product_id": str(
                    product.id
                ),

                "product_name": (
                    product.name
                    or "Peça sem nome"
                ),

                "count": (
                    len(
                        results
                    )
                ),

                "results": (
                    results
                ),
            },
            status=(
                status.HTTP_200_OK
            ),
        )


    # ======================================================
    # IMAGEM ORIGINAL
    # ======================================================

    @action(
        detail=True,
        methods=[
            "post",
        ],
        url_path=(
            "original-image"
        ),
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def original_image(
        self,
        request,
        pk=None,
    ):
        product = (
            self.get_object()
        )

        serializer = (
            OriginalAssetUploadSerializer(
                data=request.data,

                context={
                    "product": product,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        asset = (
            serializer.save()
        )

        output = (
            ProductAssetSerializer(
                asset,

                context={
                    "request": request,
                },
            )
        )

        return Response(
            output.data,
            status=(
                status.HTTP_201_CREATED
            ),
        )