# backend/app/api/graph.py
"""Graph API endpoints using PostgreSQL storage.

Replaces the original Neo4j-based implementation with PostgreSQL.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.pg_graph_storage import PGGraphStorage
from app.services.pg_graph_importer import PGGraphImporter
from app.rule_engine.event_emitter import GraphEventEmitter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/import")
async def import_graph(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导入 OWL/TTL 文件到 PostgreSQL 图存储"""
    content = await file.read()

    # 解析并导入
    from app.services.owl_parser import OWLParser

    parser = OWLParser()
    parser.load_from_string(content.decode("utf-8"))
    schema_triples, instance_triples = parser.classify_triples()

    importer = PGGraphImporter(db)
    schema_stats = await importer.import_schema(parser)
    instance_stats = await importer.import_instances(
        schema_triples, instance_triples
    )

    return {
        "message": "Graph imported successfully",
        "schema_stats": schema_stats,
        "instance_stats": instance_stats,
        "total": {
            "classes": schema_stats.get("classes", 0),
            "schema_properties": schema_stats.get("properties", 0),
            "nodes": instance_stats.get("nodes", 0),
            "relationships": instance_stats.get("relationships", 0),
        }
    }


@router.post("/clear")
async def clear_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清除全部图谱数据"""
    storage = PGGraphStorage(db)
    await storage.clear_graph()
    return {"message": "Graph cleared successfully"}


@router.get("/node/{uri:path}")
async def get_node(
    uri: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取节点详情"""
    storage = PGGraphStorage(db)

    # 首先尝试按 name 查找
    entity = await storage.get_entity_by_name(uri)
    if entity:
        return entity

    # 如果没找到，尝试按 URI 查找
    from app.models.graph import GraphEntity
    result = await db.execute(
        select(GraphEntity).where(GraphEntity.uri == uri)
    )
    entity = result.scalar_one_or_none()
    if entity:
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "properties": entity.properties or {}
        }

    raise HTTPException(status_code=404, detail="Node not found")


@router.get("/neighbors")
async def get_neighbors(
    name: str,
    hops: int = 1,
    direction: str = "both",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取节点邻居"""
    storage = PGGraphStorage(db)
    neighbors = await storage.get_instance_neighbors(name, hops, direction)
    return neighbors


@router.post("/path")
async def find_path(
    start_uri: str,
    end_uri: str,
    max_depth: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查找路径"""
    storage = PGGraphStorage(db)
    path = await storage.find_path_between_instances(start_uri, end_uri, max_depth)
    if not path:
        raise HTTPException(status_code=404, detail="Path not found")
    return path


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取图谱统计"""
    storage = PGGraphStorage(db)
    stats = await storage.get_graph_statistics()
    return stats


@router.get("/nodes")
async def get_nodes_by_label(
    label: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据标签获取节点"""
    storage = PGGraphStorage(db)
    nodes = await storage.get_instances_by_class(label, None, limit)
    return nodes


@router.get("/schema")
async def get_schema(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Schema 图（类和关系定义）"""
    storage = PGGraphStorage(db)

    # 获取所有 Schema 类节点
    nodes_data = await storage.get_ontology_classes()

    # 获取所有 Schema 关系
    rels_data = await storage.get_ontology_relationships()

    return {
        "nodes": nodes_data,
        "relationships": rels_data,
    }


@router.get("/instances/search")
async def search_instances(
    class_name: str,
    keyword: str = "",
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索实例，支持类名、关键词"""
    storage = PGGraphStorage(db)

    if keyword:
        instances = await storage.search_instances(keyword, class_name, limit)
    else:
        instances = await storage.get_instances_by_class(class_name, None, limit)

    return instances


@router.put("/entities/{entity_type}/{entity_id}")
async def update_entity(
    entity_type: str,
    entity_id: str,
    updates: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an entity and emit events for rule engine."""
    # Get event emitter from app state
    event_emitter: Optional[GraphEventEmitter] = getattr(
        request.app.state, "event_emitter", None
    )

    storage = PGGraphStorage(db, event_emitter=event_emitter)
    result = await storage.update_entity(entity_type, entity_id, updates)
    return result


@router.get("/classes")
async def get_classes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有类定义"""
    storage = PGGraphStorage(db)
    classes = await storage.get_ontology_classes()
    return classes


@router.get("/relationships/schema")
async def get_schema_relationships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Schema 关系定义"""
    storage = PGGraphStorage(db)
    relationships = await storage.get_ontology_relationships()
    return relationships


@router.get("/describe/{class_name}")
async def describe_class(
    class_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """描述一个类的定义"""
    storage = PGGraphStorage(db)
    result = await storage.describe_class(class_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
