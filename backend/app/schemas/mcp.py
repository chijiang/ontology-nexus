# backend/app/schemas/mcp.py
from datetime import datetime
from pydantic import BaseModel, Field


class MCPConfigBase(BaseModel):
    name: str = Field(..., description="Name of the MCP server")
    url: str = Field(..., description="SSE URL of the MCP server")
    mcp_type: str = Field(
        "sse", description="Type of MCP server (currently only sse supported)"
    )
    is_active: bool = Field(True, description="Whether the server is active")


class MCPConfigCreate(MCPConfigBase):
    pass


class MCPConfigUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    mcp_type: str | None = None
    is_active: bool | None = None


class MCPConfigResponse(MCPConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
