"""Tests for query tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.tools import StructuredTool

from app.services.agent_tools.query_tools import create_query_tools, QueryToolRegistry


@pytest.fixture
def mock_session():
    """Create a mock Neo4j session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_get_session_func(mock_session):
    """Create a mock get_session function."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _get_session():
        yield mock_session

    return _get_session


@pytest.fixture
def mock_graph_tools():
    """Create a mock GraphTools instance."""
    tools = MagicMock()
    tools.search_instances = AsyncMock(
        return_value=[
            {
                "name": "PO_001",
                "labels": ["PurchaseOrder"],
                "properties": {"status": "pending"},
            }
        ]
    )
    tools.get_instances_by_class = AsyncMock(
        return_value=[{"name": "PO_001", "properties": {"status": "pending"}}]
    )
    tools.get_instance_neighbors = AsyncMock(
        return_value=[
            {
                "name": "Supplier_001",
                "labels": ["Supplier"],
                "properties": {"name": "Acme"},
            }
        ]
    )
    tools.find_path_between_instances = AsyncMock(
        return_value={
            "nodes": [
                {"name": "PO_001", "labels": ["PurchaseOrder"]},
                {"name": "Supplier_001", "labels": ["Supplier"]},
            ],
            "relationships": [
                {"type": "FROM_SUPPLIER", "source": "PO_001", "target": "Supplier_001"}
            ],
        }
    )
    tools.describe_class = AsyncMock(
        return_value={
            "class": {
                "name": "PurchaseOrder",
                "label": "Purchase Order",
                "dataProperties": ["status", "total"],
            },
            "relationships": [],
        }
    )
    tools.get_ontology_classes = AsyncMock(
        return_value=[
            {
                "name": "PurchaseOrder",
                "label": "Purchase Order",
                "dataProperties": ["status"],
            }
        ]
    )
    tools.get_ontology_relationships = AsyncMock(
        return_value=[
            {
                "source": "PurchaseOrder",
                "type": "FROM_SUPPLIER",
                "target": "Supplier",
            }
        ]
    )
    tools.get_node_statistics = AsyncMock(
        return_value={
            "total_count": 100,
            "sample_names": ["PO_001", "PO_002", "PO_003"],
        }
    )
    return tools


class TestCreateQueryTools:
    """Test create_query_tools function."""

    @pytest.mark.asyncio
    async def test_search_instances(self, mock_get_session_func, mock_graph_tools):
        """Test search_instances tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            search_tool = next(t for t in tools if t.name == "search_instances")

            result = await search_tool.coroutine(search_term="PO")

            assert "PO_001" in result
            assert "PurchaseOrder" in result
            mock_graph_tools.search_instances.assert_called_once_with(
                keyword="PO", entity_type=None, limit=10
            )

    @pytest.mark.asyncio
    async def test_get_instances_by_class(
        self, mock_get_session_func, mock_graph_tools
    ):
        """Test get_instances_by_class tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_instances_by_class")

            result = await tool.coroutine(class_name="PurchaseOrder")

            assert "PO_001" in result
            mock_graph_tools.get_instances_by_class.assert_called_once_with(
                entity_type="PurchaseOrder", property_filter=None, limit=20
            )

    @pytest.mark.asyncio
    async def test_get_instances_by_class_without_filters(
        self, mock_get_session_func, mock_graph_tools
    ):
        """Test get_instances_by_class without filters parameter."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_instances_by_class")

            result = await tool.coroutine(class_name="PurchaseOrder")

            # Should be called with None for filters (the parameter was removed)
            mock_graph_tools.get_instances_by_class.assert_called_once_with(
                entity_type="PurchaseOrder", property_filter=None, limit=20
            )

    @pytest.mark.asyncio
    async def test_get_instance_neighbors(
        self, mock_get_session_func, mock_graph_tools
    ):
        """Test get_instance_neighbors tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_instance_neighbors")

            result = await tool.coroutine(instance_name="PO_001")

            assert "Supplier_001" in result
            mock_graph_tools.get_instance_neighbors.assert_called_once_with(
                hops=1,
                direction="both",
                entity_type=None,
                property_filter=None,
                entity_name="PO_001",
            )

    @pytest.mark.asyncio
    async def test_find_path_between_instances(
        self, mock_get_session_func, mock_graph_tools
    ):
        """Test find_path_between_instances tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "find_path_between_instances")

            result = await tool.coroutine(start_name="PO_001", end_name="Supplier_001")

            assert "PO_001" in result
            assert "Supplier_001" in result
            mock_graph_tools.find_path_between_instances.assert_called_once_with(
                max_depth=5, start_name="PO_001", end_name="Supplier_001"
            )

    @pytest.mark.asyncio
    async def test_describe_class(self, mock_get_session_func, mock_graph_tools):
        """Test describe_class tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "describe_class")

            result = await tool.coroutine(class_name="PurchaseOrder")

            assert "PurchaseOrder" in result
            assert "status" in result
            mock_graph_tools.describe_class.assert_called_once_with("PurchaseOrder")

    @pytest.mark.asyncio
    async def test_get_ontology_classes(self, mock_get_session_func, mock_graph_tools):
        """Test get_ontology_classes tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_ontology_classes")

            result = await tool.coroutine()

            assert "PurchaseOrder" in result
            mock_graph_tools.get_ontology_classes.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_ontology_relationships(
        self, mock_get_session_func, mock_graph_tools
    ):
        """Test get_ontology_relationships tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_ontology_relationships")

            result = await tool.coroutine()

            assert "FROM_SUPPLIER" in result
            mock_graph_tools.get_ontology_relationships.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_node_statistics(self, mock_get_session_func, mock_graph_tools):
        """Test get_node_statistics tool."""
        with patch(
            "app.services.agent_tools.query_tools.PGGraphStorage",
            return_value=mock_graph_tools,
        ):
            tools = create_query_tools(mock_get_session_func)
            tool = next(t for t in tools if t.name == "get_node_statistics")

            result = await tool.coroutine(node_label="PurchaseOrder")

            assert "100" in result
            mock_graph_tools.get_node_statistics.assert_called_once_with(
                "PurchaseOrder"
            )

    def test_tools_are_structured_tools(self, mock_get_session_func):
        """Test that all returned tools are StructuredTool instances."""
        tools = create_query_tools(mock_get_session_func)

        for tool in tools:
            assert isinstance(tool, StructuredTool)

    def test_tool_names(self, mock_get_session_func):
        """Test that tools have correct names."""
        tools = create_query_tools(mock_get_session_func)
        tool_names = [t.name for t in tools]

        expected_names = [
            "search_instances",
            "get_instances_by_class",
            "get_instance_neighbors",
            "find_path_between_instances",
            "describe_class",
            "get_ontology_classes",
            "get_ontology_relationships",
            "get_node_statistics",
        ]

        for name in expected_names:
            assert name in tool_names

    def test_tool_descriptions(self, mock_get_session_func):
        """Test that tools have descriptions."""
        tools = create_query_tools(mock_get_session_func)

        for tool in tools:
            assert tool.description
            assert len(tool.description) > 0


class TestQueryToolRegistry:
    """Test QueryToolRegistry class."""

    def test_initialization(self, mock_get_session_func):
        """Test registry initialization."""
        registry = QueryToolRegistry(mock_get_session_func)

        assert registry.get_session_func == mock_get_session_func
        assert registry._tools is None

    def test_tools_property(self, mock_get_session_func):
        """Test that tools property creates tools on first access."""
        registry = QueryToolRegistry(mock_get_session_func)

        # First access should create tools
        tools = registry.tools
        assert tools is not None
        assert len(tools) > 0

        # Second access should return cached tools
        tools2 = registry.tools
        assert tools is tools2

    def test_get_tool_names(self, mock_get_session_func):
        """Test get_tool_names method."""
        registry = QueryToolRegistry(mock_get_session_func)

        names = registry.get_tool_names()

        assert isinstance(names, list)
        assert len(names) > 0
        assert "search_instances" in names
