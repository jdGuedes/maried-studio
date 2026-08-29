import uuid

from rest_framework import serializers

from apps.common.private_media import build_private_media_url

from .models import (
    Generation,
    GenerationMode,
    SceneTemplate,
)


# ==========================================================
# SCENE TEMPLATE
# ==========================================================

class SceneTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneTemplate

        fields = [
            "id",
            "name",
            "slug",
            "generation_mode",
            "category",
            "preview_image",
            "version",
            "sort_order",
        ]


# ==========================================================
# CRIAR GERAÇÃO
# ==========================================================

class GenerationCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    mode = serializers.ChoiceField(
        choices=GenerationMode.choices
    )

    scene_template_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    model_reference_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )

    idempotency_key = serializers.CharField(
        required=False,
        max_length=100,
    )

    def validate(self, attrs):
        attrs.setdefault(
            "idempotency_key",
            uuid.uuid4().hex,
        )

        mode = attrs["mode"]

        scene_template_id = attrs.get(
            "scene_template_id"
        )

        model_reference_id = attrs.get(
            "model_reference_id"
        )

        # --------------------------------------------------
        # STILL
        # --------------------------------------------------

        if mode == GenerationMode.STILL:
            if scene_template_id:
                raise serializers.ValidationError(
                    {
                        "scene_template_id": (
                            "Still não usa cenário."
                        )
                    }
                )

            if model_reference_id:
                raise serializers.ValidationError(
                    {
                        "model_reference_id": (
                            "Still não usa modelo."
                        )
                    }
                )

        # --------------------------------------------------
        # BODY DETAIL
        # --------------------------------------------------

        if mode == GenerationMode.BODY_DETAIL:
            if scene_template_id:
                raise serializers.ValidationError(
                    {
                        "scene_template_id": (
                            "Detalhe no Corpo usa "
                            "ModelReference, não cenário."
                        )
                    }
                )

            if not model_reference_id:
                raise serializers.ValidationError(
                    {
                        "model_reference_id": (
                            "Detalhe no Corpo exige "
                            "uma modelo."
                        )
                    }
                )

        # --------------------------------------------------
        # INSTAGRAM
        # --------------------------------------------------

        if mode == GenerationMode.INSTAGRAM:
            if not scene_template_id:
                raise serializers.ValidationError(
                    {
                        "scene_template_id": (
                            "Instagramável exige "
                            "um cenário."
                        )
                    }
                )

            if model_reference_id:
                raise serializers.ValidationError(
                    {
                        "model_reference_id": (
                            "Instagramável não usa modelo."
                        )
                    }
                )

        # --------------------------------------------------
        # MODEL
        # --------------------------------------------------

        if mode == GenerationMode.MODEL:
            if scene_template_id:
                raise serializers.ValidationError(
                    {
                        "scene_template_id": (
                            "Na Modelo usa "
                            "ModelReference, não cenário."
                        )
                    }
                )

            if not model_reference_id:
                raise serializers.ValidationError(
                    {
                        "model_reference_id": (
                            "Na Modelo exige "
                            "uma modelo."
                        )
                    }
                )

        return attrs


# ==========================================================
# LISTAGEM — MINHAS CRIAÇÕES
# ==========================================================

class GenerationListSerializer(
    serializers.ModelSerializer
):
    product_id = serializers.UUIDField(
        source="product.id",
        read_only=True,
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )

    category = serializers.CharField(
        source="product.category",
        read_only=True,
    )

    category_label = serializers.SerializerMethodField()

    mode_label = serializers.SerializerMethodField()

    image_url = serializers.SerializerMethodField()

    generated_image_id = serializers.SerializerMethodField()

    scene_template_name = serializers.SerializerMethodField()

    model_reference_name = serializers.SerializerMethodField()

    class Meta:
        model = Generation

        fields = [
            "id",

            "product_id",
            "product_name",

            "category",
            "category_label",

            "mode",
            "mode_label",

            "status",

            "scene_template",
            "scene_template_name",

            "model_reference",
            "model_reference_name",

            "image_url",
            "generated_image_id",

            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_category_label(self, obj):
        product = obj.product

        get_display = getattr(
            product,
            "get_category_display",
            None,
        )

        if callable(get_display):
            return get_display()

        return product.category

    def get_mode_label(self, obj):
        get_display = getattr(
            obj,
            "get_mode_display",
            None,
        )

        if callable(get_display):
            return get_display()

        return obj.mode

    def get_scene_template_name(self, obj):
        if not obj.scene_template:
            return None

        return obj.scene_template.name

    def get_model_reference_name(self, obj):
        if not obj.model_reference:
            return None

        return obj.model_reference.name

    def get_image_url(self, obj):
        try:
            result_image = obj.result_image

            request = self.context.get(
                "request"
            )

            if not result_image.file:
                return None

            return build_private_media_url(
                request,
                "generated-image-download",
                pk=result_image.pk,
            )

        except Exception:
            return None

    def get_generated_image_id(self, obj):
        try:
            result_image = obj.result_image

            if not result_image.file:
                return None

            return str(
                result_image.pk
            )

        except Exception:
            return None


# ==========================================================
# DETALHE / RESPOSTA DA GERAÇÃO
# ==========================================================

class GenerationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    generated_image_id = serializers.SerializerMethodField()

    wallet_balance = serializers.SerializerMethodField()

    reserved_credits = serializers.SerializerMethodField()

    available_credits = serializers.SerializerMethodField()

    class Meta:
        model = Generation

        fields = [
            "id",
            "product",
            "mode",
            "scene_template",
            "model_reference",
            "status",
            "failure_type",

            "provider",
            "model",

            "credit_cost",
            "wallet_balance",
            "reserved_credits",
            "available_credits",

            "retry_count",

            "image_url",
            "generated_image_id",

            "error_code",
            "error_message",

            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_image_url(self, obj):
        try:
            result_image = obj.result_image

            request = self.context.get(
                "request"
            )

            if not result_image.file:
                return None

            return build_private_media_url(
                request,
                "generated-image-download",
                pk=result_image.pk,
            )

        except Exception:
            return None

    def get_generated_image_id(self, obj):
        try:
            result_image = obj.result_image

            if not result_image.file:
                return None

            return str(
                result_image.pk
            )

        except Exception:
            return None

    def _get_wallet(self, obj):
        try:
            from apps.credits.models import CreditWallet

            return CreditWallet.objects.get(
                organization_id=obj.organization_id
            )

        except CreditWallet.DoesNotExist:
            return None

    def get_wallet_balance(self, obj):
        wallet = self._get_wallet(
            obj
        )

        if not wallet:
            return None

        return wallet.balance

    def get_reserved_credits(self, obj):
        wallet = self._get_wallet(
            obj
        )

        if not wallet:
            return None

        return wallet.reserved_balance

    def get_available_credits(self, obj):
        wallet = self._get_wallet(
            obj
        )

        if not wallet:
            return None

        return wallet.available_balance
