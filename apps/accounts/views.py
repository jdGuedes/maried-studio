from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control
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

from .rate_limits import (
    check_rate_limits,
    client_ip,
    rate_limit_rule,
    user_identifier,
)

from .serializers import (
    AccountRecoveryChangeQuestionsSerializer,
    AccountRecoveryPasswordResetSerializer,
    AccountRecoveryQuestionsRequestSerializer,
    AccountRecoveryQuestionsVerifySerializer,
    AccountRecoveryRotateKeySerializer,
    AccountRecoverySetupSerializer,
    AccountRecoveryVerifyKeySerializer,
    AuthenticatedPasswordChangeSerializer,
    LoginSerializer,
    OrganizationMemberCreateSerializer,
    OrganizationMemberSerializer,
    OrganizationMemberUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserProfileSerializer,
)

from .services import (
    AccountPasswordService,
    PasswordChangeError,
    AccountRecoveryError,
    AccountRecoveryService,
    AccountRecoveryTokenError,
    PASSWORD_RESET_INVALID_DETAIL,
    PASSWORD_RESET_NEUTRAL_DETAIL,
    PasswordResetInvalidError,
    PasswordResetService,
)


def no_store_response(
    response,
):
    patch_cache_control(
        response,
        no_store=True,
    )

    return response


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

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "login_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "login_identifier",
                    credentials["email"],
                ),
            ]
        )

        if limited:
            return limited

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
# PASSWORD CHANGE
# ==========================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AuthenticatedPasswordChangeView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "authenticated_password_user",
                    user_identifier(
                        request
                    ),
                ),
            ]
        )

        if limited:
            return limited

        serializer = AuthenticatedPasswordChangeSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:
            user = (
                AccountPasswordService
                .change_authenticated_password(
                    user=request.user,
                    current_password=data[
                        "current_password"
                    ],
                    new_password=data[
                        "new_password"
                    ],
                )
            )

        except PasswordChangeError as exc:
            return Response(
                {
                    "code": (
                        "current_password_invalid"
                    ),
                    "detail": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_session_auth_hash(
            request,
            user,
        )

        return Response(
            {
                "detail": (
                    "Senha alterada com sucesso."
                )
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# PASSWORD RESET
# ==========================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class PasswordResetRequestView(
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
        serializer = PasswordResetRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "password_reset_request_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "password_reset_request_identifier",
                    serializer.validated_data["email"],
                ),
            ]
        )

        if limited:
            return limited

        PasswordResetService().request_reset(
            email=serializer.validated_data["email"]
        )

        return Response(
            {
                "detail": PASSWORD_RESET_NEUTRAL_DETAIL,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class PasswordResetConfirmView(
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
        serializer = PasswordResetConfirmSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "password_reset_confirm_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "password_reset_confirm_token",
                    (
                        f"{data['uid']}:"
                        f"{data['token']}"
                    ),
                ),
            ]
        )

        if limited:
            return limited

        try:
            PasswordResetService().confirm_reset(
                uid=data["uid"],
                token=data["token"],
                new_password=data["new_password"],
            )

        except PasswordResetInvalidError:
            return Response(
                {
                    "detail": PASSWORD_RESET_INVALID_DETAIL,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except DjangoValidationError as exc:
            return Response(
                {
                    "new_password": list(
                        exc.messages
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": (
                    "Senha alterada com sucesso."
                )
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# ACCOUNT RECOVERY AUTÔNOMO
# ==========================================================

class AccountRecoveryStatusView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get(
        self,
        request,
    ):
        return Response(
            AccountRecoveryService.status_for_user(
                request.user
            ),
            status=status.HTTP_200_OK,
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoverySetupView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_authenticated_user",
                    user_identifier(
                        request
                    ),
                ),
            ]
        )

        if limited:
            return limited

        serializer = AccountRecoverySetupSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            result = AccountRecoveryService.setup(
                user=request.user,
                **serializer.validated_data,
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_201_CREATED,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryRotateKeyView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_authenticated_user",
                    user_identifier(
                        request
                    ),
                ),
            ]
        )

        if limited:
            return limited

        serializer = AccountRecoveryRotateKeySerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        try:
            result = (
                AccountRecoveryService
                .rotate_key_authenticated(
                    user=request.user,
                    current_password=(
                        serializer.validated_data[
                            "current_password"
                        ]
                    ),
                )
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryChangeQuestionsView(
    APIView
):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(
        self,
        request,
    ):
        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_authenticated_user",
                    user_identifier(
                        request
                    ),
                ),
            ]
        )

        if limited:
            return limited

        serializer = AccountRecoveryChangeQuestionsSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:
            result = (
                AccountRecoveryService
                .change_questions_authenticated(
                    user=request.user,
                    current_password=data["current_password"],
                    question_1=data["question_1"],
                    answer_1=data["answer_1"],
                    question_2=data["question_2"],
                    answer_2=data["answer_2"],
                )
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryVerifyKeyView(
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
        serializer = AccountRecoveryVerifyKeySerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_key_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "recovery_key_identifier",
                    serializer.validated_data[
                        "email"
                    ],
                ),
            ]
        )

        if limited:
            return limited

        try:
            result = (
                AccountRecoveryService
                .verify_recovery_key(
                    **serializer.validated_data
                )
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryQuestionsView(
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
        serializer = AccountRecoveryQuestionsRequestSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_questions_request_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "recovery_questions_request_identifier",
                    serializer.validated_data[
                        "email"
                    ],
                ),
            ]
        )

        if limited:
            return limited

        result = (
            AccountRecoveryService
            .create_questions_challenge(
                email=serializer.validated_data[
                    "email"
                ]
            )
        )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryQuestionsVerifyView(
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
        serializer = AccountRecoveryQuestionsVerifySerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_questions_verify_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "recovery_questions_verify_challenge",
                    serializer.validated_data[
                        "challenge_id"
                    ],
                ),
            ]
        )

        if limited:
            return limited

        try:
            result = (
                AccountRecoveryService
                .verify_questions(
                    **serializer.validated_data
                )
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
        )


@method_decorator(
    csrf_protect,
    name="dispatch",
)
class AccountRecoveryPasswordResetView(
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
        serializer = AccountRecoveryPasswordResetSerializer(
            data=request.data
        )
        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        limited = check_rate_limits(
            [
                rate_limit_rule(
                    "recovery_reset_ip",
                    client_ip(
                        request
                    ),
                ),
                rate_limit_rule(
                    "recovery_reset_token",
                    data["recovery_token"],
                ),
            ]
        )

        if limited:
            return limited

        try:
            result = AccountRecoveryService.reset_password(
                recovery_token=data["recovery_token"],
                new_password=data["new_password"],
            )

        except AccountRecoveryTokenError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        except AccountRecoveryError as exc:
            return Response(
                {
                    "detail": exc.detail,
                },
                status=exc.status_code,
            )

        except DjangoValidationError as exc:
            return Response(
                {
                    "new_password": list(
                        exc.messages
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return no_store_response(
            Response(
                result,
                status=status.HTTP_200_OK,
            )
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
