# backend/app/api/data_mappings.py
"""
数据映射 API

提供实体映射、属性映射和关系映射的管理功能。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
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
    SyncDirection,
)
from app.models.scheduled_task import ScheduledTask
from app.schemas.data_product import (
    EntityMappingCreate,
    EntityMappingUpdate,
    EntityMappingResponse,
    PropertyMappingCreate,
    PropertyMappingUpdate,
    PropertyMappingResponse,
    RelationshipMappingCreate,
    RelationshipMappingUpdate,
    RelationshipMappingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-mappings", tags=["data-mappings"])


# ============================================================================
# Entity Mapping CRUD
# ============================================================================


@router.post(
    "/entity-mappings",
    response_model=EntityMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_entity_mapping(
    data: EntityMappingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建实体映射"""
    # 检查数据产品是否存在
    product_result = await db.execute(
        select(DataProduct).where(DataProduct.id == data.data_product_id)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"数据产品 ID={data.data_product_id} 不存在",
        )

    # 检查是否已存在相同的映射
    existing = await db.execute(
        select(EntityMapping).where(
            EntityMapping.data_product_id == data.data_product_id,
            EntityMapping.ontology_class_name == data.ontology_class_name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该数据产品已存在类 '{data.ontology_class_name}' 的映射",
        )

    mapping = EntityMapping(
        data_product_id=data.data_product_id,
        ontology_class_name=data.ontology_class_name,
        grpc_message_type=data.grpc_message_type,
        list_method=data.list_method,
        get_method=data.get_method,
        create_method=data.create_method,
        update_method=data.update_method,
        delete_method=data.delete_method,
        sync_enabled=data.sync_enabled,
        sync_direction=SyncDirection(data.sync_direction.value),
        id_field_mapping=data.id_field_mapping,
        name_field_mapping=data.name_field_mapping,
    )

    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)

    logger.info(
        f"Created entity mapping: {data.ontology_class_name} <-> {data.grpc_message_type}"
    )

    return EntityMappingResponse(
        id=mapping.id,
        data_product_id=mapping.data_product_id,
        ontology_class_name=mapping.ontology_class_name,
        grpc_message_type=mapping.grpc_message_type,
        list_method=mapping.list_method,
        get_method=mapping.get_method,
        create_method=mapping.create_method,
        update_method=mapping.update_method,
        delete_method=mapping.delete_method,
        sync_enabled=mapping.sync_enabled,
        sync_direction=data.sync_direction,
        id_field_mapping=mapping.id_field_mapping,
        name_field_mapping=mapping.name_field_mapping,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        property_mapping_count=0,
    )


