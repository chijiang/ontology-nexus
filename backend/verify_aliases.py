import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"
TOKEN = None  # Will need to get a token


async def get_token():
    async with httpx.AsyncClient() as client:
        # Assuming there is a test user or we can use admin/admin
        try:
            resp = await client.post(
                f"{BASE_URL}/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
            if resp.status_code != 200:
                print(f"Login failed: {resp.status_code} {resp.text}")
            return resp.json().get("access_token")
        except Exception as e:
            print(f"Error during login: {e}")
            return None


async def verify_ontology_alias():
    token = await get_token()
    if not token:
        print("Failed to get token")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update a class with multiple aliases
    class_name = "Supplier"
    new_labels = "SupplierAlias1, SupplierAlias2"

    async with httpx.AsyncClient() as client:
        print(f"Updating class {class_name} with labels: {new_labels}")
        resp = await client.put(
            f"{BASE_URL}/graph/ontology/classes/{class_name}",
            json={"label": new_labels},
            headers=headers,
        )
        print(f"Update response: {resp.status_code}")
        print(resp.json())

        # 2. Get classes and verify
        resp = await client.get(f"{BASE_URL}/graph/classes", headers=headers)
        classes = resp.json()
        target_class = next((c for c in classes if c["name"] == class_name), None)
        if target_class:
            print(f"Verified labels for {class_name}: {target_class.get('label')}")
            assert "SupplierAlias1" in target_class.get("label")
            assert "SupplierAlias2" in target_class.get("label")
        else:
            print(f"Class {class_name} not found in list")


async def verify_instance_alias():
    token = await get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get an instance
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/graph/nodes?label=Supplier&limit=1", headers=headers
        )
        nodes = resp.json()
        if not nodes:
            print("No Supplier nodes found")
            return

        node = nodes[0]
        node_name = node["name"]
        print(f"Updating instance {node_name} with aliases")

        # 2. Update aliases
        new_aliases = ["AliasA", "AliasB"]
        resp = await client.put(
            f"{BASE_URL}/graph/entities/Supplier/{node_name}",
            json={"__aliases__": new_aliases},
            headers=headers,
        )
        print(f"Update response: {resp.status_code}")

        # 3. Verify
        resp = await client.get(f"{BASE_URL}/graph/node/{node_name}", headers=headers)
        updated_node = resp.json()
        print(f"Updated node aliases: {updated_node.get('aliases')}")
        assert "AliasA" in updated_node.get("aliases")
        assert "AliasB" in updated_node.get("aliases")

        # 4. Search by alias
        resp = await client.get(
            f"{BASE_URL}/graph/instances/search?class_name=Supplier&keyword=AliasA",
            headers=headers,
        )
        search_results = resp.json()
        print(f"Search results for 'AliasA': {[n['name'] for n in search_results]}")
        assert any(n["name"] == node_name for n in search_results)


if __name__ == "__main__":
    asyncio.run(verify_ontology_alias())
    asyncio.run(verify_instance_alias())
