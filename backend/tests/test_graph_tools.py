import pytest
from app.services.graph_tools import GraphTools


@pytest.mark.asyncio
async def test_fuzzy_search_entities(neo4j_session):
    tools = GraphTools(neo4j_session)
    # 假设已有测试数据
    result = await tools.fuzzy_search_entities("Purchase", limit=5)
    assert isinstance(result, list)
    # 根据实际数据验证
