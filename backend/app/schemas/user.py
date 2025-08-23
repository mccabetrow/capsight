"""
User schemas for request/response validation.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    role: str = Field(default="user", description="User role")
    is_active: bool = Field(default=True, description="Whether user is active")


class UserCreate(BaseModel):
    """User creation schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    role: str = Field(default="user", description="User role")


class UserRead(UserBase):
    """User read schema for API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="User ID")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's full name")
    password: Optional[str] = Field(None, min_length=8, description="New password")
    is_active: Optional[bool] = Field(None, description="Whether user is active")


class UserInDB(UserBase):
    """User schema for database operations (includes password hash)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    hashed_password: str
    created_at: datetime
    updated_at: datetime
