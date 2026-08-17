from rest_framework import serializers

from apps.organizations.models import (
    Organization,
)

from .models import (
    User,
    UserRole,
)


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
        ]

        read_only_fields = [
            "id",
            "email",
            "role",
            "role_label",
            "organization",
            "is_superuser",
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