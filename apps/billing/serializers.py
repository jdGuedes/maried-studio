from rest_framework import serializers

from .services import BillingAccessService


class CurrentSubscriptionSerializer(serializers.Serializer):
    status = serializers.CharField(
        allow_null=True
    )

    operational_status = serializers.CharField()

    plan_name = serializers.CharField(
        allow_null=True
    )

    plan = serializers.DictField(
        allow_null=True
    )

    billing_cycle = serializers.CharField(
        allow_null=True
    )

    credits_per_cycle = serializers.IntegerField(
        allow_null=True
    )

    current_period_start = serializers.DateTimeField(
        allow_null=True
    )

    current_period_end = serializers.DateTimeField(
        allow_null=True
    )

    next_billing_at = serializers.DateTimeField(
        allow_null=True
    )

    grace_until = serializers.DateField(
        allow_null=True
    )

    days_remaining_in_grace = serializers.IntegerField(
        allow_null=True
    )

    @classmethod
    def from_access(cls, access):
        subscription = access.subscription

        data = {
            "status": None,
            "operational_status": access.status,
            "plan_name": None,
            "plan": None,
            "billing_cycle": None,
            "credits_per_cycle": None,
            "current_period_start": None,
            "current_period_end": None,
            "next_billing_at": None,
            "grace_until": access.grace_until,
            "days_remaining_in_grace": (
                access.days_remaining_in_grace
            ),
        }

        if subscription:
            data.update(
                {
                    "status": subscription.status,
                    "plan_name": subscription.plan.name,
                    "plan": {
                        "id": str(subscription.plan_id),
                        "name": subscription.plan.name,
                        "credits_per_cycle": (
                            subscription.plan.credits_per_cycle
                        ),
                        "billing_cycle": (
                            subscription.plan.billing_cycle
                        ),
                    },
                    "billing_cycle": (
                        subscription.plan.billing_cycle
                    ),
                    "credits_per_cycle": (
                        subscription.credits_snapshot
                    ),
                    "current_period_start": (
                        subscription.current_period_start
                    ),
                    "current_period_end": (
                        subscription.current_period_end
                    ),
                    "next_billing_at": (
                        subscription.next_billing_at
                    ),
                }
            )

        return cls(
            data
        )
