# backend/app/api/auth.py
import re
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.role import RegisterPendingResponse, ChangePasswordRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_password_strength(password: str) -> str:
    """Validate password meets minimum complexity requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not re.search(r"[a-zA-Z]", password):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    return password


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=RegisterPendingResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户（状态为pending）
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email,
        approval_status="pending",
        is_password_changed=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterPendingResponse(
        message="Registration pending approval", user_id=user.id
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 检查审批状态
    if user.approval_status == "pending":
        raise HTTPException(status_code=403, detail="Registration pending approval")
    elif user.approval_status == "rejected":
        reason = user.approval_note or "No reason provided"
        raise HTTPException(status_code=403, detail=f"Registration rejected: {reason}")

    # 检查账户状态
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码"""
    # 验证旧密码
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    # 更新密码
    current_user.password_hash = hash_password(req.new_password)
    current_user.is_password_changed = True
    await db.commit()

    return {"message": "Password changed successfully"}
