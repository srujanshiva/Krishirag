"""Unit tests for chemical safety guardrail and Pre-Harvest Interval (PHI) verification."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.agent.tools import (
    ChemicalSafetyInput,
    _handle_check_chemical_safety,
)
from backend.app.llm.gateway import LLMGateway, LLMResponse


def test_chemical_safety_detects_phi_withholding_violation():
    """Verify that attempting to spray Tricyclazole 8 days before harvest triggers PHI violation."""
    inp = ChemicalSafetyInput(chemical="Tricyclazole", crop="Rice", days_to_harvest=8)
    report = _handle_check_chemical_safety(inp)

    assert not report.is_safe
    assert report.safety_directive == "APPLICATION_BLOCKED_WITHHOLDING_VIOLATION"
    assert report.warning_level == "critical"
    assert report.phi_days == 30
    assert "Pseudomonas fluorescens" in report.alternative_recommended


def test_chemical_safety_detects_banned_substance():
    """Verify that Monocrotophos and Phorate trigger strict legal prohibition in Kerala."""
    inp = ChemicalSafetyInput(chemical="Monocrotophos", crop="Rice")
    report = _handle_check_chemical_safety(inp)

    assert not report.is_safe
    assert report.safety_directive == "BANNED_SUBSTANCE_VIOLATION"
    assert report.warning_level == "banned"
    assert report.regulatory_status == "BANNED_IN_KERALA"
    assert "Insecticides Act" in report.explanation


def test_chemical_safety_approves_safe_timing():
    """Verify that applying Mancozeb well outside the withholding window is approved."""
    inp = ChemicalSafetyInput(chemical="Mancozeb", crop="Pepper", days_to_harvest=45)
    report = _handle_check_chemical_safety(inp)

    assert report.is_safe
    assert report.safety_directive == "SAFE_TO_APPLY"
    assert report.warning_level == "safe"


def test_chemical_safety_approves_organic_biocontrol():
    """Verify that bio-agents like Pseudomonas have zero withholding days and zero residue."""
    inp = ChemicalSafetyInput(chemical="Pseudomonas fluorescens", crop="Rice", days_to_harvest=2)
    report = _handle_check_chemical_safety(inp)

    assert report.is_safe
    assert report.phi_days == 0
    assert report.max_residue_limit_ppm == 0.0


@pytest.mark.asyncio
async def test_orchestrator_executes_chemical_safety_guardrail():
    """Verify orchestrator invokes chemical safety tool and captures report for spray query."""
    mock_gateway = MagicMock(spec=LLMGateway)
    mock_gateway.complete = AsyncMock(
        return_value=LLMResponse(
            content="Do not spray Tricyclazole [1]. Use organic alternatives.",
            model_used="test-llm",
            provider="mock",
        )
    )
    orchestrator = AgentOrchestrator(llm=mock_gateway)

    result = await orchestrator.run(
        question="Can I spray Tricyclazole on my paddy crop 7 days before harvest?",
        crop="Rice",
    )

    # Verify tool execution in audit trace
    chem_audits = [a for a in result.audit_trace if a["tool"] == "check_chemical_safety"]
    assert len(chem_audits) == 1
    assert chem_audits[0]["outcome"] == "success"

    # Verify chemical safety payload was returned
    assert result.chemical_safety is not None
    assert result.chemical_safety["chemical"] == "Tricyclazole"
    assert result.chemical_safety["is_safe"] is False
    assert result.chemical_safety["phi_days"] == 30
