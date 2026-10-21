"""API tests for POST /api/v1/chat/stream Server-Sent Events endpoint."""

import json
import pytest
from httpx import AsyncClient

from backend.app.llm.gateway import LLMGateway, LLMResponse, get_llm_gateway
from backend.app.main import app
from backend.app.rag.retriever import RetrievedChunk


class MockStreamingLLM(LLMGateway):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[RetrievedChunk],
        *args,
        **kwargs,
    ) -> LLMResponse:
        cited_id = context_chunks[0].chunk_id if context_chunks else "none"
        return LLMResponse(
            content=f"Recommended seed rate for SRI rice is 5 kg per hectare [{cited_id}].",
            model_used="mock-stream-llm",
            provider="mock",
        )


@pytest.mark.asyncio
async def test_chat_stream_sse_flow(async_client: AsyncClient):
    """Verify /api/v1/chat/stream yields SSE events: status, evidence, tokens, complete, [DONE]."""
    app.dependency_overrides[get_llm_gateway] = lambda: MockStreamingLLM()

    try:
        resp = await async_client.post(
            "/api/v1/chat/stream",
            json={"question": "What is the seed rate for SRI rice?"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        lines = [line.strip() for line in resp.text.split("\n") if line.strip().startswith("data:")]
        assert len(lines) >= 4

        # Verify presence of DONE marker
        assert any("[DONE]" in line for line in lines)

        # Parse event payloads
        parsed_events = []
        for line in lines:
            payload_str = line.replace("data:", "").strip()
            if payload_str == "[DONE]":
                continue
            try:
                parsed_events.append(json.loads(payload_str))
            except Exception:
                pass

        event_types = [e.get("event") for e in parsed_events]
        assert "status" in event_types
        assert "evidence" in event_types
        assert "token" in event_types
        assert "complete" in event_types

        # Verify completion event has citations
        complete_event = next(e for e in parsed_events if e.get("event") == "complete")
        assert len(complete_event["citations"]) >= 1
        assert complete_event["conversation_id"] is not None
    finally:
        app.dependency_overrides.clear()
