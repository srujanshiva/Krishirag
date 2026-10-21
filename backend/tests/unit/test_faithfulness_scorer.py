"""Unit tests for claim-level faithfulness scorer and algorithmic grounding."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.citations.faithfulness import (
    FaithfulnessReport,
    _split_into_claims,
    evaluate_faithfulness,
)
from backend.app.llm.gateway import LLMGateway, LLMResponse
from backend.app.rag.retriever import RetrievedChunk


def test_split_into_claims_filters_boilerplate():
    """Verify claim segmentation extracts factual statements while omitting greeting filler."""
    text = (
        "Based on verified agricultural guidelines, System of Rice Intensification (SRI) "
        "requires a seed rate of 5 to 7 kg per hectare. Transplanting is performed with "
        "single 14-day-old seedlings per hill. Please consult your local extension office."
    )
    claims = _split_into_claims(text)
    assert len(claims) >= 2
    # Ensure boilerplate was omitted
    assert not any("please consult" in c.lower() for c in claims)


def test_faithfulness_scorer_perfect_grounding():
    """Verify that claims fully supported by reference chunk achieve 100% faithfulness."""
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        document_title="Package of Practices for Crops: Rice",
        publisher="Kerala Agricultural University",
        source_url=None,
        page_number=18,
        section="SRI Cultivation",
        chunk_text="For System of Rice Intensification (SRI), the seed rate is 5 to 7 kg per hectare. Transplant young seedlings at 14 days.",
        score=0.92,
    )

    answer = "SRI cultivation requires a seed rate of 5 to 7 kg per hectare [1]. Seedlings are transplanted at 14 days old [1]."
    report = evaluate_faithfulness(answer, [chunk])

    assert report.total_claims >= 2
    assert report.grounded_claims == report.total_claims
    assert report.faithfulness_percent == 100.0
    assert report.unverified_claims == 0


def test_faithfulness_scorer_flags_hallucinated_dosages():
    """Verify that hallucinated dosage claims result in lower faithfulness score."""
    chunk = RetrievedChunk(
        chunk_id="chunk-1",
        document_title="Rice Manual",
        publisher="KAU",
        source_url=None,
        page_number=25,
        section="Fertilizer Management",
        chunk_text="Recommended nitrogen application is 70 kg per hectare in 3 split doses.",
        score=0.88,
    )

    # Contradicting dosage (250 kg instead of 70 kg)
    answer = "Apply 250 kg of nitrogen per hectare in a single dose [1]."
    report = evaluate_faithfulness(answer, [chunk])

    assert report.grounded_claims == 0
    assert report.unverified_claims >= 1
    assert report.faithfulness_percent < 50.0


@pytest.mark.asyncio
async def test_orchestrator_returns_faithfulness_payload():
    """Verify orchestrator runs faithfulness scorer and populates result.faithfulness."""
    mock_gateway = MagicMock(spec=LLMGateway)
    mock_gateway.complete = AsyncMock(
        return_value=LLMResponse(
            content="System of Rice Intensification requires 5 to 7 kg seed per hectare [1].",
            model_used="test-llm",
            provider="mock",
        )
    )
    orchestrator = AgentOrchestrator(llm=mock_gateway)

    result = await orchestrator.run(
        question="What is the seed rate for System of Rice Intensification?",
        crop="Rice",
    )

    assert result.faithfulness is not None
    assert "score" in result.faithfulness
    assert "faithfulness_percent" in result.faithfulness
    assert "grounded_claims" in result.faithfulness
    assert "total_claims" in result.faithfulness
    assert result.faithfulness["faithfulness_percent"] > 0
