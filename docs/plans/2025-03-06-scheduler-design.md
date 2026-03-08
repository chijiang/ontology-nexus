# 全局定时器功能设计文档

**状态**: ✅ 已实现 (2025-03-06)
**实现分支**: scheduler-implementation
**合并状态**: 待合并

**日期**: 2025-03-06
**作者**: Claude Code
**原始状态**: 设计阶段

## 1. 概述

### 1.1 目标

为KG-Agent服务增加全局定时器功能，主要服务于两个场景：
1. 实体数据绑定时自动从数据产品中同步数据，支持自定义同步频率
2. Business Rule支持定时触发（cron表达式）

### 1.2 技术选型

- **调度器**: APScheduler (AsyncIOScheduler)
- **持久化**: PostgreSQL (SQLAlchemy JobStore)
- **前端**: 灵活的cron模板 + 手动输入

## 2. 数据库设计

### 2.1 定时任务表 (scheduled_tasks)

```python
class ScheduledTask(Base):
    """定时任务配置表"""

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 任务类型和基本信息
    task_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'sync' | 'rule'
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # data_product_id 或 rule_id

    # 调度配置
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)

    # 状态控制
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # 看门狗配置
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100

    # 元数据
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
```

### 2.2 任务执行日志表 (task_executions)

```python
class TaskExecution(Base):
    """任务执行日志表"""

    __tablename__ = "task_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("scheduled_tasks.id"), nullable=False, index=True)

    # 执行状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # 'pending' | 'running' | 'completed' | 'failed' | 'timeout'

    # 时间记录
    started_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)

    # 执行结果
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 重试信息
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 上下文信息
    triggered_by: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'scheduler' | 'manual' | 'retry'
```

## 3. 核心服务设计

### 3.1 SchedulerService (调度服务)

```python
class SchedulerService:
    """全局定时调度服务"""

    def __init__(
        self,
        db_session_factory,
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300
    ):
        self.scheduler = AsyncIOScheduler()
        self.db_session_factory = db_session_factory
        self.executor = TaskExecutor(
            max_concurrent_tasks=max_concurrent_tasks,
            default_timeout=default_timeout
        )
        self.repository = ScheduledTaskRepository()

    async def initialize(self):
        """初始化scheduler，从数据库加载所有启用的任务"""

    async def add_task(self, task: ScheduledTask) -> str:
        """添加新任务到scheduler"""

    async def update_task(self, task_id: int, updates: dict) -> bool:
        """更新任务配置（下次执行生效）"""

    async def remove_task(self, task_id: int) -> bool:
        """移除任务"""

    async def pause_task(self, task_id: int) -> bool:
        """暂停任务"""

    async def resume_task(self, task_id: int) -> bool:
        """恢复任务"""

    async def trigger_task_manually(self, task_id: int) -> dict:
        """手动触发任务执行"""

    async def get_task_status(self, task_id: int) -> dict:
        """获取任务当前状态"""

    async def get_execution_history(
        self, task_id: int, limit: int = 50
    ) -> list[TaskExecution]:
        """获取任务执行历史"""

    async def shutdown(self):
        """优雅关闭scheduler"""
```

### 3.2 TaskExecutor (任务执行器)

```python
class TaskExecutor:
    """任务执行器，负责实际的任务执行和看门狗机制"""

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: int = 300
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.default_timeout = default_timeout
        self.running_tasks: dict[int, asyncio.Task] = {}

    async def execute_task(
        self,
        task: ScheduledTask,
        triggered_by: str = "scheduler"
    ) -> dict:
        """执行单个任务，包含看门狗机制"""

    async def _execute_with_watchdog(
        self,
        task: ScheduledTask,
        execution: TaskExecution
    ) -> dict:
        """带看门狗保护的执行"""

    def _should_retry(self, error: Exception) -> bool:
        """判断错误是否可重试"""

    async def _cancel_running_task(self, task_id: int) -> bool:
        """取消正在运行的任务"""

    def get_running_tasks(self) -> list[int]:
        """获取当前运行中的任务ID列表"""
```

### 3.3 智能重试策略

```python
# 可重试错误类型
RETRYABLE_ERROR_PATTERNS = [
    r"connection.*timeout",
    r"network.*unreachable",
    r"503 Service Unavailable",
    r"504 Gateway Timeout",
    r"temporarily unavailable",
    r"Connection refused",
]

# 不可重试错误类型
NON_RETRYABLE_ERROR_PATTERNS = [
    r"authentication.*failed",
    r"unauthorized",
    r"401 Unauthorized",
    r"403 Forbidden",
    r"invalid.*format",
    r"validation.*error",
    r"400 Bad Request",
]
```

