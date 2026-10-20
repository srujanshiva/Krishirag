"""Multi-provider LLM gateway supporting Groq (primary) and Google Gemini (fallback)."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import google.generativeai as genai
from loguru import logger
from openai import APITimeoutError, AsyncOpenAI, RateLimitError

from backend.app.config import settings
from backend.app.rag.retriever import RetrievedChunk


# ── Custom Exceptions with Specific Error Codes ──────────────────────────────


class LLMException(Exception):
    """Base exception for all LLM gateway failures."""

    def __init__(self, message: str, error_code: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class LLMNotConfiguredError(LLMException):
    def __init__(self, message: str = "LLM provider is not configured with a valid API key."):
        super().__init__(message, "LLM_NOT_CONFIGURED", 503)


class LLMQuotaExceededError(LLMException):
    def __init__(self, message: str = "LLM provider rate limit or quota exceeded."):
        super().__init__(message, "LLM_QUOTA_EXCEEDED", 429)


class LLMTimeoutError(LLMException):
    def __init__(self, message: str = "LLM API request timed out."):
        super().__init__(message, "LLM_TIMEOUT", 504)


class LLMInvalidResponseError(LLMException):
    def __init__(self, message: str = "Received an invalid or empty response from LLM."):
        super().__init__(message, "LLM_INVALID_RESPONSE", 500)


@dataclass
class LLMResponse:
    content: str
    model_used: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class LLMGateway(ABC):
    """Abstract base class for LLM inference gateways."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        """Execute chat completion with grounded reference chunks."""
        pass


def build_grounded_user_prompt(
    user_query: str,
    context_chunks: List[RetrievedChunk],
    crop: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Format user query with retrieved context passages and citation IDs."""
    context_text = ""
    if context_chunks:
        context_text = "VERIFIED AGRICULTURAL REFERENCE PASSAGES:\n"
        for i, chunk in enumerate(context_chunks, 1):
            context_text += (
                f"\n--- [Passage {i}] (chunk_id: {chunk.chunk_id}) ---\n"
                f"Source: {chunk.document_title} (Publisher: {chunk.publisher}, Page: {chunk.page_number})\n"
                f"{chunk.chunk_text}\n"
            )
    else:
        context_text = "No relevant context passages were found in the knowledge base.\n"

    query_details = f"Farmer Question: {user_query}\n"
    if crop:
        query_details += f"Crop context: {crop}\n"
    if location:
        query_details += f"Location context: {location}\n"

    instructions = (
        "\nProvide an actionable, grounded advisory response answering the farmer's question. "
        "Reference citations using [chunk_id] directly after each recommendation or fact taken from that passage."
    )

    return f"{context_text}\n{query_details}\n{instructions}"


class GroqGateway(LLMGateway):
    """Primary LLM gateway utilizing Groq's high-speed inference API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

        if not self.api_key or self.api_key.startswith("YOUR_"):
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=float(self.timeout),
            )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        if not self.client:
            raise LLMNotConfiguredError("Groq API key is not configured in environment.")

        prompt_with_context = build_grounded_user_prompt(user_prompt, context_chunks)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_with_context},
        ]

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )

            if not resp.choices or not resp.choices[0].message.content:
                raise LLMInvalidResponseError("Groq returned an empty completion response.")

            choice = resp.choices[0]
            content = choice.message.content.strip()

            usage = resp.usage
            prompt_tok = usage.prompt_tokens if usage else None
            comp_tok = usage.completion_tokens if usage else None

            return LLMResponse(
                content=content,
                model_used=self.model,
                provider="groq",
                prompt_tokens=prompt_tok,
                completion_tokens=comp_tok,
            )

        except RateLimitError as e:
            logger.warning(f"Groq rate limit exceeded: {e}")
            raise LLMQuotaExceededError(str(e))
        except APITimeoutError as e:
            logger.warning(f"Groq request timed out: {e}")
            raise LLMTimeoutError(str(e))
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise LLMException(str(e), "GROQ_ERROR", 500)


class GeminiGateway(LLMGateway):
    """Secondary fallback LLM gateway utilizing Google Generative AI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-pro",
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

        if self.api_key and not self.api_key.startswith("YOUR_"):
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        if not self.model:
            raise LLMNotConfiguredError("Google Gemini API key is not configured in environment.")

        prompt_with_context = f"{system_prompt}\n\n" + build_grounded_user_prompt(
            user_prompt, context_chunks
        )

        try:
            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, self.model.generate_content, prompt_with_context),
                timeout=float(self.timeout),
            )

            if not resp or not resp.text:
                raise LLMInvalidResponseError("Gemini returned an empty completion response.")

            return LLMResponse(
                content=resp.text.strip(),
                model_used=self.model_name,
                provider="gemini",
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutError("Gemini request timed out.")
        except Exception as e:
            err_str = str(e)
            if "quota" in err_str.lower() or "429" in err_str:
                raise LLMQuotaExceededError(err_str)
            raise LLMException(err_str, "GEMINI_ERROR", 500)


class MultiProviderLLMGateway(LLMGateway):
    """Coordinates primary (Groq) and fallback (Gemini) providers with transparent failover."""

    def __init__(
        self,
        primary: Optional[LLMGateway] = None,
        fallback: Optional[LLMGateway] = None,
    ):
        self.primary = primary or GroqGateway()
        self.fallback = fallback or GeminiGateway()

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        # Try primary provider first
        try:
            return await self.primary.complete(system_prompt, user_prompt, context_chunks)
        except (LLMQuotaExceededError, LLMTimeoutError, LLMNotConfiguredError) as primary_err:
            logger.warning(
                f"Primary LLM ({self.primary.__class__.__name__}) failed ({primary_err.error_code}). "
                f"Attempting fallback ({self.fallback.__class__.__name__})..."
            )
            try:
                return await self.fallback.complete(system_prompt, user_prompt, context_chunks)
            except Exception as fallback_err:
                logger.error(f"Fallback LLM also failed: {fallback_err}")
                # Raise the primary error for clean client diagnostics
                raise primary_err


DEFAULT_SYSTEM_PROMPT = """You are KrishiRAG, an authoritative AI Agricultural Advisory System for Indian farmers.
Your mission is to provide accurate, grounded agronomic recommendations based strictly on the provided verified reference passages.

CRITICAL RULES:
1. Base your answer ONLY on the provided context passages. Never fabricate chemical names, application rates, or dosages.
2. For EVERY claim, recommendation, or number you provide, cite the source chunk using the exact format [chunk_id].
3. If the provided context does not contain enough evidence to answer the farmer's question safely, clearly state: "The verified agricultural manuals do not contain sufficient evidence to answer this question. Please consult your local Krishi Bhavan, KVK, or an agricultural extension officer."
4. Be concise, direct, and structured.
"""


def get_llm_gateway() -> LLMGateway:
    """Dependency factory for LLM gateway."""
    return MultiProviderLLMGateway()
