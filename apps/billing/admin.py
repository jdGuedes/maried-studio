from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "billing_cycle",
        "credits_per_cycle",
        "is_active",
        "sort_order",
    )

    list_filter = (
        "billing_cycle",
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
        "description",
    )

    ordering = (
        "sort_order",
        "price",
    )

    prepopulated_fields = {
        "slug": (
            "name",
        ),
    }

    list_per_page = 50


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan",
        "status",
        "price_snapshot",
        "credits_snapshot",
        "current_period_start",
        "current_period_end",
        "next_billing_at",
        "cancel_at_period_end",
    )

    list_filter = (
        "status",
        "plan",
        "cancel_at_period_end",
        "current_period_end",
        "next_billing_at",
    )

    search_fields = (
        "organization__name",
        "organization__slug",
        "plan__name",
        "plan__slug",
    )

    list_select_related = (
        "organization",
        "plan",
    )

    ordering = (
        "organization__name",
    )

    list_per_page = 50
