from rest_framework import (
    permissions,
    status,
)

from rest_framework.response import Response

from rest_framework.views import APIView

from .models import CreditWallet

from .serializers import (
    CreditWalletSerializer,
)


class CreditWalletDetailView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
    ):
        organization = getattr(
            request.user,
            "organization",
            None,
        )

        if organization is None:
            return Response(
                {
                    "detail": (
                        "Usuário não possui "
                        "uma organização vinculada."
                    )
                },
                status=(
                    status.HTTP_400_BAD_REQUEST
                ),
            )

        try:
            wallet = (
                CreditWallet.objects
                .select_related(
                    "organization"
                )
                .get(
                    organization=organization
                )
            )

        except CreditWallet.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "Carteira de créditos "
                        "não encontrada."
                    )
                },
                status=(
                    status.HTTP_404_NOT_FOUND
                ),
            )

        serializer = (
            CreditWalletSerializer(
                wallet
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )