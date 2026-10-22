from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """GET/HEAD/OPTIONS sobai pabe. Write shudhu logged-in superuser."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


class IsOwner(BasePermission):
    """Shudhu logged-in superuser (GET o na)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)