## 4. API设计

### 4.1 定时任务管理API

```
POST   /api/scheduled-tasks              # 创建任务
GET    /api/scheduled-tasks              # 列表查询
GET    /api/scheduled-tasks/{id}         # 获取详情
PUT    /api/scheduled-tasks/{id}         # 更新任务
DELETE /api/scheduled-tasks/{id}         # 删除任务
POST   /api/scheduled-tasks/{id}/pause   # 暂停任务
POST   /api/scheduled-tasks/{id}/resume  # 恢复任务
POST   /api/scheduled-tasks/{id}/trigger # 手动触发
```

### 4.2 执行日志API

```
GET    /api/task-executions              # 执行日志列表
GET    /api/task-executions/{id}         # 执行详情
GET    /api/scheduled-tasks/{id}/executions  # 任务执行历史
```

### 4.3 数据产品API扩展

```
GET    /api/data-products/{id}/sync-schedule     # 获取同步计划
PUT    /api/data-products/{id}/sync-schedule     # 设置同步计划
DELETE /api/data-products/{id}/sync-schedule     # 删除同步计划
```

### 4.4 规则API扩展

```
GET    /api/rules/{id}/schedule        # 获取规则定时配置
PUT    /api/rules/{id}/schedule        # 设置规则定时配置
DELETE /api/rules/{id}/schedule        # 删除规则定时配置
```

## 5. 前端界面设计

### 5.1 数据产品页面 - 自动同步配置

