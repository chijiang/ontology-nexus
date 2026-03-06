# backend/app/services/mcp_client.py
import logging
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP servers via SSE."""

    def __init__(self, url: str):
        self.url = url
        self._session: Optional[ClientSession] = None
        self._exit_stack = None
        self._client = None

    async def get_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the MCP server."""
        try:
            async with sse_client(self.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    # tools_result.tools is a list of Tool objects
                    return [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema,
                        }
                        for tool in tools_result.tools
                    ]
        except Exception as e:
            logger.error(f"Failed to fetch tools from MCP server at {self.url}: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        try:
            async with sse_client(self.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    return result.content
        except Exception as e:
            logger.error(f"Error calling MCP tool '{name}' at {self.url}: {e}")
            raise
