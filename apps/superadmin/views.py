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
from apps.billing.models import (
    CreditPackage,
    CreditPurchase,
    PaymentDispute,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from apps.billing.services import (
    BillingAccessService,
    BillingError,
    SubscriptionAccessStatus,
    SubscriptionService,
)
from apps.billing.stripe_services import (
    StripeConfigurationError,
    StripeCreditPackageService,
    StripePlanError,
    StripePlanService,
    StripeReconciliationError,
    StripeReconciliationService,
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
    SuperAdminCreditPackageSerializer,
    SuperAdminPaymentDisputeSerializer,
    SuperAdminCreditPurchaseSerializer,
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


def _sync_plan_with_stripe(
    *,
    request,
    plan,
):
    before_price_id = plan.stripe_price_id

    try:
        StripePlanService.sync_plan(
            plan
        )

    except StripeConfigurationError as exc:
        if str(exc).startswith(
            "STRIPE_SECRET_KEY"
        ):
            plan.stripe_sync_error = ""
            plan.save(
                update_fields=[
                    "stripe_sync_error",
                    "updated_at",
                ]
            )

            _audit(
                request=request,
                action="PLAN_STRIPE_SYNC_SKIPPED",
                entity=plan,
                metadata={
                    "plan_id": str(plan.pk),
                    "reason": "STRIPE_NOT_CONFIGURED",
                },
            )

            return None

        plan.mark_stripe_sync_error(
            str(exc)
        )

        _audit(
            request=request,
            action="PLAN_STRIPE_SYNC_FAILED",
            entity=plan,
            metadata={
                "plan_id": str(plan.pk),
                "error_type": exc.__class__.__name__,
            },
        )

        return exc

    except StripePlanError as exc:
        plan.mark_stripe_sync_error(
            str(exc)
        )

        _audit(
            request=request,
            action="PLAN_STRIPE_SYNC_FAILED",
            entity=plan,
            metadata={
                "plan_id": str(plan.pk),
                "error_type": exc.__class__.__name__,
            },
        )

        return exc

    plan.refresh_from_db()

    if (
        before_price_id
        and before_price_id
        != plan.stripe_price_id
    ):
        action = "PLAN_STRIPE_PRICE_VERSIONED"

    else:
        action = "PLAN_STRIPE_SYNCED"

    _audit(
        request=request,
        action=action,
        entity=plan,
        metadata={
            "plan_id": str(plan.pk),
            "stripe_product_id": (
                plan.stripe_product_id
            ),
            "stripe_price_id": (
                plan.stripe_price_id
            ),
        },
    )

    return None


def _sync_credit_package_with_stripe(
    *,
    request,
    package,
):
    before_price_id = package.stripe_price_id

    try:
        StripeCreditPackageService.sync_package(
            package
        )

    except StripePlanError as exc:
        package.mark_stripe_sync_error(
            str(exc)
        )

        _audit(
            request=request,
            action="CREDIT_PACKAGE_STRIPE_SYNC_FAILED",
            entity=package,
            metadata={
                "credit_package_id": str(package.pk),
                "error_type": exc.__class__.__name__,
            },
        )

        return exc

    package.refresh_from_db()

    action = (
        "CREDIT_PACKAGE_STRIPE_PRICE_VERSIONED"
        if before_price_id
        and before_price_id != package.stripe_price_id
        else "CREDIT_PACKAGE_STRIPE_SYNCED"
    )

    _audit(
        request=request,
        action=action,
        entity=package,
        metadata={
            "credit_package_id": str(package.pk),
            "stripe_product_id": package.stripe_product_id,
            "stripe_price_id": package.stripe_price_id,
        },
    )

    return None


class SuperAdminSummaryView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        subscription_statuses = {
            SubscriptionAccessStatus.ACTIVE: 0,
            SubscriptionAccessStatus.GRACE: 0,
            SubscriptionAccessStatus.BLOCKED: 0,
            SubscriptionAccessStatus.FINANCIAL_BLOCK: 0,
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
                "financial_blocked_subscriptions": (
                    subscription_statuses[
                        SubscriptionAccessStatus.FINANCIAL_BLOCK
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

                subscription = SubscriptionService.create_pending(
                    organization=organization,
                    plan=plan,
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
            subscription = SubscriptionService.create_pending(
                organization=organization,
                plan=plan,
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
            action="SUPERADMIN_SUBSCRIPTION_PENDING_CREATED",
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


class SuperAdminClientStripeReconcileView(
    APIView
):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        organization = get_object_or_404(
            Organization,
            pk=pk,
        )

        try:
            result = StripeReconciliationService.reconcile(
                organization=organization,
                actor=request.user,
            )

        except StripeReconciliationError as exc:
            _audit(
                request=request,
                action="STRIPE_RECONCILIATION",
                entity=organization,
                organization=organization,
                metadata={
                    "result": "FAILED",
                    "code": exc.code,
                    "stripe_customer_id": (
                        organization.stripe_customer_id
                    ),
                },
            )

            response_status = (
                status.HTTP_409_CONFLICT
                if exc.code in {
                    "STRIPE_SUBSCRIPTION_AMBIGUOUS",
                    "STRIPE_PAID_INVOICE_NOT_FOUND",
                }
                else status.HTTP_400_BAD_REQUEST
            )

            return Response(
                {
                    "code": exc.code,
                    "detail": exc.detail,
                    "reconciled": False,
                    "applied": False,
                },
                status=response_status,
            )

        organization.refresh_from_db()
        wallet, _ = CreditWallet.objects.get_or_create(
            organization=organization
        )
        subscription = result.subscription
        access = BillingAccessService.evaluate_subscription(
            subscription
        )

        _audit(
            request=request,
            action="STRIPE_RECONCILIATION",
            entity=organization,
            organization=organization,
            metadata={
                "result": "SUCCESS",
                "applied": result.applied,
                "cycle_type": result.cycle_type,
                "stripe_subscription_id": (
                    result.stripe_subscription_id
                ),
                "stripe_invoice_id": (
                    result.stripe_invoice_id
                ),
                "stripe_subscription_status": (
                    result.stripe_subscription_status
                ),
                "disputes_reconciled": result.disputes_reconciled,
                "financial_blocked": result.financial_blocked,
            },
        )

        return Response(
            {
                "reconciled": result.reconciled,
                "applied": result.applied,
                "cycle_type": result.cycle_type,
                "subscription_status": (
                    subscription.status
                    if subscription
                    else None
                ),
                "operational_status": access.status,
                "plan_balance": wallet.plan_balance,
                "purchased_balance": wallet.purchased_balance,
                "stripe_subscription_status": (
                    result.stripe_subscription_status
                ),
                "stripe_invoice_id": result.stripe_invoice_id,
                "stripe_subscription_id": (
                    result.stripe_subscription_id
                ),
                "disputes_reconciled": result.disputes_reconciled,
                "financial_blocked": result.financial_blocked,
            },
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

        access = BillingAccessService.evaluate_subscription(
            subscription
        )

        if subscription.status == SubscriptionStatus.ACTIVE:
            code = "STRIPE_AUTOMATIC_RENEWAL"
            detail = (
                "A renovação é automática pelo Stripe."
            )

        elif subscription.status == SubscriptionStatus.PENDING:
            code = "FIRST_PAYMENT_REQUIRED"
            detail = (
                "O primeiro pagamento deve ser iniciado "
                "pelo Checkout do cliente."
            )

        elif subscription.status == SubscriptionStatus.PAST_DUE:
            code = "STRIPE_REGULARIZATION_REQUIRED"
            detail = (
                "A regularização deve ocorrer pelo Stripe "
                "e somente o webhook confirma o pagamento."
            )

        else:
            code = "SUBSCRIPTION_NOT_RENEWABLE"
            detail = (
                "Esta assinatura não pode ser renovada "
                "por ação local."
            )

        _audit(
            request=request,
            action="SUPERADMIN_SUBSCRIPTION_RENEWAL_NOT_APPLIED",
            entity=subscription,
            organization=subscription.organization,
            metadata={
                "plan_id": str(
                    subscription.plan_id
                ),
                "subscription_status": subscription.status,
                "operational_status": access.status,
                "code": code,
            },
        )

        return Response(
            {
                "code": code,
                "detail": detail,
                "subscription": SuperAdminSubscriptionSerializer(
                    subscription
                ).data,
            },
            status=status.HTTP_409_CONFLICT,
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
                "extra_credit_limit_per_cycle": (
                    plan.extra_credit_limit_per_cycle
                ),
                "is_active": plan.is_active,
            },
        )

        _sync_plan_with_stripe(
            request=self.request,
            plan=plan,
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
            "extra_credit_limit_per_cycle": (
                plan.extra_credit_limit_per_cycle
            ),
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
            "extra_credit_limit_per_cycle": (
                plan.extra_credit_limit_per_cycle
            ),
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

        _sync_plan_with_stripe(
            request=request,
            plan=plan,
        )

        plan.refresh_from_db()

        return Response(
            SuperAdminPlanSerializer(
                plan,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminPlanStripeSyncView(
    APIView
):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        plan = get_object_or_404(
            Plan,
            pk=pk,
        )

        error = _sync_plan_with_stripe(
            request=request,
            plan=plan,
        )

        plan.refresh_from_db()

        response_status = (
            status.HTTP_400_BAD_REQUEST
            if error
            else status.HTTP_200_OK
        )

        return Response(
            SuperAdminPlanSerializer(
                plan,
                context={"request": request},
            ).data,
            status=response_status,
        )


class SuperAdminCreditPackageListView(
    generics.ListCreateAPIView
):
    serializer_class = SuperAdminCreditPackageSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return CreditPackage.objects.order_by(
            "sort_order",
            "price",
        )

    def perform_create(self, serializer):
        package = serializer.save()

        _audit(
            request=self.request,
            action="SUPERADMIN_CREDIT_PACKAGE_CREATED",
            entity=package,
            metadata={
                "name": package.name,
                "slug": package.slug,
                "price": str(package.price),
                "credits": package.credits,
                "is_active": package.is_active,
            },
        )

        _sync_credit_package_with_stripe(
            request=self.request,
            package=package,
        )


class SuperAdminCreditPackageDetailView(
    generics.RetrieveUpdateAPIView
):
    serializer_class = SuperAdminCreditPackageSerializer
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = CreditPackage.objects.all()

    def patch(self, request, *args, **kwargs):
        package = self.get_object()

        before = {
            "name": package.name,
            "slug": package.slug,
            "price": str(package.price),
            "credits": package.credits,
            "currency": package.currency,
            "is_active": package.is_active,
            "sort_order": package.sort_order,
        }

        serializer = SuperAdminCreditPackageSerializer(
            package,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        package.refresh_from_db()

        after = {
            "name": package.name,
            "slug": package.slug,
            "price": str(package.price),
            "credits": package.credits,
            "currency": package.currency,
            "is_active": package.is_active,
            "sort_order": package.sort_order,
        }

        _audit(
            request=request,
            action="SUPERADMIN_CREDIT_PACKAGE_UPDATED",
            entity=package,
            metadata={
                "before": before,
                "after": after,
            },
        )

        _sync_credit_package_with_stripe(
            request=request,
            package=package,
        )

        package.refresh_from_db()

        return Response(
            SuperAdminCreditPackageSerializer(
                package,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


class SuperAdminCreditPackageStripeSyncView(
    APIView
):
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        package = get_object_or_404(
            CreditPackage,
            pk=pk,
        )

        error = _sync_credit_package_with_stripe(
            request=request,
            package=package,
        )

        package.refresh_from_db()

        response_status = (
            status.HTTP_400_BAD_REQUEST
            if error
            else status.HTTP_200_OK
        )

        return Response(
            SuperAdminCreditPackageSerializer(
                package,
                context={"request": request},
            ).data,
            status=response_status,
        )


class SuperAdminCreditPurchaseListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminCreditPurchaseSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            CreditPurchase.objects
            .select_related(
                "organization",
                "package",
                "subscription",
                "plan",
            )
            .order_by("-created_at")
        )


class SuperAdminPaymentDisputeListView(
    generics.ListAPIView
):
    serializer_class = SuperAdminPaymentDisputeSerializer
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return (
            PaymentDispute.objects
            .select_related(
                "organization",
                "related_subscription",
                "related_credit_purchase",
            )
            .order_by("-created_at")
        )


class SuperAdminPaymentDisputeDetailView(
    generics.RetrieveAPIView
):
    serializer_class = SuperAdminPaymentDisputeSerializer
    permission_classes = [IsSuperAdmin]

    queryset = (
        PaymentDispute.objects
        .select_related(
            "organization",
            "related_subscription",
            "related_credit_purchase",
        )
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
