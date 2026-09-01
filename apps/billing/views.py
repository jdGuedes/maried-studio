import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan
from .serializers import (
    AvailablePlanSerializer,
    CurrentSubscriptionSerializer,
    SubscriptionCheckoutSerializer,
)
from .services import BillingAccessService
from .stripe_services import (
    StripeBillingError,
    StripeBillingService,
    StripeCheckoutProviderError,
    StripeCheckoutRetryRequiredError,
    StripeCheckoutUnavailableError,
    StripeConfigurationError,
    StripeSubscriptionAlreadyActiveError,
    StripeWebhookService,
)


logger = logging.getLogger(__name__)


class AvailablePlanListView(
    generics.ListAPIView
):
    serializer_class = AvailablePlanSerializer
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        return (
            Plan.objects
            .filter(
                is_active=True,
                stripe_product_id__isnull=False,
                stripe_price_id__isnull=False,
                stripe_sync_error="",
            )
            .exclude(
                stripe_product_id="",
            )
            .exclude(
                stripe_price_id="",
            )
            .order_by(
                "sort_order",
                "price",
            )
        )


class CurrentSubscriptionView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(self, request):
        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if not organization:
            return Response(
                {
                    "detail": (
                        "Usuário não possui organização vinculada."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        access = BillingAccessService.evaluate_organization(
            organization
        )

        serializer = CurrentSubscriptionSerializer.from_access(
            access
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SubscriptionCheckoutView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        serializer = SubscriptionCheckoutSerializer(
            data=request.data,
            context={},
        )
        serializer.is_valid(
            raise_exception=True
        )

        plan = serializer.context["plan"]

        try:
            checkout = (
                StripeBillingService
                .create_subscription_checkout(
                    user=request.user,
                    plan=plan,
                )
            )

        except (
            StripeCheckoutUnavailableError,
            StripeSubscriptionAlreadyActiveError,
        ) as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except StripeConfigurationError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except StripeCheckoutRetryRequiredError:
            return Response(
                {
                    "detail": (
                        "Não foi possível iniciar o pagamento. Tente novamente."
                    ),
                    "code": "CHECKOUT_RETRY_REQUIRED",
                },
                status=status.HTTP_409_CONFLICT,
            )

        except StripeCheckoutProviderError:
            return Response(
                {
                    "detail": (
                        "Não foi possível iniciar o pagamento. Tente novamente."
                    ),
                    "code": "CHECKOUT_UNAVAILABLE",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except StripeBillingError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            checkout,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(
    csrf_exempt,
    name="dispatch",
)
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(
        self,
        request,
    ):
        signature = request.headers.get(
            "Stripe-Signature",
            "",
        )

        if not signature:
            return Response(
                {
                    "detail": "Assinatura Stripe ausente.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = StripeWebhookService.construct_event(
                payload=request.body,
                signature=signature,
            )

        except StripeConfigurationError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception:
            return Response(
                {
                    "detail": "Assinatura Stripe inválida.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = StripeWebhookService.process_event(
                event
            )

        except Exception as exc:
            event_id = (
                event.get("id")
                if isinstance(event, dict)
                else getattr(event, "id", "")
            )
            event_type = (
                event.get("type")
                if isinstance(event, dict)
                else getattr(event, "type", "")
            )
            logger.exception(
                "Stripe webhook processing failed",
                extra={
                    "stripe_event_id": event_id,
                    "stripe_event_type": event_type,
                    "exception_class": (
                        exc.__class__.__name__
                    ),
                },
            )
            return Response(
                {
                    "detail": (
                        "Evento Stripe não processado."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
