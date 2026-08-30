from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.accounts.models import UserRole
from apps.billing.models import Plan, Subscription
from apps.billing.services import (
    BillingAccessService,
    BillingError,
    SubscriptionAccessStatus,
    SubscriptionService,
)
from apps.credits.models import CreditWallet
from apps.credits.services import CreditService
from apps.organizations.models import Organization
from apps.studio.models import (
    Generation,
    GenerationMode,
    GenerationStatus,
    SceneTemplate,
)

from .permissions import IsSuperAdmin
from .serializers import (
    CreditAdjustmentSerializer,
    SuperAdminAuditLogSerializer,
    SuperAdminClientCreateSerializer,
    SuperAdminClientDetailSerializer,
    SuperAdminClientListSerializer,
    SuperAdminCreditWalletSerializer,
    SuperAdminGenerationSerializer,
    SuperAdminOrganizationSerializer,
    SuperAdminOrganizationUpdateSerializer,
    SuperAdminPlanSerializer,
    SuperAdminSceneTemplateSerializer,
    SuperAdminSubscriptionSerializer,
    SuperAdminSubscriptionActionSerializer,
    SuperAdminUserSerializer,
    SuperAdminUserUpdateSerializer,
)


def _audit(
    *,
    request,
    action,
    entity,
    organization=None,
    metadata=None,
):
    AuditLog.objects.create(
        organization=organization,
        user=request.user,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=str(entity.pk),
        metadata=metadata or {},
    )


def _unique_organization_slug(name):
    base = slugify(
        name
    ) or "cliente"

    candidate = base
    suffix = 2

    while Organization.objects.filter(
        slug=candidate
    ).exists():
        candidate = (
            f"{base}-{suffix}"
        )
        suffix += 1

    return candidate


