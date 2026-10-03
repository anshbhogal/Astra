from typing import List
from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.domain import User, UserRole


class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not authorized to perform this operation."
            )
        return current_user


def require_roles(allowed_roles: List[UserRole]):
    return Depends(RoleChecker(allowed_roles))
