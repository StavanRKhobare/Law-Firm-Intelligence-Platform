"""
Pydantic schemas for Authentication
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime

# ============================================
# USER SCHEMAS
# ============================================

ALLOWED_ROLES = ["admin", "lawyer", "staff"]


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: str = Field(default="lawyer")
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ALLOWED_ROLES)}")
        return v


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=6, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        # an unknown (or null) role would make the account unusable and break the user list
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ALLOWED_ROLES)}")
        return v

    @field_validator("email", "is_active")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("cannot be null")
        return v




class UserResponse(UserBase):
    """Schema for user response"""
    user_id: int
    is_active: bool
    created_at: datetime  # Changed from str to datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    """Schema for login"""
    username: str
    password: str


class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)