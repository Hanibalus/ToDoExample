from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import hashlib

from app.database import get_db_session
from app.models import User, RefreshToken
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest, UserResponse
)
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token
)
from app.config import settings

router = APIRouter()


def hash_token(token: str) -> str:
    """Hash a token for storage"""
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new user account"""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        hashed_password=hashed_password,
        display_name=data.display_name,
        email_verified=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Generate tokens
    access_token = create_access_token(str(new_user.id))
    refresh_token = create_refresh_token()
    
    # Store refresh token hash
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Login with email and password"""
    # Find user
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(data.password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Generate tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token()
    
    # Store refresh token hash
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    await db.commit()
    await db.refresh(user)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh")
async def refresh_access_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    token_hash = hash_token(data.refresh_token)
    
    # Find refresh token
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
    )
    refresh_token_record = result.scalar_one_or_none()
    
    if not refresh_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Create new access token
    access_token = create_access_token(str(refresh_token_record.user_id))
    
    # Optionally create new refresh token (token rotation)
    new_refresh_token = create_refresh_token()
    new_token_hash = hash_token(new_refresh_token)
    new_expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_refresh_token_record = RefreshToken(
        user_id=refresh_token_record.user_id,
        token_hash=new_token_hash,
        expires_at=new_expires_at
    )
    db.add(new_refresh_token_record)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Logout by revoking refresh token"""
    token_hash = hash_token(data.refresh_token)
    
    # Find and revoke token
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token_record = result.scalar_one_or_none()
    
    if refresh_token_record:
        refresh_token_record.revoked = True
        await db.commit()
    
    return {"message": "Logged out successfully"}
