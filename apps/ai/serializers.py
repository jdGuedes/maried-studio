from rest_framework import serializers

from apps.common.private_media import build_private_media_url

from .models import (
    ModelReference,
)


class ModelReferenceSerializer(
    serializers.ModelSerializer
):
    preview_image = (
        serializers.SerializerMethodField()
    )

    preview_image_url = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = ModelReference

        fields = [
            "id",
            "code",
            "name",
            "slug",
            "description",
            "prompt_instruction",
            "preview_image",
            "preview_image_url",
            "skin_tone",
            "hair_color",
            "age_range",
            "sort_order",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_preview_image_url(
        self,
        obj,
    ):
        return self.get_preview_image(
            obj
        )

    def get_preview_image(
        self,
        obj,
    ):
        if not obj.preview_image:
            return None

        request = (
            self.context.get(
                "request"
            )
        )

        return build_private_media_url(
            request,
            "ai:model-reference-preview-download",
            pk=obj.pk,
        )
