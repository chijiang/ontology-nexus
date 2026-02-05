from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import encrypt_data, decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.schemas.config import (
    LLMConfigRequest, LLMConfigResponse,
    TestConnectionResponse
)
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LLMConfig).limit(1))
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
    result = await db.execute(select(LLMConfig).limit(1))
    config = result.scalar_one_or_none()

    if config:
        if req.api_key != "************":
            config.api_key_encrypted = encrypt_data(req.api_key)
        config.base_url = req.base_url
        config.model = req.model
        config.updated_at = datetime.utcnow()
    else:
        if req.api_key == "************":
            raise HTTPException(status_code=400, detail="Cannot use placeholder for new configuration")
        encrypted_key = encrypt_data(req.api_key)
        config = LLMConfig(
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
            result = await db.execute(select(LLMConfig).limit(1))
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
