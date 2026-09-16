from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.organizations.models import (
    Organization,
)

from .models import (
    User,
    UserRole,
)

from .services import (
    AccountRecoveryService,
)


# ==========================================================
# ORGANIZAÇÃO — PERFIL
# ==========================================================

class OrganizationProfileSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Organization

        fields = [
            "id",
            "name",
            "slug",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "slug",
            "is_active",
        ]


# ==========================================================
# USUÁRIO — PERFIL ATUAL
# ==========================================================

class UserProfileSerializer(
    serializers.ModelSerializer
):
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    organization = (
        OrganizationProfileSerializer(
            read_only=True
        )
    )

    organization_name = (
        serializers.CharField(
            write_only=True,
            required=False,
            allow_blank=False,
            max_length=160,
        )
    )

    recovery = serializers.SerializerMethodField()

    recovery_configured = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "name",
            "email",
            "role",
            "role_label",
            "organization",
            "organization_name",
            "is_superuser",
            "recovery",
            "recovery_configured",
        ]

        read_only_fields = [
            "id",
            "email",
            "role",
            "role_label",
            "organization",
            "is_superuser",
            "recovery",
            "recovery_configured",
        ]

    def get_recovery(
        self,
        obj,
    ):
        return AccountRecoveryService.status_for_user(
            obj
        )

    def get_recovery_configured(
        self,
        obj,
    ):
        return (
            self.get_recovery(
                obj
            )["recovery_configured"]
        )

    def validate_name(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Informe um nome válido."
            )

        return value

    def validate_organization_name(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Informe um nome válido para a empresa."
            )

        return value

    def update(
        self,
        instance,
        validated_data,
    ):
        organization_name = (
            validated_data.pop(
                "organization_name",
                None,
            )
        )

        if (
            "name"
            in validated_data
        ):
            instance.name = (
                validated_data[
                    "name"
                ]
            )

        instance.save(
            update_fields=[
                "name",
            ]
        )

        if (
            organization_name
            is not None
        ):
            if (
                instance.role
                != UserRole.OWNER
            ):
                raise serializers.ValidationError(
                    {
                        "organization_name": (
                            "Somente o proprietário "
                            "pode alterar o nome da empresa."
                        )
                    }
                )

            if (
                not instance.organization
            ):
                raise serializers.ValidationError(
                    {
                        "organization_name": (
                            "Usuário não possui "
                            "organização vinculada."
                        )
                    }
                )

            organization = (
                instance.organization
            )

            organization.name = (
                organization_name
            )

            organization.save(
                update_fields=[
                    "name",
                    "updated_at",
                ]
            )

        return instance


# ==========================================================
# LOGIN
# ==========================================================

class LoginSerializer(
    serializers.Serializer
):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


# ==========================================================
# MEMBRO — LEITURA
# ==========================================================

# ==========================================================
# PASSWORD RESET
# ==========================================================

class AuthenticatedPasswordChangeSerializer(
    serializers.Serializer
):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["new_password"]
            != attrs["new_password_confirm"]
        ):
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "As novas senhas nÃ£o coincidem."
                    )
                }
            )

        user = self.context[
            "request"
        ].user

        try:
            validate_password(
                attrs["new_password"],
                user,
            )

        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                    "new_password": list(
                        exc.messages
                    )
                }
            ) from exc

        return attrs


class PasswordResetRequestSerializer(
    serializers.Serializer
):
    email = serializers.EmailField()

    def validate_email(
        self,
        value,
    ):
        return (
            User.objects
            .normalize_email(
                value
            )
        )


class PasswordResetConfirmSerializer(
    serializers.Serializer
):
    uid = serializers.CharField()

    token = serializers.CharField()

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["new_password"]
            != attrs["new_password_confirm"]
        ):
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "As senhas não conferem."
                    )
                }
            )

        return attrs


class AccountRecoverySetupSerializer(
    serializers.Serializer
):
    question_1 = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    answer_1 = serializers.CharField(
        max_length=255,
        trim_whitespace=False,
        write_only=True,
    )
    question_2 = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    answer_2 = serializers.CharField(
        max_length=255,
        trim_whitespace=False,
        write_only=True,
    )

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["question_1"].strip().casefold()
            == attrs["question_2"].strip().casefold()
        ):
            raise serializers.ValidationError(
                {
                    "question_2": (
                        "Informe duas perguntas diferentes."
                    )
                }
            )

        if (
            not attrs["answer_1"].strip()
            or not attrs["answer_2"].strip()
        ):
            raise serializers.ValidationError(
                "Informe as duas respostas de segurança."
            )

        return attrs


class AccountRecoveryCurrentPasswordSerializer(
    serializers.Serializer
):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )


class AccountRecoveryRotateKeySerializer(
    AccountRecoveryCurrentPasswordSerializer
):
    pass


class AccountRecoveryChangeQuestionsSerializer(
    AccountRecoveryCurrentPasswordSerializer,
    AccountRecoverySetupSerializer,
):
    pass


class AccountRecoveryVerifyKeySerializer(
    serializers.Serializer
):
    email = serializers.EmailField()
    recovery_key = serializers.CharField(
        trim_whitespace=False,
    )

    def validate_email(
        self,
        value,
    ):
        return (
            User.objects
            .normalize_email(
                value
            )
        )


