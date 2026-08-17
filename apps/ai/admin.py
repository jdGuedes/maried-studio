from django.contrib import admin

from .models import (
    ModelReference,
)


@admin.register(ModelReference)
class ModelReferenceAdmin(
    admin.ModelAdmin
):
    list_display = (
        "code",
        "name",
        "skin_tone",
        "hair_color",
        "age_range",
        "is_active",
        "sort_order",
    )

    list_filter = (
        "is_active",
        "skin_tone",
        "hair_color",
    )

    search_fields = (
        "code",
        "name",
        "slug",
        "description",
        "prompt_instruction",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "sort_order",
        "name",
    )

    list_per_page = 50
