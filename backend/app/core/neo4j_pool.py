# backend/app/core/neo4j_pool.py
from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cache drivers by connection URI to support multiple users with different configs
_drivers: dict[str, AsyncDriver] = {}


async def get_neo4j_driver(
    uri: str,
    username: str,
    password: str,
    database: str = "neo4j",
    force_new: bool = False,
) -> AsyncDriver:
    """获取 Neo4j Driver（使用连接池，按 URI 缓存）

    Args:
        force_new: 如果为 True，强制创建新连接（用于连接失败后重试）
    """
    global _drivers

    cache_key = f"{uri}:{username}"

    # 如果强制刷新，先关闭旧连接
    if force_new and cache_key in _drivers:
        try:
            await _drivers[cache_key].close()
        except Exception:
            pass
        del _drivers[cache_key]
        logger.info(f"Forced new connection for {uri}")

    if cache_key not in _drivers:
        _drivers[cache_key] = AsyncGraphDatabase.driver(
            uri,
            auth=(username, password),
            max_connection_lifetime=60,  # 1 minute max connection lifetime (Aura may change IPs)
            max_connection_pool_size=10,
            connection_acquisition_timeout=30,
        )

    return _drivers[cache_key]


async def invalidate_driver(uri: str, username: str):
    """使指定的 driver 失效（连接失败时调用）"""
    global _drivers
    cache_key = f"{uri}:{username}"

    if cache_key in _drivers:
        try:
            await _drivers[cache_key].close()
        except Exception:
            pass
        del _drivers[cache_key]
        logger.info(f"Invalidated driver for {uri}")


async def close_neo4j():
    """关闭所有 Neo4j 连接池"""
    global _drivers
    for driver in _drivers.values():
        try:
            await driver.close()
        except Exception:
            pass
    _drivers.clear()
