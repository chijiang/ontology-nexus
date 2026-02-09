# backend/app/api/data_products.py
"""
数据产品管理 API

提供数据产品的注册、配置、连接测试和 Schema 发现功能。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.data_product import (
    DataProduct,
    EntityMapping,
    PropertyMapping,
    RelationshipMapping,
    ConnectionStatus,
)
from app.schemas.data_product import (
    DataProductCreate,
    DataProductUpdate,
    DataProductResponse,
    DataProductListResponse,
    ConnectionTestResponse,
    GrpcServiceSchema,
    GrpcMethodInfo,
    SyncLogResponse,
)
from app.services.grpc_client import DynamicGrpcClient
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-products", tags=["data-products"])


# ============================================================================
# Data Product CRUD
# ============================================================================


@router.post(
    "", response_model=DataProductResponse, status_code=status.HTTP_201_CREATED
)
async def create_data_product(
    data: DataProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """注册新的数据产品"""
    # 检查名称是否已存在
    existing = await db.execute(
        select(DataProduct).where(DataProduct.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"数据产品 '{data.name}' 已存在",
        )

    product = DataProduct(
        name=data.name,
        description=data.description,
        grpc_host=data.grpc_host,
        grpc_port=data.grpc_port,
        service_name=data.service_name,
        proto_content=data.proto_content,
        is_active=data.is_active,
        connection_status=ConnectionStatus.UNKNOWN,
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)

    logger.info(
        f"Created data product: {product.name} ({product.grpc_host}:{product.grpc_port})"
    )
    return product


@router.get("", response_model=DataProductListResponse)
async def list_data_products(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出所有数据产品"""
    query = select(DataProduct)
    if active_only:
        query = query.where(DataProduct.is_active == True)

    # 获取总数
    count_query = select(func.count(DataProduct.id))
    if active_only:
        count_query = count_query.where(DataProduct.is_active == True)
    total = (await db.execute(count_query)).scalar()

    # 获取列表
    query = query.offset(skip).limit(limit).order_by(DataProduct.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return DataProductListResponse(items=items, total=total)


@router.get("/{product_id}", response_model=DataProductResponse)
async def get_data_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取数据产品详情"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    return product


@router.put("/{product_id}", response_model=DataProductResponse)
async def update_data_product(
    product_id: int,
    data: DataProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新数据产品配置"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    # 检查名称冲突
    if data.name and data.name != product.name:
        existing = await db.execute(
            select(DataProduct).where(DataProduct.name == data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"数据产品名称 '{data.name}' 已被使用",
            )

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)

    logger.info(f"Updated data product: {product.name}")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除数据产品（同时删除所有关联的映射）"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    await db.delete(product)
    await db.commit()

    logger.info(f"Deleted data product: {product.name}")


# ============================================================================
# Connection Testing & Schema Discovery
# ============================================================================


@router.post("/{product_id}/test-connection", response_model=ConnectionTestResponse)
async def test_connection(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """测试 gRPC 连接"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    try:
        async with DynamicGrpcClient(product.grpc_host, product.grpc_port) as client:
            success, message, latency = await client.test_connection()

            # 更新连接状态
            if success:
                product.connection_status = ConnectionStatus.CONNECTED
                product.last_error = None
            else:
                product.connection_status = ConnectionStatus.DISCONNECTED
                product.last_error = message

            product.last_health_check = datetime.utcnow()
            await db.commit()

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"连接失败: {message}",
                )

            return ConnectionTestResponse(
                success=success, message=message, latency_ms=latency
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection for product {product_id}: {e}")
        product.connection_status = ConnectionStatus.DISCONNECTED
        product.last_error = str(e)
        product.last_health_check = datetime.utcnow()
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"连接异常: {str(e)}",
        )


@router.get("/{product_id}/schema", response_model=GrpcServiceSchema)
async def get_service_schema(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 gRPC 服务 Schema（使用 Server Reflection）"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    async with DynamicGrpcClient(product.grpc_host, product.grpc_port) as client:
        try:
            info = await client.get_service_info(product.service_name)

            methods = [
                GrpcMethodInfo(
                    name=m["name"],
                    input_type=m["input_type"].split(".")[-1],
                    output_type=m["output_type"].split(".")[-1],
                    is_streaming=m["is_streaming"],
                )
                for m in info["methods"]
            ]

            message_types = [
                {
                    "name": mt["name"],
                    "fields": [
                        {
                            "name": f["name"],
                            "type": f["type"],
                            "label": f[
                                "label"
                            ],  # Note: frontend might need transformation
                        }
                        for f in mt["fields"]
                    ],
                }
                for mt in info["message_types"]
            ]

            return GrpcServiceSchema(
                service_name=product.service_name,
                methods=methods,
                message_types=message_types,
            )
        except Exception as e:
            logger.error(f"Failed to get schema for {product.name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取 Schema 失败: {str(e)}",
            )


@router.get("/{product_id}/methods")
async def list_available_methods(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出数据产品的可用 gRPC 方法"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    async with DynamicGrpcClient(product.grpc_host, product.grpc_port) as client:
        try:
            services = await client.list_services()

            all_methods = [
                {
                    "service": s,
                    "is_target": s == product.service_name
                    or s.endswith(f".{product.service_name}"),
                }
                for s in services
            ]

            return {"methods": all_methods}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取方法列表失败: {str(e)}",
            )


# ============================================================================
# Entity Mappings
# ============================================================================


@router.get("/{product_id}/entity-mappings")
async def list_entity_mappings(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出数据产品的所有实体映射"""
    result = await db.execute(select(DataProduct).where(DataProduct.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={product_id} 不存在",
        )

    # 获取映射列表以及属性映射数量
    mappings_result = await db.execute(
        select(EntityMapping)
        .options(selectinload(EntityMapping.property_mappings))
        .where(EntityMapping.data_product_id == product_id)
    )
    mappings = mappings_result.scalars().all()

    # 构建响应
    items = []
    for mapping in mappings:
        items.append(
            {
                "id": mapping.id,
                "data_product_id": mapping.data_product_id,
                "ontology_class_name": mapping.ontology_class_name,
                "grpc_message_type": mapping.grpc_message_type,
                "list_method": mapping.list_method,
                "get_method": mapping.get_method,
                "create_method": mapping.create_method,
                "update_method": mapping.update_method,
                "delete_method": mapping.delete_method,
                "sync_enabled": mapping.sync_enabled,
                "sync_direction": (
                    mapping.sync_direction.value if mapping.sync_direction else "pull"
                ),
                "id_field_mapping": mapping.id_field_mapping,
                "name_field_mapping": mapping.name_field_mapping,
                "created_at": (
                    mapping.created_at.isoformat() if mapping.created_at else None
                ),
                "updated_at": (
                    mapping.updated_at.isoformat() if mapping.updated_at else None
                ),
                "property_mapping_count": len(mapping.property_mappings),
            }
        )

    return {"items": items, "total": len(items)}


# ============================================================================
# Synchronization
# ============================================================================


@router.post("/{product_id}/sync", response_model=SyncLogResponse)
async def trigger_sync(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发数据产品同步"""
    sync_service = SyncService(db)
    try:
        # 这里为了简单直接阻塞运行，在大规模场景下应使用 BackgroundTasks 或 Celery
        result = await sync_service.sync_data_product(product_id)

        # 获取最新的日志记录
        logs = await sync_service.get_sync_logs(product_id=product_id, limit=1)
        if not logs:
            raise HTTPException(status_code=500, detail="同步已触发但未找到日志")
        return logs[0]
    except Exception as e:
        logger.exception(f"Sync failed for product {product_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失败: {str(e)}",
        )


@router.get("/{product_id}/sync-logs", response_model=List[SyncLogResponse])
async def list_sync_logs(
    product_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询同步日志"""
    sync_service = SyncService(db)
    return await sync_service.get_sync_logs(product_id=product_id, limit=limit)