class SuperAdminSummaryView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        subscription_statuses = {
            SubscriptionAccessStatus.ACTIVE: 0,
            SubscriptionAccessStatus.GRACE: 0,
            SubscriptionAccessStatus.BLOCKED: 0,
        }

        for subscription in (
            Subscription.objects
            .select_related(
                "organization",
                "plan",
            )
            .all()
        ):
            access = (
                BillingAccessService
                .evaluate_subscription(
                    subscription
                )
            )
            subscription_statuses[access.status] += 1

        return Response(
            {
                "organizations": Organization.objects.count(),
                "active_organizations": Organization.objects.filter(
                    is_active=True
                ).count(),
                "users": get_user_model().objects.count(),
                "plans": Plan.objects.count(),
                "subscriptions": Subscription.objects.count(),
                "operational_active_subscriptions": (
                    subscription_statuses[
                        SubscriptionAccessStatus.ACTIVE
                    ]
                ),
                "operational_grace_subscriptions": (
                    subscription_statuses[
                        SubscriptionAccessStatus.GRACE
                    ]
                ),
                "operational_blocked_subscriptions": (
                    subscription_statuses[
                        SubscriptionAccessStatus.BLOCKED
                    ]
                ),
                "credit_wallets": CreditWallet.objects.count(),
                "generations": Generation.objects.count(),
                "failed_generations": Generation.objects.filter(
                    status=GenerationStatus.FAILED
                ).count(),
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminAuditLogListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminAuditLogSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            AuditLog.objects
            .select_related(
                "organization",
                "user",
            )
            .order_by(
                "-created_at"
            )
        )


class SuperAdminClientListCreateView(
    generics.ListCreateAPIView
):
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            Organization.objects
            .select_related(
                "credit_wallet",
                "subscription__plan",
            )
            .prefetch_related(
                "users"
            )
            .order_by(
                "name"
            )
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SuperAdminClientCreateSerializer

        return SuperAdminClientListSerializer

    def create(self, request, *args, **kwargs):
        serializer = SuperAdminClientCreateSerializer(
            data=request.data,
            context={},
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data
        plan = serializer.context["plan"]
        User = get_user_model()

        try:
            with transaction.atomic():
                organization = Organization.objects.create(
                    name=data["name"],
                    slug=_unique_organization_slug(
                        data["name"]
                    ),
                    is_active=True,
                )

                user = User.objects.create_user(
                    email=data["email"],
                    password=data["initial_password"],
                    name=data["name"],
                    organization=organization,
                    role=UserRole.OWNER,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )

                CreditWallet.objects.get_or_create(
                    organization=organization
                )

                subscription = SubscriptionService.activate(
                    organization=organization,
                    plan=plan,
                    actor=request.user,
                )

                _audit(
                    request=request,
                    action="SUPERADMIN_CLIENT_CREATED",
                    entity=organization,
                    organization=organization,
                    metadata={
                        "organization_id": str(
                            organization.pk
                        ),
                        "user_id": user.pk,
                        "plan_id": str(
                            plan.pk
                        ),
                        "subscription_id": str(
                            subscription.pk
                        ),
                    },
                )

        except BillingError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SuperAdminClientDetailSerializer(
                organization,
                context={
                    "request": request,
                },
            ).data,
            status=status.HTTP_201_CREATED,
        )


class SuperAdminClientDetailView(
    generics.RetrieveAPIView
):
    serializer_class = SuperAdminClientDetailSerializer
    permission_classes = [IsSuperAdmin]

    queryset = (
        Organization.objects
        .select_related(
            "credit_wallet",
            "subscription__plan",
        )
        .prefetch_related(
            "users"
        )
    )


class SuperAdminClientActivateSubscriptionView(
    APIView
):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        organization = get_object_or_404(
            Organization,
            pk=pk,
        )

        serializer = SuperAdminSubscriptionActionSerializer(
            data=request.data,
            context={},
        )
        serializer.is_valid(
            raise_exception=True
        )

        plan = serializer.context["plan"]

        try:
            subscription = SubscriptionService.activate(
                organization=organization,
                plan=plan,
                actor=request.user,
            )

        except BillingError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        _audit(
            request=request,
            action="SUPERADMIN_SUBSCRIPTION_ACTIVATED",
            entity=subscription,
            organization=organization,
            metadata={
                "plan_id": str(
                    plan.pk
                ),
            },
        )

        organization.refresh_from_db()

        return Response(
            SuperAdminClientDetailSerializer(
                organization,
                context={
                    "request": request,
                },
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminSubscriptionRenewView(
    APIView
):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        subscription = get_object_or_404(
            Subscription.objects.select_related(
                "organization",
                "plan",
            ),
            pk=pk,
        )

        try:
            subscription = (
                SubscriptionService.renew_current_cycle(
                    subscription=subscription,
                    actor=request.user,
                )
            )

        except BillingError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        _audit(
            request=request,
            action="SUPERADMIN_SUBSCRIPTION_RENEWED",
            entity=subscription,
            organization=subscription.organization,
            metadata={
                "plan_id": str(
                    subscription.plan_id
                ),
                "operational_status": (
                    BillingAccessService
                    .evaluate_subscription(
                        subscription
                    )
                    .status
                ),
            },
        )

        return Response(
            SuperAdminSubscriptionSerializer(
                subscription
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminOrganizationListView(generics.ListAPIView):
    serializer_class = SuperAdminOrganizationSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            Organization.objects
            .annotate(users_count=Count("users"))
            .order_by("name")
        )


class SuperAdminOrganizationDetailView(
    generics.RetrieveUpdateAPIView
):
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Organization.objects.annotate(
            users_count=Count("users")
        )

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return SuperAdminOrganizationUpdateSerializer
        return SuperAdminOrganizationSerializer

    def patch(self, request, *args, **kwargs):
        organization = self.get_object()

        before = {
            "name": organization.name,
            "is_active": organization.is_active,
        }

        serializer = SuperAdminOrganizationUpdateSerializer(
            organization,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        organization.refresh_from_db()

        after = {
            "name": organization.name,
            "is_active": organization.is_active,
        }

        action = (
            "SUPERADMIN_ORGANIZATION_STATUS_CHANGED"
            if before["is_active"] != after["is_active"]
            else "SUPERADMIN_ORGANIZATION_UPDATED"
        )

        _audit(
            request=request,
            action=action,
            entity=organization,
            organization=organization,
            metadata={
                "before": before,
                "after": after,
            },
        )

        return Response(
            SuperAdminOrganizationSerializer(
                organization,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminUserListView(generics.ListAPIView):
    serializer_class = SuperAdminUserSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            get_user_model()
            .objects
            .select_related("organization")
            .order_by("email")
        )


class SuperAdminUserDetailView(
    generics.RetrieveUpdateAPIView
):
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    queryset = (
        get_user_model()
        .objects
        .select_related("organization")
    )

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return SuperAdminUserUpdateSerializer
        return SuperAdminUserSerializer

    def patch(self, request, *args, **kwargs):
        user = self.get_object()

        before = {
            "name": user.name,
            "is_active": user.is_active,
        }

        serializer = SuperAdminUserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user.refresh_from_db()

        after = {
            "name": user.name,
            "is_active": user.is_active,
        }

        action = (
            "SUPERADMIN_USER_STATUS_CHANGED"
            if before["is_active"] != after["is_active"]
            else "SUPERADMIN_USER_UPDATED"
        )

        _audit(
            request=request,
            action=action,
            entity=user,
            organization=user.organization,
            metadata={
                "before": before,
                "after": after,
            },
        )

        return Response(
            SuperAdminUserSerializer(
                user,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminPlanListView(
    generics.ListCreateAPIView
):
    serializer_class = SuperAdminPlanSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return Plan.objects.order_by(
            "sort_order",
            "price",
        )

    def perform_create(self, serializer):
        plan = serializer.save()

        _audit(
            request=self.request,
            action="SUPERADMIN_PLAN_CREATED",
            entity=plan,
            metadata={
                "name": plan.name,
                "slug": plan.slug,
                "price": str(plan.price),
                "credits_per_cycle": plan.credits_per_cycle,
                "is_active": plan.is_active,
            },
        )


class SuperAdminPlanDetailView(
    generics.RetrieveUpdateAPIView
):
    serializer_class = SuperAdminPlanSerializer
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = Plan.objects.all()

    def patch(self, request, *args, **kwargs):
        plan = self.get_object()

        before = {
            "name": plan.name,
            "slug": plan.slug,
            "price": str(plan.price),
            "credits_per_cycle": plan.credits_per_cycle,
            "is_active": plan.is_active,
            "sort_order": plan.sort_order,
        }

        serializer = SuperAdminPlanSerializer(
            plan,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        plan.refresh_from_db()

        after = {
            "name": plan.name,
            "slug": plan.slug,
            "price": str(plan.price),
            "credits_per_cycle": plan.credits_per_cycle,
            "is_active": plan.is_active,
            "sort_order": plan.sort_order,
        }

        _audit(
            request=request,
            action="SUPERADMIN_PLAN_UPDATED",
            entity=plan,
            metadata={
                "before": before,
                "after": after,
            },
        )

        return Response(
            SuperAdminPlanSerializer(
                plan,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminSubscriptionListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminSubscriptionSerializer
    permission_classes = [IsSuperAdmin]

    queryset = (
        Subscription.objects
        .select_related("organization", "plan")
        .order_by("organization__name")
    )


class SuperAdminSubscriptionDetailView(
    generics.RetrieveAPIView
):
    serializer_class = SuperAdminSubscriptionSerializer
    permission_classes = [IsSuperAdmin]

    queryset = Subscription.objects.select_related(
        "organization",
        "plan",
    )


class SuperAdminCreditWalletListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminCreditWalletSerializer
    permission_classes = [IsSuperAdmin]

    queryset = (
        CreditWallet.objects
        .select_related("organization")
        .order_by("organization__name")
    )


class SuperAdminGenerationListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminGenerationSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        queryset = (
            Generation.objects
            .select_related(
                "organization",
                "user",
                "product",
            )
            .order_by("-created_at")
        )

        status_filter = self.request.query_params.get(
            "status"
        )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        return queryset


class SuperAdminGenerationDetailView(
    generics.RetrieveAPIView
):
    serializer_class = SuperAdminGenerationSerializer
    permission_classes = [IsSuperAdmin]

    queryset = Generation.objects.select_related(
        "organization",
        "user",
        "product",
    )


class SuperAdminSceneTemplateListCreateView(
    generics.ListCreateAPIView
):
    serializer_class = SuperAdminSceneTemplateSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        queryset = (
            SceneTemplate.objects
            .filter(
                generation_mode=GenerationMode.INSTAGRAM
            )
            .order_by(
                "category",
                "sort_order",
                "name",
            )
        )

        category = self.request.query_params.get(
            "category"
        )

        is_active = self.request.query_params.get(
            "is_active"
        )

        if category:
            queryset = queryset.filter(
                category=category
            )

        if is_active in {"true", "false"}:
            queryset = queryset.filter(
                is_active=(is_active == "true")
            )

        return queryset


class SuperAdminSceneTemplateDetailView(
    generics.RetrieveUpdateAPIView
):
    serializer_class = SuperAdminSceneTemplateSerializer
    permission_classes = [IsSuperAdmin]

    queryset = SceneTemplate.objects.filter(
        generation_mode=GenerationMode.INSTAGRAM
    )


class CreditAdjustmentView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = CreditAdjustmentSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        organization = get_object_or_404(
            Organization,
            pk=data["organization_id"],
        )

        wallet, _ = CreditWallet.objects.get_or_create(
            organization=organization
        )

        try:
            wallet = CreditService.adjust_credits(
                wallet,
                data["amount"],
                balance_type=data["balance_type"],
                actor=request.user,
                reason=data["reason"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _audit(
            request=request,
            action="SUPERADMIN_CREDIT_ADJUSTMENT",
            entity=wallet,
            organization=organization,
            metadata={
                "amount": data["amount"],
                "balance_type": data["balance_type"],
                "reason": data["reason"],
            },
        )

        return Response(
            SuperAdminCreditWalletSerializer(
                wallet
            ).data,
            status=status.HTTP_200_OK,
        )
