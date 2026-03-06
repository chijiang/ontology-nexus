# backend/app/schemas/role.py
import re
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List


# Approval Status 枚举
class ApprovalStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ==================== Role Schemas ====================


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    role_type: str = "system"  # "system" or "business"


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: int
    is_system: bool
    role_type: str = "system"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==================== UserRole Schemas ====================


class AssignRoleRequest(BaseModel):
    role_id: int


# ==================== Permission Schemas ====================


class PagePermissionCreate(BaseModel):
    page_id: str


class ActionPermissionCreate(BaseModel):
    entity_type: str
    action_name: str


class EntityPermissionCreate(BaseModel):
    entity_class_name: str


# ==================== Role Detail with Permissions ====================


class RoleDetailResponse(RoleResponse):
    page_permissions: List[str] = []
    action_permissions: List[dict] = []  # [{"entity_type": str, "action_name": str}]
    entity_permissions: List[str] = []


# ==================== User Schemas (扩展) ====================


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None


class UserCreate(UserBase):
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_admin: bool
    approval_status: str
    approval_note: Optional[str] = None
    is_password_changed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int


# ==================== User Approval ====================


class ApproveUserRequest(BaseModel):
    note: Optional[str] = None


class RejectUserRequest(BaseModel):
    reason: str


# ==================== Password Reset ====================


class ResetPasswordResponse(BaseModel):
    message: str
    default_password: str  # 返回默认密码供admin查看


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters long")
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Password must contain at least one letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


# ==================== Permission Cache ====================


class PermissionCacheResponse(BaseModel):
    accessible_pages: List[str]
    accessible_actions: dict  # {entity_type: [action_names]}
    accessible_entities: List[str]
    is_admin: bool


# ==================== Register Response (修改) ====================


class RegisterPendingResponse(BaseModel):
    message: str
    user_id: int
