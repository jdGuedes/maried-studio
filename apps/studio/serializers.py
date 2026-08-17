import uuid

from rest_framework import serializers

from .models import (
    Generation,
    GenerationMode,
    SceneTemplate,
)


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
        scene_template_id = attrs.get("scene_template_id")
        model_reference_id = attrs.get("model_reference_id")

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


class GenerationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

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

            "error_code",
            "error_message",

            "created_at",
            "started_at",
            "completed_at",
        ]

    def get_image_url(self, obj):
        try:
            url = obj.result_image.file.url

            request = self.context.get("request")

            if request:
                return request.build_absolute_uri(url)

            return url

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
        wallet = self._get_wallet(obj)

        if not wallet:
            return None

        return wallet.balance

    def get_reserved_credits(self, obj):
        wallet = self._get_wallet(obj)

        if not wallet:
            return None

        return wallet.reserved_balance

    def get_available_credits(self, obj):
        wallet = self._get_wallet(obj)

        if not wallet:
            return None

        return wallet.available_balance
