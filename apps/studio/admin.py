from django.contrib import admin

from .models import (
    GeneratedImage,
    Generation,
    GenerationRule,
    PreservationRule,
    SceneTemplate,
)


@admin.register(GenerationRule)
class GenerationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "generation_mode",
        "framing",
        "body_area",
        "product_priority",
        "detail_level",
        "is_active",
    )

    list_filter = (
        "category",
        "generation_mode",
        "product_priority",
        "detail_level",
        "is_active",
    )

    search_fields = (
        "category",
        "generation_mode",
        "framing",
        "body_area",
        "placement_instruction",
    )

    ordering = (
        "category",
        "generation_mode",
    )

    list_per_page = 50


@admin.register(SceneTemplate)
class SceneTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "generation_mode",
        "category",
        "version",
        "is_active",
        "sort_order",
    )

    list_filter = (
        "generation_mode",
        "category",
        "is_active",
        "version",
    )

    search_fields = (
        "name",
        "slug",
        "category",
        "prompt_template",
    )

    ordering = (
        "generation_mode",
        "category",
        "sort_order",
    )

    list_per_page = 50


@admin.register(PreservationRule)
class PreservationRuleAdmin(admin.ModelAdmin):
    list_display = (
        "rule_type",
        "category",
        "priority",
        "is_active",
    )

    list_filter = (
        "category",
        "priority",
        "is_active",
    )

    search_fields = (
        "rule_type",
        "category",
        "instruction",
    )

    ordering = (
        "category",
        "priority",
    )

    list_per_page = 50


@admin.register(Generation)
class GenerationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "mode",
        "status",
        "provider",
        "model",
        "credit_cost",
        "retry_count",
        "created_at",
    )

    list_filter = (
        "mode",
        "status",
        "provider",
        "created_at",
    )

    search_fields = (
        "id",
        "product__name",
        "user__email",
    )

    readonly_fields = (
        "final_prompt",
        "input_tokens",
        "output_tokens",
        "api_cost_usd",
        "retry_count",
        "started_at",
        "completed_at",
        "error_code",
        "error_message",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "generation",
        "width",
        "height",
        "file_size",
        "created_at",
    )

    search_fields = (
        "id",
        "generation__id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 50