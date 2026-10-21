"""Unit tests for the scientific fertilizer dosage and land area conversion tool."""

import pytest
from pydantic import ValidationError

from backend.app.agent.tools import (
    REGISTERED_TOOLS,
    DosageCalculatorInput,
    DosageCalculatorReport,
)


@pytest.mark.asyncio
async def test_fertilizer_dosage_tool_rice_acreage():
    """Verify Rice dosage converts accurately from acres to commercial bags."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    res, audit = await tool.execute(
        DosageCalculatorInput(crop="Rice", area_value=2.5, area_unit="acre")
    )
    assert isinstance(res, DosageCalculatorReport)
    assert audit.outcome == "success"
    assert "Rice" in res.crop
    assert "2.5 Acres" in res.input_display
    assert res.area_hectares > 0.9 and res.area_hectares < 1.1  # 2.5 / 2.47105 ~= 1.0117 ha
    assert res.urea_kg > 130.0  # ~141 kg
    assert res.dap_kg > 80.0   # ~88 kg
    assert res.mop_kg > 60.0   # ~67 kg
    assert len(res.application_splits) == 3
    assert "Basal" in res.application_splits[0]
    assert "Tillering" in res.application_splits[1]


@pytest.mark.asyncio
async def test_fertilizer_dosage_tool_coconut_palms():
    """Verify Coconut per-palm dosage calculates bags for tree count."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    res, audit = await tool.execute(
        DosageCalculatorInput(crop="Coconut", area_value=100, area_unit="palms")
    )
    assert isinstance(res, DosageCalculatorReport)
    assert "Coconut" in res.crop
    assert "100 Adult Palms" in res.input_display
    # Adult palm standard: 1.1 kg Urea, 0.7 kg DAP, 2.0 kg MOP
    assert res.urea_kg == 110.0
    assert res.dap_kg == 70.0
    assert res.mop_kg == 200.0
    assert len(res.application_splits) >= 2


@pytest.mark.asyncio
async def test_fertilizer_dosage_tool_pepper_vines():
    """Verify Black Pepper per-vine dosage calculation."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    res, audit = await tool.execute(
        DosageCalculatorInput(crop="Pepper", area_value=50, area_unit="vines")
    )
    assert isinstance(res, DosageCalculatorReport)
    assert "Pepper" in res.crop
    assert "50 Pepper Vines" in res.input_display
    # 50 vines: Urea = 11.0 kg, DAP = 7.5 kg, MOP = 11.75 kg
    assert res.urea_kg == 11.0
    assert res.dap_kg == 7.5
    assert res.mop_kg == 11.75


@pytest.mark.asyncio
async def test_fertilizer_dosage_tool_cents_and_gunthas():
    """Verify smallholder traditional land units (Cents & Gunthas)."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    # 50 Cents (0.5 Acre)
    res_cents, _ = await tool.execute(
        DosageCalculatorInput(crop="Rice", area_value=50, area_unit="cent")
    )
    assert "Cents" in res_cents.input_display
    assert res_cents.area_hectares < 0.25

    # 20 Gunthas (0.5 Acre)
    res_guntha, _ = await tool.execute(
        DosageCalculatorInput(crop="Maize", area_value=20, area_unit="guntha")
    )
    assert "Gunthas" in res_guntha.input_display
    assert res_guntha.urea_kg > 0



@pytest.mark.asyncio
async def test_fertilizer_dosage_validation_error():
    """Verify input validation rejects zero or negative area."""
    tool = REGISTERED_TOOLS["calculate_fertilizer_dosage"]

    with pytest.raises(ValidationError):
        await tool.execute({"crop": "Rice", "area_value": -5.0, "area_unit": "acre"})
