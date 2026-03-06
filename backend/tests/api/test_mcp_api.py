import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_mcp_servers(async_client, auth_headers):
    response = await async_client.get("/api/mcp", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_register_mcp_server(async_client, auth_headers):
    server_data = {
        "name": "Test MCP",
        "url": "http://localhost:8000/sse",
        "mcp_type": "sse",
        "is_active": True,
    }
    response = await async_client.post(
        "/api/mcp", json=server_data, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test MCP"
    assert data["url"] == "http://localhost:8000/sse"
    assert "id" in data

    # Cleanup or verify list
    response = await async_client.get("/api/mcp", headers=auth_headers)
    assert any(s["name"] == "Test MCP" for s in response.json())


@pytest.mark.asyncio
async def test_update_mcp_server(async_client, auth_headers):
    # First register
    server_data = {"name": "To Update", "url": "http://localhost:8001/sse"}
    resp = await async_client.post("/api/mcp", json=server_data, headers=auth_headers)
    server_id = resp.json()["id"]

    # Update
    update_data = {"is_active": False}
    response = await async_client.put(
        f"/api/mcp/{server_id}", json=update_data, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_mcp_server(async_client, auth_headers):
    # First register
    server_data = {"name": "To Delete", "url": "http://localhost:8002/sse"}
    resp = await async_client.post("/api/mcp", json=server_data, headers=auth_headers)
    server_id = resp.json()["id"]

    # Delete
    response = await async_client.delete(f"/api/mcp/{server_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    response = await async_client.get("/api/mcp", headers=auth_headers)
    assert not any(s["id"] == server_id for s in response.json())
