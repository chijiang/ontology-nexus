# backend/app/api/mcp.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.deps import get_current_user, require_admin
from app.models.user import User
from app.models.mcp_config import MCPConfig
from app.schemas.mcp import MCPConfigCreate, MCPConfigUpdate, MCPConfigResponse
from typing import List

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("", response_model=List[MCPConfigResponse])
async def list_mcp_servers(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """List all registered MCP servers."""
    result = await db.execute(select(MCPConfig).order_by(MCPConfig.id))
    return result.scalars().all()


@router.post("", response_model=MCPConfigResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    req: MCPConfigCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register a new MCP server."""
    # Check if name already exists
    result = await db.execute(select(MCPConfig).where(MCPConfig.name == req.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MCP server with name '{req.name}' already exists",
        )

    server = MCPConfig(**req.model_dump())
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.put("/{server_id}", response_model=MCPConfigResponse)
async def update_mcp_server(
    server_id: int,
    req: MCPConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an MCP server configuration."""
    server = await db.get(MCPConfig, server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found"
        )

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(server, key, value)

    await db.commit()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove an MCP server."""
    server = await db.get(MCPConfig, server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MCP server not found"
        )

    await db.delete(server)
    await db.commit()
    return None
