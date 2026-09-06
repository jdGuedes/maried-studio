from rest_framework import serializers

from apps.audit.models import AuditLog
from apps.billing.services import BillingAccessService
from apps.accounts.models import User
from apps.billing.models import (
    CreditPackage,
    CreditPurchase,
    PaymentDispute,
    Plan,
    Subscription,
)
from apps.products.models import Product
from apps.credits.models import CreditWallet
from apps.organizations.models import Organization
from apps.studio.models import Generation, GenerationMode, SceneTemplate


class SuperAdminOrganizationSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "is_active", "users_count",
            "stripe_customer_id", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "users_count", "stripe_customer_id",
            "created_at", "updated_at",
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
    stripe_ready_for_checkout = serializers.BooleanField(
        read_only=True,
    )
    stripe_sync_status = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "description", "price",
            "billing_cycle", "credits_per_cycle",
            "extra_credit_limit_per_cycle", "is_active",
            "sort_order", "stripe_product_id", "stripe_price_id",
            "stripe_synced_at", "stripe_sync_error",
            "stripe_ready_for_checkout", "stripe_sync_status",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "stripe_product_id", "stripe_price_id",
            "stripe_synced_at", "stripe_sync_error",
            "stripe_ready_for_checkout", "stripe_sync_status",
            "created_at", "updated_at",
        ]

    def get_stripe_sync_status(self, obj):
        if obj.stripe_sync_error:
            return "ERROR"

        if (
            obj.stripe_product_id
            and obj.stripe_price_id
        ):
            return "SYNCED"

        return "PENDING"


class SuperAdminSubscriptionSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )
    operational_status = serializers.SerializerMethodField()
    grace_until = serializers.SerializerMethodField()
    days_remaining_in_grace = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id", "organization", "organization_name", "plan",
            "plan_name", "status", "price_snapshot", "credits_snapshot",
            "started_at", "current_period_start", "current_period_end",
            "next_billing_at", "cancel_at_period_end", "canceled_at",
            "stripe_customer_id", "stripe_subscription_id",
            "stripe_price_id", "stripe_status",
            "last_processed_stripe_invoice_id",
            "operational_status", "grace_until",
            "days_remaining_in_grace",
            "created_at", "updated_at",
        ]

    def _access(self, obj):
        access = getattr(
            obj,
            "_superadmin_access",
            None,
        )

        if access is None:
            access = BillingAccessService.evaluate_subscription(
                obj
            )
            obj._superadmin_access = access

        return access

    def get_operational_status(self, obj):
        return self._access(obj).status

    def get_grace_until(self, obj):
        return self._access(obj).grace_until

    def get_days_remaining_in_grace(self, obj):
        return self._access(obj).days_remaining_in_grace


class SuperAdminClientCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=160,
        trim_whitespace=True,
    )
    email = serializers.EmailField()
    initial_password = serializers.CharField(
        min_length=8,
        max_length=128,
        write_only=True,
    )
    plan_id = serializers.UUIDField()

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Informe um nome válido."
            )

        return value.strip()

    def validate_email(self, value):
        email = User.objects.normalize_email(
            value
        )

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise serializers.ValidationError(
                "Já existe usuário com este e-mail."
            )

        return email

    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(
                pk=value,
                is_active=True,
            )

        except Plan.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Selecione um plano ativo."
            ) from exc

        self.context["plan"] = plan

        return value


class SuperAdminSubscriptionActionSerializer(
    serializers.Serializer
):
    plan_id = serializers.UUIDField()

    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(
                pk=value,
                is_active=True,
            )

        except Plan.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Selecione um plano ativo."
            ) from exc

        self.context["plan"] = plan

        return value


class SuperAdminAuditLogSerializer(
    serializers.ModelSerializer
):
    actor_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "entity_type",
            "entity_id",
            "actor_email",
            "organization",
            "organization_name",
            "metadata",
            "created_at",
        ]


class SuperAdminClientListSerializer(
    serializers.ModelSerializer
):
    user = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    operational_status = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "user",
            "subscription",
            "wallet",
            "operational_status",
            "created_at",
        ]

    def get_user(self, obj):
        user = (
            obj.users
            .filter(
                is_superuser=False
            )
            .order_by(
                "date_joined"
            )
            .first()
        )

        if not user:
            return None

        return {
            "id": user.pk,
            "name": user.name,
            "email": user.email,
            "is_active": user.is_active,
        }

    def get_subscription(self, obj):
        subscription = getattr(
            obj,
            "subscription",
            None,
        )

        if not subscription:
            return None

        return {
            "id": str(subscription.pk),
            "plan": str(subscription.plan_id),
            "plan_name": subscription.plan.name,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
        }

    def get_wallet(self, obj):
        wallet = getattr(
            obj,
            "credit_wallet",
            None,
        )

        if not wallet:
            return None

        return {
            "id": str(wallet.pk),
            "available_balance": wallet.available_balance,
            "plan_balance": wallet.plan_balance,
            "purchased_balance": wallet.purchased_balance,
            "reserved_balance": wallet.reserved_balance,
        }

    def get_operational_status(self, obj):
        access = BillingAccessService.evaluate_organization(
            obj
        )

        return access.status


