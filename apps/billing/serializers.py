from rest_framework import serializers

from .models import (
    CreditPackage,
    CreditPurchase,
    Plan,
)
from .services import (
    BillingAccessService,
    CreditPurchaseService,
)


class CurrentSubscriptionSerializer(serializers.Serializer):
    status = serializers.CharField(
        allow_null=True
    )

    operational_status = serializers.CharField()

    can_create = serializers.BooleanField()

    can_purchase_credits = serializers.BooleanField()

    can_start_subscription = serializers.BooleanField()

    financial_blocked = serializers.BooleanField()

    access_reason = serializers.CharField()

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

    cancel_at_period_end = serializers.BooleanField()

    grace_until = serializers.DateField(
        allow_null=True
    )

    days_remaining_in_grace = serializers.IntegerField(
        allow_null=True
    )

    extra_credit_limit_per_cycle = serializers.IntegerField()

    paid_credits_this_cycle = serializers.IntegerField()

    pending_credits_this_cycle = serializers.IntegerField()

    remaining_extra_credits = serializers.IntegerField()

    @classmethod
    def from_access(cls, access):
        subscription = access.subscription
        allowance = (
            CreditPurchaseService
            .allowance_for_subscription(
                subscription
            )
            if subscription
            else {
                "extra_credit_limit_per_cycle": 0,
                "paid_credits_this_cycle": 0,
                "pending_credits_this_cycle": 0,
                "remaining_extra_credits": 0,
            }
        )

        data = {
            "status": None,
            "operational_status": access.status,
            "can_create": access.can_create,
            "can_purchase_credits": access.can_purchase_credits,
            "can_start_subscription": access.can_start_subscription,
            "financial_blocked": access.financial_blocked,
            "access_reason": access.access_reason,
            "plan_name": None,
            "plan": None,
            "billing_cycle": None,
            "credits_per_cycle": None,
            "current_period_start": None,
            "current_period_end": None,
            "next_billing_at": None,
            "cancel_at_period_end": False,
            "grace_until": access.grace_until,
            "days_remaining_in_grace": (
                access.days_remaining_in_grace
            ),
            **allowance,
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
                        "extra_credit_limit_per_cycle": (
                            subscription
                            .plan
                            .extra_credit_limit_per_cycle
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
                    "cancel_at_period_end": (
                        subscription.cancel_at_period_end
                    ),
                }
            )

        return cls(
            data
        )


class AvailablePlanSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "price",
            "billing_cycle",
            "credits_per_cycle",
            "extra_credit_limit_per_cycle",
            "stripe_ready_for_checkout",
        ]


class SubscriptionCheckoutSerializer(
    serializers.Serializer
):
    plan_id = serializers.UUIDField()

    def validate_plan_id(
        self,
        value,
    ):
        try:
            plan = Plan.objects.get(
                pk=value,
            )

        except Plan.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Plano indisponível para pagamento no momento."
            ) from exc

        if not plan.stripe_ready_for_checkout:
            raise serializers.ValidationError(
                "Plano indisponível para pagamento no momento."
            )

        self.context["plan"] = plan

        return value


class CreditPackageSerializer(serializers.ModelSerializer):
    checkout_available = serializers.SerializerMethodField()
    checkout_unavailable_reason = serializers.SerializerMethodField()
    pending_purchase = serializers.SerializerMethodField()

    class Meta:
        model = CreditPackage
        fields = [
            "id",
            "name",
            "description",
            "credits",
            "price",
            "currency",
            "stripe_ready_for_checkout",
            "checkout_available",
            "checkout_unavailable_reason",
            "pending_purchase",
        ]

    def _remaining(self):
        return self.context.get(
            "remaining_extra_credits",
            0,
        )

    def _can_purchase(self):
        return self.context.get(
            "can_purchase_credits",
            False,
        )

    def get_checkout_available(self, obj):
        return (
            self._can_purchase()
            and obj.stripe_ready_for_checkout
            and obj.credits <= self._remaining()
        )

    def get_checkout_unavailable_reason(self, obj):
        if not self._can_purchase():
            return "EXTRA_CREDIT_PURCHASE_NOT_ALLOWED"

        if not obj.stripe_ready_for_checkout:
            return "PACKAGE_NOT_READY"

        if obj.credits > self._remaining():
            return "EXTRA_CREDIT_LIMIT_EXCEEDED"

        return ""

    def get_pending_purchase(self, obj):
        purchase = (
            self.context
            .get(
                "pending_purchases_by_package",
                {},
            )
            .get(obj.pk)
        )

        if not purchase:
            return None

        return {
            "id": str(purchase.pk),
            "status": purchase.status,
            "checkout_session_id": (
                purchase.stripe_checkout_session_id
            ),
            "checkout_url": purchase.stripe_checkout_url,
            "expires_at": purchase.expires_at,
            "credits_snapshot": purchase.credits_snapshot,
        }


class CreditCheckoutSerializer(
    serializers.Serializer
):
    package_id = serializers.UUIDField()

    def validate_package_id(
        self,
        value,
    ):
        try:
            package = CreditPackage.objects.get(
                pk=value,
                is_active=True,
            )

        except CreditPackage.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Pacote indisponível para pagamento no momento."
            ) from exc

        if not package.stripe_ready_for_checkout:
            raise serializers.ValidationError(
                "Pacote indisponível para pagamento no momento."
            )

        self.context["package"] = package

        return value


class CreditPurchaseSerializer(
    serializers.ModelSerializer
):
    package_name = serializers.CharField(
        source="package.name",
        read_only=True,
    )

    class Meta:
        model = CreditPurchase
        fields = [
            "id",
            "package_name",
            "status",
            "credits_snapshot",
            "price_snapshot",
            "currency_snapshot",
            "stripe_checkout_session_id",
            "cycle_start",
            "cycle_end",
            "paid_at",
            "created_at",
            "updated_at",
        ]
