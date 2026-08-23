from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from uuid import UUID
from datetime import date

from api.schemas.targets import NutrientTargetsSchema
from api.schemas.engine_schemas import FoodSchema

class NutrientSummarySchema(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sodium: float

class MealFoodSchema(BaseModel):
    food: FoodSchema
    quantity_g: float
    serving_description: str
    preparation_note: Optional[str] = None

class AssemblerMealSchema(BaseModel):
    meal_type: str
    foods: List[MealFoodSchema]
    total_nutrition: NutrientSummarySchema
    rationale: List[str]

class MedicationTimingAdviceSchema(BaseModel):
    medication_name: str
    dose: str
    instruction: str
    meal_association: str
    warnings: List[str]

class GapSuggestionSchema(BaseModel):
    nutrient: str
    current_amount: float
    target_amount: float
    gap_percentage: float
    suggested_foods: List[str]
    note: str

class NutrientGapReportSchema(BaseModel):
    met: List[str] = Field(default_factory=list)
    borderline: List[str] = Field(default_factory=list)
    deficient: List[str] = Field(default_factory=list)
    surplus: List[str] = Field(default_factory=list)
    suggestions: List[GapSuggestionSchema] = Field(default_factory=list)
    medication_depletion_notes: List[str] = Field(default_factory=list)

class DayPlanResponse(BaseModel):
    user_id: UUID
    targets: NutrientTargetsSchema
    meals: Dict[str, AssemblerMealSchema]
    medication_timing: List[MedicationTimingAdviceSchema]
    nutrient_gaps: NutrientGapReportSchema
    safety_notes: List[str] = Field(default_factory=list)
    calculation_notes: List[str] = Field(default_factory=list)
    general_tips: List[str] = Field(default_factory=list)
