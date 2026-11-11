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


def check_password(v: str) -> str:
    # bcrypt rejects anything over 72 bytes
    if len(v.encode("utf-8")) > 72:
        raise ValueError("Password is too long (72 bytes at most)")
    return v


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=100)

    _check_password = field_validator("password")(check_password)


class UserResponse(UserBase):
    """Schema for user response"""
    user_id: int
    is_active: bool
    created_at: datetime
    lawyer_id: Optional[int] = None
    must_change_password: bool = False
    last_login_at: Optional[datetime] = None

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
    new_password: str = Field(..., min_length=8, max_length=100)

    _check_password = field_validator("new_password")(check_password)


# ============================================
# TEAM: ONBOARDING
# ============================================

class JoinRequestCreate(BaseModel):
    """What someone submits when asking to join the firm."""
    fname: str = Field(..., min_length=1, max_length=50)
    lname: str = Field(..., min_length=1, max_length=50)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    phoneno: Optional[str] = Field(None, max_length=15)
    requested_role: str = "lawyer"
    bar_id: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=50)
    group_id: Optional[int] = None
    message: Optional[str] = Field(None, max_length=2000)

    _check_password = field_validator("password")(check_password)

    @field_validator("requested_role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("lawyer", "staff"):
            raise ValueError("Role must be lawyer or staff")
        return v


class JoinRequestResponse(BaseModel):
    request_id: int
    fname: str
    lname: str
    username: str
    email: str
    phoneno: Optional[str] = None
    requested_role: str
    bar_id: Optional[str] = None
    designation: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    message: Optional[str] = None
    status: str
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JoinRequestApprove(BaseModel):
    """The admin can correct or complete what the applicant entered."""
    role: Optional[str] = None
    bar_id: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=50)
    group_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is not None and v not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ALLOWED_ROLES)}")
        return v


class JoinRequestReject(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)


class MemberCreate(BaseModel):
    """An admin adds someone directly. Pass lawyer_id to give an existing lawyer a login."""
    fname: str = Field(..., min_length=1, max_length=50)
    lname: str = Field(..., min_length=1, max_length=50)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: str = "lawyer"
    lawyer_id: Optional[int] = None
    phoneno: Optional[str] = Field(None, max_length=15)
    bar_id: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=50)
    group_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ALLOWED_ROLES)}")
        return v


class MemberResponse(UserResponse):
    lawyer_name: Optional[str] = None


class MemberCreated(BaseModel):
    """temporary_password is shown once and is never stored in clear text."""
    member: MemberResponse
    temporary_password: str


class MemberRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(ALLOWED_ROLES)}")
        return v


class DirectoryEntry(BaseModel):
    """Enough to pick a colleague from a list."""
    user_id: int
    name: str
    role: str
    lawyer_id: Optional[int] = None
