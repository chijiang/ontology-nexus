import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.schema_matcher import SchemaMatcher

@pytest.mark.asyncio
async def test_schema_matcher_initialization():
    # Mock Neo4j session
    session = AsyncMock()
    
    # Mock LLM and Neo4j configs
    llm_config = {
        "api_key": "test_key",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4"
    }
    neo4j_config = {"database": "neo4j"}
    
    # Instantiate SchemaMatcher
    matcher = SchemaMatcher(session, llm_config, neo4j_config)
    
    # Verify attributes are initialized to empty dicts
    assert matcher.classes == {}
    assert matcher.properties == {}
    
    # Mock the return values for _load_schema queries
    mock_result_classes = MagicMock()
    mock_result_classes.data = AsyncMock(return_value=[
        {"c": {"name": "TestClass", "uri": "http://test/TestClass", "label": "Test Class"}}
    ])
    
    mock_result_props = MagicMock()
    mock_result_props.data = AsyncMock(return_value=[
        {"p": {"name": "testProp", "uri": "http://test/testProp", "label": "Test Prop", "labels": ["DataProperty"]}}
    ])
    
    session.run.side_effect = [mock_result_classes, mock_result_props]
    
    # Call initialize
    await matcher.initialize()
    
    # Verify schema is loaded
    assert "TestClass" in matcher.classes
    assert "testProp" in matcher.properties
    assert matcher.classes["TestClass"]["uri"] == "http://test/TestClass"
    assert matcher.properties["testProp"]["label"] == "Test Prop"

@pytest.mark.asyncio
async def test_match_entities_no_attribute_error():
    # Verify that match_entities doesn't raise AttributeError even if initialize hasn't been called
    session = AsyncMock()
    llm_config = {
        "api_key": "test_key",
        "base_url": "https://api.openai.com1",
        "model": "gpt-4"
    }
    neo4j_config = {"database": "neo4j"}
    
    matcher = SchemaMatcher(session, llm_config, neo4j_config)
    
    # Mock _llm_match to avoid external API calls
    matcher._llm_match = AsyncMock(return_value={})
    
    # This should NOT raise AttributeError: 'SchemaMatcher' object has no attribute 'classes'
    result = await matcher.match_entities("测试查询")
    
    assert "entities" in result
    assert result["entities"] == {}
