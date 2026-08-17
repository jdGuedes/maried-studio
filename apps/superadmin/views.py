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
    SuperAdminPlanSerializer,
    SuperAdminSceneTemplateSerializer,
    SuperAdminSubscriptionSerializer,
    SuperAdminUserSerializer,
)


class SuperAdminSummaryView(
    APIView
):
    permission_classes = [
        IsSuperAdmin,
    ]

    def get(
        self,
        request,
    ):
        return Response(
            {
                "organizations": (
                    Organization.objects.count()
                ),
                "active_organizations": (
                    Organization.objects
                    .filter(
                        is_active=True
                    )
                    .count()
                ),
                "users": (
                    get_user_model()
                    .objects
                    .count()
                ),
                "plans": (
                    Plan.objects.count()
                ),
                "subscriptions": (
                    Subscription.objects.count()
                ),
                "credit_wallets": (
                    CreditWallet.objects.count()
                ),
                "generations": (
                    Generation.objects.count()
                ),
                "failed_generations": (
                    Generation.objects
                    .filter(
                        status=GenerationStatus.FAILED
                    )
                    .count()
                ),
            },
            status=status.HTTP_200_OK,
        )


class SuperAdminOrganizationListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminOrganizationSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    def get_queryset(
        self,
    ):
        return (
            Organization.objects
            .annotate(
                users_count=Count(
                    "users"
                )
            )
            .order_by(
                "name"
            )
        )


class SuperAdminUserListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminUserSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    def get_queryset(
        self,
    ):
        return (
            get_user_model()
            .objects
            .select_related(
                "organization"
            )
            .order_by(
                "email"
            )
        )


class SuperAdminPlanListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminPlanSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    queryset = (
        Plan.objects
        .order_by(
            "sort_order",
            "price",
        )
    )


class SuperAdminSubscriptionListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminSubscriptionSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    queryset = (
        Subscription.objects
        .select_related(
            "organization",
            "plan",
        )
        .order_by(
            "organization__name"
        )
    )


class SuperAdminCreditWalletListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminCreditWalletSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    queryset = (
        CreditWallet.objects
        .select_related(
            "organization"
        )
        .order_by(
            "organization__name"
        )
    )


class SuperAdminGenerationListView(
    generics.ListAPIView
):
    serializer_class = (
        SuperAdminGenerationSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    def get_queryset(
        self,
    ):
        queryset = (
            Generation.objects
            .select_related(
                "organization",
                "user",
                "product",
            )
            .order_by(
                "-created_at"
            )
        )

        status_filter = (
            self.request
            .query_params
            .get(
                "status"
            )
        )

        if status_filter:
            queryset = (
                queryset.filter(
                    status=status_filter
                )
            )

        return queryset


class SuperAdminSceneTemplateListCreateView(
    generics.ListCreateAPIView
):
    serializer_class = (
        SuperAdminSceneTemplateSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    def get_queryset(
        self,
    ):
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

        category = (
            self.request
            .query_params
            .get(
                "category"
            )
        )

        is_active = (
            self.request
            .query_params
            .get(
                "is_active"
            )
        )

        if category:
            queryset = (
                queryset.filter(
                    category=category
                )
            )

        if is_active in {
            "true",
            "false",
        }:
            queryset = (
                queryset.filter(
                    is_active=(
                        is_active == "true"
                    )
                )
            )

        return queryset


class SuperAdminSceneTemplateDetailView(
    generics.RetrieveUpdateAPIView
):
    serializer_class = (
        SuperAdminSceneTemplateSerializer
    )

    permission_classes = [
        IsSuperAdmin,
    ]

    queryset = (
        SceneTemplate.objects
        .filter(
            generation_mode=GenerationMode.INSTAGRAM
        )
    )


class CreditAdjustmentView(
    APIView
):
    permission_classes = [
        IsSuperAdmin,
    ]

    def post(
        self,
        request,
    ):
        serializer = (
            CreditAdjustmentSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = (
            serializer.validated_data
        )

        organization = get_object_or_404(
            Organization,
            pk=data[
                "organization_id"
            ],
        )

        wallet, _ = (
            CreditWallet.objects
            .get_or_create(
                organization=organization
            )
        )

        try:
            wallet = (
                CreditService
                .adjust_credits(
                    wallet,
                    data["amount"],
                    balance_type=(
                        data["balance_type"]
                    ),
                    actor=request.user,
                    reason=data["reason"],
                )
            )

        except ValueError as exc:
            return Response(
                {
                    "detail": str(
                        exc
                    )
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        AuditLog.objects.create(
            organization=organization,
            user=request.user,
            action=(
                "SUPERADMIN_CREDIT_ADJUSTMENT"
            ),
            entity_type=(
                "CreditWallet"
            ),
            entity_id=str(
                wallet.id
            ),
            metadata={
                "amount": data[
                    "amount"
                ],
                "balance_type": data[
                    "balance_type"
                ],
                "reason": data[
                    "reason"
                ],
            },
        )

        output = (
            SuperAdminCreditWalletSerializer(
                wallet
            )
        )

        return Response(
            output.data,
            status=status.HTTP_200_OK,
        )