@router.get("/entity-mappings", response_model=List[EntityMappingResponse])
async def list_entity_mappings(
    data_product_id: int = None,
    ontology_class_name: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出实体映射"""
    query = select(EntityMapping).options(selectinload(EntityMapping.property_mappings))

    if data_product_id:
        query = query.where(EntityMapping.data_product_id == data_product_id)
    if ontology_class_name:
        query = query.where(EntityMapping.ontology_class_name == ontology_class_name)

    result = await db.execute(query)
    mappings = result.scalars().all()

    # Get all scheduled task target_ids for type='sync' to check existence
    mapping_ids = [m.id for m in mappings]
    has_schedule_map = {}
    if mapping_ids:
        schedule_result = await db.execute(
            select(ScheduledTask.target_id)
            .where(ScheduledTask.task_type == "sync")
            .where(ScheduledTask.target_id.in_(mapping_ids))
        )
        scheduled_ids = set(schedule_result.scalars().all())
        has_schedule_map = {mid: (mid in scheduled_ids) for mid in mapping_ids}

    return [
        EntityMappingResponse(
            id=m.id,
            data_product_id=m.data_product_id,
            ontology_class_name=m.ontology_class_name,
            grpc_message_type=m.grpc_message_type,
            list_method=m.list_method,
            get_method=m.get_method,
            create_method=m.create_method,
            update_method=m.update_method,
            delete_method=m.delete_method,
            sync_enabled=m.sync_enabled,
            sync_direction=m.sync_direction.value if m.sync_direction else "pull",
            id_field_mapping=m.id_field_mapping,
            name_field_mapping=m.name_field_mapping,
            created_at=m.created_at,
            updated_at=m.updated_at,
            property_mapping_count=len(m.property_mappings),
            has_schedule=has_schedule_map.get(m.id, False),
        )
        for m in mappings
    ]


@router.get("/entity-mappings/{mapping_id}", response_model=EntityMappingResponse)
async def get_entity_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取实体映射详情"""
    result = await db.execute(
        select(EntityMapping)
        .options(selectinload(EntityMapping.property_mappings))
        .where(EntityMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"实体映射 ID={mapping_id} 不存在",
        )

    # Check for schedule
    schedule_result = await db.execute(
        select(ScheduledTask.id)
        .where(ScheduledTask.task_type == "sync")
        .where(ScheduledTask.target_id == mapping_id)
        .limit(1)
    )
    has_schedule = schedule_result.scalar_one_or_none() is not None

    return EntityMappingResponse(
        id=mapping.id,
        data_product_id=mapping.data_product_id,
        ontology_class_name=mapping.ontology_class_name,
        grpc_message_type=mapping.grpc_message_type,
        list_method=mapping.list_method,
        get_method=mapping.get_method,
        create_method=mapping.create_method,
        update_method=mapping.update_method,
        delete_method=mapping.delete_method,
        sync_enabled=mapping.sync_enabled,
        sync_direction=(
            mapping.sync_direction.value if mapping.sync_direction else "pull"
        ),
        id_field_mapping=mapping.id_field_mapping,
        name_field_mapping=mapping.name_field_mapping,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        property_mapping_count=len(mapping.property_mappings),
        has_schedule=has_schedule,
    )


@router.put("/entity-mappings/{mapping_id}", response_model=EntityMappingResponse)
async def update_entity_mapping(
    mapping_id: int,
    data: EntityMappingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新实体映射"""
    result = await db.execute(
        select(EntityMapping)
        .options(selectinload(EntityMapping.property_mappings))
        .where(EntityMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"实体映射 ID={mapping_id} 不存在",
        )

    update_data = data.model_dump(exclude_unset=True)

    # 处理 sync_direction 枚举转换
    if "sync_direction" in update_data and update_data["sync_direction"]:
        update_data["sync_direction"] = SyncDirection(
            update_data["sync_direction"].value
        )

    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.commit()
    await db.refresh(mapping)

    # Check for schedule
    schedule_result = await db.execute(
        select(ScheduledTask.id)
        .where(ScheduledTask.task_type == "sync")
        .where(ScheduledTask.target_id == mapping_id)
        .limit(1)
    )
    has_schedule = schedule_result.scalar_one_or_none() is not None

    return EntityMappingResponse(
        id=mapping.id,
        data_product_id=mapping.data_product_id,
        ontology_class_name=mapping.ontology_class_name,
        grpc_message_type=mapping.grpc_message_type,
        list_method=mapping.list_method,
        get_method=mapping.get_method,
        create_method=mapping.create_method,
        update_method=mapping.update_method,
        delete_method=mapping.delete_method,
        sync_enabled=mapping.sync_enabled,
        sync_direction=(
            mapping.sync_direction.value if mapping.sync_direction else "pull"
        ),
        id_field_mapping=mapping.id_field_mapping,
        name_field_mapping=mapping.name_field_mapping,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        property_mapping_count=len(mapping.property_mappings),
        has_schedule=has_schedule,
    )


@router.delete("/entity-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除实体映射（同时删除关联的属性映射）"""
    result = await db.execute(
        select(EntityMapping).where(EntityMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"实体映射 ID={mapping_id} 不存在",
        )

    await db.delete(mapping)
    await db.commit()

    logger.info(f"Deleted entity mapping ID={mapping_id}")


# ============================================================================
# Property Mapping CRUD
# ============================================================================


@router.post(
    "/entity-mappings/{mapping_id}/properties",
    response_model=PropertyMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property_mapping(
    mapping_id: int,
    data: PropertyMappingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加属性映射"""
    # 检查实体映射是否存在
    entity_result = await db.execute(
        select(EntityMapping).where(EntityMapping.id == mapping_id)
    )
    if not entity_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"实体映射 ID={mapping_id} 不存在",
        )

    # 检查是否已存在相同的属性映射
    existing = await db.execute(
        select(PropertyMapping).where(
            PropertyMapping.entity_mapping_id == mapping_id,
            PropertyMapping.ontology_property == data.ontology_property,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"属性 '{data.ontology_property}' 的映射已存在",
        )

    prop_mapping = PropertyMapping(
        entity_mapping_id=mapping_id,
        ontology_property=data.ontology_property,
        grpc_field=data.grpc_field,
        transform_expression=data.transform_expression,
        inverse_transform=data.inverse_transform,
        is_required=data.is_required,
        sync_on_update=data.sync_on_update,
    )

    db.add(prop_mapping)
    await db.commit()
    await db.refresh(prop_mapping)

    logger.info(
        f"Created property mapping: {data.ontology_property} <-> {data.grpc_field}"
    )
    return prop_mapping


@router.get(
    "/entity-mappings/{mapping_id}/properties",
    response_model=List[PropertyMappingResponse],
)
async def list_property_mappings(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出实体映射的属性映射"""
    result = await db.execute(
        select(PropertyMapping).where(PropertyMapping.entity_mapping_id == mapping_id)
    )
    return result.scalars().all()


@router.put("/property-mappings/{prop_id}", response_model=PropertyMappingResponse)
async def update_property_mapping(
    prop_id: int,
    data: PropertyMappingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新属性映射"""
    result = await db.execute(
        select(PropertyMapping).where(PropertyMapping.id == prop_id)
    )
    prop_mapping = result.scalar_one_or_none()

    if not prop_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"属性映射 ID={prop_id} 不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prop_mapping, key, value)

    await db.commit()
    await db.refresh(prop_mapping)

    return prop_mapping


@router.delete("/property-mappings/{prop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_mapping(
    prop_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除属性映射"""
    result = await db.execute(
        select(PropertyMapping).where(PropertyMapping.id == prop_id)
    )
    prop_mapping = result.scalar_one_or_none()

    if not prop_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"属性映射 ID={prop_id} 不存在",
        )

    await db.delete(prop_mapping)
    await db.commit()


# ============================================================================
# Relationship Mapping CRUD
# ============================================================================


@router.post(
    "/relationship-mappings",
    response_model=RelationshipMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship_mapping(
    data: RelationshipMappingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建关系映射"""
    # 检查源实体映射
    source_result = await db.execute(
        select(EntityMapping).where(EntityMapping.id == data.source_entity_mapping_id)
    )
    source_mapping = source_result.scalar_one_or_none()
    if not source_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"源实体映射 ID={data.source_entity_mapping_id} 不存在",
        )

    # 检查目标实体映射
    target_result = await db.execute(
        select(EntityMapping).where(EntityMapping.id == data.target_entity_mapping_id)
    )
    target_mapping = target_result.scalar_one_or_none()
    if not target_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标实体映射 ID={data.target_entity_mapping_id} 不存在",
        )

    # 检查是否已存在相同的关系映射
    existing = await db.execute(
        select(RelationshipMapping).where(
            RelationshipMapping.source_entity_mapping_id
            == data.source_entity_mapping_id,
            RelationshipMapping.target_entity_mapping_id
            == data.target_entity_mapping_id,
            RelationshipMapping.ontology_relationship == data.ontology_relationship,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"关系 '{data.ontology_relationship}' 的映射已存在",
        )

    rel_mapping = RelationshipMapping(
        source_entity_mapping_id=data.source_entity_mapping_id,
        target_entity_mapping_id=data.target_entity_mapping_id,
        ontology_relationship=data.ontology_relationship,
        source_fk_field=data.source_fk_field,
        target_id_field=data.target_id_field,
        sync_enabled=data.sync_enabled,
    )

    db.add(rel_mapping)
    await db.commit()
    await db.refresh(rel_mapping)

    logger.info(f"Created relationship mapping: {data.ontology_relationship}")

    return RelationshipMappingResponse(
        id=rel_mapping.id,
        source_entity_mapping_id=rel_mapping.source_entity_mapping_id,
        target_entity_mapping_id=rel_mapping.target_entity_mapping_id,
        ontology_relationship=rel_mapping.ontology_relationship,
        source_fk_field=rel_mapping.source_fk_field,
        target_id_field=rel_mapping.target_id_field,
        sync_enabled=rel_mapping.sync_enabled,
        created_at=rel_mapping.created_at,
        source_ontology_class=source_mapping.ontology_class_name,
        target_ontology_class=target_mapping.ontology_class_name,
    )


@router.get("/relationship-mappings", response_model=List[RelationshipMappingResponse])
async def list_relationship_mappings(
    source_entity_mapping_id: int = None,
    target_entity_mapping_id: int = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出关系映射"""
    query = select(RelationshipMapping).options(
        selectinload(RelationshipMapping.source_entity_mapping),
        selectinload(RelationshipMapping.target_entity_mapping),
    )

    if source_entity_mapping_id:
        query = query.where(
            RelationshipMapping.source_entity_mapping_id == source_entity_mapping_id
        )
    if target_entity_mapping_id:
        query = query.where(
            RelationshipMapping.target_entity_mapping_id == target_entity_mapping_id
        )

    result = await db.execute(query)
    mappings = result.scalars().all()

    return [
        RelationshipMappingResponse(
            id=m.id,
            source_entity_mapping_id=m.source_entity_mapping_id,
            target_entity_mapping_id=m.target_entity_mapping_id,
            ontology_relationship=m.ontology_relationship,
            source_fk_field=m.source_fk_field,
            target_id_field=m.target_id_field,
            sync_enabled=m.sync_enabled,
            created_at=m.created_at,
            source_ontology_class=(
                m.source_entity_mapping.ontology_class_name
                if m.source_entity_mapping
                else None
            ),
            target_ontology_class=(
                m.target_entity_mapping.ontology_class_name
                if m.target_entity_mapping
                else None
            ),
        )
        for m in mappings
    ]


@router.delete(
    "/relationship-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_relationship_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除关系映射"""
    result = await db.execute(
        select(RelationshipMapping).where(RelationshipMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"关系映射 ID={mapping_id} 不存在",
        )

    await db.delete(mapping)
    await db.commit()

    logger.info(f"Deleted relationship mapping ID={mapping_id}")
