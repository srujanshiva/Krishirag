"""Unit tests for agent agrometeorological weather tool invocation and reasoning."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.agent.orchestrator import AgentOrchestrator
from backend.app.llm.gateway import LLMGateway, LLMResponse
from backend.app.rag.retriever import RetrievedChunk


@pytest.fixture
def mock_llm_gateway():
    gateway = MagicMock(spec=LLMGateway)
    gateway.complete = AsyncMock(
        return_value=LLMResponse(
            content=(
                "Based on the verified Rice manual [1], fungicide application should be delayed. "
                "Because of the current rainfall risk in Palakkad, foliar spraying today is unfavorable."
            ),
            model_used="test-llm",
            provider="mock",
        )
    )
    return gateway


@pytest.mark.asyncio
async def test_agent_routes_to_weather_tool_on_spraying_intent(mock_llm_gateway):
    """Verify orchestrator invokes lookup_weather tool when weather/spraying intent is detected."""
    orchestrator = AgentOrchestrator(llm=mock_llm_gateway)

    result = await orchestrator.run(
        question="Can I spray pesticide on my rice crop today in Palakkad?",
        crop="Rice",
        location="Palakkad",
    )

    # Verify weather tool was executed and recorded in audit trace
    weather_audits = [a for a in result.audit_trace if a["tool"] == "lookup_weather"]
    assert len(weather_audits) == 1
    assert weather_audits[0]["outcome"] == "success"

    # Verify weather payload is present in result
    assert result.weather is not None
    assert "Palakkad" in result.weather["location"]
    assert "temperature_c" in result.weather
    assert "spraying_advisory" in result.weather
    assert "fieldwork_advisory" in result.weather

    # Verify LLM was supplied the agrometeorological prompt
    call_args = mock_llm_gateway.complete.call_args[1]
    user_prompt = call_args["user_prompt"]
    assert "REAL-TIME AGROMETEOROLOGICAL FORECAST" in user_prompt
    assert "Palakkad" in user_prompt


@pytest.mark.asyncio
async def test_agent_infers_location_from_conversation_history(mock_llm_gateway):
    """Verify orchestrator extracts location from previous conversation turns for weather tool."""
    orchestrator = AgentOrchestrator(llm=mock_llm_gateway)

    history = [
        {"role": "user", "content": "I am a paddy farmer from Coimbatore."},
        {"role": "assistant", "content": "Welcome! How can I assist your paddy cultivation?"},
    ]

    result = await orchestrator.run(
        question="What is the weather forecast and is it safe to spray today?",
        conversation_history=history,
    )

    weather_audits = [a for a in result.audit_trace if a["tool"] == "lookup_weather"]
    assert len(weather_audits) == 1
    assert result.weather is not None
    assert "Coimbatore" in result.weather["location"]
