"""
API Router for Authentication
Handles user registration, login, and token management
"""
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.models import JoinRequest, PracticeGroup, utcnow
from ..models.user import User
from ..schemas.auth import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    PasswordChange,
    JoinRequestCreate,
)
from ..core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_user_from_token,
    require_role,
)
from ..core.audit import record
from ..config import settings

router = APIRouter()

# Same token URL as core.security.oauth2_scheme, but a missing token is not an
# automatic 401, so register() can allow the very first account without one.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Register a new user (admin only)
    
    - **username**: Unique username (3-50 chars)
    - **email**: Valid email address
    - **password**: Password (min 6 chars)
    - **full_name**: Full name (optional)
    - **role**: User role (admin/lawyer/staff) - default: lawyer
    
    Needs an admin token. The one exception is an empty users table:
    the first account is created as admin so the system can be set up.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        caller = get_user_from_token(token, db)
        if not caller.is_active or caller.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin can create accounts",
            )

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # The first account ever created is the admin
    role = "admin" if user_count == 0 else user_data.role
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=role,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


def _login(db: Session, username: str, password: str) -> Token:
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        # A join request still waiting for approval gets a clearer message
        pending = db.query(JoinRequest).filter(
            JoinRequest.username == username,
            JoinRequest.status == "Pending",
        ).first()
        if pending and verify_password(password, pending.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your request to join is waiting for an admin's approval",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    user.last_login_at = utcnow()
    record(db, user, "login", "user", user.user_id)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login with username and password. Returns a JWT access token."""
    return _login(db, form_data.username, form_data.password)


@router.post("/login-json", response_model=Token)
async def login_json(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Login with a JSON body. This is what the app uses."""
    return _login(db, login_data.username, login_data.password)


@router.get("/setup-status")
async def setup_status(db: Session = Depends(get_db)):
    """Public. True until the first account exists, so the app can offer first-time setup."""
    return {"needs_first_admin": db.query(User).count() == 0}


@router.get("/practice-groups")
async def public_practice_groups(db: Session = Depends(get_db)):
    """Public names only, for the join-request form."""
    groups = db.query(PracticeGroup).order_by(PracticeGroup.group_name).all()
    return [{"group_id": g.group_id, "group_name": g.group_name} for g in groups]


@router.post("/join-requests", status_code=status.HTTP_201_CREATED)
async def submit_join_request(data: JoinRequestCreate, db: Session = Depends(get_db)):
    """Public. Ask to join the firm. Nothing can be accessed until an admin approves."""
    username_taken = db.query(User).filter(User.username == data.username).first() or db.query(JoinRequest).filter(
        func.lower(JoinRequest.username) == data.username.lower(), JoinRequest.status == "Pending"
    ).first()
    if username_taken:
        raise HTTPException(status_code=400, detail="Username is not available")
    email_taken = db.query(User).filter(User.email == data.email).first() or db.query(JoinRequest).filter(
        func.lower(JoinRequest.email) == data.email.lower(), JoinRequest.status == "Pending"
    ).first()
    if email_taken:
        raise HTTPException(status_code=400, detail="This email is already registered or awaiting approval")
    if data.group_id and not db.get(PracticeGroup, data.group_id):
        raise HTTPException(status_code=404, detail=f"Practice group {data.group_id} not found")

    fields = data.model_dump(exclude={"password"})
    request = JoinRequest(**fields, hashed_password=get_password_hash(data.password))
    db.add(request)
    db.flush()
    record(db, None, "join_request_submitted", "join_request", request.request_id, detail={"username": data.username})
    db.commit()
    return {"request_id": request.request_id, "status": request.status}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information
    
    Requires authentication (Bearer token)
    """
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password
    
    Requires authentication
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    if password_data.new_password == password_data.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.must_change_password = False
    record(db, current_user, "password_changed", "user", current_user.user_id)
    db.commit()
    
    return {"message": "Password changed successfully"}


# ============================================
# USER MANAGEMENT (ADMIN ONLY)
# ============================================

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(require_role(["admin"]))])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get all users (Admin only)
    
    Requires admin role
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role(["admin"]))])
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get specific user by ID (Admin only)
    
    Requires admin role
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
