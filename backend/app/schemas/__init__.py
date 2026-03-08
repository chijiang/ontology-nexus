# backend/app/schemas/__init__.py
"""
Pydantic Schemas Package

Exports all schema definitions for API request/response validation.
"""

from app.schemas.role import (
    # Enums
    ApprovalStatus,
    # Role Schemas
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleDetailResponse,
    # UserRole Schemas
    AssignRoleRequest,
    # Permission Schemas
    PagePermissionCreate,
    ActionPermissionCreate,
    EntityPermissionCreate,
    # User Schemas
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    # User Approval
    ApproveUserRequest,
    RejectUserRequest,
    # Password Reset
    ResetPasswordResponse,
    ChangePasswordRequest,
    # Permission Cache
    PermissionCacheResponse,
    # Register Response
    RegisterPendingResponse,
)

from app.schemas.data_product import (
    # Enums
    ConnectionStatusEnum,
    SyncDirectionEnum,
    # Data Product Schemas
    DataProductCreate,
    DataProductUpdate,
    DataProductResponse,
    DataProductListResponse,
    ConnectionTestResponse,
    # Entity Mapping Schemas
    EntityMappingCreate,
    EntityMappingUpdate,
    EntityMappingResponse,
    # Property Mapping Schemas
    PropertyMappingCreate,
    PropertyMappingUpdate,
    PropertyMappingResponse,
    # Relationship Mapping Schemas
    RelationshipMappingCreate,
    RelationshipMappingUpdate,
    RelationshipMappingResponse,
    # Sync Schemas
    SyncRequest,
    SyncResult,
    SyncLogResponse,
    SyncStatusResponse,
)

from app.schemas.config import (
    # Config Schemas
    LLMConfigRequest,
    LLMConfigResponse,
    TestConnectionResponse,
)

from app.schemas.scheduled_task import (
    # Enums
    TaskTypeEnum,
    TaskStatusEnum,
    TriggeredByEnum,
    CronTemplateTypeEnum,
    # Scheduled Task Schemas
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    ScheduledTaskListResponse,
    # Task Execution Schemas
    TaskExecutionCreate,
    TaskExecutionResponse,
    TaskExecutionListResponse,
    # Cron Template Schemas
    CronTemplate,
    CronTemplateListResponse,
    # Manual Trigger Schema
    ManualTriggerRequest,
    ManualTriggerResponse,
    # Validation/Status Schemas
    CronValidationRequest,
    CronValidationResponse,
)

__all__ = [
    # Enums from role.py
    'ApprovalStatus',
    # Role Schemas
    'RoleCreate',
    'RoleUpdate',
    'RoleResponse',
    'RoleDetailResponse',
    # UserRole Schemas
    'AssignRoleRequest',
    # Permission Schemas
    'PagePermissionCreate',
    'ActionPermissionCreate',
    'EntityPermissionCreate',
    # User Schemas
    'UserCreate',
    'UserUpdate',
    'UserResponse',
    'UserListResponse',
    # User Approval
    'ApproveUserRequest',
    'RejectUserRequest',
    # Password Reset
    'ResetPasswordResponse',
    'ChangePasswordRequest',
    # Permission Cache
    'PermissionCacheResponse',
    # Register Response
    'RegisterPendingResponse',

    # Enums from data_product.py
    'ConnectionStatusEnum',
    'SyncDirectionEnum',
    # Data Product Schemas
    'DataProductCreate',
    'DataProductUpdate',
    'DataProductResponse',
    'DataProductListResponse',
    'ConnectionTestResponse',
    # Entity Mapping Schemas
    'EntityMappingCreate',
    'EntityMappingUpdate',
    'EntityMappingResponse',
    # Property Mapping Schemas
    'PropertyMappingCreate',
    'PropertyMappingUpdate',
    'PropertyMappingResponse',
    # Relationship Mapping Schemas
    'RelationshipMappingCreate',
    'RelationshipMappingUpdate',
    'RelationshipMappingResponse',
    # Sync Schemas
    'SyncRequest',
    'SyncResult',
    'SyncLogResponse',
    'SyncStatusResponse',

    # Config Schemas
    'LLMConfigRequest',
    'LLMConfigResponse',
    'TestConnectionResponse',

    # Enums from scheduled_task.py
    'TaskTypeEnum',
    'TaskStatusEnum',
    'TriggeredByEnum',
    'CronTemplateTypeEnum',
    # Scheduled Task Schemas
    'ScheduledTaskCreate',
    'ScheduledTaskUpdate',
    'ScheduledTaskResponse',
    'ScheduledTaskListResponse',
    # Task Execution Schemas
    'TaskExecutionCreate',
    'TaskExecutionResponse',
    'TaskExecutionListResponse',
    # Cron Template Schemas
    'CronTemplate',
    'CronTemplateListResponse',
    # Manual Trigger Schema
    'ManualTriggerRequest',
    'ManualTriggerResponse',
    # Validation/Status Schemas
    'CronValidationRequest',
    'CronValidationResponse',
]
