from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    message = "Acesso permitido somente ao SuperAdmin."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
