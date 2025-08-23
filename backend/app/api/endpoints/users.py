"""
User management endpoints.
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth import AuthService
from app.services.users import UserService
from app.schemas.user import User, UserUpdate, UserProfile

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user(
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Get current user profile."""
    return UserProfile.from_orm(current_user)


@router.put("/me", response_model=UserProfile)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Update current user profile."""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(
            user_id=current_user.id,
            user_update=user_update
        )
        return UserProfile.from_orm(updated_user)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/me")
async def delete_current_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
) -> Any:
    """Delete current user account."""
    try:
        user_service = UserService(db)
        await user_service.delete_user(current_user.id)
        return {"message": "User account deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get("/", response_model=List[UserProfile])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_admin_user)
) -> Any:
    """Get all users (admin only)."""
    try:
        user_service = UserService(db)
        users = await user_service.get_users(skip=skip, limit=limit)
        return [UserProfile.from_orm(user) for user in users]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )
