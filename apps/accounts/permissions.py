from rest_framework import permissions

from .models import UserRole


class CanManageOrganizationMembers(
    permissions.BasePermission
):
    """
    Permite acesso à gestão de membros somente para:

    - OWNER
    - ADMIN

    MEMBER não possui acesso à gestão da equipe.

    O isolamento por organização continua sendo responsabilidade
    do queryset das views.
    """

    message = (
        "Você não possui permissão para "
        "gerenciar membros da organização."
    )

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        if not user.is_active:
            return False

        if not user.organization_id:
            return False

        if not user.organization.is_active:
            return False

        return user.role in {
            UserRole.OWNER,
            UserRole.ADMIN,
        }
