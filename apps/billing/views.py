from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CurrentSubscriptionSerializer
from .services import BillingAccessService


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

