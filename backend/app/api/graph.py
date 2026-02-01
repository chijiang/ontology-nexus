# backend/app/api/graph.py
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.neo4j_config import Neo4jConfig
from app.core.neo4j_pool import get_neo4j_driver
from app.services.graph_tools import GraphTools
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/import")
async def import_graph(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导入 OWL 文件"""
    # 获取 Neo4j 配置
    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    content = await file.read()

    # 解析并导入
    from app.services.owl_parser import OWLParser
    from app.services.graph_importer import GraphImporter

    parser = OWLParser()
    parser.load_from_string(content.decode("utf-8"))
    schema_triples, instance_triples = parser.classify_triples()

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database,
    )

    async with driver.session(database=neo4j_config.database) as session:
        importer = GraphImporter(session)
        schema_stats = await importer.import_schema(parser)
        instance_stats = await importer.import_instances(
            schema_triples, instance_triples
        )

    return {
        "message": "Graph imported successfully",
        "schema_stats": schema_stats,
        "instance_stats": instance_stats,
    }


@router.get("/node/{uri:path}")
async def get_node(
    uri: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取节点详情"""
    # 获取配置
    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database,
    )

    async with driver.session(database=neo4j_config.database) as session:
        record = await session.run("MATCH (n {uri: $uri}) RETURN n", uri=uri)
        data = await record.data()
        if not data:
            raise HTTPException(status_code=404, detail="Node not found")
        return data[0]["n"]


@router.get("/neighbors")
async def get_neighbors(
    name: str,
    hops: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取节点邻居"""
    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database,
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        neighbors = await tools.get_instance_neighbors(name, hops)
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
    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database,
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        path = await tools.find_path_between_nodes(start_uri, end_uri, max_depth)
        return path


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取图谱统计"""
    from neo4j.exceptions import ServiceUnavailable, SessionExpired
    from app.core.neo4j_pool import invalidate_driver

    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    uri = decrypt_data(neo4j_config.uri_encrypted)
    username = decrypt_data(neo4j_config.username_encrypted)
    password = decrypt_data(neo4j_config.password_encrypted)

    # 尝试两次：第一次失败后刷新连接重试
    for attempt in range(2):
        try:
            driver = await get_neo4j_driver(
                uri=uri,
                username=username,
                password=password,
                database=neo4j_config.database,
                force_new=(attempt > 0),  # 第二次尝试时强制新连接
            )

            async with driver.session(database=neo4j_config.database) as session:
                tools = GraphTools(session)
                stats = await tools.get_node_statistics()
                return stats

        except (ServiceUnavailable, SessionExpired, OSError) as e:
            if attempt == 0:
                # 第一次失败，使连接失效并重试
                await invalidate_driver(uri, username)
                continue
            else:
                raise HTTPException(
                    status_code=503, detail=f"Neo4j connection failed: {str(e)}"
                )


@router.get("/nodes")
async def get_nodes_by_label(
    label: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据标签获取节点"""
    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    driver = await get_neo4j_driver(
        uri=decrypt_data(neo4j_config.uri_encrypted),
        username=decrypt_data(neo4j_config.username_encrypted),
        password=decrypt_data(neo4j_config.password_encrypted),
        database=neo4j_config.database,
    )

    async with driver.session(database=neo4j_config.database) as session:
        tools = GraphTools(session)
        nodes = await tools.get_instances_by_class(label, None, limit)
        return nodes


@router.get("/schema")
async def get_schema(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Schema 图（类和关系定义）"""
    from neo4j.exceptions import ServiceUnavailable, SessionExpired
    from app.core.neo4j_pool import invalidate_driver

    result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    uri = decrypt_data(neo4j_config.uri_encrypted)
    username = decrypt_data(neo4j_config.username_encrypted)
    password = decrypt_data(neo4j_config.password_encrypted)

    for attempt in range(2):
        try:
            driver = await get_neo4j_driver(
                uri=uri,
                username=username,
                password=password,
                database=neo4j_config.database,
                force_new=(attempt > 0),
            )

            async with driver.session(database=neo4j_config.database) as session:
                # 获取所有 Schema 类节点
                nodes_result = await session.run(
                    """
                    MATCH (c:Class:__Schema)
                    RETURN c.name as name, c.label as label, c.dataProperties as dataProperties
                    """
                )
                nodes_data = await nodes_result.data()

                # 获取所有 Schema 关系
                rels_result = await session.run(
                    """
                    MATCH (c1:Class:__Schema)-[r]->(c2:Class:__Schema)
                    RETURN c1.name as source, type(r) as type, c2.name as target
                    """
                )
                rels_data = await rels_result.data()

                return {
                    "nodes": nodes_data,
                    "relationships": rels_data,
                }

        except (ServiceUnavailable, SessionExpired, OSError) as e:
            if attempt == 0:
                await invalidate_driver(uri, username)
                continue
            else:
                raise HTTPException(
                    status_code=503, detail=f"Neo4j connection failed: {str(e)}"
                )
