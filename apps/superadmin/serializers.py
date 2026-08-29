from rest_framework import serializers

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.credits.models import CreditWallet
from apps.organizations.models import Organization
from apps.studio.models import Generation, GenerationMode, SceneTemplate


class SuperAdminOrganizationSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "is_active", "users_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "users_count", "created_at", "updated_at",
        ]


class SuperAdminOrganizationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["name", "is_active"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe um nome válido.")
        return value


class SuperAdminUserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "name", "role", "role_label",
            "organization", "organization_name", "is_active",
            "is_staff", "is_superuser", "date_joined",
        ]


class SuperAdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "is_active"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe um nome válido.")
        return value


class SuperAdminPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "description", "price",
            "billing_cycle", "credits_per_cycle", "is_active",
            "sort_order", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SuperAdminSubscriptionSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )

    class Meta:
        model = Subscription
        fields = [
            "id", "organization", "organization_name", "plan",
            "plan_name", "status", "price_snapshot", "credits_snapshot",
            "started_at", "current_period_start", "current_period_end",
            "next_billing_at", "cancel_at_period_end", "canceled_at",
            "created_at", "updated_at",
        ]


class SuperAdminCreditWalletSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    available_balance = serializers.IntegerField(read_only=True)
    total_balance = serializers.IntegerField(read_only=True)

    class Meta:
        model = CreditWallet
        fields = [
            "id", "organization", "organization_name", "balance",
            "reserved_balance", "plan_balance", "purchased_balance",
            "plan_reserved_balance", "purchased_reserved_balance",
            "available_balance", "total_balance", "created_at",
            "updated_at",
        ]


class SuperAdminGenerationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Generation
        fields = [
            "id", "organization", "organization_name", "user",
            "user_email", "product", "product_name", "mode", "status",
            "failure_type", "provider", "model", "credit_cost",
            "error_code", "error_message", "created_at", "started_at",
            "completed_at",
        ]


class SuperAdminSceneTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneTemplate
        fields = [
            "id", "name", "slug", "generation_mode", "category",
            "preview_image", "prompt_template", "version", "is_active",
            "sort_order", "created_at", "updated_at",
        ]

    def validate_generation_mode(self, value):
        if value != GenerationMode.INSTAGRAM:
            raise serializers.ValidationError(
                "SceneTemplate é permitido apenas para Instagramável na V1."
            )
        return value


class CreditAdjustmentSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    amount = serializers.IntegerField()
    balance_type = serializers.ChoiceField(
        choices=["PLAN", "PURCHASED"]
    )
    reason = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
