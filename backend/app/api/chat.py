# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException, Request
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
from app.models.conversation import Conversation, Message
from app.services.agent import EnhancedAgentService
import json

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    conversation_id: int | None = None
    mode: str = "llm"  # "llm" or "non-llm"


@router.post("/v2/stream")
async def chat_stream_v2(
    req: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enhanced streaming chat using LangGraph-based agent.

    This endpoint uses the EnhancedAgentService with PostgreSQL for graph storage.
    """
    # Get global config
    llm_result = await db.execute(select(LLMConfig).limit(1))
    llm_config = llm_result.scalar_one_or_none()
    if not llm_config:
        raise HTTPException(status_code=400, detail="LLM not configured")

    # Handle conversation
    conversation = None
    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(user_id=current_user.id, title="新对话")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # Save user message
    user_message = Message(
        conversation_id=conversation.id, role="user", content=req.query
    )
    db.add(user_message)
    await db.commit()

    # Fetch history (last 3 rounds = 6 messages)
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id, Message.id < user_message.id)
        .order_by(Message.id.desc())
        .limit(6)
    )
    history_messages = history_result.scalars().all()
    # Reverse to get chronological order
    history = [
        {"role": m.role, "content": m.content} for m in reversed(history_messages)
    ]

    # Create llm_dict by decrypting API key
    llm_dict = {
        "api_key": decrypt_data(llm_config.api_key_encrypted),
        "base_url": llm_config.base_url,
        "model": llm_config.model,
    }

    # Get action components from app state
    action_executor = request.app.state.action_executor
    action_registry = request.app.state.action_registry

    if req.mode == "non-llm":
        from app.services.agent.non_llm_service import NonLLMService

        service = NonLLMService()

        async def event_generator():
            # Send conversation_id immediately
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id}, ensure_ascii=False)}\n\n"

            full_content = ""
            async for chunk in service.match_and_execute(
                req.query, db, action_executor, action_registry
            ):
                chunk["conversation_id"] = conversation.id
                if chunk.get("type") == "content":
                    full_content += chunk.get("content", "")
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # If no content was generated (no match), fallback or just end?
            # NonLLMService yields specific message if no match?
            # Implementation above yields nothing if no match.
            # Let's add a default message if full_content is empty
            if not full_content:
                msg = "抱歉，无法识别此指令。请尝试使用标准模版或切换回 LLM 模式。"
                full_content = msg
                yield f"data: {json.dumps({'type': 'content', 'content': msg, 'conversation_id': conversation.id}, ensure_ascii=False)}\n\n"

            # Save assistant message
            async with db.begin_nested():
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_content,
                )
                db.add(assistant_message)
                conversation.updated_at = datetime.utcnow()
                await db.commit()

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Create enhanced agent (Neo4j config is now empty, using PostgreSQL)
    agent = EnhancedAgentService(
        llm_config=llm_dict,
        neo4j_config=None,  # Using PostgreSQL now
        action_executor=action_executor,
        action_registry=action_registry,
    )

    async def event_generator():
        full_content = ""
        thinking = ""
        graph_data = None

        # Send conversation_id immediately
        yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation.id}, ensure_ascii=False)}\n\n"

        async for chunk in agent.astream_chat(req.query, history=history):
            chunk["conversation_id"] = conversation.id

            if chunk.get("type") == "thinking":
                thinking += chunk.get("content", "")
            elif chunk.get("type") == "content":
                full_content += chunk.get("content", "")
            elif chunk.get("type") == "graph_data":
                graph_data = {
                    "nodes": chunk.get("nodes", []),
                    "edges": chunk.get("edges", []),
                }

            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # Save assistant message
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")
