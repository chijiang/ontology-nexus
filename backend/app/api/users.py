# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.role import UserRole
from app.schemas.role import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    ApproveUserRequest,
    RejectUserRequest,
    ResetPasswordResponse,
    AssignRoleRequest,
    PermissionCacheResponse,
)
from app.api.deps import get_current_user
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/users", tags=["users"])


async def require_admin(current_user: User = Depends(get_current_user)):
    """验证用户是否为admin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    approval_status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（admin only）"""
    query = select(User)

    # 筛选条件
    if approval_status:
        query = query.where(User.approval_status == approval_status)

    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（admin only）"""
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    # 创建用户（直接approved）
    user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        approval_status="approved",
        approved_by=current_user.id,
        is_password_changed=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/pending-approvals", response_model=UserListResponse)
async def get_pending_approvals(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取待审批用户列表（admin only）"""
    result = await db.execute(
        select(User).where(User.approval_status == "pending")
    )
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=len(users)
    )


@router.post("/{user_id}/approve")
async def approve_user(
    user_id: int,
    req: ApproveUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """审批通过用户注册（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.approval_status != "pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.approval_status = "approved"
    user.approved_by = current_user.id
    user.approved_at = func.now()
    user.approval_note = req.note
    await db.commit()

    return {"message": "User approved successfully"}


@router.post("/{user_id}/reject")
async def reject_user(
    user_id: int,
    req: RejectUserRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """拒绝用户注册（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.approval_status != "pending":
        raise HTTPException(status_code=400, detail="User is not pending approval")

    user.approval_status = "rejected"
    user.approved_by = current_user.id
    user.approved_at = func.now()
    user.approval_note = req.reason
    await db.commit()

    return {"message": "User rejected"}


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重置用户密码为默认值（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 默认密码
    default_password = "123456"
    user.password_hash = hash_password(default_password)
    user.is_password_changed = False
    await db.commit()

    return ResetPasswordResponse(
        message="Password reset successfully",
        default_password=default_password
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户（admin only）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 更新字段
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（admin only）"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted"}


@router.post("/{user_id}/roles")
async def assign_role(
    user_id: int,
    req: AssignRoleRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """为用户分配角色（admin only）"""
    # 检查用户是否存在
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # 检查是否已分配
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == req.role_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role already assigned")

    # 创建关联
    user_role = UserRole(
        user_id=user_id,
        role_id=req.role_id,
        assigned_by=current_user.id
    )
    db.add(user_role)
    await db.commit()

    return {"message": "Role assigned successfully"}


@router.delete("/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """移除用户角色（admin only）"""
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
    )
    user_role = result.scalar_one_or_none()

    if not user_role:
        raise HTTPException(status_code=404, detail="Role assignment not found")

    await db.delete(user_role)
    await db.commit()

    return {"message": "Role removed successfully"}


@router.get("/me/permissions", response_model=PermissionCacheResponse)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的权限缓存"""
    cache = await PermissionService.get_permission_cache(db, current_user)
    return PermissionCacheResponse(**cache)
