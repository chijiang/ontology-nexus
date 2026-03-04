# backend/app/api/roles.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from app.core.database import get_db
from app.models.role import (
    Role,
    UserRole,
    RolePagePermission,
    RoleActionPermission,
    RoleEntityPermission,
)
from app.models.user import User
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    PagePermissionCreate,
    ActionPermissionCreate,
    EntityPermissionCreate,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    role_type: str = Query(
        None, description="Filter by role type: 'system' or 'business'"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有角色，可按类型筛选"""
    query = select(Role)
    if role_type:
        query = query.where(Role.role_type == role_type)
    result = await db.execute(query)
    roles = result.scalars().all()

    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色详情（包含权限）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # 获取页面权限
    page_result = await db.execute(
        select(RolePagePermission.page_id).where(RolePagePermission.role_id == role_id)
    )
    page_permissions = [row[0] for row in page_result.all()]

    # 获取action权限
    action_result = await db.execute(
        select(RoleActionPermission).where(RoleActionPermission.role_id == role_id)
    )
    action_permissions = [
        {"entity_type": p.entity_type, "action_name": p.action_name}
        for p in action_result.scalars().all()
    ]

    # 获取实体权限
    entity_result = await db.execute(
        select(RoleEntityPermission.entity_class_name).where(
            RoleEntityPermission.role_id == role_id
        )
    )
    entity_permissions = [row[0] for row in entity_result.all()]

    return RoleDetailResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        role_type=role.role_type,
        created_at=role.created_at,
        updated_at=role.updated_at,
        page_permissions=page_permissions,
        action_permissions=action_permissions,
        entity_permissions=entity_permissions,
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建角色（admin only）"""
    # 检查名称是否存在
    result = await db.execute(select(Role).where(Role.name == role_data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Role name already exists")

    role = Role(
        name=role_data.name,
        description=role_data.description,
        is_system=False,
        role_type=role_data.role_type,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新角色（admin only）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system role")

    # 更新字段
    if role_data.name is not None:
        # 检查名称是否重复
        existing = await db.execute(
            select(Role).where(Role.name == role_data.name, Role.id != role_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Role name already exists")
        role.name = role_data.name

    if role_data.description is not None:
        role.description = role_data.description

    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除角色（admin only）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system role")

    # 检查是否有用户使用此角色
    user_count = await db.execute(
        select(func.count()).select_from(
            select(UserRole).where(UserRole.role_id == role_id).subquery()
        )
    )
    if user_count.scalar() > 0:
        raise HTTPException(
            status_code=400, detail="Cannot delete role with assigned users"
        )

    await db.delete(role)
    await db.commit()

    return {"message": "Role deleted"}


# ==================== 权限管理 ====================


@router.get("/{role_id}/permissions/pages", response_model=List[str])
async def get_page_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的页面权限"""
    result = await db.execute(
        select(RolePagePermission.page_id).where(RolePagePermission.role_id == role_id)
    )
    return [row[0] for row in result.all()]


@router.post("/{role_id}/permissions/pages")
async def add_page_permission(
    role_id: int,
    perm: PagePermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加页面权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RolePagePermission).where(
            RolePagePermission.role_id == role_id,
            RolePagePermission.page_id == perm.page_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RolePagePermission(role_id=role_id, page_id=perm.page_id)
    db.add(permission)
    await db.commit()

    return {"message": "Page permission added"}


@router.delete("/{role_id}/permissions/pages/{page_id}")
async def remove_page_permission(
    role_id: int,
    page_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除页面权限（admin only）"""
    result = await db.execute(
        select(RolePagePermission).where(
            RolePagePermission.role_id == role_id, RolePagePermission.page_id == page_id
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Page permission removed"}


@router.get("/{role_id}/permissions/actions")
async def get_action_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的Action权限"""
    result = await db.execute(
        select(RoleActionPermission).where(RoleActionPermission.role_id == role_id)
    )
    permissions = result.scalars().all()

    return [
        {"entity_type": p.entity_type, "action_name": p.action_name}
        for p in permissions
    ]


@router.post("/{role_id}/permissions/actions")
async def add_action_permission(
    role_id: int,
    perm: ActionPermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加Action权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RoleActionPermission).where(
            RoleActionPermission.role_id == role_id,
            RoleActionPermission.entity_type == perm.entity_type,
            RoleActionPermission.action_name == perm.action_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RoleActionPermission(
        role_id=role_id, entity_type=perm.entity_type, action_name=perm.action_name
    )
    db.add(permission)
    await db.commit()

    return {"message": "Action permission added"}


@router.delete("/{role_id}/permissions/actions/{entity_type}/{action_name}")
async def remove_action_permission(
    role_id: int,
    entity_type: str,
    action_name: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除Action权限（admin only）"""
    result = await db.execute(
        select(RoleActionPermission).where(
            RoleActionPermission.role_id == role_id,
            RoleActionPermission.entity_type == entity_type,
            RoleActionPermission.action_name == action_name,
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Action permission removed"}


@router.get("/{role_id}/permissions/entities", response_model=List[str])
async def get_entity_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色的实体类型权限"""
    result = await db.execute(
        select(RoleEntityPermission.entity_class_name).where(
            RoleEntityPermission.role_id == role_id
        )
    )
    return [row[0] for row in result.all()]


@router.post("/{role_id}/permissions/entities")
async def add_entity_permission(
    role_id: int,
    perm: EntityPermissionCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """添加实体类型权限（admin only）"""
    # 检查角色是否存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Role not found")

    # 检查是否已存在
    existing = await db.execute(
        select(RoleEntityPermission).where(
            RoleEntityPermission.role_id == role_id,
            RoleEntityPermission.entity_class_name == perm.entity_class_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Permission already exists")

    permission = RoleEntityPermission(
        role_id=role_id, entity_class_name=perm.entity_class_name
    )
    db.add(permission)
    await db.commit()

    return {"message": "Entity permission added"}


@router.delete("/{role_id}/permissions/entities/{entity_class_name}")
async def remove_entity_permission(
    role_id: int,
    entity_class_name: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除实体类型权限（admin only）"""
    result = await db.execute(
        select(RoleEntityPermission).where(
            RoleEntityPermission.role_id == role_id,
            RoleEntityPermission.entity_class_name == entity_class_name,
        )
    )
    permission = result.scalar_one_or_none()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(permission)
    await db.commit()

    return {"message": "Entity permission removed"}
