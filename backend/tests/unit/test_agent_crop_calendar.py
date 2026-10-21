"""Unit tests verifying agent intent routing to lookup_crop_calendar tool and multi-turn context."""

import pytest
from backend.app.agent.orchestrator import AgentOrchestrator, AgentState
from backend.app.llm.gateway import LLMGateway, LLMResponse
from backend.app.rag.retriever import RetrievedChunk


class MockLLM(LLMGateway):
    def __init__(self, answer: str = "Recommended sowing for rice is May-June [1]."):
        self.answer = answer
        self.recorded_history = None
        self.recorded_prompt = None

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[RetrievedChunk],
        conversation_history: list[dict] | None = None,
    ) -> LLMResponse:
        self.recorded_prompt = user_prompt
        self.recorded_history = conversation_history
        return LLMResponse(
            content=self.answer,
            model_used="mock-llm",
            provider="mock",
        )


@pytest.mark.asyncio
async def test_agent_routes_to_crop_calendar_tool_on_calendar_intent():
    """Verify AgentOrchestrator invokes lookup_crop_calendar and records audit trace."""
    mock_llm = MockLLM()
    orchestrator = AgentOrchestrator(llm=mock_llm)

    result = await orchestrator.run(
        question="What is the sowing window and crop calendar for rice?",
        crop="Rice",
    )

    # Verify tool was invoked and audited
    tools_executed = [entry["tool"] for entry in result.audit_trace]
    assert "lookup_crop_calendar" in tools_executed
    assert "retrieve_knowledge" in tools_executed
    assert "check_evidence_coverage" in tools_executed

    # Verify crop calendar data was injected into the prompt
    assert mock_llm.recorded_prompt is not None
    assert "OFFICIAL CROP CALENDAR DATA" in mock_llm.recorded_prompt
    assert "Active Tillering" in mock_llm.recorded_prompt or "Rice" in mock_llm.recorded_prompt


@pytest.mark.asyncio
async def test_agent_infers_crop_from_conversation_history():
    """Verify anaphoric questions resolve crop context from previous turns."""
    mock_llm = MockLLM(answer="For that crop, apply split fertilizers [1].")
    orchestrator = AgentOrchestrator(llm=mock_llm)

    history = [
        {"role": "user", "content": "How do I cultivate black pepper in Kerala?"},
        {"role": "assistant", "content": "Plant rooted cuttings in May-June with monsoon rains [1]."},
    ]

    # User asks follow-up with calendar intent without explicitly naming pepper
    result = await orchestrator.run(
        question="When is the harvesting season and critical growth stages for it?",
        conversation_history=history,
    )

    # Should detect Pepper from conversation history and execute crop calendar tool
    tools_executed = [entry["tool"] for entry in result.audit_trace]
    assert "lookup_crop_calendar" in tools_executed
    assert mock_llm.recorded_prompt is not None
    assert "Pepper" in mock_llm.recorded_prompt
    assert mock_llm.recorded_history == history
