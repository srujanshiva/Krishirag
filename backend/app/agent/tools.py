"""Typed tool registry with timeout enforcement and structured audit logging."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.rag.retriever import AgriculturalRetriever, RetrievedChunk, retriever


# ── Tool Input / Output Schemas ──────────────────────────────────────────────


class RetrieveKnowledgeInput(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    top_k: int = Field(5, ge=1, le=10, description="Maximum passages to retrieve")
    crop: Optional[str] = Field(None, description="Optional crop filter context")


class CoverageInput(BaseModel):
    chunks: List[Any] = Field(..., description="List of retrieved passage chunks")
    min_threshold: float = Field(0.38, ge=0.0, le=1.0, description="Minimum cosine similarity")


class CoverageReport(BaseModel):
    sufficient: bool
    top_score: float
    evidence_count: int
    recommendation: str


class CropCalendarInput(BaseModel):
    crop: str = Field(..., description="Crop name (e.g. Rice, Pepper, Coconut)")
    season: Optional[str] = Field(None, description="Season (e.g. Kharif, Rabi, Summer)")


class CropCalendarReport(BaseModel):
    crop: str
    season: str
    sowing_window: str
    critical_stages: List[str]
    harvest_window: str


# ── Tool Execution Wrapper & Audit Trace ──────────────────────────────────────


@dataclass
class ToolAuditEntry:
    tool_name: str
    args: Dict[str, Any]
    duration_ms: float
    outcome: str
    error_message: Optional[str] = None


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type
    handler: Callable[[Any], Any]
    timeout_seconds: float = 10.0

    async def execute(self, raw_input: Any) -> Tuple[Any, ToolAuditEntry]:
        """Validate input schema, enforce timeout, and record execution metrics."""
        start_time = time.perf_counter()
        validated_input = (
            raw_input
            if isinstance(raw_input, self.input_schema)
            else self.input_schema(**raw_input)
        )
        sanitized_args = validated_input.model_dump()

        try:
            if asyncio.iscoroutinefunction(self.handler):
                result = await asyncio.wait_for(
                    self.handler(validated_input),
                    timeout=self.timeout_seconds,
                )
            else:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self.handler, validated_input),
                    timeout=self.timeout_seconds,
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            audit = ToolAuditEntry(
                tool_name=self.name,
                args=sanitized_args,
                duration_ms=round(elapsed_ms, 2),
                outcome="success",
            )
            logger.info(f"Tool '{self.name}' succeeded in {audit.duration_ms}ms")
            return result, audit

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            audit = ToolAuditEntry(
                tool_name=self.name,
                args=sanitized_args,
                duration_ms=round(elapsed_ms, 2),
                outcome="timeout",
                error_message=f"Execution exceeded timeout limit of {self.timeout_seconds}s",
            )
            logger.error(f"Tool '{self.name}' timed out after {audit.duration_ms}ms")
            raise TimeoutError(audit.error_message)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            audit = ToolAuditEntry(
                tool_name=self.name,
                args=sanitized_args,
                duration_ms=round(elapsed_ms, 2),
                outcome="error",
                error_message=str(e),
            )
            logger.error(f"Tool '{self.name}' failed: {e}")
            raise


# ── Handlers Implementation ──────────────────────────────────────────────────


def _handle_retrieve_knowledge(input_data: RetrieveKnowledgeInput) -> List[RetrievedChunk]:
    search_query = input_data.query
    if input_data.crop and input_data.crop.lower() not in search_query.lower():
        search_query = f"{input_data.crop} {search_query}"
    return retriever.retrieve(search_query, top_k=input_data.top_k)


def _handle_check_coverage(input_data: CoverageInput) -> CoverageReport:
    chunks = input_data.chunks
    if not chunks:
        return CoverageReport(
            sufficient=False,
            top_score=0.0,
            evidence_count=0,
            recommendation="Insufficient evidence: Consult local Krishi Bhavan / KVK.",
        )

    # Extract score if RetrievedChunk or dict
    top_score = 0.0
    for c in chunks:
        score = c.score if hasattr(c, "score") else c.get("score", 0.0)
        if score > top_score:
            top_score = score

    sufficient = top_score >= input_data.min_threshold
    return CoverageReport(
        sufficient=sufficient,
        top_score=round(top_score, 4),
        evidence_count=len(chunks),
        recommendation="Sufficient evidence to proceed" if sufficient else "Low evidence coverage",
    )


def _handle_lookup_crop_calendar(input_data: CropCalendarInput) -> CropCalendarReport:
    crop_lower = input_data.crop.strip().lower()

    # Authoritative SAU / Kerala package of practices reference dates
    if "rice" in crop_lower or "paddy" in crop_lower:
        return CropCalendarReport(
            crop="Rice (Oryza sativa L.)",
            season=input_data.season or "Kharif (Virippu) / Rabi (Mundakan)",
            sowing_window="May–June (Virippu) / September–October (Mundakan)",
            critical_stages=[
                "Active Tillering (20-25 DAT)",
                "Panicle Initiation (40-45 DAT)",
                "Flowering / Heading (60-70 DAT)",
                "Grain Filling / Dough stage (80-90 DAT)",
            ],
            harvest_window="September–October (Virippu) / January–February (Mundakan)",
        )
    elif "pepper" in crop_lower or "black pepper" in crop_lower:
        return CropCalendarReport(
            crop="Black Pepper (Piper nigrum L.)",
            season=input_data.season or "South-West Monsoon",
            sowing_window="May–June with onset of monsoon rains",
            critical_stages=[
                "Spike emergence (June-July)",
                "Berry development (August-October)",
                "Maturity (December-January)",
            ],
            harvest_window="December to February",
        )
    elif "coconut" in crop_lower:
        return CropCalendarReport(
            crop="Coconut (Cocos nucifera L.)",
            season=input_data.season or "Perennial",
            sowing_window="May–June planting of 9-12 month seedlings",
            critical_stages=[
                "Pre-monsoon fertilizer split (May-June)",
                "Post-monsoon fertilizer split (September-October)",
                "Summer irrigation management",
            ],
            harvest_window="Regular monthly harvest (45-50 days intervals)",
        )
    else:
        return CropCalendarReport(
            crop=input_data.crop,
            season=input_data.season or "General",
            sowing_window="Consult local agro-climatic guide for optimal sowing window",
            critical_stages=["Vegetative", "Flowering", "Maturity"],
            harvest_window="At physiological maturity",
        )


# ── Registered Tools Dictionary ──────────────────────────────────────────────


REGISTERED_TOOLS: Dict[str, Tool] = {
    "retrieve_knowledge": Tool(
        name="retrieve_knowledge",
        description="Search vetted agricultural knowledge base for agronomic guidance.",
        input_schema=RetrieveKnowledgeInput,
        output_schema=List[RetrievedChunk],
        handler=_handle_retrieve_knowledge,
        timeout_seconds=10.0,
    ),
    "check_evidence_coverage": Tool(
        name="check_evidence_coverage",
        description="Evaluate if retrieved evidence is sufficient and above confidence threshold.",
        input_schema=CoverageInput,
        output_schema=CoverageReport,
        handler=_handle_check_coverage,
        timeout_seconds=3.0,
    ),
    "lookup_crop_calendar": Tool(
        name="lookup_crop_calendar",
        description="Lookup official crop calendar, sowing windows, and critical growth stages.",
        input_schema=CropCalendarInput,
        output_schema=CropCalendarReport,
        handler=_handle_lookup_crop_calendar,
        timeout_seconds=2.0,
    ),
}
