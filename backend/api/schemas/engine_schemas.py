from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum

class Classification(str, Enum):
    BLOCKED = "blocked"
    AVOID = "avoid"
    LIMIT = "limit"
    RECOMMENDED = "recommended"
    NEUTRAL = "neutral"

class DietaryPattern(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    EGGETARIAN = "eggetarian"
    NON_VEGETARIAN = "non_vegetarian"
    JAIN = "jain"

class ConditionalRuleSchema(BaseModel):
    parameter: str
    operator: str
    value: float
    restrict_nutrients: List[str]

class ConditionSchema(BaseModel):
    name: str
    restrict_nutrients: List[str] = []
    encourage_nutrients: List[str] = []
    conditional_restrictions: List[ConditionalRuleSchema] = []
    lab_values: Dict[str, float] = {}

class FoodInteractionSchema(BaseModel):
    interacting_food_category: str
    description: str
    severity: str

class DepletionSchema(BaseModel):
    nutrient: str
    severity: str = "moderate"
    recommendation: str = ""

class MedicationSchema(BaseModel):
    name: str
    dose: Optional[str] = None
    depletes_nutrients: List[DepletionSchema] = []
    food_interactions: List[FoodInteractionSchema] = []
    timing: Optional[str] = None

class FoodSchema(BaseModel):
    name: str
    category: str
    nutrients: Dict[str, float] = {}
    allergens: List[str] = []
    dietary_tags: List[str] = []
    glycemic_index: Optional[int] = None
    purine_level: Optional[str] = None
    vitamin_k_mcg: Optional[float] = None
    nutrient_source: Optional[str] = None

class UserProfileSchema(BaseModel):
    age: int
    sex: str
    weight_kg: float
    height_cm: float
    activity_level: str
    dietary_pattern: DietaryPattern
    allergies: List[str] = []
    conditions: List[ConditionSchema] = []
    medications: List[MedicationSchema] = []
    food_dislikes: List[str] = []

class FiredRuleSchema(BaseModel):
    rule_type: str
    reason: str

class EvaluationResultSchema(BaseModel):
    food_name: str
    classification: Classification
    reasons: List[str]
    fired_rules: List[FiredRuleSchema]