class AccountRecoveryQuestionsRequestSerializer(
    serializers.Serializer
):
    email = serializers.EmailField()

    def validate_email(
        self,
        value,
    ):
        return (
            User.objects
            .normalize_email(
                value
            )
        )


class AccountRecoveryQuestionsVerifySerializer(
    serializers.Serializer
):
    challenge_id = serializers.CharField()
    answers = serializers.ListField(
        child=serializers.DictField(),
        min_length=2,
        max_length=2,
    )

    def validate_answers(
        self,
        value,
    ):
        normalized = []

        for item in value:
            question_id = item.get(
                "question_id"
            )
            answer = item.get(
                "answer"
            )

            if (
                not question_id
                or answer is None
                or not str(answer).strip()
            ):
                raise serializers.ValidationError(
                    "Informe as duas respostas de segurança."
                )

            normalized.append(
                {
                    "question_id": str(
                        question_id
                    ),
                    "answer": str(
                        answer
                    ),
                }
            )

        return normalized


class AccountRecoveryPasswordResetSerializer(
    serializers.Serializer
):
    recovery_token = serializers.CharField(
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(
        self,
        attrs,
    ):
        if (
            attrs["new_password"]
            != attrs["new_password_confirm"]
        ):
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "As senhas não conferem."
                    )
                }
            )

        return attrs


class OrganizationMemberSerializer(
    serializers.ModelSerializer
):
    role_label = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = User

        fields = [
            "id",
            "name",
            "email",
            "role",
            "role_label",
            "is_active",
            "date_joined",
        ]

        read_only_fields = fields


# ==========================================================
# MEMBRO — CRIAÇÃO
# ==========================================================

class OrganizationMemberCreateSerializer(
    serializers.ModelSerializer
):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    class Meta:
        model = User

        fields = [
            "id",
            "name",
            "email",
            "password",
            "role",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "is_active",
        ]

    def validate_name(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Informe um nome válido."
            )

        return value

    def validate_email(
        self,
        value,
    ):
        value = (
            User.objects
            .normalize_email(value)
        )

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "Já existe um usuário com este e-mail."
            )

        return value

    def validate_role(
        self,
        value,
    ):
        request = self.context[
            "request"
        ]

        actor = request.user

        # --------------------------------------------------
        # NINGUÉM CRIA OUTRO OWNER PELA API COMUM
        # --------------------------------------------------

        if value == UserRole.OWNER:
            raise serializers.ValidationError(
                "Não é permitido criar outro proprietário."
            )

        # --------------------------------------------------
        # ADMIN SÓ PODE CRIAR MEMBER
        # --------------------------------------------------

        if (
            actor.role == UserRole.ADMIN
            and value != UserRole.MEMBER
        ):
            raise serializers.ValidationError(
                "Administrador pode criar somente membros."
            )

        # --------------------------------------------------
        # OWNER PODE CRIAR ADMIN OU MEMBER
        # --------------------------------------------------

        if (
            actor.role == UserRole.OWNER
            and value not in {
                UserRole.ADMIN,
                UserRole.MEMBER,
            }
        ):
            raise serializers.ValidationError(
                "Papel de usuário inválido."
            )

        return value

    def create(
        self,
        validated_data,
    ):
        request = self.context[
            "request"
        ]

        actor = request.user

        organization = (
            actor.organization
        )

        password = (
            validated_data.pop(
                "password"
            )
        )

        user = User.objects.create_user(
            organization=organization,
            password=password,
            is_active=True,
            **validated_data,
        )

        return user


# ==========================================================
# MEMBRO — ATUALIZAÇÃO
# ==========================================================

class OrganizationMemberUpdateSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = User

        fields = [
            "name",
            "role",
            "is_active",
        ]

    def validate_name(
        self,
        value,
    ):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Informe um nome válido."
            )

        return value

    def validate(
        self,
        attrs,
    ):
        request = self.context[
            "request"
        ]

        actor = request.user

        target = self.instance

        # --------------------------------------------------
        # NÃO GERENCIAMOS OWNER PELA API COMUM
        # --------------------------------------------------

        if target.role == UserRole.OWNER:
            raise serializers.ValidationError(
                "O proprietário não pode ser alterado "
                "pela gestão comum de membros."
            )

        # --------------------------------------------------
        # ADMIN NÃO ALTERA ADMIN
        # --------------------------------------------------

        if (
            actor.role == UserRole.ADMIN
            and target.role != UserRole.MEMBER
        ):
            raise serializers.ValidationError(
                "Administrador pode gerenciar "
                "somente membros."
            )

        new_role = attrs.get(
            "role",
            target.role,
        )

        # --------------------------------------------------
        # NINGUÉM PROMOVE PARA OWNER
        # --------------------------------------------------

        if new_role == UserRole.OWNER:
            raise serializers.ValidationError(
                {
                    "role": (
                        "Não é permitido promover "
                        "usuário para proprietário."
                    )
                }
            )

        # --------------------------------------------------
        # ADMIN NÃO PROMOVE MEMBER PARA ADMIN
        # --------------------------------------------------

        if (
            actor.role == UserRole.ADMIN
            and new_role != UserRole.MEMBER
        ):
            raise serializers.ValidationError(
                {
                    "role": (
                        "Administrador não pode promover "
                        "membros para administrador."
                    )
                }
            )

        return attrs
