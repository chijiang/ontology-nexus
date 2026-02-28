# backend/app/api/conversations.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.llm_config import LLMConfig
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    extra_metadata: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    role: str
    content: str
    extra_metadata: dict | None = None


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取用户的所有对话"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    req: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    conversation = Conversation(user_id=current_user.id, title=req.title or "新对话")
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情及消息"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除对话"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()
    return {"message": "Deleted"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: int,
    req: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加消息到对话"""
    # 验证对话所有权
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = Message(
        conversation_id=conversation_id,
        role=req.role,
        content=req.content,
        extra_metadata=req.extra_metadata,
    )
    db.add(message)

    # 更新对话时间
    conversation.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)
    # The relationship messages in conversation is now sorted by Message.id in the model
    return message


@router.post("/{conversation_id}/generate-title")
async def generate_title(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """使用 LLM 为对话生成标题"""
    # 获取对话和消息
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id, Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not conversation.messages:
        return {"title": conversation.title}

    # 获取 LLM 配置（全局配置）
    llm_result = await db.execute(select(LLMConfig).limit(1))
    llm_config = llm_result.scalar_one_or_none()
    if not llm_config:
        raise HTTPException(status_code=400, detail="LLM not configured")

    # 构建对话摘要
    messages_text = "\n".join(
        [f"{m.role}: {m.content[:200]}" for m in conversation.messages[:5]]
    )

    # 使用 LLM 生成标题
    llm = ChatOpenAI(
        api_key=decrypt_data(llm_config.api_key_encrypted),
        base_url=llm_config.base_url,
        model=llm_config.model,
        temperature=0.7,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Generate a brief title based on the following conversation (no more than 15 characters / 8 words). Return only the title and nothing else.",
            ),
            ("human", "{messages}"),
        ]
    )

    chain = prompt | llm
    response = await chain.ainvoke({"messages": messages_text})
    new_title = response.content.strip().replace('"', "").replace("'", "")[:30]

    # 更新标题
    conversation.title = new_title
    await db.commit()

    return {"title": new_title}
