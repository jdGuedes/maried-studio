from rest_framework import (
    permissions,
    status,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from .serializers import (
    UserProfileSerializer,
)


class CurrentUserProfileView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
    ):
        serializer = (
            UserProfileSerializer(
                request.user,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(
        self,
        request,
    ):
        serializer = (
            UserProfileSerializer(
                request.user,
                data=request.data,
                partial=True,
                context={
                    "request": request,
                },
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        output = (
            UserProfileSerializer(
                request.user,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            output.data,
            status=status.HTTP_200_OK,
        )