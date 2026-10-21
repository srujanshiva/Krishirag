"""Unit tests for the multimodal leaf disease visual diagnostic tool."""

import pytest
from backend.app.agent.tools import (
    REGISTERED_TOOLS,
    LeafDiagnosticInput,
    LeafDiagnosticReport,
)


@pytest.mark.asyncio
async def test_leaf_diagnostic_rice_blast_symptoms():
    """Verify diagnostic identifies Rice leaf blast from spindle symptoms and image."""
    tool = REGISTERED_TOOLS["diagnose_crop_image"]
    # 1x1 green pixel png
    fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res, audit = await tool.execute(
        LeafDiagnosticInput(
            image_data=fake_b64,
            crop="Rice",
            notes="spindle shaped diamond lesions with brown margins and ash center",
        )
    )
    assert isinstance(res, LeafDiagnosticReport)
    assert audit.outcome == "success"
    assert "Rice" in res.crop
    assert any("Blast" in d for d in res.suspected_diseases)
    assert res.confidence_score >= 0.70
    assert "Tricyclazole" in res.immediate_action or "Kasugamycin" in res.immediate_action
    assert any("blast" in kw.lower() for kw in res.search_keywords)


@pytest.mark.asyncio
async def test_leaf_diagnostic_pepper_quick_wilt():
    """Verify diagnostic identifies Pepper quick wilt from yellowing/wilting symptoms."""
    tool = REGISTERED_TOOLS["diagnose_crop_image"]
    fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res, audit = await tool.execute(
        LeafDiagnosticInput(
            image_data=fake_b64,
            crop="Pepper",
            notes="yellowing leaves and sudden wilting of vine",
        )
    )
    assert isinstance(res, LeafDiagnosticReport)
    assert "Pepper" in res.crop
    assert any("Quick Wilt" in d or "Foot Rot" in d for d in res.suspected_diseases)
    assert "Bordeaux" in res.immediate_action or "Potassium phosphonate" in res.immediate_action


@pytest.mark.asyncio
async def test_leaf_diagnostic_coconut_leaf_spot():
    """Verify diagnostic identifies Coconut grey leaf spot from spot symptoms."""
    tool = REGISTERED_TOOLS["diagnose_crop_image"]
    fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res, audit = await tool.execute(
        LeafDiagnosticInput(
            image_data=fake_b64,
            crop="Coconut",
            notes="grey spots with dark brown margins on lower fronds",
        )
    )
    assert isinstance(res, LeafDiagnosticReport)
    assert "Coconut" in res.crop
    assert any("Grey Leaf Spot" in d or "Leaf Blight" in d for d in res.suspected_diseases)
    assert "Hexaconazole" in res.immediate_action or "Mancozeb" in res.immediate_action


@pytest.mark.asyncio
async def test_leaf_diagnostic_handles_data_uri_prefix():
    """Verify diagnostic correctly strips data:image/jpeg;base64, prefixes."""
    tool = REGISTERED_TOOLS["diagnose_crop_image"]
    data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    res, audit = await tool.execute(
        LeafDiagnosticInput(image_data=data_uri, crop="Rice", notes="yellow margins")
    )
    assert audit.outcome == "success"
    assert "Bacterial Leaf Blight" in res.suspected_diseases[0]
