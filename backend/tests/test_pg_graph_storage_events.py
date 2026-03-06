import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.pg_graph_storage import PGGraphStorage
from app.rule_engine.models import GraphViewEvent


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_event_emitter():
    return MagicMock()


@pytest.fixture
def storage(mock_db, mock_event_emitter):
    return PGGraphStorage(mock_db, mock_event_emitter)


@pytest.mark.asyncio
async def test_search_instances_emits_event(storage, mock_db, mock_event_emitter):
    # Mock DB result
    mock_entity = MagicMock()
    mock_entity.name = "TestNode"
    mock_entity.entity_type = "TestType"
    mock_entity.properties = {"key": "value"}

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_entity]
    mock_db.execute.return_value = mock_result

    # Call method
    await storage.search_instances(keyword="Test")

    # Verify event emission
    mock_event_emitter.emit.assert_called()
    args, _ = mock_event_emitter.emit.call_args
    event = args[0]
    assert isinstance(event, GraphViewEvent)
    assert len(event.nodes) == 1
    assert event.nodes[0]["id"] == "TestNode"


@pytest.mark.asyncio
async def test_find_path_emits_event(storage, mock_db, mock_event_emitter):
    # Mock DB results for start/end nodes and path
    mock_node = MagicMock()
    mock_node.id = 1
    mock_node.name = "Node1"
    mock_node.entity_type = "Type1"

    mock_db.execute.side_effect = [
        # Start node
        MagicMock(one_or_none=MagicMock(return_value=(1, "Start", "Type1"))),
        # End node
        MagicMock(one_or_none=MagicMock(return_value=(2, "End", "Type2"))),
        # Path
        MagicMock(
            first=MagicMock(
                return_value=(["Start", "End"], ["Type1", "Type2"], ["REL"])
            )
        ),
    ]

    # Call method
    await storage.find_path_between_instances("Start", "End")

    # Verify event emission
    mock_event_emitter.emit.assert_called()
    args, _ = mock_event_emitter.emit.call_args
    event = args[0]
    assert isinstance(event, GraphViewEvent)
    assert len(event.nodes) == 2
    assert len(event.edges) == 1
