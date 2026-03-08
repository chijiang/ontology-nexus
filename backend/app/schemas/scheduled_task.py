# backend/app/schemas/scheduled_task.py
"""
Pydantic Schemas for Scheduled Task APIs

这些 schema 用于 API 请求/响应的验证和序列化。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from typing import Literal
from enum import Enum


# ============================================================================
# Enums
# ============================================================================


class TaskTypeEnum(str, Enum):
    """任务类型枚举"""

    SYNC = "sync"
    RULE = "rule"


class TaskStatusEnum(str, Enum):
    """任务执行状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TriggeredByEnum(str, Enum):
    """触发方式枚举"""

    CRON = "cron"
    MANUAL = "manual"
    RETRY = "retry"


class CronTemplateTypeEnum(str, Enum):
    """Cron 模板类型枚举"""

    INTERVAL = "interval"  # 间隔执行
    SPECIFIC = "specific"  # 定时执行
    ADVANCED = "advanced"  # 高级表达式


# ============================================================================
# Scheduled Task Schemas
# ============================================================================


class ScheduledTaskBase(BaseModel):
    """定时任务基础 Schema"""

    task_type: Literal["sync", "rule"] = Field(..., description="任务类型")
    task_name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    target_id: int = Field(..., gt=0, description="关联目标ID")
    cron_expression: str = Field(..., min_length=1, max_length=100, description="Cron表达式")
    is_enabled: bool = Field(default=True, description="是否启用")
    timeout_seconds: int = Field(default=300, ge=1, le=3600, description="超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    retry_interval_seconds: int = Field(default=60, ge=1, le=3600, description="重试间隔（秒）")
    priority: int = Field(default=50, ge=0, le=100, description="优先级")
    description: Optional[str] = Field(None, description="任务描述")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """验证 Cron 表达式格式"""
        parts = v.strip().split()
        if not 5 <= len(parts) <= 7:
            raise ValueError("Cron expression must have 5-7 parts")
        return v


class ScheduledTaskCreate(ScheduledTaskBase):
    """创建定时任务请求"""

    pass


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""

    task_name: Optional[str] = Field(None, min_length=1, max_length=255)
    cron_expression: Optional[str] = Field(None, min_length=1, max_length=100)
    is_enabled: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_interval_seconds: Optional[int] = Field(None, ge=1, le=3600)
    priority: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """验证 Cron 表达式格式"""
        if v is not None:
            parts = v.strip().split()
            if not 5 <= len(parts) <= 7:
                raise ValueError("Cron expression must have 5-7 parts")
        return v


class ScheduledTaskResponse(BaseModel):
    """定时任务响应"""

    id: int
    task_type: str
    task_name: str
    target_id: int
    cron_expression: str
    is_enabled: bool
    timeout_seconds: int
    max_retries: int
    retry_interval_seconds: int
    priority: int
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskListResponse(BaseModel):
    """定时任务列表响应"""

    items: List[ScheduledTaskResponse]
    total: int


# ============================================================================
# Task Execution Schemas
# ============================================================================


class TaskExecutionBase(BaseModel):
    """任务执行基础 Schema"""

    status: Literal["pending", "running", "completed", "failed", "timeout"] = Field(
        ..., description="执行状态"
    )
    started_at: datetime = Field(..., description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    duration_seconds: Optional[float] = Field(None, description="执行时长（秒）")
    result_data: Optional[dict] = Field(None, description="执行结果数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    is_retry: bool = Field(default=False, description="是否为重试")
    triggered_by: Optional[Literal["cron", "manual", "retry"]] = Field(
        None, description="触发方式"
    )


class TaskExecutionCreate(TaskExecutionBase):
    """创建任务执行记录请求"""

    task_id: int = Field(..., gt=0, description="关联的定时任务ID")


class TaskExecutionResponse(BaseModel):
    """任务执行响应"""

    id: int
    task_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    result_data: Optional[dict]
    error_message: Optional[str]
    error_type: Optional[str]
    retry_count: int
    is_retry: bool
    triggered_by: Optional[str]

    model_config = {"from_attributes": True}


class TaskExecutionListResponse(BaseModel):
    """任务执行列表响应"""

    items: List[TaskExecutionResponse]
    total: int


# ============================================================================
# Cron Template Schemas
# ============================================================================


class CronTemplate(BaseModel):
    """Cron 表达式模板"""

    name: str = Field(..., description="模板名称")
    type: Literal["interval", "specific", "advanced"] = Field(..., description="模板类型")
    expression: str = Field(..., description="Cron 表达式")
    description: str = Field(..., description="模板描述")
    example: str = Field(..., description="示例说明")


class CronTemplateListResponse(BaseModel):
    """Cron 模板列表响应"""

    items: List[CronTemplate]


# ============================================================================
# Manual Trigger Schema
# ============================================================================


class ManualTriggerRequest(BaseModel):
    """手动触发任务请求"""

    task_id: int = Field(..., gt=0, description="要触发的定时任务ID")


class ManualTriggerResponse(BaseModel):
    """手动触发任务响应"""

    execution_id: int = Field(..., description="执行记录ID")
    task_id: int = Field(..., description="定时任务ID")
    status: str = Field(..., description="执行状态")
    message: str = Field(..., description="响应消息")


# ============================================================================
# Validation/Status Schemas
# ============================================================================


class CronValidationRequest(BaseModel):
    """Cron 表达式验证请求"""

    cron_expression: str = Field(..., description="要验证的 Cron 表达式")


class CronValidationResponse(BaseModel):
    """Cron 表达式验证响应"""

    is_valid: bool = Field(..., description="是否有效")
    message: str = Field(..., description="验证消息")
    next_run_times: Optional[List[datetime]] = Field(None, description="下次执行时间列表")
