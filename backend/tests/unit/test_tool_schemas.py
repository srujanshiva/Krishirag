"""Unit tests for typed tool registry, schemas, and audit execution."""

import asyncio
import pytest
from pydantic import ValidationError

from backend.app.agent.tools import (
    REGISTERED_TOOLS,
    CoverageInput,
    CoverageReport,
    CropCalendarInput,
    CropCalendarReport,
    RetrieveKnowledgeInput,
    Tool,
)
from backend.app.rag.retriever import RetrievedChunk


def test_tool_registry_contains_only_approved_tools():
    """Verify only safe, bounded tools are exposed; no shell or unconstrained tools."""
    expected_tools = {
        "retrieve_knowledge",
        "check_evidence_coverage",
        "lookup_crop_calendar",
        "lookup_weather",
        "check_chemical_safety",
        "calculate_fertilizer_dosage",
        "diagnose_crop_image",
    }
    assert set(REGISTERED_TOOLS.keys()) == expected_tools

    for name, tool in REGISTERED_TOOLS.items():
        assert isinstance(tool, Tool)
        assert tool.name == name
        assert tool.timeout_seconds > 0.0


@pytest.mark.asyncio
async def test_retrieve_knowledge_tool_execution():
    """Verify retrieve_knowledge tool execution, validation, and audit recording."""
    tool = REGISTERED_TOOLS["retrieve_knowledge"]

    # Input validation: query cannot be empty
    with pytest.raises(ValidationError):
        await tool.execute({"query": "", "top_k": 5})

    # Valid execution
    res, audit = await tool.execute({"query": "rice blast symptoms", "top_k": 2})
    assert isinstance(res, list)
    assert audit.tool_name == "retrieve_knowledge"
    assert audit.outcome == "success"
    assert audit.duration_ms > 0.0


@pytest.mark.asyncio
async def test_check_evidence_coverage_tool():
    """Verify check_evidence_coverage evaluates thresholds correctly."""
    tool = REGISTERED_TOOLS["check_evidence_coverage"]

    # Empty chunks -> insufficient
    res_empty, audit1 = await tool.execute(CoverageInput(chunks=[]))
    assert isinstance(res_empty, CoverageReport)
    assert res_empty.sufficient is False
    assert res_empty.evidence_count == 0

    # High score chunks -> sufficient
    dummy_chunk = RetrievedChunk(
        chunk_id="chunk-test-1",
        document_title="Rice POP",
        publisher="TNAU",
        source_url=None,
        page_number=1,
        section="Intro",
        chunk_text="Rice cultivation guide.",
        score=0.85,
    )
    res_high, audit2 = await tool.execute(CoverageInput(chunks=[dummy_chunk], min_threshold=0.40))
    assert res_high.sufficient is True
    assert res_high.top_score == 0.85
    assert res_high.evidence_count == 1


@pytest.mark.asyncio
async def test_lookup_crop_calendar_tool():
    """Verify crop calendar returns accurate seasonal recommendations."""
    tool = REGISTERED_TOOLS["lookup_crop_calendar"]

    res_rice, audit = await tool.execute(CropCalendarInput(crop="Rice"))
    assert isinstance(res_rice, CropCalendarReport)
    assert "Rice" in res_rice.crop
    assert len(res_rice.critical_stages) >= 3

    res_pepper, _ = await tool.execute(CropCalendarInput(crop="Black Pepper"))
    assert "Pepper" in res_pepper.crop
    assert "Monsoon" in res_pepper.season or "Monsoon" in res_pepper.sowing_window


@pytest.mark.asyncio
async def test_lookup_weather_tool():
    """Verify weather tool executes, returns agronomic spraying advisory, and logs audit trace."""
    tool = REGISTERED_TOOLS["lookup_weather"]

    res_weather, audit = await tool.execute({"location": "Palakkad", "crop": "Rice"})
    assert audit.tool_name == "lookup_weather"
    assert audit.outcome == "success"
    assert audit.duration_ms > 0.0

    assert "Palakkad" in res_weather.location
    assert isinstance(res_weather.temperature_c, float)
    assert isinstance(res_weather.precipitation_prob_percent, int)
    assert "SPRAYING" in res_weather.spraying_advisory
    assert len(res_weather.fieldwork_advisory) > 0


@pytest.mark.asyncio
async def test_calculate_fertilizer_dosage_tool():
    """Verify scientific land area to commercial fertilizer calculation."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    # Rice 2 acres
    res_rice, audit = await tool.execute({"crop": "Rice", "area_value": 2.0, "area_unit": "acre"})
    assert audit.tool_name == "calculate_fertilizer_dosage"
    assert audit.outcome == "success"
    assert "Rice" in res_rice.crop
    assert res_rice.urea_kg > 0
    assert res_rice.dap_kg > 0
    assert res_rice.mop_kg > 0
    assert len(res_rice.application_splits) >= 3

    # Coconut 50 palms
    res_coconut, _ = await tool.execute({"crop": "Coconut", "area_value": 50, "area_unit": "palms"})
    assert "Coconut" in res_coconut.crop
    assert res_coconut.urea_kg == 55.0  # 50 * 1.1 kg
    assert res_coconut.mop_kg == 100.0  # 50 * 2.0 kg


@pytest.mark.asyncio
async def test_diagnose_crop_image_tool():
    """Verify visual leaf symptom analysis and candidate disease identification."""
    tool = REGISTERED_TOOLS["diagnose_crop_image"]

    fake_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    res, audit = await tool.execute({
        "image_data": fake_png,
        "crop": "Rice",
        "notes": "spindle diamond shaped spots with grey center",
    })
    assert audit.tool_name == "diagnose_crop_image"
    assert audit.outcome == "success"
    assert "Rice" in res.crop
    assert any("Blast" in d for d in res.suspected_diseases)
    assert res.confidence_score > 0.6
    assert len(res.immediate_action) > 0

