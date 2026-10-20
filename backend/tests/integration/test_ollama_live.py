"""Real integration test executing live local inference via Ollama.

This test requires:
1. Ollama daemon running on http://localhost:11434
2. Model 'qwen2.5:3b' (or configured OLLAMA_MODEL) pulled locally.

If either requirement is not met, the test SKIPS with explicit diagnostics.
Mocked responses are strictly forbidden in this test file.
"""

import time
import httpx
import pytest

from backend.app.config import settings
from backend.app.llm.gateway import OllamaGateway, LLMResponse
from backend.app.rag.retriever import RetrievedChunk


@pytest.fixture
async def require_live_ollama():
    """Verify live Ollama service and target model presence prior to running integration test."""
    tags_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(tags_url)
            if resp.status_code != 200:
                pytest.skip(
                    f"Ollama endpoint {tags_url} returned HTTP {resp.status_code}. "
                    "Live Ollama integration test skipped."
                )
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            target_model = settings.OLLAMA_MODEL
            # Match model name or tag e.g. qwen2.5:3b or qwen2.5:3b-instruct
            if not any(target_model in m for m in models):
                pytest.skip(
                    f"Target model '{target_model}' is not pulled in local Ollama daemon. "
                    f"Available models: {models}. Run 'ollama pull {target_model}' to execute live inference."
                )
    except httpx.ConnectError:
        pytest.skip(
            f"Ollama daemon is not running on {settings.OLLAMA_BASE_URL}. "
            "Please start the native Ollama service or container to run live local tests."
        )
    except Exception as e:
        pytest.skip(f"Live Ollama diagnostic probe failed: {e}. Test skipped.")


@pytest.mark.ollama_live
@pytest.mark.asyncio
async def test_ollama_live_inference_completion(require_live_ollama):
    """Execute REAL local LLM inference via Ollama, verifying grounded response and citation formatting."""
    gateway = OllamaGateway(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )

    test_chunk = RetrievedChunk(
        chunk_id="chunk-ollama-live-001",
        document_title="TNAU Crop Production Guide - Rice",
        publisher="Tamil Nadu Agricultural University",
        source_url="https://tnagriculture.in/dashboard/CPG/01_Rice.pdf",
        page_number=54,
        section="SRI Fertilizer Schedule",
        chunk_text="For System of Rice Intensification (SRI), apply 150 kg N/ha in four splits: 25% basal, 25% active tillering, 25% panicle initiation, and 25% heading.",
        score=0.85,
    )

    start_time = time.perf_counter()
    response: LLMResponse = await gateway.complete(
        system_prompt=(
            "You are KrishiRAG, an agricultural advisory assistant. "
            "Answer the query using ONLY the provided verified passage. "
            "Always cite the exact chunk ID [chunk-ollama-live-001] after every recommendation."
        ),
        user_prompt="What are the four splits of nitrogen fertilizer for SRI rice?",
        context_chunks=[test_chunk],
    )
    duration_s = time.perf_counter() - start_time

    # Verify real local response properties
    assert isinstance(response, LLMResponse)
    assert response.provider == "ollama"
    assert response.model_used == settings.OLLAMA_MODEL
    assert len(response.content.strip()) > 20
    assert "[chunk-ollama-live-001]" in response.content

    # Output verified tokens and duration to stdout
    print(f"\n[LIVE OLLAMA INFERENCE VERIFIED]")
    print(f"Model: {response.model_used}")
    print(f"Duration: {duration_s:.2f}s")
    print(f"Prompt Tokens: {response.prompt_tokens}")
    print(f"Completion Tokens: {response.completion_tokens}")
    print(f"Response: {response.content}")
