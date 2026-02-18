# backend/app/services/permission_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.role import Role, UserRole, RolePagePermission, RoleActionPermission, RoleEntityPermission
from app.rule_engine.action_registry import ActionRegistry
from typing import List, Dict, Optional

# Global action registry (initialized in main.py)
_action_registry: ActionRegistry | None = None


def init_permission_service(registry: ActionRegistry):
    """Initialize the permission service with action registry.

    Args:
        registry: ActionRegistry instance
    """
    global _action_registry
    _action_registry = registry


# 功能模块枚举
class PageId:
    CHAT = "chat"
    RULES = "rules"
    ACTIONS = "actions"
    DATA_PRODUCTS = "data-products"
    ONTOLOGY = "ontology"
    ADMIN = "admin"

    @classmethod
    def all(cls) -> List[str]:
        return [cls.CHAT, cls.RULES, cls.ACTIONS, cls.DATA_PRODUCTS, cls.ONTOLOGY, cls.ADMIN]


class PermissionService:
    """权限检查和缓存服务"""

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        result = await db.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_accessible_pages(db: AsyncSession, user: User) -> List[str]:
        """获取用户可访问的页面列表"""
        # Admin拥有所有权限
        if user.is_admin:
            return PageId.all()

        # 获取用户角色的页面权限
        result = await db.execute(
            select(RolePagePermission.page_id)
            .join(UserRole, UserRole.role_id == RolePagePermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def check_page_access(db: AsyncSession, user: User, page_id: str) -> bool:
        """检查用户是否有页面访问权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RolePagePermission)
            .join(UserRole, UserRole.role_id == RolePagePermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RolePagePermission.page_id == page_id
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_accessible_actions(db: AsyncSession, user: User) -> Dict[str, List[str]]:
        """获取用户可执行的Action，返回 {entity_type: [action_names]}"""
        if user.is_admin:
            # Admin拥有所有action权限
            # 这里需要从action registry获取所有action
            if _action_registry is None:
                # Registry not initialized, return empty dict
                return {}
            result: Dict[str, List[str]] = {}
            all_actions = _action_registry.list_all()
            for action in all_actions:
                if action.entity_type not in result:
                    result[action.entity_type] = []
                result[action.entity_type].append(action.action_name)
            return result

        # 获取用户角色的action权限
        result = await db.execute(
            select(RoleActionPermission)
            .join(UserRole, UserRole.role_id == RoleActionPermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        permissions = result.scalars().all()

        # 按entity_type分组
        actions_dict: Dict[str, List[str]] = {}
        for perm in permissions:
            if perm.entity_type not in actions_dict:
                actions_dict[perm.entity_type] = []
            actions_dict[perm.entity_type].append(perm.action_name)

        return actions_dict

    @staticmethod
    async def check_action_permission(
        db: AsyncSession,
        user: User,
        entity_type: str,
        action_name: str
    ) -> bool:
        """检查用户是否有指定Action的执行权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RoleActionPermission)
            .join(UserRole, UserRole.role_id == RoleActionPermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RoleActionPermission.entity_type == entity_type,
                RoleActionPermission.action_name == action_name
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_accessible_entities(db: AsyncSession, user: User) -> List[str]:
        """获取用户可访问的实体类型列表"""
        if user.is_admin:
            # Admin拥有所有实体类型的访问权限
            # 从GraphEntity表获取所有类名
            from app.models.graph import GraphEntity
            result = await db.execute(
                select(GraphEntity.entity_type).distinct()
            )
            return list({row[0] for row in result.all() if row[0]})

        result = await db.execute(
            select(RoleEntityPermission.entity_class_name)
            .join(UserRole, UserRole.role_id == RoleEntityPermission.role_id)
            .where(UserRole.user_id == user.id)
            .distinct()
        )
        return [row[0] for row in result.all()]

    @staticmethod
    async def check_entity_access(
        db: AsyncSession,
        user: User,
        entity_class_name: str
    ) -> bool:
        """检查用户是否有指定实体类型的访问权限"""
        if user.is_admin:
            return True

        result = await db.execute(
            select(RoleEntityPermission)
            .join(UserRole, UserRole.role_id == RoleEntityPermission.role_id)
            .where(
                UserRole.user_id == user.id,
                RoleEntityPermission.entity_class_name == entity_class_name
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_permission_cache(db: AsyncSession, user: User) -> dict:
        """获取用户权限缓存（登录后调用）"""
        accessible_pages = await PermissionService.get_accessible_pages(db, user)
        accessible_actions = await PermissionService.get_accessible_actions(db, user)
        accessible_entities = await PermissionService.get_accessible_entities(db, user)

        return {
            "accessible_pages": accessible_pages,
            "accessible_actions": accessible_actions,
            "accessible_entities": accessible_entities,
            "is_admin": user.is_admin
        }
