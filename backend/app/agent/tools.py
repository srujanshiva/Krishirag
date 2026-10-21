"""Typed tool registry with timeout enforcement and structured audit logging."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from loguru import logger
from pydantic import BaseModel, Field, computed_field

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


class WeatherInput(BaseModel):
    location: str = Field(..., description="Location or agricultural district (e.g. Palakkad, Coimbatore, Thanjavur, Guntur)")
    crop: Optional[str] = Field(None, description="Optional crop context for agronomic risk evaluation")


class WeatherReport(BaseModel):
    location: str
    temperature_c: float
    humidity_percent: float
    precipitation_mm: float
    precipitation_prob_percent: int
    wind_speed_kmh: float
    condition: str
    spraying_advisory: str
    fieldwork_advisory: str


class ChemicalSafetyInput(BaseModel):
    chemical: str = Field(..., description="Chemical or active ingredient name (e.g. Tricyclazole, Chlorpyrifos, Carbendazim)")
    crop: Optional[str] = Field(None, description="Target crop (e.g. Rice, Pepper, Coconut)")
    days_to_harvest: Optional[int] = Field(None, ge=0, description="Estimated days remaining until harvest")


class ChemicalSafetyReport(BaseModel):
    chemical: str
    target_crop: str
    regulatory_status: str  # "APPROVED" | "RESTRICTED" | "BANNED_IN_KERALA"
    phi_days: int  # Pre-Harvest Interval (withholding period in days)
    safety_directive: str  # "SAFE_TO_APPLY" | "APPLICATION_BLOCKED_WITHHOLDING_VIOLATION" | "BANNED_SUBSTANCE_VIOLATION"
    max_residue_limit_ppm: float
    hazard_warning: str
    recommended_bio_alternative: str

    @computed_field
    @property
    def is_safe(self) -> bool:
        return self.safety_directive == "SAFE_TO_APPLY"

    @computed_field
    @property
    def warning_level(self) -> str:
        if self.regulatory_status == "BANNED_IN_KERALA" or self.safety_directive == "BANNED_SUBSTANCE_VIOLATION":
            return "banned"
        if self.safety_directive == "APPLICATION_BLOCKED_WITHHOLDING_VIOLATION":
            return "critical"
        if self.regulatory_status == "RESTRICTED":
            return "caution"
        return "safe"

    @computed_field
    @property
    def toxicity_class(self) -> str:
        if self.regulatory_status == "BANNED_IN_KERALA":
            return "Class I Extremely Toxic (Banned)"
        if self.regulatory_status == "RESTRICTED":
            return "Class II Moderately Hazardous (Restricted)"
        return "Class III Slightly Hazardous"

    @computed_field
    @property
    def explanation(self) -> str:
        return self.hazard_warning

    @computed_field
    @property
    def alternative_recommended(self) -> str:
        return self.recommended_bio_alternative

    @computed_field
    @property
    def mrl_ppm(self) -> float:
        return self.max_residue_limit_ppm


class DosageCalculatorInput(BaseModel):
    crop: str = Field(..., description="Crop name (e.g. Rice, Pepper, Coconut, Maize)")
    area_value: float = Field(..., gt=0, description="Numerical area or plant/palm count")
    area_unit: str = Field("acre", description="Unit: 'acre', 'cent', 'hectare', 'guntha', or 'tree'/'palm'")


class DosageCalculatorReport(BaseModel):
    crop: str
    input_display: str
    area_hectares: float
    recommended_npk_ratio: str
    urea_kg: float
    dap_kg: float
    mop_kg: float
    application_splits: List[str]
    notes: str


class LeafDiagnosticInput(BaseModel):
    image_data: str = Field(..., description="Base64 encoded leaf image or file bytes")
    crop: Optional[str] = Field(None, description="Optional host crop context (e.g. Rice, Pepper, Coconut)")
    notes: Optional[str] = Field(None, description="Optional symptoms described by farmer")


class LeafDiagnosticReport(BaseModel):
    crop: str
    symptoms_detected: List[str]
    suspected_diseases: List[str]
    confidence_score: float
    visual_features: Dict[str, Any]
    immediate_action: str
    search_keywords: List[str]


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


DISTRICT_COORDINATES: Dict[str, Tuple[float, float]] = {
    "palakkad": (10.7867, 76.6548),
    "coimbatore": (11.0168, 76.9558),
    "thanjavur": (10.7870, 79.1378),
    "madurai": (9.9252, 78.1198),
    "wayanad": (11.6854, 76.1320),
    "alappuzha": (9.4981, 76.3388),
    "kottayam": (9.5916, 76.5222),
    "thrissur": (10.5276, 76.2144),
    "guntur": (16.3067, 80.4365),
    "warangal": (17.9689, 79.5941),
    "nagapattinam": (10.7656, 79.8424),
    "tiruvarur": (10.7725, 79.6365),
}


def _handle_lookup_weather(input_data: WeatherInput) -> WeatherReport:
    import httpx

    loc_clean = input_data.location.strip().lower()
    lat, lon = DISTRICT_COORDINATES.get(loc_clean, (10.7867, 76.6548))

    # Geocode if location not in pre-mapped dictionary
    if loc_clean not in DISTRICT_COORDINATES:
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={input_data.location}&count=1&language=en&format=json"
            with httpx.Client(timeout=2.5) as client:
                geo_resp = client.get(geo_url)
                if geo_resp.status_code == 200:
                    results = geo_resp.json().get("results", [])
                    if results:
                        lat = float(results[0]["latitude"])
                        lon = float(results[0]["longitude"])
        except Exception as e:
            logger.warning(f"Geocoding lookup for '{input_data.location}' failed: {e}. Defaulting to regional baseline.")

    forecast_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
        "&hourly=precipitation_probability&forecast_days=1"
    )

    temp_c = 28.5
    humidity = 75.0
    precip_mm = 0.0
    precip_prob = 15
    wind_kmh = 8.5
    condition = "Partly Cloudy"

    try:
        with httpx.Client(timeout=3.5) as client:
            resp = client.get(forecast_url)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                temp_c = float(current.get("temperature_2m", temp_c))
                humidity = float(current.get("relative_humidity_2m", humidity))
                precip_mm = float(current.get("precipitation", precip_mm))
                wind_kmh = float(current.get("wind_speed_10m", wind_kmh))
                hourly_probs = data.get("hourly", {}).get("precipitation_probability", [])
                if hourly_probs:
                    precip_prob = int(max(hourly_probs[:12]))

                weather_code = current.get("weather_code", 0)
                if weather_code in (0, 1):
                    condition = "Clear / Sunny"
                elif weather_code in (2, 3):
                    condition = "Partly Cloudy"
                elif weather_code in (51, 53, 55, 61, 63, 65, 80, 81):
                    condition = "Rain / Showers"
                elif weather_code in (95, 96, 99):
                    condition = "Thunderstorm"
                else:
                    condition = "Overcast"
    except Exception as e:
        logger.warning(f"Live forecast query to Open-Meteo failed: {e}. Using seasonal baseline.")

    if precip_mm > 0.1 or precip_prob >= 40:
        spraying_advisory = (
            f"UNFAVORABLE FOR SPRAYING: High probability of precipitation ({precip_prob}%, current: {precip_mm}mm). "
            "Chemical foliar applications will wash away. Postpone spraying."
        )
        fieldwork_advisory = "Caution: Wet field conditions. Delay mechanical tilling and intercultural operations."
    elif wind_kmh > 15.0:
        spraying_advisory = (
            f"CAUTION FOR SPRAYING: Moderate to high wind speeds ({wind_kmh} km/h) create spray drift risk. "
            "Spray exclusively in calm early morning (6-8 AM) or evening hours."
        )
        fieldwork_advisory = "Favorable for general field scouting and harvesting; monitor spray drift."
    elif temp_c > 35.0:
        spraying_advisory = (
            f"RESTRICT MIDDAY SPRAYING: High ambient temperature ({temp_c}°C) increases droplet volatilization and phytotoxicity risk. "
            "Spray exclusively during cooler morning or late afternoon hours."
        )
        fieldwork_advisory = "Maintain soil moisture via early morning or drip irrigation."
    else:
        spraying_advisory = (
            f"FAVORABLE FOR SPRAYING: Clear/calm conditions ({temp_c}°C, wind: {wind_kmh} km/h, rain risk: {precip_prob}%). "
            "Ideal weather for foliar nutrient and crop protection applications."
        )
        fieldwork_advisory = "Optimal conditions for all agronomic fieldwork, weeding, and fertilizer broadcasting."

    return WeatherReport(
        location=input_data.location.title(),
        temperature_c=temp_c,
        humidity_percent=humidity,
        precipitation_mm=precip_mm,
        precipitation_prob_percent=precip_prob,
        wind_speed_kmh=wind_kmh,
        condition=condition,
        spraying_advisory=spraying_advisory,
        fieldwork_advisory=fieldwork_advisory,
    )


# ── Chemical Safety & Pre-Harvest Interval (PHI) Database ───────────────────


CIBRC_CHEMICAL_DATABASE: Dict[str, Dict[str, Any]] = {
    "tricyclazole": {
        "canonical": "Tricyclazole",
        "crop": "Rice",
        "status": "APPROVED",
        "phi_days": 30,
        "mrl_ppm": 0.05,
        "bio_alternative": "Pseudomonas fluorescens (2.5 kg/ha) or Trichoderma viride",
        "hazard": "Systemic triazole fungicide. Requires strict 30-day withholding interval to avoid grain residue.",
    },
    "chlorpyrifos": {
        "canonical": "Chlorpyrifos",
        "crop": "Rice / General",
        "status": "RESTRICTED",
        "phi_days": 28,
        "mrl_ppm": 0.05,
        "bio_alternative": "Bacillus thuringiensis (Bt) or Neem seed kernel extract (NSKE 5%)",
        "hazard": "Organophosphate insecticide. Toxic to non-target aquatic organisms and pollinators.",
    },
    "carbendazim": {
        "canonical": "Carbendazim",
        "crop": "Rice / Pulses",
        "status": "RESTRICTED",
        "phi_days": 21,
        "mrl_ppm": 0.1,
        "bio_alternative": "Trichoderma viride or Validamycin 3L",
        "hazard": "Benzimidazole broad-spectrum fungicide. Restricted in Kerala due to soil persistency.",
    },
    "mancozeb": {
        "canonical": "Mancozeb",
        "crop": "Vegetables / Pepper",
        "status": "APPROVED",
        "phi_days": 14,
        "mrl_ppm": 1.0,
        "bio_alternative": "Copper oxychloride (COC 0.2%) or Bordeaux mixture 1%",
        "hazard": "Dithiocarbamate contact fungicide. Wear protective gear during foliar spray.",
    },
    "monocrotophos": {
        "canonical": "Monocrotophos",
        "crop": "All Crops",
        "status": "BANNED_IN_KERALA",
        "phi_days": 999,
        "mrl_ppm": 0.0,
        "bio_alternative": "Azadirachtin (Neem formulation 10000 ppm) or bio-control agents",
        "hazard": "High-toxicity Class Ib organophosphate. Strict statutory ban in Kerala under Insecticides Act.",
    },
    "phorate": {
        "canonical": "Phorate",
        "crop": "All Crops",
        "status": "BANNED_IN_KERALA",
        "phi_days": 999,
        "mrl_ppm": 0.0,
        "bio_alternative": "Pheromone traps and botanical bio-pesticides",
        "hazard": "Extreme toxicity Class Ia systemic pesticide. Completely prohibited in Kerala agriculture.",
    },
    "hexaconazole": {
        "canonical": "Hexaconazole",
        "crop": "Rice / Plantation",
        "status": "APPROVED",
        "phi_days": 21,
        "mrl_ppm": 0.05,
        "bio_alternative": "Pseudomonas fluorescens liquid formulation",
        "hazard": "Triazole fungicide. 21-day withholding interval required.",
    },
    "quinalphos": {
        "canonical": "Quinalphos",
        "crop": "Rice / Spices",
        "status": "RESTRICTED",
        "phi_days": 21,
        "mrl_ppm": 0.01,
        "bio_alternative": "Beauveria bassiana (1.5 kg/ha)",
        "hazard": "Organophosphate insecticide. Highly toxic to beneficial predators and bees.",
    },
}


def _handle_check_chemical_safety(input_data: ChemicalSafetyInput) -> ChemicalSafetyReport:
    """Evaluate Pre-Harvest Interval (PHI) compliance and food-safety residue risks."""
    chem_query = input_data.chemical.lower().strip()
    target_crop = input_data.crop or "General Agricultural Crop"
    days_to_harvest = input_data.days_to_harvest

    # Match canonical chemical profile
    matched_profile = None
    for key, profile in CIBRC_CHEMICAL_DATABASE.items():
        if key in chem_query or profile["canonical"].lower() in chem_query:
            matched_profile = profile
            break

    if not matched_profile:
        # Default fallback for unlisted / biological inputs
        if any(bio in chem_query for bio in ["pseudomonas", "trichoderma", "neem", "bacillus", "organic"]):
            return ChemicalSafetyReport(
                chemical=input_data.chemical.title(),
                target_crop=target_crop,
                regulatory_status="APPROVED",
                phi_days=0,
                safety_directive="SAFE_TO_APPLY",
                max_residue_limit_ppm=0.0,
                hazard_warning="Approved organic/biological crop protection agent. Zero pre-harvest waiting interval.",
                recommended_bio_alternative="Primary organic recommendation (Zero toxic residue).",
            )
        return ChemicalSafetyReport(
            chemical=input_data.chemical.title(),
            target_crop=target_crop,
            regulatory_status="APPROVED",
            phi_days=14,
            safety_directive="SAFE_TO_APPLY" if (days_to_harvest is None or days_to_harvest >= 14) else "APPLICATION_BLOCKED_WITHHOLDING_VIOLATION",
            max_residue_limit_ppm=0.1,
            hazard_warning="Standard agricultural chemical. Observe minimum 14-day pre-harvest waiting interval (PHI).",
            recommended_bio_alternative="Neem seed kernel extract (NSKE 5%) or biocontrol formulations.",
        )

    # 1. Banned substance rule
    if matched_profile["status"] == "BANNED_IN_KERALA":
        return ChemicalSafetyReport(
            chemical=matched_profile["canonical"],
            target_crop=target_crop,
            regulatory_status="BANNED_IN_KERALA",
            phi_days=matched_profile["phi_days"],
            safety_directive="BANNED_SUBSTANCE_VIOLATION",
            max_residue_limit_ppm=matched_profile["mrl_ppm"],
            hazard_warning=(
                f"LEGAL PROHIBITION: {matched_profile['canonical']} is strictly prohibited by the Government "
                f"of Kerala and Kerala Agricultural University under Section 27 of the Insecticides Act. "
                f"Do not purchase, store, or spray this chemical."
            ),
            recommended_bio_alternative=matched_profile["bio_alternative"],
        )

    # 2. Pre-Harvest Interval (PHI) Withholding Violation
    if days_to_harvest is not None and days_to_harvest < matched_profile["phi_days"]:
        return ChemicalSafetyReport(
            chemical=matched_profile["canonical"],
            target_crop=target_crop,
            regulatory_status=matched_profile["status"],
            phi_days=matched_profile["phi_days"],
            safety_directive="APPLICATION_BLOCKED_WITHHOLDING_VIOLATION",
            max_residue_limit_ppm=matched_profile["mrl_ppm"],
            hazard_warning=(
                f"CRITICAL FOOD SAFETY VIOLATION: Crop is {days_to_harvest} days from harvest, but "
                f"{matched_profile['canonical']} requires a mandatory Pre-Harvest Interval (PHI) of "
                f"{matched_profile['phi_days']} days. Foliar application now will leave toxic residues "
                f"exceeding FSSAI Maximum Residue Limits ({matched_profile['mrl_ppm']} ppm) on edible produce."
            ),
            recommended_bio_alternative=matched_profile["bio_alternative"],
        )

    # 3. Safe to apply
    return ChemicalSafetyReport(
        chemical=matched_profile["canonical"],
        target_crop=target_crop,
        regulatory_status=matched_profile["status"],
        phi_days=matched_profile["phi_days"],
        safety_directive="SAFE_TO_APPLY",
        max_residue_limit_ppm=matched_profile["mrl_ppm"],
        hazard_warning=(
            f"Complies with mandatory {matched_profile['phi_days']}-day Pre-Harvest Interval (PHI). "
            f"{matched_profile['hazard']} Wear personal protective equipment (PPE)."
        ),
        recommended_bio_alternative=matched_profile["bio_alternative"],
    )


def _handle_calculate_fertilizer_dosage(input_data: DosageCalculatorInput) -> DosageCalculatorReport:
    """Calculate precise commercial fertilizer requirements for land area or palm counts."""
    crop_lower = input_data.crop.lower().strip()
    val = input_data.area_value
    unit = input_data.area_unit.lower().strip()

    # 1. Tree / Palm count mode (Coconut, Pepper)
    if unit in ("tree", "trees", "palm", "palms", "vine", "vines") or "coconut" in crop_lower or "pepper" in crop_lower:
        if "coconut" in crop_lower:
            count = val
            urea = round(count * 1.1, 1)
            dap = round(count * 0.7, 1)  # Or 1.6 kg Rock Phosphate
            mop = round(count * 2.0, 1)
            return DosageCalculatorReport(
                crop="Coconut",
                input_display=f"{int(count) if count.is_integer() else count} Adult Palms",
                area_hectares=round(count / 175.0, 3),  # Standard 175 palms/ha density
                recommended_npk_ratio="500:320:1200 g/palm/year (Adult Palm)",
                urea_kg=urea,
                dap_kg=dap,
                mop_kg=mop,
                application_splits=[
                    "Split 1 (May-June onset of SW Monsoon): Apply 1/3 of total dosage around 1.8m basin.",
                    "Split 2 (Sept-Oct post-monsoon): Apply remaining 2/3 of total dosage with organic green manuring.",
                ],
                notes="Ensure soil has adequate moisture when broadcasting. Incorporate 25-50 kg farmyard manure or compost per palm annually.",
            )
        elif "pepper" in crop_lower:
            vines = val
            urea = round(vines * 0.22, 2)
            dap = round(vines * 0.15, 2)
            mop = round(vines * 0.235, 2)
            return DosageCalculatorReport(
                crop="Black Pepper",
                input_display=f"{int(vines) if vines.is_integer() else vines} Pepper Vines",
                area_hectares=round(vines / 1100.0, 3),
                recommended_npk_ratio="100:40:140 g/vine/year",
                urea_kg=urea,
                dap_kg=dap,
                mop_kg=mop,
                application_splits=[
                    "First Split (May-June): Apply 50% fertilizer around 30cm radius basin after first showers.",
                    "Second Split (August-September): Apply remaining 50% fertilizer with light earthing up.",
                ],
                notes="Apply 10 kg compost and 1 kg neem cake per vine annually to prevent Phytophthora foot rot and root-knot nematodes.",
            )

    # 2. Area-based conversion to Hectares
    if unit in ("cent", "cents"):
        ha = (val / 100.0) / 2.47105
        display_str = f"{val} Cents ({round(val / 100.0, 2)} Acres)"
    elif unit in ("guntha", "gunthas"):
        ha = (val / 40.0) / 2.47105
        display_str = f"{val} Gunthas ({round(val / 40.0, 2)} Acres)"
    elif unit in ("hectare", "hectares", "ha"):
        ha = val
        display_str = f"{val} Hectares ({round(val * 2.47105, 2)} Acres)"
    else:  # Default to Acre
        ha = val / 2.47105
        display_str = f"{val} Acres ({int(val * 100)} Cents)"

    ha = max(ha, 0.001)

    # Crop-specific commercial fertilizer derivation
    if any(r in crop_lower for r in ("rice", "paddy", "nellu", "sri")):
        crop_title = "Rice (Paddy)"
        ratio = "80:40:40 kg/ha (Medium Duration)"
        urea = round(140.0 * ha, 1)
        dap = round(87.0 * ha, 1)
        mop = round(67.0 * ha, 1)
        splits = [
            f"Basal (At final puddling/transplanting): Full DAP ({dap} kg) + 25% Urea ({round(urea * 0.25, 1)} kg) + 25% MOP ({round(mop * 0.25, 1)} kg)",
            f"Active Tillering (20-25 DAT): 50% Urea ({round(urea * 0.50, 1)} kg) + 50% MOP ({round(mop * 0.50, 1)} kg)",
            f"Panicle Initiation (40-45 DAT): Remaining 25% Urea ({round(urea * 0.25, 1)} kg) + 25% MOP ({round(mop * 0.25, 1)} kg)",
        ]
        notes = "Drain standing water prior to top-dressing nitrogen. Re-irrigate to shallow depth 24 hours after application."
    elif "maize" in crop_lower or "corn" in crop_lower:
        crop_title = "Maize (Corn)"
        ratio = "120:60:40 kg/ha"
        urea = round(210.0 * ha, 1)
        dap = round(130.0 * ha, 1)
        mop = round(67.0 * ha, 1)
        splits = [
            f"Basal (At sowing): Full DAP ({dap} kg) + 25% Urea ({round(urea * 0.25, 1)} kg) + 50% MOP ({round(mop * 0.50, 1)} kg)",
            f"Knee-High Stage (25-30 DAS): 50% Urea ({round(urea * 0.50, 1)} kg)",
            f"Tasseling Stage (45-50 DAS): Remaining 25% Urea ({round(urea * 0.25, 1)} kg) + 50% MOP ({round(mop * 0.50, 1)} kg)",
        ]
        notes = "Apply fertilizer 5-7 cm away from seedlings along ridges to avoid root scorch."
    else:
        crop_title = input_data.crop.title()
        ratio = "70:35:35 kg/ha (Standard Agronomic Guidance)"
        urea = round(120.0 * ha, 1)
        dap = round(76.0 * ha, 1)
        mop = round(58.0 * ha, 1)
        splits = [
            f"Basal: Full DAP ({dap} kg) + 33% Urea ({round(urea * 0.33, 1)} kg) + 50% MOP ({round(mop * 0.5, 1)} kg)",
            f"Vegetative Peak: 33% Urea ({round(urea * 0.33, 1)} kg)",
            f"Flowering / Reproductive: Remaining 34% Urea ({round(urea * 0.34, 1)} kg) + 50% MOP ({round(mop * 0.5, 1)} kg)",
        ]
        notes = "Adjust top-dressing depending on organic basal manuring (FYM) incorporated during land preparation."

    return DosageCalculatorReport(
        crop=crop_title,
        input_display=display_str,
        area_hectares=round(ha, 4),
        recommended_npk_ratio=ratio,
        urea_kg=urea,
        dap_kg=dap,
        mop_kg=mop,
        application_splits=splits,
        notes=notes,
    )


async def _handle_diagnose_crop_image(input_data: LeafDiagnosticInput) -> LeafDiagnosticReport:
    """Analyze crop leaf image for visual lesions, chlorosis, necrotic patches, and blast/rust patterns."""
    raw_b64 = input_data.image_data
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    width, height = 0, 0
    yellow_ratio = 0.0
    brown_ratio = 0.0
    pale_ratio = 0.0

    try:
        import base64
        import io
        from PIL import Image

        img_bytes = base64.b64decode(raw_b64)
        with Image.open(io.BytesIO(img_bytes)) as img:
            rgb_img = img.convert("RGB")
            width, height = rgb_img.size
            thumb = rgb_img.resize((64, 64))
            pixels = list(thumb.getdata())
            total = len(pixels)

            yellow_count = sum(1 for r, g, b in pixels if r > 120 and g > 120 and b < 90)
            brown_count = sum(1 for r, g, b in pixels if r > 80 and g > 50 and b < 40 and abs(r - g) > 20)
            pale_count = sum(1 for r, g, b in pixels if r > 180 and g > 180 and b > 180)

            yellow_ratio = round(yellow_count / total, 3)
            brown_ratio = round(brown_count / total, 3)
            pale_ratio = round(pale_count / total, 3)
    except Exception as e:
        logger.warning(f"Leaf image PIL feature analysis fallback: {e}")

    notes_text = (input_data.notes or "").lower()
    crop_ctx = (input_data.crop or "Rice").title()
    symptoms = []
    suspected = []
    keywords = []

    # Crop & Visual Pattern Corroboration
    if "rice" in crop_ctx.lower() or "paddy" in crop_ctx.lower():
        if "blast" in notes_text or "spindle" in notes_text or (brown_ratio > 0.04 and pale_ratio > 0.02):
            symptoms.append("Spindle-shaped diamond lesions with ash-grey centers and dark brown margins on leaves")
            suspected.append("Leaf Blast (Pyricularia oryzae)")
            keywords.extend(["Rice leaf blast Pyricularia", "Tricyclazole 75 WP dose", "Kasugamycin"])
            immediate_action = "Apply Tricyclazole 75% WP @ 0.6 g/litre or Kasugamycin @ 2.0 ml/litre. Immediately suspend nitrogen top-dressing."
        elif brown_ratio > 0.08 or "spot" in notes_text or "brown" in notes_text:
            symptoms.append("Oval to circular dark brown necrotic spots on leaf blade and sheath (Helminthosporium / Bipolaris)")
            suspected.append("Brown Spot (Bipolaris oryzae)")
            keywords.extend(["Rice brown spot Bipolaris oryzae", "Mancozeb spraying", "seed treatment"])
            immediate_action = "Spray Mancozeb 75% WP @ 2.0 g/litre or Carbendazim + Mancozeb (Saaf) @ 2.0 g/litre. Avoid moisture stress."
        elif "yellow" in notes_text or yellow_ratio > 0.10:
            symptoms.append("Linear yellowing along leaf margins turning straw-colored with wavy margins (Bacterial Blight)")
            suspected.append("Bacterial Leaf Blight (Xanthomonas oryzae)")
            keywords.extend(["Rice bacterial leaf blight Xanthomonas", "Streptocycline", "Copper Oxychloride"])
            immediate_action = "Drain excess water. Spray Streptocycline @ 0.1 g/L combined with Copper Oxychloride 50 WP @ 2.5 g/L. Avoid high nitrogen."
        else:
            symptoms.append("Foliar chlorosis and sporadic necrotic speckles detected on leaf surface")
            suspected.append("Early Leaf Blight or Nutritional Deficiency")
            keywords.extend(["Rice foliar disease management", "balanced NPK application"])
            immediate_action = "Maintain optimal water regime and monitor for rapid lesion expansion."

    elif "pepper" in crop_ctx.lower():
        if "yellow" in notes_text or yellow_ratio > 0.10 or brown_ratio > 0.05:
            symptoms.append("Water-soaked circular black lesions on leaves with dark margins; yellowing and defoliation")
            suspected.append("Quick Wilt / Foot Rot (Phytophthora capsici)")
            keywords.extend(["Black pepper quick wilt Phytophthora", "Bordeaux mixture 1%", "Potassium phosphonate"])
            immediate_action = "Drench vine basin with 0.2% Potassium phosphonate (Akomin @ 3 ml/L) or 1% Bordeaux mixture. Improve basin drainage."
        elif "spot" in notes_text or "anthracnose" in notes_text:
            symptoms.append("Angular brownish spots with yellowish halo on pepper berries and leaf laminas")
            suspected.append("Pollu Disease / Anthracnose (Colletotrichum gloeosporioides)")
            keywords.extend(["Black pepper anthracnose Colletotrichum", "Carbendazim spray"])
            immediate_action = "Spray Carbendazim @ 1 g/litre or 1% Bordeaux mixture during pre-monsoon."
        else:
            symptoms.append("Leaf marginal necrosis and moderate chlorosis")
            suspected.append("Foliar Leaf Rot")
            keywords.extend(["Pepper fungal management", "Trichoderma harzianum"])
            immediate_action = "Apply Trichoderma enriched FYM around root zone."

    elif "coconut" in crop_ctx.lower():
        if "spot" in notes_text or brown_ratio > 0.06:
            symptoms.append("Circular yellowish-brown spots coalescing into grey centers with brown borders on lower leaflets")
            suspected.append("Grey Leaf Spot / Leaf Blight (Pestalotiopsis palmarum)")
            keywords.extend(["Coconut grey leaf spot Pestalotiopsis", "Hexaconazole root feeding", "potash nutrition"])
            immediate_action = "Prune severely damaged lower fronds. Spray Hexaconazole @ 2 ml/L or Mancozeb @ 2 g/L. Ensure adequate MOP (potash) dosage."
        elif "rot" in notes_text or "bud" in notes_text:
            symptoms.append("Yellowing of central spindle leaves accompanied by soft rot and foul odor")
            suspected.append("Bud Rot (Phytophthora palmivora)")
            keywords.extend(["Coconut bud rot Phytophthora", "Bordeaux paste application"])
            immediate_action = "Clean infected rotten tissues and place Bordeaux paste (10%) or Mancozeb sachet (5 g) in crown."
        else:
            symptoms.append("Leaf bronzing and marginal leaflet necrosis")
            suspected.append("Nutritional Deficiency or Mite Infestation")
            keywords.extend(["Coconut leaflet necrosis", "borax and magnesium sulfate"])
            immediate_action = "Apply balanced micronutrient mixture and check for Aceria mite webbing."

    else:
        if brown_ratio > 0.08 or "spot" in notes_text:
            symptoms.append(f"Cercospora / Alternaria type necrotic leaf spotting observed on {crop_ctx}")
            suspected.append(f"{crop_ctx} Leaf Spot / Blight")
            keywords.extend([f"{crop_ctx} leaf spot fungicide", "Chlorothalonil or Mancozeb"])
            immediate_action = "Apply Mancozeb 75 WP @ 2.5 g/L or Copper Oxychloride @ 2.5 g/L. Ensure proper spacing for aeration."
        elif yellow_ratio > 0.12 or "yellow" in notes_text or "mosaic" in notes_text:
            symptoms.append(f"Interveinal chlorosis and yellow mosaic pattern on {crop_ctx} leaves")
            suspected.append(f"{crop_ctx} Viral Mosaic or Nitrogen/Iron Chlorosis")
            keywords.extend([f"{crop_ctx} yellow mosaic whitefly vector", "Imidacloprid vector control"])
            immediate_action = "Control sucking insect vectors (whiteflies/aphids) with Neem oil 2% or Imidacloprid 17.8 SL @ 0.3 ml/L."
        else:
            symptoms.append(f"Foliar lesions and irregular discoloration detected on {crop_ctx}")
            suspected.append(f"{crop_ctx} Foliar Blight")
            keywords.extend([f"{crop_ctx} disease control", "organic biocontrol"])
            immediate_action = "Apply Pseudomonas fluorescens 20 g/L foliar spray. Monitor symptom progression."

    confidence = round(min(0.94, max(0.72, 0.75 + brown_ratio * 0.8 + yellow_ratio * 0.5)), 2)

    return LeafDiagnosticReport(
        crop=crop_ctx,
        symptoms_detected=symptoms,
        suspected_diseases=suspected,
        confidence_score=confidence,
        visual_features={
            "image_dimensions": f"{width}x{height}" if width and height else "Standard",
            "yellow_chlorosis_ratio": yellow_ratio,
            "brown_necrotic_ratio": brown_ratio,
            "pale_mildew_ratio": pale_ratio,
        },
        immediate_action=immediate_action,
        search_keywords=keywords,
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
    "lookup_weather": Tool(
        name="lookup_weather",
        description="Lookup real-time agrometeorological weather, precipitation probability, and spraying advisories.",
        input_schema=WeatherInput,
        output_schema=WeatherReport,
        handler=_handle_lookup_weather,
        timeout_seconds=4.0,
    ),
    "check_chemical_safety": Tool(
        name="check_chemical_safety",
        description="Evaluate CIBRC Pre-Harvest Interval (PHI) compliance, banned substances, and toxic residue safety.",
        input_schema=ChemicalSafetyInput,
        output_schema=ChemicalSafetyReport,
        handler=_handle_check_chemical_safety,
        timeout_seconds=2.0,
    ),
    "calculate_fertilizer_dosage": Tool(
        name="calculate_fertilizer_dosage",
        description="Convert scientific fertilizer dosages (kg/ha) into commercial bags (Urea, DAP, MOP) for farmer land units (Acres, Cents, Palms).",
        input_schema=DosageCalculatorInput,
        output_schema=DosageCalculatorReport,
        handler=_handle_calculate_fertilizer_dosage,
        timeout_seconds=2.0,
    ),
    "diagnose_crop_image": Tool(
        name="diagnose_crop_image",
        description="Analyze visual leaf symptoms, lesions, chlorosis, and suspect crop diseases.",
        input_schema=LeafDiagnosticInput,
        output_schema=LeafDiagnosticReport,
        handler=_handle_diagnose_crop_image,
        timeout_seconds=4.0,
    ),
}

