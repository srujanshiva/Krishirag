"""Unit tests for regional Indic script detection and multilingual prompt directives."""

from backend.app.llm.gateway import build_grounded_user_prompt, detect_query_language
from backend.app.rag.retriever import RetrievedChunk


def test_detect_query_language_indic_scripts():
    """Verify detection of Telugu, Hindi, Tamil, and Malayalam scripts."""
    # Telugu
    assert detect_query_language("వరి సాగులో నారుమడి ఎరువుల యాజమాన్యం") == "Telugu (తెలుగు)"

    # Hindi
    assert detect_query_language("धान में ब्लास्ट रोग के नियंत्रण के उपाय क्या हैं?") == "Hindi (हिन्दी)"

    # Tamil
    assert detect_query_language("நெல் பயிரில் இலை சுருட்டு புழு கட்டுப்பாடு") == "Tamil (தமிழ்)"

    # Malayalam
    assert detect_query_language("കുരുമുളകിലെ ദ്രുതവാട്ടം രോഗനിയന്ത്രണം") == "Malayalam (മലയാളം)"

    # English (returns None)
    assert detect_query_language("How to control rice blast?") is None


def test_build_grounded_prompt_injects_language_requirement():
    """Verify prompt injects regional language requirement when Indic query is received."""
    chunk = RetrievedChunk(
        chunk_id="chunk-test-1",
        document_title="TNAU POP",
        publisher="TNAU",
        source_url=None,
        page_number=1,
        section="Intro",
        chunk_text="Rice blast is controlled by Tricyclazole 75 WP at 0.6 g/L.",
        score=0.88,
    )

    telugu_query = "వరిలో అగ్గితెగులు నివారణ మందులు ఏమిటి?"
    prompt = build_grounded_user_prompt(telugu_query, [chunk])

    assert "LANGUAGE REQUIREMENT" in prompt
    assert "Telugu (తెలుగు)" in prompt
    assert "You MUST generate your entire advisory response in the exact same language" in prompt
