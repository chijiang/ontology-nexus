# backend/app/api/config.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.core.neo4j_pool import get_neo4j_driver
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig
from app.schemas.config import (
    LLMConfigRequest, LLMConfigResponse,
    Neo4jConfigRequest, Neo4jConfigResponse,
    TestConnectionResponse
)
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        return LLMConfigResponse(base_url="", model="", has_api_key=False)

    return LLMConfigResponse(
        base_url=config.base_url,
        model=config.model,
        has_api_key=bool(config.api_key_encrypted)
    )


@router.put("/llm")
async def update_llm_config(
    req: LLMConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if config:
        if req.api_key != "************":
            config.api_key_encrypted = encrypt_data(req.api_key)
        config.base_url = req.base_url
        config.model = req.model
    else:
        if req.api_key == "************":
            raise HTTPException(status_code=400, detail="Cannot use placeholder for new configuration")
        encrypted_key = encrypt_data(req.api_key)
        config = LLMConfig(
            user_id=current_user.id,
            api_key_encrypted=encrypted_key,
            base_url=req.base_url,
            model=req.model
        )
        db.add(config)

    await db.commit()
    return {"message": "LLM config updated"}


@router.post("/test/llm", response_model=TestConnectionResponse)
async def test_llm_connection(
    req: LLMConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        api_key = req.api_key
        if api_key == "************":
            result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
            config = result.scalar_one_or_none()
            if not config:
                return TestConnectionResponse(success=False, message="No saved API key found")
            api_key = decrypt_data(config.api_key_encrypted)

        llm = ChatOpenAI(
            api_key=api_key,
            base_url=req.base_url,
            model=req.model,
            max_tokens=10
        )
        await llm.ainvoke("test")
        return TestConnectionResponse(success=True, message="LLM connection successful")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e))


@router.get("/neo4j", response_model=Neo4jConfigResponse)
async def get_neo4j_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if not config:
        return Neo4jConfigResponse(uri="", username="", database="neo4j", has_password=False)

    return Neo4jConfigResponse(
        uri=decrypt_data(config.uri_encrypted),
        username=decrypt_data(config.username_encrypted),
        database=config.database,
        has_password=bool(config.password_encrypted)
    )


@router.put("/neo4j")
async def update_neo4j_config(
    req: Neo4jConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    config = result.scalar_one_or_none()

    if config:
        config.uri_encrypted = encrypt_data(req.uri)
        config.username_encrypted = encrypt_data(req.username)
        if req.password != "************":
            config.password_encrypted = encrypt_data(req.password)
        config.database = req.database
    else:
        if req.password == "************":
            raise HTTPException(status_code=400, detail="Cannot use placeholder for new configuration")
        config = Neo4jConfig(
            user_id=current_user.id,
            uri_encrypted=encrypt_data(req.uri),
            username_encrypted=encrypt_data(req.username),
            password_encrypted=encrypt_data(req.password),
            database=req.database
        )
        db.add(config)

    await db.commit()
    return {"message": "Neo4j config updated"}


@router.post("/test/neo4j", response_model=TestConnectionResponse)
async def test_neo4j_connection(
    req: Neo4jConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        password = req.password
        if password == "************":
            result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
            config = result.scalar_one_or_none()
            if not config:
                return TestConnectionResponse(success=False, message="No saved password found")
            password = decrypt_data(config.password_encrypted)

        driver = await get_neo4j_driver(
            uri=req.uri,
            username=req.username,
            password=password,
            database=req.database
        )
        async with driver.session(database=req.database) as session:
            result = await session.run("RETURN 1 AS n")
            await result.data()
        return TestConnectionResponse(success=True, message="Neo4j connection successful")
    except Exception as e:
        return TestConnectionResponse(success=False, message=str(e))
