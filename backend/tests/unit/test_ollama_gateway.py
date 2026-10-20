"""Unit tests for OllamaGateway and local LLM fallback / offline mode enforcement."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.config import settings
from backend.app.llm.gateway import (
    GroqGateway,
    GeminiGateway,
    OllamaGateway,
    MultiProviderLLMGateway,
    LLMNotConfiguredError,
    LLMQuotaExceededError,
    LLMTimeoutError,
    LLMInvalidResponseError,
    LLMResponse,
)
from backend.app.rag.retriever import RetrievedChunk


@pytest.fixture
def sample_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-test-123",
        document_title="TNAU Rice Production Guide",
        publisher="TNAU",
        source_url="https://example.com/rice.pdf",
        page_number=42,
        section="Nutrient Management",
        chunk_text="Apply 150 kg N/ha in four equal splits for short duration varieties.",
        score=0.88,
    )


@pytest.mark.asyncio
async def test_ollama_gateway_successful_completion(sample_chunk):
    """Verify OllamaGateway formats prompt, executes chat API, and returns LLMResponse."""
    gateway = OllamaGateway(base_url="http://localhost:11434", model="qwen2.5:3b", timeout=30)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "qwen2.5:3b",
        "message": {
            "role": "assistant",
            "content": "For short duration rice, apply 150 kg N/ha in four equal splits [chunk-test-123].",
        },
        "prompt_eval_count": 128,
        "eval_count": 34,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        res = await gateway.complete(
            system_prompt="You are an expert agronomist.",
            user_prompt="What is the nitrogen split for rice?",
            context_chunks=[sample_chunk],
        )

        assert isinstance(res, LLMResponse)
        assert res.provider == "ollama"
        assert res.model_used == "qwen2.5:3b"
        assert "[chunk-test-123]" in res.content
        assert res.prompt_tokens == 128
        assert res.completion_tokens == 34

        # Verify request payload
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "qwen2.5:3b"
        assert payload["stream"] is False
        assert len(payload["messages"]) == 2
        assert "chunk-test-123" in payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_ollama_gateway_connection_refused(sample_chunk):
    """Verify ConnectError is mapped to LLMNotConfiguredError with actionable guidance."""
    gateway = OllamaGateway(base_url="http://localhost:11434", model="qwen2.5:3b", timeout=5)

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(LLMNotConfiguredError) as exc_info:
            await gateway.complete(
                system_prompt="System instructions",
                user_prompt="Farmer query",
                context_chunks=[sample_chunk],
            )
        assert "Ollama daemon is not running" in str(exc_info.value)
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_ollama_gateway_model_not_found(sample_chunk):
    """Verify HTTP 404 is mapped to LLMNotConfiguredError instructing model pull."""
    gateway = OllamaGateway(base_url="http://localhost:11434", model="qwen2.5:3b", timeout=5)

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"error": "model 'qwen2.5:3b' not found, try pulling it first"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        with pytest.raises(LLMNotConfiguredError) as exc_info:
            await gateway.complete(
                system_prompt="System instructions",
                user_prompt="Farmer query",
                context_chunks=[sample_chunk],
            )
        assert "not found or endpoint unavailable" in str(exc_info.value)
        assert "ollama pull qwen2.5:3b" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_gateway_timeout(sample_chunk):
    """Verify TimeoutException is mapped to LLMTimeoutError (HTTP 504)."""
    gateway = OllamaGateway(base_url="http://localhost:11434", model="qwen2.5:3b", timeout=10)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(LLMTimeoutError) as exc_info:
            await gateway.complete(
                system_prompt="System instructions",
                user_prompt="Farmer query",
                context_chunks=[sample_chunk],
            )
        assert "timed out" in str(exc_info.value)
        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_ollama_gateway_empty_response(sample_chunk):
    """Verify empty message content raises LLMInvalidResponseError."""
    gateway = OllamaGateway(base_url="http://localhost:11434", model="qwen2.5:3b")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "qwen2.5:3b",
        "message": {"role": "assistant", "content": "   "},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        with pytest.raises(LLMInvalidResponseError):
            await gateway.complete(
                system_prompt="System instructions",
                user_prompt="Farmer query",
                context_chunks=[sample_chunk],
            )


@pytest.mark.asyncio
async def test_multi_provider_offline_mode_strict_containment(sample_chunk):
    """Verify OFFLINE_MODE=True strictly restricts inference to local Ollama and never calls cloud."""
    with patch.object(settings, "OFFLINE_MODE", True):
        multi_gateway = MultiProviderLLMGateway()

        assert len(multi_gateway.providers) == 1
        assert isinstance(multi_gateway.providers[0], OllamaGateway)

        # Mock Ollama failing to ensure it raises without falling back to cloud
        with patch.object(
            OllamaGateway,
            "complete",
            side_effect=LLMNotConfiguredError("Ollama daemon offline"),
        ) as mock_ollama:
            with pytest.raises(LLMNotConfiguredError):
                await multi_gateway.complete(
                    system_prompt="System",
                    user_prompt="Query",
                    context_chunks=[sample_chunk],
                )
            mock_ollama.assert_called_once()


@pytest.mark.asyncio
async def test_multi_provider_fallback_to_ollama_when_cloud_quota_exceeded(sample_chunk):
    """Verify that when ENABLE_LOCAL_LLM_FALLBACK is True and cloud quotas are exceeded, system fails over to Ollama."""
    mock_groq = AsyncMock(spec=GroqGateway)
    mock_groq.complete.side_effect = LLMQuotaExceededError("Groq 429 daily limit reached")

    mock_gemini = AsyncMock(spec=GeminiGateway)
    mock_gemini.complete.side_effect = LLMQuotaExceededError("Gemini 429 quota exhausted")

    mock_ollama = AsyncMock(spec=OllamaGateway)
    mock_ollama.complete.return_value = LLMResponse(
        content="Offline advisory from local model [chunk-test-123]",
        model_used="qwen2.5:3b",
        provider="ollama",
    )

    multi_gateway = MultiProviderLLMGateway(providers=[mock_groq, mock_gemini, mock_ollama])

    res = await multi_gateway.complete(
        system_prompt="System prompt",
        user_prompt="Farmer query",
        context_chunks=[sample_chunk],
    )

    assert res.provider == "ollama"
    assert "Offline advisory" in res.content
    mock_groq.complete.assert_called_once()
    mock_gemini.complete.assert_called_once()
    mock_ollama.complete.assert_called_once()
