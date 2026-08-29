from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.billing.models import Plan, Subscription
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
    SuperAdminCreditWalletSerializer,
    SuperAdminGenerationSerializer,
    SuperAdminOrganizationSerializer,
    SuperAdminOrganizationUpdateSerializer,
    SuperAdminPlanSerializer,
    SuperAdminSceneTemplateSerializer,
    SuperAdminSubscriptionSerializer,
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


class SuperAdminSummaryView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(
            {
                "organizations": Organization.objects.count(),
                "active_organizations": Organization.objects.filter(
                    is_active=True
                ).count(),
                "users": get_user_model().objects.count(),
                "plans": Plan.objects.count(),
                "subscriptions": Subscription.objects.count(),
                "credit_wallets": CreditWallet.objects.count(),
                "generations": Generation.objects.count(),
                "failed_generations": Generation.objects.filter(
                    status=GenerationStatus.FAILED
                ).count(),
            },
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