```
┌─────────────────────────────────────────────────────────┐
│ 数据产品详情                                              │
├─────────────────────────────────────────────────────────┤
│ 基本信息...                                               │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 自动同步设置                           [启用] □        │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 同步频率:                                            │ │
│ │ ○ 按间隔: 每 [30▼] [分钟▼]                           │ │
│ │ ○ 按时间: 每天 [02▼:[00▼]                            │ │
│ │ ○ 高级: [0 */5 * * *]                    │ │
│ │                                                     │ │
│ │ 高级选项:                                            │ │
│ │   超时时间: [300] 秒                                 │ │
│ │   最大重试: [3] 次                                   │ │
│ │   重试间隔: [60] 秒                                  │ │
│ │                                                     │ │
│ │ [保存配置]                                           │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 最近同步:                                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 2025-03-06 10:30  成功  120条记录                   │ │
│ │ 2025-03-06 10:00  成功  118条记录                   │ │
│ │ 2025-03-06 09:30  失败  连接超时                     │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 5.2 规则页面 - 定时触发配置

```
┌─────────────────────────────────────────────────────────┐
│ 规则详情                                                 │
├─────────────────────────────────────────────────────────┤
│ 基本信息...                                               │
│                                                         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 触发方式                                              │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ ○ 事件触发  实体: [Supplier▼]  属性: [status▼]      │ │
│ │ ○ 定时触发                                          │ │
│ │ ○ 混合触发  (事件 + 定时)                            │ │
│ │                                                     │ │
│ │ [定时触发配置展开▼]                                   │ │
│ │ ┌─────────────────────────────────────────────────┐ │ │
│ │ │ 触发频率:                                        │ │ │
│ │ │ ○ 按间隔: 每 [1▼] [小时▼]                      │ │ │
│ │ │ ○ 按时间: 每周一 [09▼:[00▼]                     │ │ │
│ │ │ ○ 高级: [0 9 * * 1]                   │ │ │
│ │ │                                                 │ │ │
│ │ │ 高级选项:                                        │ │ │
│ │ │   超时时间: [120] 秒                             │ │ │
│ │ │   最大重试: [2] 次                               │ │ │
│ │ │                                                 │ │ │
│ │ │ [保存配置]                                      │ │ │
│ │ └─────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 最近执行:                                               │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 2025-03-06 09:00  定时触发  成功                     │ │
│ │ 2025-03-06 08:00  定时触发  成功                     │ │
│ │ 2025-03-06 07:55  事件触发  成功 (Supplier.status变更) │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 5.3 Cron模板组件设计

```typescript
interface CronTemplate {
  type: 'interval' | 'specific' | 'advanced';
  interval?: {
    value: number;
    unit: 'second' | 'minute' | 'hour' | 'day';
  };
  specific?: {
    frequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
    time?: string;  // HH:MM
    dayOfWeek?: number;  // 0-6
    dayOfMonth?: number;  // 1-31
  };
  advanced?: string;  // raw cron expression
}

// 模板转换函数
function templateToCron(template: CronTemplate): string
function cronToTemplate(cron: string): CronTemplate
```

## 6. 看门狗机制详情

### 6.1 并发控制
- 使用 `asyncio.Semaphore` 限制最大并发任务数
- 默认最大并发数: 10
- 可通过配置调整

### 6.2 超时控制
- 每个任务使用 `asyncio.wait_for` 包装
- 默认超时: 300秒 (5分钟)
- 数据同步任务: 600秒 (10分钟)
- 规则执行任务: 120秒 (2分钟)
- 超时后任务标记为 `timeout` 状态

### 6.3 队列管理
- APScheduler 内置 `max_instances=1` 防止任务堆积
- 同一任务的上次执行未完成时，跳过本次调度
- 记录跳过事件到日志

### 6.4 智能重试逻辑

```python
class RetryStrategy:
    @staticmethod
    def should_retry(error: Exception, attempt: int, max_retries: int) -> bool:
        if attempt >= max_retries:
            return False
        return RetryStrategy._is_retryable_error(error)

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        error_msg = str(error).lower()
        error_type = type(error).__name__

        # 检查是否为可重试错误
        for pattern in RETRYABLE_ERROR_PATTERNS:
            if re.search(pattern, error_msg):
                return True

        # 检查是否为不可重试错误
        for pattern in NON_RETRYABLE_ERROR_PATTERNS:
            if re.search(pattern, error_msg):
                return False

        # 默认网络相关错误可重试
        return any(keyword in error_type for keyword in [
            'Connection', 'Timeout', 'Network'
        ])
```

## 7. 应用生命周期集成

### 7.1 Startup流程

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === Startup ===
    await init_db()

    # ... 现有初始化代码 ...

    # 初始化定时调度服务
    scheduler_service = SchedulerService(
        db_session_factory=async_session,
        max_concurrent_tasks=settings.SCHEDULER_MAX_CONCURRENT,
        default_timeout=settings.SCHEDULER_DEFAULT_TIMEOUT
    )
    await scheduler_service.initialize()
    await scheduler_service.start()

    # 存储到app.state
    app.state.scheduler_service = scheduler_service

    yield

    # === Shutdown ===
    await scheduler_service.shutdown()
    await engine.dispose()
```

### 7.2 环境变量

```bash
# .env
SCHEDULER_MAX_CONCURRENT=10
SCHEDULER_DEFAULT_TIMEOUT=300
SCHEDULER_JOB_STORES=sqlalchemy
SCHEDULER_COALESCE=true
```

## 8. 错误处理和日志

### 8.1 日志级别

- **INFO**: 任务调度开始/完成、配置变更
- **WARNING**: 任务跳过、重试开始、超时警告
- **ERROR**: 任务失败、重试耗尽
- **DEBUG**: 详细的执行流程

### 8.2 错误分类

| 错误类型 | 是否重试 | 处理方式 |
|---------|---------|---------|
| 网络超时 | 是 | 自动重试，记录warning |
| 连接拒绝 | 是 | 自动重试，记录warning |
| 5xx错误 | 是 (503,504) | 自动重试，否则不重试 |
| 4xx错误 | 否 | 记录error，需人工处理 |
| 数据格式错误 | 否 | 记录error，需人工处理 |
| 超时 | 是 | 重试，但增加超时时间 |

## 9. 数据库迁移

创建 Alembic 迁移脚本:

```bash
uv run alembic revision -m "add scheduled tasks tables"
```

## 10. 实现优先级

### Phase 1: 核心功能 (高优先级)
1. 数据库表和迁移
2. SchedulerService 基础实现
3. TaskExecutor 和看门狗机制
4. 数据产品同步定时任务集成

### Phase 2: 规则集成 (中优先级)
1. 规则定时触发支持
2. 混合触发模式（事件+定时）
3. 规则执行日志集成

### Phase 3: 前端界面 (中优先级)
1. 数据产品自动同步配置UI
2. 规则定时触发配置UI
3. Cron模板组件
4. 执行历史展示

### Phase 4: 增强功能 (低优先级)
1. 任务执行统计和分析
2. 失败告警通知
3. 任务依赖关系
4. 任务分组管理
