"""
Shared FastAPI dependencies for auth / RBAC.
"""

from collections.abc import Callable, Mapping

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db, get_user_primary_role


def _as_user_dict(current_user) -> dict:
    if isinstance(current_user, dict):
        return dict(current_user)

    if isinstance(current_user, Mapping):
        return dict(current_user)

    return {
        "id": getattr(current_user, "id"),
        "username": getattr(current_user, "username", None),
        "email": getattr(current_user, "email", None),
    }


def require_roles(*allowed_roles: str) -> Callable:
    """
    Require JWT login and one of the given roles.

    Example:
        current_user=Depends(require_roles("developer", "admin"))
    """

    allowed = {role.lower() for role in allowed_roles}

    def dependency(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        user = _as_user_dict(current_user)
        user_id = int(user["id"])
        role = get_user_primary_role(db, user_id).lower()

        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色：{', '.join(sorted(allowed))}",
            )

        user["role"] = role
        return user

    return dependency


# Common aliases
require_login = get_current_user
require_developer = require_roles("developer", "admin")
require_admin = require_roles("admin")
