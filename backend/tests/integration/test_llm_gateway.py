"""Integration test for Groq LLM Gateway using real credentials."""

import pytest
from backend.app.config import settings
from backend.app.llm.gateway import DEFAULT_SYSTEM_PROMPT, GroqGateway, LLMResponse
from backend.app.rag.retriever import RetrievedChunk


@pytest.mark.integration
@pytest.mark.asyncio
async def test_groq_gateway_live_completion():
    """Verify live Groq API connection and grounded answer generation."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("YOUR_"):
        pytest.skip("GROQ_API_KEY not configured for live integration test")

    gateway = GroqGateway()
    dummy_chunk = RetrievedChunk(
        chunk_id="chunk-test-12345",
        document_title="TNAU Crop Production Guide — Rice",
        publisher="TNAU",
        source_url="https://tnagriculture.in/guide.pdf",
        page_number=14,
        section="Nutrient Management",
        chunk_text="For transplanted rice, the recommended fertilizer dose is 120:38:38 kg N:P2O5:K2O per hectare.",
        score=0.92,
    )

    response = await gateway.complete(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        user_prompt="What is the recommended fertilizer dose for transplanted rice?",
        context_chunks=[dummy_chunk],
    )

    assert isinstance(response, LLMResponse)
    assert response.provider == "groq"
    assert response.model_used == settings.LLM_MODEL
    assert len(response.content) > 10
    assert "120" in response.content or "transplanted" in response.content.lower()
