"""Bounded agentic orchestrator state machine for farmer query advisory."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from loguru import logger

from backend.app.agent.safety import PromptSafetyGuard
from backend.app.agent.tools import (
    REGISTERED_TOOLS,
    CoverageInput,
    CoverageReport,
    RetrieveKnowledgeInput,
    ToolAuditEntry,
)
from backend.app.citations.validator import CitationValidator
from backend.app.llm.gateway import (
    DEFAULT_SYSTEM_PROMPT,
    LLMGateway,
    LLMNotConfiguredError,
    LLMQuotaExceededError,
    LLMTimeoutError,
    get_llm_gateway,
)
from backend.app.rag.retriever import RetrievedChunk
from backend.app.schemas.citations import CitationResponse


class AgentState(str, Enum):
    START = "START"
    VALIDATE_INPUT = "VALIDATE_INPUT"
    ASSESS_CONTEXT = "ASSESS_CONTEXT"
    RETRIEVE = "RETRIEVE"
    ASSESS_EVIDENCE = "ASSESS_EVIDENCE"
    CALL_LLM = "CALL_LLM"
    VALIDATE_CITATIONS = "VALIDATE_CITATIONS"
    SAFE_FALLBACK = "SAFE_FALLBACK"
    REJECT = "REJECT"
    RESPOND = "RESPOND"


@dataclass
class OrchestratorResult:
    state: AgentState
    answer: str
    citations: List[CitationResponse]
    uncertainty: str
    retrieval_score: Optional[float]
    evidence_count: int
    iterations_used: int
    audit_trace: List[Dict[str, Any]] = field(default_factory=list)


class AgentOrchestrator:
    """Bounded, deterministic state machine governing query validation, evidence retrieval,

    grounded LLM inference, and citation verification.
    """

    def __init__(
        self,
        llm: Optional[LLMGateway] = None,
        max_iterations: int = 10,
        max_wall_seconds: float = 75.0,
    ):
        self.llm = llm or get_llm_gateway()
        self.max_iterations = max_iterations
        self.max_wall_seconds = max_wall_seconds

    async def run(
        self,
        question: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
    ) -> OrchestratorResult:
        """Execute state machine transitions with hard bounded termination guarantees."""
        start_time = time.perf_counter()
        current_state = AgentState.START
        iteration = 0
        audit_records: List[Dict[str, Any]] = []

        retrieved_chunks: List[RetrievedChunk] = []
        coverage_report: Optional[CoverageReport] = None
        raw_llm_answer: str = ""
        final_answer: str = ""
        citations: List[CitationResponse] = []
        uncertainty: str = "high"
        top_score: Optional[float] = None

        while current_state not in (AgentState.RESPOND, AgentState.REJECT, AgentState.SAFE_FALLBACK):
            iteration += 1
            # Hard bounds enforcement
            elapsed_time = time.perf_counter() - start_time
            if iteration > self.max_iterations or elapsed_time > self.max_wall_seconds:
                logger.warning(
                    f"Agent bounds exceeded (iteration={iteration}/{self.max_iterations}, "
                    f"elapsed={elapsed_time:.1f}s). Forcing SAFE_FALLBACK."
                )
                current_state = AgentState.SAFE_FALLBACK
                break

            logger.info(f"Agent state: {current_state.value} (iteration {iteration})")

            # ── 1. START -> VALIDATE_INPUT ──────────────────────────────────
            if current_state == AgentState.START:
                current_state = AgentState.VALIDATE_INPUT

            # ── 2. VALIDATE_INPUT ───────────────────────────────────────────
            elif current_state == AgentState.VALIDATE_INPUT:
                stripped_q = question.strip()
                if not stripped_q or len(stripped_q) > 2000:
                    current_state = AgentState.REJECT
                    final_answer = "Invalid query length. Questions must be between 1 and 2000 characters."
                    break

                is_safe, violation_reason = PromptSafetyGuard.inspect_query(stripped_q)
                if not is_safe:
                    logger.warning(f"Rejecting query due to safety guardrail: {violation_reason}")
                    current_state = AgentState.REJECT
                    final_answer = (
                        "Query rejected by agricultural safety filters. "
                        "Please submit genuine agronomic or crop-related inquiries only."
                    )
                    break

                current_state = AgentState.ASSESS_CONTEXT

            # ── 3. ASSESS_CONTEXT -> RETRIEVE ───────────────────────────────
            elif current_state == AgentState.ASSESS_CONTEXT:
                # Prepare search parameters
                current_state = AgentState.RETRIEVE

            # ── 4. RETRIEVE ─────────────────────────────────────────────────
            elif current_state == AgentState.RETRIEVE:
                retrieve_tool = REGISTERED_TOOLS["retrieve_knowledge"]
                chunks_res, audit = await retrieve_tool.execute(
                    RetrieveKnowledgeInput(query=question, top_k=5, crop=crop)
                )
                audit_records.append(
                    {
                        "tool": audit.tool_name,
                        "duration_ms": audit.duration_ms,
                        "outcome": audit.outcome,
                    }
                )
                retrieved_chunks = chunks_res
                current_state = AgentState.ASSESS_EVIDENCE

            # ── 5. ASSESS_EVIDENCE ──────────────────────────────────────────
            elif current_state == AgentState.ASSESS_EVIDENCE:
                coverage_tool = REGISTERED_TOOLS["check_evidence_coverage"]
                report, audit = await coverage_tool.execute(
                    CoverageInput(chunks=retrieved_chunks, min_threshold=0.38)
                )
                audit_records.append(
                    {
                        "tool": audit.tool_name,
                        "duration_ms": audit.duration_ms,
                        "outcome": audit.outcome,
                    }
                )
                coverage_report = report
                top_score = report.top_score if report.evidence_count > 0 else None

                if not report.sufficient:
                    logger.info("Evidence coverage insufficient for safe advisory. Routing to SAFE_FALLBACK.")
                    current_state = AgentState.SAFE_FALLBACK
                else:
                    current_state = AgentState.CALL_LLM

            # ── 6. CALL_LLM ─────────────────────────────────────────────────
            elif current_state == AgentState.CALL_LLM:
                # Wrap evidence in XML-safe delimiters
                wrapped_corpus = PromptSafetyGuard.wrap_evidence_passages(retrieved_chunks)
                grounded_prompt = (
                    f"{wrapped_corpus}\n\n"
                    f"Farmer Question: {question}\n"
                    f"Crop context: {crop or 'None specified'}\n"
                    f"Location context: {location or 'None specified'}\n\n"
                    "Provide an authoritative agricultural advisory answering the query. "
                    "For every recommendation or numeric rate, cite the exact source chunk ID using [chunk_id]."
                )

                try:
                    resp = await self.llm.complete(
                        system_prompt=DEFAULT_SYSTEM_PROMPT,
                        user_prompt=grounded_prompt,
                        context_chunks=retrieved_chunks,
                    )
                    raw_llm_answer = resp.content
                    current_state = AgentState.VALIDATE_CITATIONS
                except (LLMNotConfiguredError, LLMQuotaExceededError, LLMTimeoutError) as e:
                    logger.error(f"LLM gateway raised fatal error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected LLM completion error: {e}. Transitioning to SAFE_FALLBACK.")
                    current_state = AgentState.SAFE_FALLBACK

            # ── 7. VALIDATE_CITATIONS ───────────────────────────────────────
            elif current_state == AgentState.VALIDATE_CITATIONS:
                val = CitationValidator.validate(raw_llm_answer, retrieved_chunks)
                final_answer = val.cleaned_answer
                citations = val.citations

                # Grounding confidence metric
                if val.valid_count > 0 and (top_score or 0.0) >= 0.65:
                    uncertainty = "none"
                elif val.valid_count > 0 and (top_score or 0.0) >= 0.48:
                    uncertainty = "low"
                else:
                    uncertainty = "high"
                    if "krishi bhavan" not in final_answer.lower() and "kvk" not in final_answer.lower():
                        final_answer += (
                            "\n\nNote: The verified knowledge base does not contain specific cited recommendations "
                            "for this query. Please consult your local Krishi Bhavan or KVK officer."
                        )

                current_state = AgentState.RESPOND

        # ── 8. TERMINAL STATES ──────────────────────────────────────────────
        if current_state == AgentState.SAFE_FALLBACK:
            final_answer = (
                "The verified agricultural reference manuals in our knowledge base do not contain sufficient evidence "
                "to answer this specific agronomic query safely. Please contact your local Krishi Bhavan, "
                "Krishi Vigyan Kendra (KVK), or an agricultural extension officer for customized on-field advice."
            )
            citations = []
            uncertainty = "high"

        return OrchestratorResult(
            state=current_state,
            answer=final_answer,
            citations=citations,
            uncertainty=uncertainty,
            retrieval_score=top_score,
            evidence_count=len(retrieved_chunks),
            iterations_used=iteration,
            audit_trace=audit_records,
        )
