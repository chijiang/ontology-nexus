# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig
from app.models.conversation import Conversation, Message
from app.services.qa_agent import QAAgent
import json

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    conversation_id: int | None = None


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式问答"""

    # 获取用户配置
    llm_result = await db.execute(
        select(LLMConfig).where(LLMConfig.user_id == current_user.id)
    )
    llm_config = llm_result.scalar_one_or_none()
    if not llm_config:
        raise HTTPException(status_code=400, detail="LLM not configured")

    neo4j_result = await db.execute(
        select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id)
    )
    neo4j_config = neo4j_result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    # 处理对话
    conversation = None
    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    # 如果没有对话，创建新的
    if not conversation:
        conversation = Conversation(user_id=current_user.id, title="新对话")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # 保存用户消息
    user_message = Message(
        conversation_id=conversation.id, role="user", content=req.query
    )
    db.add(user_message)
    await db.commit()

    llm_dict = {
        "api_key": decrypt_data(llm_config.api_key_encrypted),
        "base_url": llm_config.base_url,
        "model": llm_config.model,
    }
    neo4j_dict = {
        "uri": decrypt_data(neo4j_config.uri_encrypted),
        "username": decrypt_data(neo4j_config.username_encrypted),
        "password": decrypt_data(neo4j_config.password_encrypted),
        "database": neo4j_config.database,
    }

    agent = QAAgent(current_user.id, db, llm_dict, neo4j_dict)

    async def event_generator():
        full_content = ""
        thinking = ""
        graph_data = None

        async for chunk in agent.astream_chat(req.query):
            # 发送 conversation_id 给前端
            if chunk.get("type") == "thinking":
                chunk["conversation_id"] = conversation.id
                thinking = chunk.get("content", "")
            elif chunk.get("type") == "content":
                full_content += chunk.get("content", "")
            elif chunk.get("type") == "graph_data":
                graph_data = {
                    "nodes": chunk.get("nodes", []),
                    "edges": chunk.get("edges", []),
                }

            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 保存助手消息
        async with db.begin_nested():
            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_content,
                extra_metadata=(
                    {"thinking": thinking, "graph_data": graph_data}
                    if (thinking or graph_data)
                    else None
                ),
            )
            db.add(assistant_message)
            conversation.updated_at = datetime.utcnow()
            await db.commit()

        # 发送 conversation_id
        yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/completions")
async def chat_completion(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """非流式问答（兼容接口）"""
    pass
