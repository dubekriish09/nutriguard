from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class DepletionFlagSchema(BaseModel):
    medication_name: str
    nutrient: str
    note: str

class NutrientTargetsSchema(BaseModel):
    # Macros
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    
    # Micros
    sodium_mg: float = 2300.0
    potassium_mg: float = 3500.0
    calcium_mg: float = 1000.0
    iron_mg: float = 19.0
    phosphorus_mg: float = 700.0
    magnesium_mg: float = 320.0
    vitamin_c_mg: float = 65.0
    vitamin_b12_mcg: float = 2.4
    vitamin_d_iu: float = 600.0
    folate_mcg: float = 400.0
    
    # Limits
    sat_fat_g: float = 20.0
    added_sugar_g: float = 25.0
    
    # Flags & Modifiers
    prioritize_low_gi: bool = False
    restrict_purines: bool = False
    restrict_potassium: bool = False
    restrict_phosphorus: bool = False
    restrict_protein: bool = False
    avoid_raw_cruciferous: bool = False
    small_frequent_meals: bool = False
    avoid_late_dinner: bool = False
    
    protein_limit_g: Optional[float] = None
    phosphorus_limit_mg: Optional[float] = None
    potassium_limit_mg: Optional[float] = None
    
    depletion_flags: List[Dict[str, Any]] = Field(default_factory=list)
    calculation_notes: List[str] = Field(default_factory=list)
