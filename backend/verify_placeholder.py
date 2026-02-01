import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.api.config import update_llm_config, update_neo4j_config, test_llm_connection, test_neo4j_connection
from app.schemas.config import LLMConfigRequest, Neo4jConfigRequest
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig

async def test_logic():
    print("Testing update_llm_config with placeholder...")
    db = MagicMock()
    db.execute = AsyncMock()
    
    current_user = User(id=1)
    existing_config = LLMConfig(user_id=1, api_key_encrypted="encrypted_old_key", base_url="old_url", model="old_model")
    
    # Mock return value for select(LLMConfig)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_config
    db.execute.return_value = mock_result
    
    # Update with placeholder
    req = LLMConfigRequest(api_key="************", base_url="new_url", model="new_model")
    await update_llm_config(req, current_user, db)
    
    assert existing_config.api_key_encrypted == "encrypted_old_key", "API Key should NOT be updated"
    assert existing_config.base_url == "new_url", "Base URL SHOULD be updated"
    assert existing_config.model == "new_model", "Model SHOULD be updated"
    print("✅ update_llm_config with placeholder passed")

    print("Testing update_llm_config with NEW key...")
    req_new = LLMConfigRequest(api_key="new_key", base_url="new_url", model="new_model")
    await update_llm_config(req_new, current_user, db)
    assert existing_config.api_key_encrypted != "encrypted_old_key", "API Key SHOULD be updated"
    print("✅ update_llm_config with new key passed")

    print("Testing update_neo4j_config with placeholder...")
    existing_neo4j = Neo4jConfig(user_id=1, password_encrypted="old_pass", uri_encrypted="old_uri", username_encrypted="old_user", database="neo4j")
    mock_result.scalar_one_or_none.return_value = existing_neo4j
    
    req_neo4j = Neo4jConfigRequest(uri="new_uri", username="new_user", password="************", database="new_db")
    await update_neo4j_config(req_neo4j, current_user, db)
    
    assert existing_neo4j.password_encrypted == "old_pass", "Password should NOT be updated"
    assert existing_neo4j.database == "new_db", "Database SHOULD be updated"
    print("✅ update_neo4j_config with placeholder passed")

if __name__ == "__main__":
    asyncio.run(test_logic())