class SuperAdminClientDetailSerializer(
    serializers.ModelSerializer
):
    user = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    wallet = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    audit_logs = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "stripe_customer_id",
            "created_at",
            "updated_at",
            "user",
            "subscription",
            "wallet",
            "usage",
            "audit_logs",
        ]

    def get_user(self, obj):
        user = (
            obj.users
            .filter(
                is_superuser=False
            )
            .order_by(
                "date_joined"
            )
            .first()
        )

        if not user:
            return None

        return SuperAdminUserSerializer(
            user
        ).data

    def get_subscription(self, obj):
        subscription = getattr(
            obj,
            "subscription",
            None,
        )

        access = BillingAccessService.evaluate_subscription(
            subscription
        )

        if not subscription:
            return {
                "operational_status": access.status,
                "grace_until": access.grace_until,
                "days_remaining_in_grace": (
                    access.days_remaining_in_grace
                ),
            }

        data = SuperAdminSubscriptionSerializer(
            subscription
        ).data

        data["operational_status"] = access.status
        data["grace_until"] = access.grace_until
        data["days_remaining_in_grace"] = (
            access.days_remaining_in_grace
        )

        return data

    def get_wallet(self, obj):
        wallet, _created = CreditWallet.objects.get_or_create(
            organization=obj
        )

        return SuperAdminCreditWalletSerializer(
            wallet
        ).data

    def get_usage(self, obj):
        return {
            "products_count": Product.objects.filter(
                organization=obj
            ).count(),
            "generations_count": Generation.objects.filter(
                organization=obj
            ).count(),
        }

    def get_audit_logs(self, obj):
        from apps.audit.models import AuditLog

        logs = (
            AuditLog.objects
            .filter(
                organization=obj
            )
            .select_related(
                "user"
            )
            .order_by(
                "-created_at"
            )[:10]
        )

        return SuperAdminAuditLogSerializer(
            logs,
            many=True,
        ).data


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


class SuperAdminCreditPackageSerializer(serializers.ModelSerializer):
    stripe_ready_for_checkout = serializers.BooleanField(
        read_only=True,
    )
    stripe_sync_status = serializers.SerializerMethodField()

    class Meta:
        model = CreditPackage
        fields = [
            "id", "name", "slug", "description", "credits",
            "price", "currency", "is_active", "sort_order",
            "stripe_product_id", "stripe_price_id",
            "stripe_synced_at", "stripe_sync_error",
            "stripe_ready_for_checkout", "stripe_sync_status",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "stripe_product_id", "stripe_price_id",
            "stripe_synced_at", "stripe_sync_error",
            "stripe_ready_for_checkout", "stripe_sync_status",
            "created_at", "updated_at",
        ]

    def get_stripe_sync_status(self, obj):
        if obj.stripe_sync_error:
            return "ERROR"

        if (
            obj.stripe_product_id
            and obj.stripe_price_id
        ):
            return "SYNCED"

        return "PENDING"


class SuperAdminCreditPurchaseSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    package_name = serializers.CharField(
        source="package.name",
        read_only=True,
    )
    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )

    class Meta:
        model = CreditPurchase
        fields = [
            "id", "organization", "organization_name",
            "package", "package_name", "subscription", "plan",
            "plan_name", "status", "credits_snapshot",
            "price_snapshot", "currency_snapshot",
            "stripe_price_id_snapshot",
            "extra_credit_limit_snapshot",
            "cycle_start", "cycle_end",
            "stripe_customer_id",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "expires_at", "paid_at",
            "processed_event_id",
            "created_at", "updated_at",
        ]


class SuperAdminPaymentDisputeSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    subscription_id = serializers.UUIDField(
        source="related_subscription_id",
        read_only=True,
    )
    credit_purchase_id = serializers.UUIDField(
        source="related_credit_purchase_id",
        read_only=True,
    )
    is_blocking = serializers.BooleanField(
        read_only=True,
    )
    stripe_dispute_reference = serializers.SerializerMethodField()

    class Meta:
        model = PaymentDispute
        fields = [
            "id",
            "organization",
            "organization_name",
            "stripe_dispute_reference",
            "stripe_payment_intent_id",
            "stripe_charge_id",
            "stripe_customer_id",
            "subscription_id",
            "credit_purchase_id",
            "origin_type",
            "amount",
            "currency",
            "status",
            "reason",
            "evidence_due_by",
            "resolved_at",
            "is_blocking",
            "created_at",
            "updated_at",
        ]

    def get_stripe_dispute_reference(self, obj):
        if not obj.stripe_dispute_id:
            return ""

        return obj.stripe_dispute_id[-8:]


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
            "retry_count", "error_code", "error_message",
            "created_at", "started_at",
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
