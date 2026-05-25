from rest_framework import permissions


class HasRole(permissions.BasePermission):
    required_roles: tuple[str, ...] = ()

    @classmethod
    def of(cls, *roles: str) -> type:
        return type(
            f"HasRole_{'_'.join(roles)}",
            (cls,),
            {"required_roles": tuple(roles)},
        )

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.required_roles)
