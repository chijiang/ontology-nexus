import pytest
from unittest.mock import AsyncMock, patch
from app.services.mcp_client import MCPClient


@pytest.mark.asyncio
async def test_mcp_client_get_tools():
    url = "http://localhost:8000/sse"

    # Mocking the mcp SDK components
    with patch("app.services.mcp_client.sse_client") as mock_sse_client:
        mock_session = AsyncMock()
        tool = AsyncMock()
        tool.name = "tool1"
        tool.description = "desc1"
        tool.inputSchema = {"type": "object"}
        mock_session.list_tools.return_value.tools = [tool]

        # mock_sse_client returns a context manager
        mock_sse_client.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
        )

        with patch("app.services.mcp_client.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            client = MCPClient(url)
            tools = await client.get_tools()

            assert len(tools) == 1
            assert tools[0]["name"] == "tool1"


@pytest.mark.asyncio
async def test_mcp_client_call_tool():
    url = "http://localhost:8000/sse"

    with patch("app.services.mcp_client.sse_client") as mock_sse_client:
        mock_session = AsyncMock()
        mock_session.call_tool.return_value = AsyncMock()
        mock_session.call_tool.return_value.content = [AsyncMock(text="result_text")]

        mock_sse_client.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
        )

        with patch("app.services.mcp_client.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session

            client = MCPClient(url)
            result = await client.call_tool("tool1", {"arg": "val"})

            assert result[0].text == "result_text"
            mock_session.call_tool.assert_called_once_with("tool1", {"arg": "val"})
