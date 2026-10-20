"""Chat endpoint providing grounded agricultural advisory via bounded agentic state machine."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.db.models import Conversation, Message
from backend.app.db.session import get_db
from backend.app.rag.retriever import retriever
from backend.app.llm.gateway import (
    LLMGateway,
    LLMNotConfiguredError,
    LLMQuotaExceededError,
    LLMTimeoutError,
    get_llm_gateway,
)
from backend.app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["Chat Advisory"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_advisory(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
):
    """Deliver verified, grounded agronomic advisory with verified citations via bounded agent."""
    request_id = uuid.uuid4()

    # 1. Conversation Management
    conv_id = request.conversation_id or uuid.uuid4()
    conv_stmt = select(Conversation).where(Conversation.id == conv_id)
    res = await db.execute(conv_stmt)
    conversation = res.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(id=conv_id)
        db.add(conversation)
        await db.flush()

    # Persist user question
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)
    await db.flush()

    # 2. Execute Bounded Agentic State Machine
    orchestrator = AgentOrchestrator(llm=llm)
    try:
        orch_res = await orchestrator.run(
            question=request.question,
            crop=request.crop,
            location=request.location,
        )
    except LLMNotConfiguredError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": e.error_code, "message": e.message},
        )
    except LLMQuotaExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_code": e.error_code, "message": e.message},
        )
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error_code": e.error_code, "message": e.message},
        )

    # 3. Persist Assistant Response
    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content=orch_res.answer,
        citations=[c.model_dump() for c in orch_res.citations],
        uncertainty=orch_res.uncertainty,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        request_id=request_id,
        answer=orch_res.answer,
        citations=orch_res.citations,
        uncertainty=orch_res.uncertainty,
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        retrieval_score=orch_res.retrieval_score,
        evidence_count=orch_res.evidence_count,
    )
