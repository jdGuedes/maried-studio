from PIL import Image

from rest_framework import serializers

from apps.common.private_media import build_private_media_url

from apps.studio.models import (
    GenerationStatus,
)

from .models import (
    AssetType,
    Product,
    ProductAsset,
)


# ==========================================================
# CONFIGURAÇÕES DE IMAGEM
# ==========================================================

ALLOWED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

MAX_IMAGE_SIZE = 15 * 1024 * 1024

MIN_IMAGE_WIDTH = 500
MIN_IMAGE_HEIGHT = 500


# ==========================================================
# INSPEÇÃO DA IMAGEM
# ==========================================================

def inspect_uploaded_image(uploaded):
    if uploaded.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError(
            "A imagem pode ter no máximo 15 MB."
        )

    try:
        uploaded.seek(0)

        image = Image.open(
            uploaded
        )

        image.verify()

        uploaded.seek(0)

        image = Image.open(
            uploaded
        )

        width, height = image.size

        image_format = image.format

    except Exception as exc:
        raise serializers.ValidationError(
            "O arquivo enviado não é uma imagem válida."
        ) from exc

    if (
        image_format
        not in ALLOWED_IMAGE_FORMATS
    ):
        raise serializers.ValidationError(
            "Formato não suportado. "
            "Use JPEG, PNG ou WEBP."
        )

    if (
        width < MIN_IMAGE_WIDTH
        or
        height < MIN_IMAGE_HEIGHT
    ):
        raise serializers.ValidationError(
            "A imagem precisa ter pelo menos "
            "500x500 pixels."
        )

    mime_type = (
        ALLOWED_IMAGE_FORMATS[
            image_format
        ]
    )

    uploaded.seek(0)

    return {
        "mime_type": mime_type,
        "width": width,
        "height": height,
        "file_size": uploaded.size,
    }


# ==========================================================
# ASSET
# ==========================================================

class ProductAssetSerializer(
    serializers.ModelSerializer
):
    file = serializers.ImageField(
        write_only=True,
        required=False,
    )

    file_url = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = ProductAsset

        fields = [
            "id",
            "asset_type",
            "file",
            "file_url",
            "mime_type",
            "width",
            "height",
            "file_size",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "mime_type",
            "width",
            "height",
            "file_size",
            "created_at",
        ]

    def get_file_url(
        self,
        obj,
    ):
        if not obj.file:
            return None

        request = (
            self.context.get(
                "request"
            )
        )

        return build_private_media_url(
            request,
            "product-asset-download",
            pk=obj.pk,
        )

    def validate_file(
        self,
        uploaded,
    ):
        inspect_uploaded_image(
            uploaded
        )

        return uploaded

    def create(
        self,
        validated_data,
    ):
        uploaded = (
            validated_data[
                "file"
            ]
        )

        metadata = (
            inspect_uploaded_image(
                uploaded
            )
        )

        asset = (
            ProductAsset.objects
            .create(
                **validated_data,
                **metadata,
            )
        )

        return asset


# ==========================================================
# RESULTADOS DA PEÇA
# ==========================================================

class ProductGenerationSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()

    mode = serializers.CharField()

    mode_label = (
        serializers.SerializerMethodField()
    )

    style_name = (
        serializers.SerializerMethodField()
    )

    image_url = (
        serializers.SerializerMethodField()
    )

    generated_image_id = (
        serializers.SerializerMethodField()
    )

    created_at = (
        serializers.DateTimeField()
    )

    completed_at = (
        serializers.DateTimeField(
            allow_null=True
        )
    )

    def get_mode_label(
        self,
        obj,
    ):
        return (
            obj.get_mode_display()
        )

    def get_style_name(
        self,
        obj,
    ):
        if not obj.scene_template:
            return None

        return (
            obj.scene_template.name
        )

    def get_image_url(
        self,
        obj,
    ):
        try:
            result = (
                obj.result_image
            )

        except Exception:
            return None

        if (
            not result
            or
            not result.file
        ):
            return None

        request = (
            self.context.get(
                "request"
            )
        )

        return build_private_media_url(
            request,
            "generated-image-download",
            pk=result.pk,
        )

    def get_generated_image_id(
        self,
        obj,
    ):
        try:
            result = (
                obj.result_image
            )

        except Exception:
            return None

        if not result:
            return None

        return str(
            result.pk
        )


