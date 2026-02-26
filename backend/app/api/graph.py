# backend/app/api/graph.py
"""Graph API endpoints using PostgreSQL storage.

Implementation with PostgreSQL.
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
from app.services.permission_service import PermissionService
from app.rule_engine.event_emitter import GraphEventEmitter
from fastapi.responses import JSONResponse, Response

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
    instance_stats = await importer.import_instances(schema_triples, instance_triples)

    return {
        "message": "Graph imported successfully",
        "schema_stats": schema_stats,
        "instance_stats": instance_stats,
        "total": {
            "classes": schema_stats.get("classes", 0),
            "schema_properties": schema_stats.get("properties", 0),
            "nodes": instance_stats.get("nodes", 0),
            "relationships": instance_stats.get("relationships", 0),
        },
    }


@router.post("/clear")
async def clear_graph(
    clear_ontology: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清除图谱数据"""
    storage = PGGraphStorage(db)
    await storage.clear_graph(clear_ontology=clear_ontology)
    return {"message": f"Graph cleared successfully (ontology={clear_ontology})"}


@router.get("/node/{uri:path}")
async def get_node(
    uri: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取节点详情"""
    storage = PGGraphStorage(db)

    # 1. 尝试按数字 ID 查找
    if uri.isdigit():
        entity = await storage.get_entity_by_id(int(uri))
        if entity:
            return entity

    # 2. 尝试按 name 查找
    entity = await storage.get_entity_by_name(uri)
    if entity:
        return entity

    # 3. 尝试按 URI 查找
    from app.models.graph import GraphEntity

    result = await db.execute(select(GraphEntity).where(GraphEntity.uri == uri))
    entity = result.scalar_one_or_none()
    if entity:
        return {
            "id": entity.id,
            "name": entity._display_name,  # Map _display_name to compat "name" field
            "entity_type": entity.entity_type,
            "properties": entity.properties or {},
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
    # 获取当前用户的权限
    accessible_entity_types = await PermissionService.get_accessible_entities(
        db, current_user
    )

    # 如果是受限用户，且无任何实体级权限，直接返回空
    if not current_user.is_admin and not accessible_entity_types:
        return []

    if name.isdigit():
        neighbors = await storage.get_instance_neighbors(
            entity_id=int(name),
            hops=hops,
            direction=direction,
            accessible_entity_types=accessible_entity_types,
        )
    else:
        neighbors = await storage.get_instance_neighbors(
            entity_name=name,
            hops=hops,
            direction=direction,
            accessible_entity_types=accessible_entity_types,
        )

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
    # 获取当前用户的权限
    accessible_entity_types = await PermissionService.get_accessible_entities(
        db, current_user
    )

    # 如果是受限用户，且无任何实体级权限，直接返回空
    if not current_user.is_admin and not accessible_entity_types:
        raise HTTPException(status_code=403, detail="No entity access permissions")

    kwargs = {
        "max_depth": max_depth,
        "accessible_entity_types": accessible_entity_types,
    }
    if start_uri.isdigit():
        kwargs["start_id"] = int(start_uri)
    else:
        kwargs["start_name"] = start_uri

    if end_uri.isdigit():
        kwargs["end_id"] = int(end_uri)
    else:
        kwargs["end_name"] = end_uri

    path = await storage.find_path_between_instances(**kwargs)
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
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(
        db, current_user
    )

    # Admin用户拥有所有权限，传None不过滤
    entity_types = None if current_user.is_admin else accessible_entities

    storage = PGGraphStorage(db)

    # 获取所有 Schema 类节点
    nodes_data = await storage.get_ontology_classes(entity_types)

    # 获取所有 Schema 关系
    rels_data = await storage.get_ontology_relationships(entity_types)

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
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(
        db, current_user
    )

    # Admin用户拥有所有权限，传None不过滤
    entity_types = None if current_user.is_admin else accessible_entities

    storage = PGGraphStorage(db)
    classes = await storage.get_ontology_classes(entity_types)
    return classes


@router.get("/relationships/schema")
async def get_schema_relationships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Schema 关系定义"""
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(
        db, current_user
    )
    entity_types = None if current_user.is_admin else accessible_entities

    storage = PGGraphStorage(db)
    relationships = await storage.get_ontology_relationships(entity_types)
    return relationships


@router.get("/describe/{class_name}")
async def describe_class(
    class_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """描述一个类的定义"""
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(
        db, current_user
    )
    entity_types = None if current_user.is_admin else accessible_entities

    storage = PGGraphStorage(db)
    result = await storage.describe_class(class_name, entity_types)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/export/ontology")
async def export_ontology(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导出本体为 OWL/Turtle 文件"""
    storage = PGGraphStorage(db)
    classes = await storage.get_ontology_classes()
    relationships = await storage.get_ontology_relationships()

    from app.services.ontology_exporter import OntologyExporter

    exporter = OntologyExporter()
    ttl_content = exporter.export_to_ttl(classes, relationships)

    return Response(
        content=ttl_content,
        media_type="text/turtle",
        headers={"Content-Disposition": "attachment; filename=ontology.ttl"},
    )


@router.post("/ontology/classes")
async def add_ontology_class(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加本体类"""
    storage = PGGraphStorage(db)
    result = await storage.add_ontology_class(
        data["name"], data.get("label"), data.get("data_properties"), data.get("color")
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.put("/ontology/classes/{name}")
async def update_ontology_class(
    name: str,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新本体类"""
    storage = PGGraphStorage(db)
    result = await storage.update_ontology_class(
        name, data.get("label"), data.get("data_properties"), data.get("color")
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/ontology/classes/{name}")
async def delete_ontology_class(
    name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除本体类"""
    storage = PGGraphStorage(db)
    result = await storage.delete_ontology_class(name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ontology/relationships")
async def add_ontology_relationship(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加本体关系"""
    storage = PGGraphStorage(db)
    result = await storage.add_ontology_relationship(
        data["source"], data["type"], data["target"]
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.api_route("/ontology/relationships", methods=["DELETE"])
async def delete_ontology_relationship(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除本体关系"""
    storage = PGGraphStorage(db)
    result = await storage.delete_ontology_relationship(
        data["source"], data["type"], data["target"]
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/instances/random")
async def get_random_instances(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取随机实例图谱作为初始展示"""
    # 获取用户可访问的实体类型
    accessible_entities = await PermissionService.get_accessible_entities(
        db, current_user
    )

    # Admin用户拥有所有权限，传None不过滤
    entity_types = None if current_user.is_admin else accessible_entities

    storage = PGGraphStorage(db)
    result = await storage.get_random_graph(limit, entity_types)
    return result
