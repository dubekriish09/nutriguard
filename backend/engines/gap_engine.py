from typing import List, Dict
from pydantic import BaseModel, Field
from engines.meal_engine import DailyMealPlan
from api.schemas.targets import NutrientTargetsSchema
from engines.meal_engine import ApprovedFoodPool

class GapSuggestion(BaseModel):
    nutrient: str
    current_amount: float
    target_amount: float
    gap_percentage: float
    suggested_foods: List[str]
    note: str

from api.schemas.engine_schemas import DepletionSchema

class NutrientGapReport(BaseModel):
    met: List[str] = Field(default_factory=list)
    borderline: List[str] = Field(default_factory=list)
    deficient: List[str] = Field(default_factory=list)
    surplus: List[str] = Field(default_factory=list)
    suggestions: List[GapSuggestion] = Field(default_factory=list)
    medication_depletion_notes: List[str] = []
    depletion_flags: List[DepletionSchema] = []

def check_nutrient_gaps(
    day_plan: DailyMealPlan,
    targets: NutrientTargetsSchema,
    pool: ApprovedFoodPool
) -> NutrientGapReport:
    report = NutrientGapReport()
    
    # 1. Sum actual nutrients from the meal plan
    actuals = {
        'calories_kcal': 0.0, 'protein_g': 0.0, 'carbs_g': 0.0, 'fat_g': 0.0,
        'fiber_g': 0.0, 'sodium_mg': 0.0, 'potassium_mg': 0.0, 'calcium_mg': 0.0,
        'iron_mg': 0.0, 'phosphorus_mg': 0.0, 'magnesium_mg': 0.0,
        'vitamin_c_mg': 0.0, 'vitamin_b12_mcg': 0.0, 'vitamin_d_iu': 0.0,
        'folate_mcg': 0.0, 'vitamin_k_mcg': 0.0, 'sat_fat_g': 0.0
    }
    
    for meal in day_plan.meals:
        for opt in meal.options:
            for key in actuals.keys():
                actuals[key] += opt.food.nutrients.get(key, 0) * opt.portion_multiplier

    # Mapping of nutrient keys to human-readable names and their target attribute
    target_map = {
        'calories_kcal': ('Calories', targets.calories_kcal),
        'protein_g': ('Protein', targets.protein_g),
        'carbs_g': ('Carbohydrates', targets.carbs_g),
        'fat_g': ('Fat', targets.fat_g),
        'fiber_g': ('Fiber', targets.fiber_g),
        'iron_mg': ('Iron', targets.iron_mg),
        'calcium_mg': ('Calcium', targets.calcium_mg),
        'vitamin_b12_mcg': ('Vitamin B12', targets.vitamin_b12_mcg),
        'vitamin_c_mg': ('Vitamin C', targets.vitamin_c_mg),
        'potassium_mg': ('Potassium', targets.potassium_mg),
        'magnesium_mg': ('Magnesium', targets.magnesium_mg),
        'folate_mcg': ('Folate', targets.folate_mcg)
    }
    
    # Limits (do not generate gap suggestions for these, only surplus warnings)
    limits = {
        'sodium_mg': ('Sodium', targets.sodium_mg),
        'sat_fat_g': ('Saturated Fat', targets.sat_fat_g)
    }
    if targets.restrict_protein and targets.protein_limit_g:
        limits['protein_g'] = ('Protein Limit', targets.protein_limit_g)
    if targets.restrict_potassium and targets.potassium_limit_mg:
        limits['potassium_mg'] = ('Potassium Limit', targets.potassium_limit_mg)
    if targets.restrict_phosphorus and targets.phosphorus_limit_mg:
        limits['phosphorus_mg'] = ('Phosphorus Limit', targets.phosphorus_limit_mg)

    # 2. Check Targets (Floors)
    for key, (name, target_val) in target_map.items():
        # If this nutrient is currently strictly restricted by a limit, skip floor gap checking
        if key in limits and limits[key][0] != 'Saturated Fat' and limits[key][0] != 'Sodium':
            continue
            
        actual = actuals[key]
        if target_val <= 0:
            continue
            
        pct = (actual / target_val) * 100
        
        if pct >= 80 and pct <= 130:
            report.met.append(name)
        elif pct > 130:
            report.surplus.append(name)
        elif pct >= 60:
            report.borderline.append(name)
        else:
            report.deficient.append(name)

        # Generate Gap Suggestions
        if pct < 80:
            # Find top 3 approved foods rich in this nutrient
            suggested_foods_str = []
            if key in pool.by_nutrient_strength:
                top_foods = pool.by_nutrient_strength[key][:3]
                for sf in top_foods:
                    amt = sf.food.nutrients.get(key, 0)
                    # format e.g. "ragi roti (3.9mg)"
                    unit = key.split('_')[-1] # mg, g, mcg, iu
                    suggested_foods_str.append(f"{sf.food.name.lower()} ({amt}{unit})")
            
            note = f"Consider adding: {', '.join(suggested_foods_str)} — all are in your approved food list."
            if key == 'iron_mg':
                note += " Note: pair iron-rich foods with vitamin C sources (amla, lemon juice, guava) to improve absorption. Avoid tea/coffee within 1 hour."
            
            report.suggestions.append(
                GapSuggestion(
                    nutrient=name,
                    current_amount=round(actual, 1),
                    target_amount=round(target_val, 1),
                    gap_percentage=round(pct, 1),
                    suggested_foods=suggested_foods_str,
                    note=note
                )
            )

    # 3. Check Limits (Ceilings)
    for key, (name, limit_val) in limits.items():
        actual = actuals[key]
        if limit_val <= 0:
            continue
            
        pct = (actual / limit_val) * 100
        if pct > 100:
            report.surplus.append(f"{name} (Limit Exceeded)")
            report.suggestions.append(
                GapSuggestion(
                    nutrient=name,
                    current_amount=round(actual, 1),
                    target_amount=round(limit_val, 1),
                    gap_percentage=round(pct, 1),
                    suggested_foods=[],
                    note=f"⚠ Your plan provides {round(actual, 1)} against a strict limit of {round(limit_val, 1)}. You must reduce intake of {name}-heavy foods."
                )
            )
        elif pct >= 80:
            report.borderline.append(f"{name} (Near Limit)")

    # 4. Medication Depletion Notes
    for flag in targets.depletion_flags:
        # Example: "Metformin can reduce Vitamin B12 absorption over time. Ensure adequate dietary intake..."
        report.medication_depletion_notes.append(flag.note)
        
    # Deduplicate depletion notes
    report.medication_depletion_notes = list(set(report.medication_depletion_notes))

    return report
