# backend/app/schemas/data_product.py
"""
Pydantic Schemas for Data Product and Mapping APIs

这些 schema 用于 API 请求/响应的验证和序列化。
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ConnectionStatusEnum(str, Enum):
    """连接状态枚举"""

    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SyncDirectionEnum(str, Enum):
    """同步方向枚举"""

    PULL = "pull"
    PUSH = "push"
    BIDIRECTIONAL = "bidirectional"


# ============================================================================
# Data Product Schemas
# ============================================================================


class DataProductCreate(BaseModel):
    """创建数据产品请求"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    grpc_host: str = Field(..., min_length=1, max_length=255)
    grpc_port: int = Field(default=50051, ge=1, le=65535)
    service_name: str = Field(..., min_length=1, max_length=255)
    proto_content: Optional[str] = None
    is_active: bool = True


class DataProductUpdate(BaseModel):
    """更新数据产品请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    grpc_host: Optional[str] = Field(None, min_length=1, max_length=255)
    grpc_port: Optional[int] = Field(None, ge=1, le=65535)
    service_name: Optional[str] = Field(None, min_length=1, max_length=255)
    proto_content: Optional[str] = None
    is_active: Optional[bool] = None


class DataProductResponse(BaseModel):
    """数据产品响应"""

    id: int
    name: str
    description: Optional[str]
    grpc_host: str
    grpc_port: int
    service_name: str
    connection_status: ConnectionStatusEnum
    last_health_check: Optional[datetime]
    last_error: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataProductListResponse(BaseModel):
    """数据产品列表响应"""

    items: List[DataProductResponse]
    total: int


class ConnectionTestResponse(BaseModel):
    """连接测试响应"""

    success: bool
    message: str
    latency_ms: Optional[float] = None


class GrpcMethodInfo(BaseModel):
    """gRPC 方法信息"""

    name: str
    input_type: str
    output_type: str
    is_streaming: bool = False


class GrpcServiceSchema(BaseModel):
    """gRPC 服务 Schema"""

    service_name: str
    methods: List[GrpcMethodInfo]
    message_types: List[dict]  # Message 类型定义


# ============================================================================
# Entity Mapping Schemas
# ============================================================================


class EntityMappingCreate(BaseModel):
    """创建实体映射请求"""

    data_product_id: int
    ontology_class_name: str = Field(..., min_length=1, max_length=255)
    grpc_message_type: str = Field(..., min_length=1, max_length=255)

    # gRPC 方法映射（可选）
    list_method: Optional[str] = None
    get_method: Optional[str] = None
    create_method: Optional[str] = None
    update_method: Optional[str] = None
    delete_method: Optional[str] = None

    # 同步配置
    sync_enabled: bool = True
    sync_direction: SyncDirectionEnum = SyncDirectionEnum.PULL

    # 字段映射
    id_field_mapping: str = "id"
    name_field_mapping: str = "name"


class EntityMappingUpdate(BaseModel):
    """更新实体映射请求"""

    grpc_message_type: Optional[str] = None
    list_method: Optional[str] = None
    get_method: Optional[str] = None
    create_method: Optional[str] = None
    update_method: Optional[str] = None
    delete_method: Optional[str] = None
    sync_enabled: Optional[bool] = None
    sync_direction: Optional[SyncDirectionEnum] = None
    id_field_mapping: Optional[str] = None
    name_field_mapping: Optional[str] = None


class EntityMappingResponse(BaseModel):
    """实体映射响应"""

    id: int
    data_product_id: int
    ontology_class_name: str
    grpc_message_type: str
    list_method: Optional[str]
    get_method: Optional[str]
    create_method: Optional[str]
    update_method: Optional[str]
    delete_method: Optional[str]
    sync_enabled: bool
    sync_direction: SyncDirectionEnum
    id_field_mapping: str
    name_field_mapping: str
    created_at: datetime
    updated_at: datetime

    # 附带信息
    property_mapping_count: Optional[int] = 0
    has_schedule: bool = False

    class Config:
        from_attributes = True


# ============================================================================
# Property Mapping Schemas
# ============================================================================


class PropertyMappingCreate(BaseModel):
    """创建属性映射请求"""

    ontology_property: str = Field(..., min_length=1, max_length=255)
    grpc_field: str = Field(..., min_length=1, max_length=255)
    transform_expression: Optional[str] = None
    inverse_transform: Optional[str] = None
    is_required: bool = False
    sync_on_update: bool = True


class PropertyMappingUpdate(BaseModel):
    """更新属性映射请求"""

    grpc_field: Optional[str] = None
    transform_expression: Optional[str] = None
    inverse_transform: Optional[str] = None
    is_required: Optional[bool] = None
    sync_on_update: Optional[bool] = None


class PropertyMappingResponse(BaseModel):
    """属性映射响应"""

    id: int
    entity_mapping_id: int
    ontology_property: str
    grpc_field: str
    transform_expression: Optional[str]
    inverse_transform: Optional[str]
    is_required: bool
    sync_on_update: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Relationship Mapping Schemas
# ============================================================================


class RelationshipMappingCreate(BaseModel):
    """创建关系映射请求"""

    source_entity_mapping_id: int
    target_entity_mapping_id: int
    ontology_relationship: str = Field(..., min_length=1, max_length=255)
    source_fk_field: str = Field(..., min_length=1, max_length=255)
    target_id_field: str = "id"
    sync_enabled: bool = True


class RelationshipMappingUpdate(BaseModel):
    """更新关系映射请求"""

    source_fk_field: Optional[str] = None
    target_id_field: Optional[str] = None
    sync_enabled: Optional[bool] = None


class RelationshipMappingResponse(BaseModel):
    """关系映射响应"""

    id: int
    source_entity_mapping_id: int
    target_entity_mapping_id: int
    ontology_relationship: str
    source_fk_field: str
    target_id_field: str
    sync_enabled: bool
    created_at: datetime

    # 附带的映射信息
    source_ontology_class: Optional[str] = None
    target_ontology_class: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Sync Schemas
# ============================================================================


class SyncRequest(BaseModel):
    """同步请求"""

    sync_type: str = "full"  # "full" or "incremental"


class SyncResult(BaseModel):
    """同步结果"""

    success: bool
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    errors: List[str] = []
    duration_ms: float


class SyncLogResponse(BaseModel):
    """同步日志响应"""

    id: int
    data_product_id: Optional[int]
    entity_mapping_id: Optional[int]
    sync_type: Optional[str]
    direction: Optional[str]
    status: str
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncStatusResponse(BaseModel):
    """同步状态响应"""

    is_syncing: bool
    current_entity_mapping_id: Optional[int] = None
    progress_percent: Optional[float] = None
    last_sync: Optional[SyncLogResponse] = None
