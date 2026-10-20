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
                max_tokens=500,
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
        model_name: str = "gemini-3.5-flash",
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
        if not self.api_key or self.api_key.startswith("YOUR_"):
            raise LLMNotConfiguredError("Google Gemini API key is not configured in environment.")

        grounded_prompt = build_grounded_user_prompt(user_prompt, context_chunks)

        try:
            import functools

            # Configure generative model with explicit system instruction for citation grounding
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_prompt,
            )

            gen_func = functools.partial(
                model.generate_content,
                grounded_prompt,
                generation_config={"max_output_tokens": 2048, "temperature": 0.2},
            )
            loop = asyncio.get_running_loop()
            resp = await asyncio.wait_for(
                loop.run_in_executor(None, gen_func),
                timeout=55.0,
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


class OllamaGateway(LLMGateway):
    """Local LLM gateway utilizing Ollama native service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        import httpx

        prompt_with_context = build_grounded_user_prompt(user_prompt, context_chunks)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_with_context},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            },
        }

        url = f"{self.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 404:
                err_data = {}
                try:
                    err_data = resp.json()
                except Exception:
                    pass
                err_msg = err_data.get("error", resp.text)
                raise LLMNotConfiguredError(
                    f"Ollama model '{self.model}' not found or endpoint unavailable: {err_msg}. "
                    f"Run: ollama pull {self.model}"
                )
            elif resp.status_code != 200:
                raise LLMException(
                    f"Ollama server returned error (HTTP {resp.status_code}): {resp.text}",
                    "OLLAMA_ERROR",
                    resp.status_code,
                )

            data = resp.json()
            message_obj = data.get("message", {})
            content = message_obj.get("content", "").strip()

            if not content:
                raise LLMInvalidResponseError("Ollama returned an empty completion response.")

            prompt_tok = data.get("prompt_eval_count")
            comp_tok = data.get("eval_count")

            return LLMResponse(
                content=content,
                model_used=self.model,
                provider="ollama",
                prompt_tokens=prompt_tok,
                completion_tokens=comp_tok,
            )

        except httpx.ConnectError as e:
            logger.warning(f"Ollama daemon connection failed at {self.base_url}: {e}")
            raise LLMNotConfiguredError(
                f"Ollama daemon is not running at {self.base_url}. Please ensure Ollama service is active."
            )
        except httpx.TimeoutException as e:
            logger.warning(f"Ollama request timed out after {self.timeout}s: {e}")
            raise LLMTimeoutError(f"Ollama local inference request timed out after {self.timeout}s.")
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Unexpected Ollama gateway error: {e}")
            raise LLMException(str(e), "OLLAMA_ERROR", 500)


class MultiProviderLLMGateway(LLMGateway):
    """Coordinates primary and fallback providers with transparent failover and offline mode enforcement."""

    def __init__(
        self,
        providers: Optional[List[LLMGateway]] = None,
        primary: Optional[LLMGateway] = None,
        fallback: Optional[LLMGateway] = None,
    ):
        if providers is not None:
            self.providers = providers
            return

        # If explicit primary / fallback passed (e.g. in unit tests)
        if primary is not None:
            self.providers = [primary]
            if fallback is not None:
                self.providers.append(fallback)
            return

        chain: List[LLMGateway] = []

        # 1. Strict OFFLINE_MODE enforcement: Only local provider allowed.
        if settings.OFFLINE_MODE:
            chain.append(OllamaGateway())
            self.providers = chain
            return

        # 2. Build provider chain based on LLM_PROVIDER
        configured_provider = settings.LLM_PROVIDER.lower().strip()
        if configured_provider == "ollama":
            chain.append(OllamaGateway())
            if settings.ENABLE_LOCAL_LLM_FALLBACK:
                chain.append(GroqGateway())
                chain.append(GeminiGateway())
        elif configured_provider in ("gemini", "google"):
            chain.append(GeminiGateway())
            chain.append(GroqGateway())
            if settings.ENABLE_LOCAL_LLM_FALLBACK:
                chain.append(OllamaGateway())
        else:  # default: "groq"
            chain.append(GroqGateway())
            chain.append(GeminiGateway())
            if settings.ENABLE_LOCAL_LLM_FALLBACK:
                chain.append(OllamaGateway())

        self.providers = chain

    @property
    def primary(self) -> Optional[LLMGateway]:
        return self.providers[0] if self.providers else None

    @property
    def fallback(self) -> Optional[LLMGateway]:
        return self.providers[1] if len(self.providers) > 1 else None

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: List[RetrievedChunk],
    ) -> LLMResponse:
        if not self.providers:
            raise LLMNotConfiguredError("No LLM providers are configured.")

        # In OFFLINE_MODE, verify NO cloud provider is ever called
        if settings.OFFLINE_MODE:
            first_provider = self.providers[0]
            if not isinstance(first_provider, OllamaGateway):
                raise LLMNotConfiguredError(
                    "OFFLINE_MODE is enabled but active provider is not a local gateway (Ollama)."
                )
            return await first_provider.complete(system_prompt, user_prompt, context_chunks)

        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                return await provider.complete(system_prompt, user_prompt, context_chunks)
            except (LLMQuotaExceededError, LLMTimeoutError, LLMNotConfiguredError) as err:
                last_error = err
                next_provider = self.providers[i + 1] if i + 1 < len(self.providers) else None
                if next_provider:
                    logger.warning(
                        f"Provider {provider.__class__.__name__} failed ({err.error_code}). "
                        f"Attempting failover to {next_provider.__class__.__name__}..."
                    )
                else:
                    logger.error(f"All configured LLM providers failed. Last error: {err}")
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} error: {e}")
                last_error = e
                next_provider = self.providers[i + 1] if i + 1 < len(self.providers) else None
                if next_provider:
                    logger.warning(f"Attempting failover to {next_provider.__class__.__name__}...")

        if isinstance(last_error, LLMException):
            raise last_error
        raise LLMException(str(last_error or "All providers failed"), "ALL_PROVIDERS_FAILED", 500)


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
