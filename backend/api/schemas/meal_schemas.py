from engines.gap_engine import NutrientGapReport as NutrientGapResponse
from engines.timing_engine import MedicationTimingAdvice as MedicationTimingSchema
from pydantic import BaseModel
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from api.schemas.targets import NutrientTargetsSchema

class MealFoodSchema(BaseModel):
    food_name: str
    quantity_g: float
    serving_description: str
    preparation_note: Optional[str] = None
    key_nutrients: dict    # {"calories": 120, "protein_g": 4.2, ...}

class MealSchema(BaseModel):
    meal_type: str         # breakfast/mid_morning/lunch/evening_snack/dinner
    foods: List[MealFoodSchema]
    total_nutrition: dict
    rationale: List[str]   # rule-generated reasons







class DayPlanResponse(BaseModel):
    user_id: UUID
    plan_id: UUID
    generated_at: datetime
    profile_summary: str
    targets: NutrientTargetsSchema
    meals: Dict[str, MealSchema]    # keyed by meal_type
    medication_timing: List[MedicationTimingSchema]
    nutrient_gaps: NutrientGapResponse
    safety_notes: List[str]
    calculation_notes: List[str]
    safety_validated: bool
