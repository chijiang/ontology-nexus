# backend/tests/test_permissions.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestPermissionService:
    """测试权限服务"""

    async def test_get_accessible_pages_for_admin(self, db: AsyncSession, admin_user: User):
        """Admin用户应能访问所有页面"""
        from app.services.permission_service import PermissionService
        from app.services.permission_service import PageId

        pages = await PermissionService.get_accessible_pages(db, admin_user)
        assert set(pages) == set(PageId.all())

    async def test_get_accessible_pages_for_regular_user(self, db: AsyncSession, regular_user: User):
        """普通用户只能访问授权的页面"""
        from app.services.permission_service import PermissionService

        pages = await PermissionService.get_accessible_pages(db, regular_user)
        assert 'chat' in pages
        assert 'admin' not in pages


class TestUserAPI:
    """测试用户管理API"""

    async def test_create_user_as_admin(self, client: AsyncClient, admin_token: str):
        """Admin可以创建用户"""
        response = await client.post(
            "/api/users",
            json={"username": "testuser", "password": "password123"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["approval_status"] == "approved"

    async def test_create_user_as_regular_user_forbidden(
        self, client: AsyncClient, user_token: str
    ):
        """普通用户不能创建用户"""
        response = await client.post(
            "/api/users",
            json={"username": "testuser", "password": "password123"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

    async def test_list_users_requires_admin(
        self, client: AsyncClient, user_token: str
    ):
        """列出用户需要admin权限"""
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403


class TestAuthFlow:
    """测试认证流程"""

    async def test_register_creates_pending_user(self, client: AsyncClient):
        """注册后用户状态为pending"""
        response = await client.post(
            "/auth/register",
            json={"username": "newuser", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Registration pending approval"

    async def test_pending_user_cannot_login(self, client: AsyncClient):
        """待审批用户无法登录"""
        # 先注册
        await client.post(
            "/auth/register",
            json={"username": "pendinguser", "password": "password123"}
        )

        # 尝试登录
        response = await client.post(
            "/auth/login",
            json={"username": "pendinguser", "password": "password123"}
        )
        assert response.status_code == 403
        assert "pending approval" in response.json()["detail"]

    async def test_admin_can_approve_user(
        self, client: AsyncClient, admin_token: str, db: AsyncSession
    ):
        """Admin可以审批用户"""
        # 注册用户
        await client.post(
            "/auth/register",
            json={"username": "approveuser", "password": "password123"}
        )

        # 获取待审批用户
        response = await client.get(
            "/api/users/pending-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        users = response.json()["items"]
        user_id = next(u["id"] for u in users if u["username"] == "approveuser")

        # 审批通过
        response = await client.post(
            f"/api/users/{user_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200

        # 现在可以登录
        response = await client.post(
            "/auth/login",
            json={"username": "approveuser", "password": "password123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
