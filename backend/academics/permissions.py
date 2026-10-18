from rest_framework.permissions import BasePermission, SAFE_METHODS


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "ADMIN"
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


class RolePermission(BasePermission):
    """A view declares read_roles (GET) and write_roles (POST/PUT/DELETE).
    None means 'any logged-in user'."""

    def has_permission(self, request, view):
        role = get_role(request.user)
        if role is None:
            return False
        roles = view.read_roles if request.method in SAFE_METHODS else view.write_roles
        return roles is None or role in roles
