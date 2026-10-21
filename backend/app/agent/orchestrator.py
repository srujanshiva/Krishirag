"""Bounded agentic orchestrator state machine for farmer query advisory."""

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

from backend.app.agent.safety import PromptSafetyGuard
from backend.app.agent.tools import (
    REGISTERED_TOOLS,
    ChemicalSafetyInput,
    ChemicalSafetyReport,
    CoverageInput,
    CoverageReport,
    CropCalendarInput,
    CropCalendarReport,
    DosageCalculatorInput,
    DosageCalculatorReport,
    LeafDiagnosticInput,
    LeafDiagnosticReport,
    RetrieveKnowledgeInput,
    ToolAuditEntry,
    WeatherInput,
    WeatherReport,
)
from backend.app.citations.faithfulness import evaluate_faithfulness
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
    weather: Optional[Dict[str, Any]] = None
    faithfulness: Optional[Dict[str, Any]] = None
    chemical_safety: Optional[Dict[str, Any]] = None
    dosage_calculation: Optional[Dict[str, Any]] = None
    visual_diagnostic: Optional[Dict[str, Any]] = None


class AgentOrchestrator:
    """Bounded, deterministic state machine governing query validation, evidence retrieval,

    grounded LLM inference, and citation verification.
    """

    def __init__(
        self,
        llm: Optional[LLMGateway] = None,
        max_iterations: int = 10,
        max_wall_seconds: float = 120.0,
    ):
        self.llm = llm or get_llm_gateway()
        self.max_iterations = max_iterations
        self.max_wall_seconds = max_wall_seconds

    @staticmethod
    def _detect_crop_name(text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Detect referenced crop from current question or recent conversation history."""
        text_lower = text.lower()
        crops = [
            ("rice", ["rice", "paddy", "sri", "nellu"]),
            ("pepper", ["pepper", "black pepper", "kurumulaku"]),
            ("coconut", ["coconut", "thep", "keram", "tenkai"]),
            ("wheat", ["wheat", "gehun"]),
            ("cotton", ["cotton", "kapas", "patthi"]),
            ("maize", ["maize", "corn", "makka"]),
            ("banana", ["banana", "plantain", "vazha"]),
        ]
        for canonical, aliases in crops:
            if any(alias in text_lower for alias in aliases):
                return canonical.capitalize()

        if conversation_history:
            for turn in reversed(conversation_history[-4:]):
                content_lower = turn.get("content", "").lower()
                for canonical, aliases in crops:
                    if any(alias in content_lower for alias in aliases):
                        return canonical.capitalize()

        return None

    @staticmethod
    def _detect_location_name(
        text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """Detect referenced geographic district or agro-climatic region."""
        locations = [
            "palakkad", "coimbatore", "thanjavur", "madurai", "wayanad", "alappuzha",
            "kottayam", "thrissur", "guntur", "warangal", "nagapattinam", "tiruvarur",
            "kerala", "tamil nadu", "andhra pradesh", "telangana", "karnataka",
        ]
        text_lower = text.lower()
        for loc in locations:
            if loc in text_lower:
                return loc.title()

        if conversation_history:
            for turn in reversed(conversation_history[-4:]):
                content_lower = turn.get("content", "").lower()
                for loc in locations:
                    if loc in content_lower:
                        return loc.title()

        return None

    @staticmethod
    def _detect_chemical_inquiry(text: str) -> Optional[Tuple[str, Optional[int]]]:
        """Detect chemical compound name and optional days-to-harvest from question."""
        text_lower = text.lower()
        chemicals = [
            "tricyclazole", "chlorpyrifos", "carbendazim", "mancozeb",
            "monocrotophos", "phorate", "hexaconazole", "quinalphos",
            "malathion", "glyphosate", "pseudomonas", "neem"
        ]
        detected_chem = None
        for chem in chemicals:
            if chem in text_lower:
                detected_chem = chem
                break

        if not detected_chem:
            if any(w in text_lower for w in ["pesticide", "fungicide", "insecticide", "spray", "spraying"]):
                detected_chem = "chemical"
            else:
                return None

        days_match = re.search(r"(\d+)\s*(?:days?|d)\s*(?:to|before|until)?\s*harvest", text_lower)
        if not days_match:
            days_match = re.search(r"harvest(?:ing)?\s*(?:in|after)?\s*(\d+)\s*(?:days?|d)", text_lower)

        days = int(days_match.group(1)) if days_match else None
        return detected_chem, days

    @staticmethod
    def _detect_dosage_inquiry(text: str) -> Optional[Tuple[float, str]]:
        """Detect land area or plant count inquiry for fertilizer calculation."""
        text_lower = text.lower()
        keywords = [
            "fertilizer", "fertiliser", "dosage", "dose", "urea", "dap", "potash",
            "mop", "npk", "factamfos", "how much fertilizer", "split", "bag", "bags"
        ]
        if not any(k in text_lower for k in keywords):
            return None

        # Match numeric value followed by unit
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(acre|acres|cent|cents|hectare|hectares|ha|guntha|gunthas|palm|palms|tree|trees|vine|vines)",
            text_lower,
        )
        if match:
            val = float(match.group(1))
            unit = match.group(2).lower()
            return val, unit

        # Match area if keywords present
        for u in ["acre", "cent", "hectare", "ha", "guntha"]:
            m = re.search(rf"(\d+(?:\.\d+)?)\s*{u}", text_lower)
            if m:
                return float(m.group(1)), u

        return None

    async def run(
        self,
        question: str,
        crop: Optional[str] = None,
        location: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        image_data: Optional[str] = None,
    ) -> OrchestratorResult:
        """Execute state machine transitions with hard bounded termination guarantees."""
        start_time = time.perf_counter()
        current_state = AgentState.START
        iteration = 0
        audit_records: List[Dict[str, Any]] = []

        retrieved_chunks: List[RetrievedChunk] = []
        coverage_report: Optional[CoverageReport] = None
        calendar_report: Optional[CropCalendarReport] = None
        weather_report: Optional[WeatherReport] = None
        chemical_safety_report: Optional[ChemicalSafetyReport] = None
        dosage_report: Optional[DosageCalculatorReport] = None
        visual_diagnostic_report: Optional[LeafDiagnosticReport] = None
        faithfulness_payload: Optional[Dict[str, Any]] = None
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
                effective_crop = crop or self._detect_crop_name(question, conversation_history)
                effective_location = location or self._detect_location_name(question, conversation_history)

                # Check if question has calendar, sowing, planting, seasonal, or growth stage intent
                calendar_keywords = [
                    "calendar", "sowing", "sow", "plant", "planting", "season",
                    "harvest", "stages", "growth stage", "critical stages", "when to grow",
                    "when should i grow", "when to cultivate", "cultivation schedule", "split dose",
                ]
                has_calendar_intent = any(k in question.lower() for k in calendar_keywords)

                if has_calendar_intent and effective_crop:
                    try:
                        cal_tool = REGISTERED_TOOLS["lookup_crop_calendar"]
                        cal_res, audit = await cal_tool.execute(
                            CropCalendarInput(crop=effective_crop)
                        )
                        audit_records.append(
                            {
                                "tool": audit.tool_name,
                                "duration_ms": audit.duration_ms,
                                "outcome": audit.outcome,
                            }
                        )
                        calendar_report = cal_res
                        logger.info(f"Crop calendar tool executed for crop '{effective_crop}'")
                    except Exception as e:
                        logger.warning(f"Crop calendar lookup failed: {e}")

                # Check if question has weather, rain, temperature, spraying, wind, or forecast intent
                weather_keywords = [
                    "weather", "forecast", "rain", "rainfall", "temperature",
                    "wind", "spray", "spraying", "humidity", "irrigate", "irrigation",
                    "monsoon", "climate", "storm", "today", "tomorrow",
                ]
                has_weather_intent = any(w in question.lower() for w in weather_keywords)

                if has_weather_intent and effective_location:
                    try:
                        weather_tool = REGISTERED_TOOLS["lookup_weather"]
                        w_res, audit = await weather_tool.execute(
                            WeatherInput(location=effective_location, crop=effective_crop)
                        )
                        audit_records.append(
                            {
                                "tool": audit.tool_name,
                                "duration_ms": audit.duration_ms,
                                "outcome": audit.outcome,
                            }
                        )
                        weather_report = w_res
                        logger.info(f"Weather tool executed for location '{effective_location}'")
                    except Exception as e:
                        logger.warning(f"Weather lookup failed: {e}")

                # Check chemical safety inquiry (Pre-Harvest Interval & CIBRC/KAU bans)
                chem_info = self._detect_chemical_inquiry(question)
                if chem_info:
                    chem_name, days_harvest = chem_info
                    try:
                        safety_tool = REGISTERED_TOOLS["check_chemical_safety"]
                        safety_res, audit = await safety_tool.execute(
                            ChemicalSafetyInput(chemical=chem_name, crop=effective_crop, days_to_harvest=days_harvest)
                        )
                        audit_records.append(
                            {
                                "tool": audit.tool_name,
                                "duration_ms": audit.duration_ms,
                                "outcome": audit.outcome,
                            }
                        )
                        chemical_safety_report = safety_res
                        logger.info(f"Chemical safety guardrail executed: {safety_res.chemical} - Safe: {safety_res.is_safe}")
                    except Exception as e:
                        logger.warning(f"Chemical safety check failed: {e}")

                # Check fertilizer dosage inquiry (Land Area to Commercial Fertilizer Bags)
                dosage_info = self._detect_dosage_inquiry(question)
                if dosage_info:
                    val, unit = dosage_info
                    target_crop = effective_crop or "Rice"
                    try:
                        dosage_tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]
                        d_res, audit = await dosage_tool.execute(
                            DosageCalculatorInput(crop=target_crop, area_value=val, area_unit=unit)
                        )
                        audit_records.append(
                            {
                                "tool": audit.tool_name,
                                "duration_ms": audit.duration_ms,
                                "outcome": audit.outcome,
                            }
                        )
                        dosage_report = d_res
                        logger.info(f"Fertilizer dosage calculated: {d_res.crop} ({d_res.input_display}) - Urea: {d_res.urea_kg}kg, DAP: {d_res.dap_kg}kg, MOP: {d_res.mop_kg}kg")
                    except Exception as e:
                        logger.warning(f"Fertilizer dosage calculation failed: {e}")

                # Check visual leaf disease diagnostic if image is provided
                if image_data:
                    try:
                        diag_tool = REGISTERED_TOOLS["diagnose_crop_image"]
                        diag_res, audit = await diag_tool.execute(
                            LeafDiagnosticInput(image_data=image_data, crop=effective_crop, notes=question)
                        )
                        audit_records.append(
                            {
                                "tool": audit.tool_name,
                                "duration_ms": audit.duration_ms,
                                "outcome": audit.outcome,
                            }
                        )
                        visual_diagnostic_report = diag_res
                        logger.info(f"Visual leaf diagnostic completed: {diag_res.crop} - Suspected: {diag_res.suspected_diseases}")
                    except Exception as e:
                        logger.warning(f"Leaf image diagnostic tool failed: {e}")

                current_state = AgentState.RETRIEVE

            # ── 4. RETRIEVE ─────────────────────────────────────────────────
            elif current_state == AgentState.RETRIEVE:
                retrieve_tool = REGISTERED_TOOLS["retrieve_knowledge"]
                effective_crop = crop or self._detect_crop_name(question, conversation_history)
                search_q = question
                if visual_diagnostic_report and visual_diagnostic_report.search_keywords:
                    diag_kw = " ".join(visual_diagnostic_report.search_keywords[:2])
                    search_q = f"{search_q} {diag_kw}"
                elif effective_crop and effective_crop.lower() not in question.lower():
                    search_q = f"{effective_crop} {question}"

                chunks_res, audit = await retrieve_tool.execute(
                    RetrieveKnowledgeInput(query=search_q, top_k=4, crop=effective_crop)
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

                if not report.sufficient and not calendar_report and not weather_report:
                    logger.info("Evidence coverage insufficient for safe advisory. Routing to SAFE_FALLBACK.")
                    current_state = AgentState.SAFE_FALLBACK
                else:
                    current_state = AgentState.CALL_LLM

            # ── 6. CALL_LLM ─────────────────────────────────────────────────
            elif current_state == AgentState.CALL_LLM:
                # Wrap evidence in XML-safe delimiters
                wrapped_corpus = PromptSafetyGuard.wrap_evidence_passages(retrieved_chunks)
                effective_crop = crop or self._detect_crop_name(question, conversation_history)
                effective_location = location or self._detect_location_name(question, conversation_history)

                calendar_section = ""
                if calendar_report:
                    calendar_section = (
                        f"\nOFFICIAL CROP CALENDAR DATA ({calendar_report.crop}):\n"
                        f"- Recommended Season: {calendar_report.season}\n"
                        f"- Sowing Window: {calendar_report.sowing_window}\n"
                        f"- Critical Stages: {', '.join(calendar_report.critical_stages)}\n"
                        f"- Harvest Window: {calendar_report.harvest_window}\n"
                    )

                weather_section = ""
                if weather_report:
                    weather_section = (
                        f"\nREAL-TIME AGROMETEOROLOGICAL FORECAST ({weather_report.location}):\n"
                        f"- Ambient Temperature: {weather_report.temperature_c}°C | Relative Humidity: {weather_report.humidity_percent}%\n"
                        f"- Current Precipitation: {weather_report.precipitation_mm}mm | 12h Rain Risk: {weather_report.precipitation_prob_percent}%\n"
                        f"- Wind Speed: {weather_report.wind_speed_kmh} km/h | Sky Condition: {weather_report.condition}\n"
                        f"- Spraying Advisory: {weather_report.spraying_advisory}\n"
                        f"- Fieldwork Advisory: {weather_report.fieldwork_advisory}\n"
                        f"ADVISORY DIRECTIVE: Incorporate these live meteorological constraints directly into your recommendations.\n"
                    )

                chemical_section = ""
                if chemical_safety_report:
                    warning_note = ""
                    if not chemical_safety_report.is_safe:
                        warning_note = (
                            f"CRITICAL SAFETY WARNING: {chemical_safety_report.warning_level.upper()} VIOLATION!\n"
                            f"Issue: {chemical_safety_report.explanation}\n"
                            f"MANDATORY REGULATORY DIRECTIVE: Explicitly instruct the farmer NOT to apply {chemical_safety_report.chemical}. "
                            f"Recommend safe biological or organic alternative: {chemical_safety_report.alternative_recommended}.\n"
                        )
                    else:
                        warning_note = (
                            f"Regulatory Safety Guidance: Pre-Harvest Interval (PHI) is {chemical_safety_report.phi_days} days. "
                            f"FSSAI Maximum Residue Limit (MRL): {chemical_safety_report.mrl_ppm} ppm. Always wear PPE.\n"
                        )
                    chemical_section = (
                        f"\nREGULATORY CHEMICAL SAFETY & PHI DIRECTIVE:\n"
                        f"- Chemical: {chemical_safety_report.chemical} ({chemical_safety_report.toxicity_class})\n"
                        f"{warning_note}"
                    )

                dosage_section = ""
                if dosage_report:
                    dosage_section = (
                        f"\nOFFICIAL COMMERCIAL FERTILIZER CALCULATION ({dosage_report.crop} for {dosage_report.input_display}):\n"
                        f"- Recommended NPK Ratio: {dosage_report.recommended_npk_ratio}\n"
                        f"- Commercial Fertilizer Quantities: Urea: {dosage_report.urea_kg} kg | DAP: {dosage_report.dap_kg} kg | Muriate of Potash (MOP): {dosage_report.mop_kg} kg\n"
                        f"- Recommended Split Applications:\n  " + "\n  ".join(dosage_report.application_splits) + "\n"
                        f"- Agronomic Advice: {dosage_report.notes}\n"
                    )

                diagnostic_section = ""
                if visual_diagnostic_report:
                    diagnostic_section = (
                        f"\nMULTIMODAL LEAF DISEASE VISUAL DIAGNOSTIC REPORT ({visual_diagnostic_report.crop}):\n"
                        f"- Suspected Pathologies: {', '.join(visual_diagnostic_report.suspected_diseases)} (Confidence: {int(visual_diagnostic_report.confidence_score * 100)}%)\n"
                        f"- Detected Visual Lesion Symptoms: {', '.join(visual_diagnostic_report.symptoms_detected)}\n"
                        f"- First-Line Management Directive: {visual_diagnostic_report.immediate_action}\n"
                        f"ADVISORY DIRECTIVE: Explicitly explain whether the farmer's uploaded leaf image matches these symptoms and cite verified Package of Practices recommendations.\n"
                    )

                grounded_prompt = (
                    f"{wrapped_corpus}\n"
                    f"{calendar_section}\n"
                    f"{weather_section}\n"
                    f"{chemical_section}\n"
                    f"{dosage_section}\n"
                    f"{diagnostic_section}\n"
                    f"Farmer Question: {question}\n"
                    f"Crop context: {effective_crop or 'None specified'}\n"
                    f"Location context: {effective_location or location or 'None specified'}\n\n"
                    "Provide an authoritative agricultural advisory answering the query. "
                    "For every recommendation or numeric rate, cite the exact source passage using [1], [2] (or [chunk_id])."
                )

                try:
                    import inspect
                    sig = inspect.signature(self.llm.complete)
                    call_kwargs = {
                        "system_prompt": DEFAULT_SYSTEM_PROMPT,
                        "user_prompt": grounded_prompt,
                        "context_chunks": retrieved_chunks,
                    }
                    if "conversation_history" in sig.parameters or any(
                        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                    ):
                        call_kwargs["conversation_history"] = conversation_history

                    resp = await self.llm.complete(**call_kwargs)
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
                is_insufficient_notice = any(
                    phrase in final_answer.lower()
                    for phrase in [
                        "do not contain sufficient evidence",
                        "does not contain sufficient evidence",
                        "not contain enough evidence",
                        "insufficient evidence",
                        "no specific cited recommendations",
                    ]
                )

                if is_insufficient_notice:
                    uncertainty = "high"
                elif val.valid_count > 0 and (top_score or 0.0) >= 0.65:
                    uncertainty = "none"
                elif (val.valid_count > 0 and (top_score or 0.0) >= 0.48) or (calendar_report and val.valid_count > 0):
                    uncertainty = "low"
                elif calendar_report and not val.valid_count:
                    # Grounded in official crop calendar tool
                    uncertainty = "low"
                else:
                    uncertainty = "high"
                    if "krishi bhavan" not in final_answer.lower() and "kvk" not in final_answer.lower():
                        final_answer += (
                            "\n\nNote: The verified knowledge base does not contain specific cited recommendations "
                            "for this query. Please consult your local Krishi Bhavan or KVK officer."
                        )

                # Evaluate Claim-Level Faithfulness Scorer (Algorithmic Grounding)
                try:
                    faith_res = evaluate_faithfulness(final_answer, retrieved_chunks)
                    faithfulness_payload = faith_res.to_dict()
                    logger.info(
                        f"Faithfulness score: {faith_res.faithfulness_percent}% "
                        f"({faith_res.grounded_claims}/{faith_res.total_claims} claims grounded)"
                    )
                except Exception as e:
                    logger.warning(f"Faithfulness evaluation failed: {e}")

                # Ensure chemical safety warning is explicitly present if a violation was intercepted
                if chemical_safety_report and not chemical_safety_report.is_safe:
                    if chemical_safety_report.chemical.lower() not in final_answer.lower() or "alternative" not in final_answer.lower():
                        final_answer += (
                            f"\n\n⚠️ **REGULATORY FOOD SAFETY & PHI INTERCEPTION:**\n"
                            f"{chemical_safety_report.explanation}\n"
                            f"**Recommended Safe Alternative:** {chemical_safety_report.alternative_recommended}"
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

        weather_payload = weather_report.model_dump() if weather_report else None
        chem_payload = chemical_safety_report.model_dump() if chemical_safety_report else None
        dosage_payload = dosage_report.model_dump() if dosage_report else None
        visual_payload = visual_diagnostic_report.model_dump() if visual_diagnostic_report else None
        return OrchestratorResult(
            state=current_state,
            answer=final_answer,
            citations=citations,
            uncertainty=uncertainty,
            retrieval_score=top_score,
            evidence_count=len(retrieved_chunks),
            iterations_used=iteration,
            audit_trace=audit_records,
            weather=weather_payload,
            faithfulness=faithfulness_payload,
            chemical_safety=chem_payload,
            dosage_calculation=dosage_payload,
            visual_diagnostic=visual_payload,
        )
