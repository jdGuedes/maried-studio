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

    current_period_end = serializers.DateTimeField(
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
            "current_period_end": None,
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
                    "current_period_end": (
                        subscription.current_period_end
                    ),
                }
            )

        return cls(
            data
        )