# ==========================================================
# PRODUCT
# ==========================================================

class ProductSerializer(
    serializers.ModelSerializer
):
    assets = (
        ProductAssetSerializer(
            many=True,
            read_only=True,
        )
    )

    original_image = (
        serializers.ImageField(
            write_only=True,
            required=False,
        )
    )

    original_image_url = (
        serializers.SerializerMethodField()
    )

    category_label = (
        serializers.CharField(
            source="get_category_display",
            read_only=True,
        )
    )

    generations_count = (
        serializers.SerializerMethodField()
    )

    generations = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "category",
            "category_label",
            "status",

            "original_image",
            "original_image_url",

            "assets",

            "generations_count",
            "generations",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
            "generations_count",
            "generations",
        ]

    # ======================================================
    # IMAGEM ORIGINAL
    # ======================================================

    def validate_original_image(
        self,
        uploaded,
    ):
        inspect_uploaded_image(
            uploaded
        )

        return uploaded

    def get_original_image_url(
        self,
        obj,
    ):
        asset = (
            obj.assets
            .filter(
                asset_type=(
                    AssetType.ORIGINAL
                )
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        if (
            not asset
            or
            not asset.file
        ):
            return None

        request = (
            self.context.get(
                "request"
            )
        )

        return build_private_media_url(
            request,
            "product-asset-download",
            pk=asset.pk,
        )

    # ======================================================
    # CONTAGEM DE RESULTADOS
    # ======================================================

    def get_generations_count(
        self,
        obj,
    ):
        return (
            obj.generations
            .filter(
                status=(
                    GenerationStatus
                    .COMPLETED
                )
            )
            .count()
        )

    # ======================================================
    # RESULTADOS GERADOS
    # ======================================================

    def get_generations(
        self,
        obj,
    ):
        # Evita devolver toda a galeria
        # na listagem geral.
        request = (
            self.context.get(
                "request"
            )
        )

        view = (
            self.context.get(
                "view"
            )
        )

        if (
            view
            and
            getattr(
                view,
                "action",
                None,
            )
            == "list"
        ):
            return []

        queryset = (
            obj.generations
            .filter(
                status=(
                    GenerationStatus
                    .COMPLETED
                )
            )
            .select_related(
                "scene_template"
            )
            .select_related(
                "result_image"
            )
            .order_by(
                "-created_at"
            )
        )

        return (
            ProductGenerationSerializer(
                queryset,
                many=True,
                context={
                    "request": request,
                },
            ).data
        )

    # ======================================================
    # CREATE
    # ======================================================

    def create(
        self,
        validated_data,
    ):
        original_image = (
            validated_data.pop(
                "original_image",
                None,
            )
        )

        product = (
            Product.objects.create(
                **validated_data
            )
        )

        if original_image:
            metadata = (
                inspect_uploaded_image(
                    original_image
                )
            )

            ProductAsset.objects.create(
                product=product,

                asset_type=(
                    AssetType.ORIGINAL
                ),

                file=original_image,

                **metadata,
            )

        return product


# ==========================================================
# TROCAR IMAGEM ORIGINAL
# ==========================================================

class OriginalAssetUploadSerializer(
    serializers.Serializer
):
    file = (
        serializers.ImageField()
    )

    def validate_file(
        self,
        uploaded,
    ):
        inspect_uploaded_image(
            uploaded
        )

        return uploaded

    def create(
        self,
        validated_data,
    ):
        product = (
            self.context[
                "product"
            ]
        )

        uploaded = (
            validated_data[
                "file"
            ]
        )

        metadata = (
            inspect_uploaded_image(
                uploaded
            )
        )

        # Uma única imagem ORIGINAL
        # por produto.
        product.assets.filter(
            asset_type=(
                AssetType.ORIGINAL
            )
        ).delete()

        return (
            ProductAsset.objects
            .create(
                product=product,

                asset_type=(
                    AssetType.ORIGINAL
                ),

                file=uploaded,

                **metadata,
            )
        )
