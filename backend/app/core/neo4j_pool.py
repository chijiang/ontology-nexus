# backend/app/core/neo4j_pool.py
from neo4j import AsyncDriver, AsyncGraphDatabase
from typing import Optional
from app.core.config import settings

_pool: Optional[AsyncDriver] = None


async def get_neo4j_driver(
    uri: str = None,
    username: str = None,
    password: str = None,
    database: str = None
) -> AsyncDriver:
    """获取 Neo4j Driver（使用连接池）"""
    global _pool

    if _pool is None:
        uri = uri or settings.NEO4J_URI
        username = username or settings.NEO4J_USERNAME
        password = password or settings.NEO4J_PASSWORD
        database = database or settings.NEO4J_DATABASE

        _pool = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password)
        )

    return _pool


async def close_neo4j():
    """关闭 Neo4j 连接池"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
