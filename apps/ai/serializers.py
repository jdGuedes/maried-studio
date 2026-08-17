from rest_framework import serializers

from .models import (
    ModelReference,
)


class ModelReferenceSerializer(
    serializers.ModelSerializer
):
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
        if not obj.preview_image:
            return None

        request = (
            self.context.get(
                "request"
            )
        )

        url = obj.preview_image.url

        if request:
            return (
                request
                .build_absolute_uri(
                    url
                )
            )

        return url
