"""Chat endpoint providing grounded agricultural advisory via bounded agentic state machine."""

import asyncio
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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

    # Fetch prior conversation history (up to last 6 messages / 3 turns)
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    history_res = await db.execute(history_stmt)
    prior_messages = history_res.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages[-6:]
    ]

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
            conversation_history=conversation_history,
            image_data=request.image_data,
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
        weather=orch_res.weather,
        faithfulness=orch_res.faithfulness,
        chemical_safety=orch_res.chemical_safety,
        dosage_calculation=orch_res.dosage_calculation,
        visual_diagnostic=orch_res.visual_diagnostic,
    )


@router.post("/chat/stream")
async def chat_advisory_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
):
    """Deliver real-time Server-Sent Events (SSE) token stream with citation grounding."""
    conv_id = request.conversation_id or uuid.uuid4()
    conv_stmt = select(Conversation).where(Conversation.id == conv_id)
    res = await db.execute(conv_stmt)
    conversation = res.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(id=conv_id)
        db.add(conversation)
        await db.flush()

    # Fetch prior conversation history (up to last 6 messages)
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    history_res = await db.execute(history_stmt)
    prior_messages = history_res.scalars().all()
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages[-6:]
    ]

    # Persist user message
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)
    await db.flush()

    async def event_generator():
        yield f"data: {json.dumps({'event': 'status', 'state': 'VALIDATE_INPUT', 'message': 'Validating agronomic query...'})}\n\n"
        await asyncio.sleep(0.01)

        orchestrator = AgentOrchestrator(llm=llm)
        run_task = asyncio.create_task(
            orchestrator.run(
                question=request.question,
                crop=request.crop,
                location=request.location,
                conversation_history=conversation_history,
                image_data=request.image_data,
            )
        )
        try:
            while not run_task.done():
                done, _ = await asyncio.wait([run_task], timeout=2.0)
                if not run_task.done():
                    yield ": keep-alive\n\n"
            orch_res = await run_task
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
            return

        yield f"data: {json.dumps({'event': 'evidence', 'evidence_count': orch_res.evidence_count, 'retrieval_score': orch_res.retrieval_score})}\n\n"

        # Stream answer tokens in progressive increments
        words = orch_res.answer.split(" ")
        for i in range(0, len(words), 3):
            chunk_words = " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
            yield f"data: {json.dumps({'event': 'token', 'token': chunk_words})}\n\n"
            await asyncio.sleep(0.02)

        # Persist assistant message
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

        # Emit completion metadata with citations
        metadata_payload = {
            "event": "complete",
            "conversation_id": str(conversation.id),
            "message_id": str(assistant_msg.id),
            "uncertainty": orch_res.uncertainty,
            "citations": [c.model_dump() for c in orch_res.citations],
            "evidence_count": orch_res.evidence_count,
            "retrieval_score": orch_res.retrieval_score,
            "weather": orch_res.weather,
            "faithfulness": orch_res.faithfulness,
            "chemical_safety": orch_res.chemical_safety,
            "dosage_calculation": orch_res.dosage_calculation,
            "visual_diagnostic": orch_res.visual_diagnostic,
        }
        yield f"data: {json.dumps(metadata_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
