from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import (
    csrf_protect,
    ensure_csrf_cookie,
)

from rest_framework import (
    generics,
    permissions,
    status,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from .models import (
    User,
)

from .permissions import (
    CanManageOrganizationMembers,
)

from .serializers import (
    LoginSerializer,
    OrganizationMemberCreateSerializer,
    OrganizationMemberSerializer,
    OrganizationMemberUpdateSerializer,
    UserProfileSerializer,
)


# ==========================================================
# CSRF
# ==========================================================

@method_decorator(
    ensure_csrf_cookie,
    name="dispatch",
)
class CsrfCookieView(
    APIView
):
    permission_classes = [
        permissions.AllowAny,
    ]

    def get(
        self,
        request,
    ):
        get_token(
            request
        )

        return Response(
            {
                "detail": (
                    "CSRF cookie initialized."
                )
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# LOGIN / LOGOUT
# ==========================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class LoginView(
    APIView
):
    permission_classes = [
        permissions.AllowAny,
    ]

    authentication_classes = []

    def post(
        self,
        request,
    ):
        serializer = LoginSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        credentials = serializer.validated_data

        user = authenticate(
            request=request,
            username=credentials["email"],
            password=credentials["password"],
        )

        if user is None:
            return Response(
                {
                    "detail": (
                        "E-mail ou senha inválidos."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {
                    "detail": (
                        "Conta inativa."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_superuser:
            if not user.organization_id:
                return Response(
                    {
                        "detail": (
                            "Usuário não possui organização vinculada."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not user.organization.is_active:
                return Response(
                    {
                        "detail": (
                            "Organização inativa."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        login(
            request,
            user,
        )

        output = UserProfileSerializer(
            user,
            context={
                "request": request,
            },
        )

        return Response(
            {
                "user": output.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class LogoutView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        logout(
            request
        )

        return Response(
            {
                "detail": (
                    "Sessão encerrada."
                )
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# PERFIL ATUAL
# ==========================================================

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


# ==========================================================
# MEMBROS DA ORGANIZAÇÃO
#
# GET  -> lista membros
# POST -> cria membro
# ==========================================================

class OrganizationMemberListCreateView(
    generics.ListCreateAPIView
):
    permission_classes = [
        permissions.IsAuthenticated,
        CanManageOrganizationMembers,
    ]

    def get_queryset(
        self,
    ):
        organization = (
            self.request.user.organization
        )

        return (
            User.objects
            .filter(
                organization=organization
            )
            .order_by(
                "name",
                "email",
            )
        )

    def get_serializer_class(
        self,
    ):
        if (
            self.request.method
            == "POST"
        ):
            return (
                OrganizationMemberCreateSerializer
            )

        return (
            OrganizationMemberSerializer
        )

    def get_serializer_context(
        self,
    ):
        context = (
            super()
            .get_serializer_context()
        )

        context[
            "request"
        ] = self.request

        return context


# ==========================================================
# DETALHE / EDIÇÃO DO MEMBRO
#
# GET   -> detalhe
# PATCH -> altera nome, papel ou status
#
# DELETE propositalmente NÃO existe na V1.
# Histórico deve ser preservado.
# ==========================================================

class OrganizationMemberDetailView(
    generics.RetrieveUpdateAPIView
):
    permission_classes = [
        permissions.IsAuthenticated,
        CanManageOrganizationMembers,
    ]

    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_queryset(
        self,
    ):
        organization = (
            self.request.user.organization
        )

        return (
            User.objects
            .filter(
                organization=organization
            )
        )

    def get_serializer_class(
        self,
    ):
        if (
            self.request.method
            == "PATCH"
        ):
            return (
                OrganizationMemberUpdateSerializer
            )

        return (
            OrganizationMemberSerializer
        )

    def get_serializer_context(
        self,
    ):
        context = (
            super()
            .get_serializer_context()
        )

        context[
            "request"
        ] = self.request

        return context

    def patch(
        self,
        request,
        *args,
        **kwargs,
    ):
        instance = self.get_object()

        serializer = (
            OrganizationMemberUpdateSerializer(
                instance,
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
            OrganizationMemberSerializer(
                instance,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            output.data,
            status=status.HTTP_200_OK,
        )
