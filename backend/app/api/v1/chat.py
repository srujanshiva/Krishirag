"""Chat endpoint providing grounded agricultural advisory with citation validation."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.citations.validator import CitationValidator
from backend.app.db.models import Conversation, Message
from backend.app.db.session import get_db
from backend.app.llm.gateway import (
    DEFAULT_SYSTEM_PROMPT,
    LLMGateway,
    LLMNotConfiguredError,
    LLMQuotaExceededError,
    LLMTimeoutError,
    get_llm_gateway,
)
from backend.app.rag.retriever import AgriculturalRetriever, RetrievedChunk
from backend.app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["Chat Advisory"])
retriever = AgriculturalRetriever()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_advisory(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    llm: LLMGateway = Depends(get_llm_gateway),
):
    """Deliver verified, grounded agronomic advisory with verified citations."""
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

    # 2. Retrieval from Knowledge Base
    search_query = request.question
    if request.crop and request.crop.lower() not in search_query.lower():
        search_query = f"{request.crop} {search_query}"

    retrieved_chunks = retriever.retrieve(search_query, top_k=5, score_threshold=0.35)
    top_score: Optional[float] = retrieved_chunks[0].score if retrieved_chunks else None

    # 3. Grounded Advisory Generation or Safe Guardrail Fallback
    if not retrieved_chunks:
        # Knowledge Base does not cover query or is empty
        answer_text = (
            "The verified agricultural manuals in our knowledge base do not contain sufficient evidence "
            "to safely answer this specific query. Please consult your local Krishi Bhavan, "
            "Krishi Vigyan Kendra (KVK), or an agricultural extension officer for on-field diagnosis."
        )
        uncertainty = "high"
        final_citations = []
    else:
        try:
            llm_response = await llm.complete(
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                user_prompt=request.question,
                context_chunks=retrieved_chunks,
            )

            # Validate and strip hallucinated citation IDs
            validation_result = CitationValidator.validate(
                raw_answer=llm_response.content,
                retrieved_chunks=retrieved_chunks,
            )

            answer_text = validation_result.cleaned_answer
            final_citations = validation_result.citations

            # If citations were cited and verified, confidence is strong
            if len(final_citations) > 0 and (top_score or 0.0) >= 0.65:
                uncertainty = "none"
            elif len(final_citations) > 0 and (top_score or 0.0) >= 0.50:
                uncertainty = "low"
            else:
                uncertainty = "high"
                if "krishi bhavan" not in answer_text.lower() and "kvk" not in answer_text.lower():
                    answer_text += (
                        "\n\nNote: The verified agricultural knowledge base does not contain sufficient evidence "
                        "for this query. Please consult your local Krishi Bhavan or KVK officer."
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

    # 4. Persist Assistant Response
    assistant_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        citations=[c.model_dump() for c in final_citations],
        uncertainty=uncertainty,
    )
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(
        request_id=request_id,
        answer=answer_text,
        citations=final_citations,
        uncertainty=uncertainty,
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        retrieval_score=top_score,
        evidence_count=len(retrieved_chunks),
    )
