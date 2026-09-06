from django.contrib import admin

from .models import PaymentDispute, Plan, Subscription


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


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "origin_type",
        "status",
        "amount",
        "currency",
        "stripe_dispute_id",
        "created_at",
        "resolved_at",
    )

    list_filter = (
        "status",
        "origin_type",
        "currency",
    )

    search_fields = (
        "organization__name",
        "stripe_dispute_id",
        "stripe_payment_intent_id",
        "stripe_charge_id",
        "stripe_customer_id",
    )

    readonly_fields = (
        "stripe_dispute_id",
        "stripe_payment_intent_id",
        "stripe_charge_id",
        "stripe_customer_id",
        "related_subscription",
        "related_credit_purchase",
        "origin_type",
        "amount",
        "currency",
        "status",
        "reason",
        "evidence_due_by",
        "resolved_at",
        "last_event_id",
        "created_at",
        "updated_at",
    )

    list_select_related = (
        "organization",
        "related_subscription",
        "related_credit_purchase",
    )

    list_per_page = 50
