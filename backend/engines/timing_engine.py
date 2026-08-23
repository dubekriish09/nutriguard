from pydantic import BaseModel, Field
from typing import List, Optional
from dataclasses import dataclass, field
from api.schemas.engine_schemas import UserProfileSchema, FoodSchema
from engines.meal_engine import DailyMealPlan, Meal

class MedicationTimingAdvice(BaseModel):
    medication_name: str
    dose: str
    instruction: str
    meal_association: str
    warnings: List[str] = Field(default_factory=list)

def _get_breakfast(plan: DailyMealPlan) -> Optional[Meal]:
    for m in plan.meals:
        if m.name.lower() == 'breakfast':
            return m
    return None

def _get_all_foods_in_plan(plan: DailyMealPlan) -> List[str]:
    foods = []
    for m in plan.meals:
        for opt in m.options:
            foods.append(opt.food)
    return foods

def assign_medication_timing(
    medications: List[Medication],
    meal_plan: DailyMealPlan,
    has_ckd: bool = False # Optional helper to check CKD for ACE inhibitors
) -> List[MedicationTimingAdvice]:
    
    advice_list = []
    med_names = [m.name.lower() for m in medications]
    
    all_foods = []
    for m in meal_plan.meals:
        for opt in m.options:
            all_foods.append(opt.food)
            
    breakfast = _get_breakfast(meal_plan)

    for med in medications:
        name = med.name.lower().replace('_', ' ')
        dose = med.dose or "Standard dose"
        advice = MedicationTimingAdvice(
            medication_name=med.name,
            dose=dose,
            instruction="",
            meal_association="",
            warnings=[]
        )

        # ---------------------------------------------------------
        # LEVOTHYROXINE
        # ---------------------------------------------------------
        if 'levothyroxine' in name:
            advice.meal_association = "before_breakfast"
            advice.instruction = "Take on an empty stomach, 30-60 min before eating."
            advice.warnings.append("Avoid calcium-rich foods and calcium or iron supplements within 4 hours.")
            
            if breakfast:
                has_dairy = any('dairy' in opt.food.dietary_tags or 'calcium_rich' in opt.food.dietary_tags for opt in breakfast.options)
                if has_dairy:
                    advice.warnings.append("⚠ Breakfast contains dairy/calcium. Ensure strict 60-min gap before eating.")

        # ---------------------------------------------------------
        # METFORMIN
        # ---------------------------------------------------------
        elif 'metformin' in name:
            advice.meal_association = "with_food"
            advice.instruction = "Take with a main meal (lunch or dinner) to reduce GI side effects."
            advice.warnings.append("Monitor Vitamin B12 levels periodically.")

        # ---------------------------------------------------------
        # WARFARIN
        # ---------------------------------------------------------
        elif 'warfarin' in name:
            advice.meal_association = "any_time"
            advice.instruction = "Take consistently at the same time each day."
            
            vit_k_foods = []
            for food in all_foods:
                if 'vitamin_k_rich' in food.dietary_tags or food.nutrients.get('vitamin_k_mcg', 0) > 50:
                    vit_k_foods.append(food.name)
            
            if vit_k_foods:
                unique_vk = list(set(vit_k_foods))
                advice.warnings.append(
                    f"⚠ These Vitamin K-rich foods appear in your plan: {', '.join(unique_vk)}. "
                    "Eat them consistently — do not suddenly increase or remove them. Discuss with your doctor."
                )
            else:
                advice.warnings.append("Maintain consistent Vitamin K intake. Notify doctor before major diet changes.")

        # ---------------------------------------------------------
        # IRON SUPPLEMENTS
        # ---------------------------------------------------------
        elif 'ferrous' in name or 'iron supplement' in name:
            advice.meal_association = "empty_stomach"
            advice.instruction = "Take 30-60 min before a meal. If stomach upset occurs, take with a small non-dairy snack."
            advice.warnings.append("Pair with Vitamin C (e.g., lemon water, amla) for best absorption.")
            advice.warnings.append("Avoid within 2 hours of dairy, tea, coffee, and antacids.")
            
            if any('calcium_carbonate' in m for m in med_names):
                advice.warnings.append("⚠ Calcium Carbonate detected in medications. Space them at least 2 hours apart. Do NOT take iron and calcium supplements at the same time..")

        # ---------------------------------------------------------
        # CALCIUM CARBONATE
        # ---------------------------------------------------------
        elif 'calcium_carbonate' in name:
            advice.meal_association = "with_food"
            advice.instruction = "Take with food (requires stomach acid for absorption)."
            
            if any('ferrous' in m or 'iron' in m for m in med_names):
                advice.warnings.append("⚠ Do NOT take at the same time as Iron supplements (space 2 hours).")
            if any('levothyroxine' in m for m in med_names):
                advice.warnings.append("⚠ Do NOT take within 4 hours of Levothyroxine.")

        # ---------------------------------------------------------
        # STATINS
        # ---------------------------------------------------------
        elif 'statin' in name or 'atorvastatin' in name or 'rosuvastatin' in name:
            advice.meal_association = "evening_dinner"
            advice.instruction = "Take in the evening or with dinner (cholesterol synthesis peaks at night)."
            if any('grapefruit' in f.name.lower() for f in all_foods):
                advice.warnings.append("⚠ Grapefruit detected in diet. May interact with statins.")

        # ---------------------------------------------------------
        # ACE INHIBITORS
        # ---------------------------------------------------------
        elif 'pril' in name or 'enalapril' in name or 'ramipril' in name:
            advice.meal_association = "any_time"
            advice.instruction = "Take at a consistent time each day."
            
            high_k_foods = [f.name for f in all_foods if f.nutrients.get('potassium_mg', 0) > 400]
            if has_ckd and high_k_foods:
                advice.warnings.append(
                    f"⚠ Hyperkalemia risk: CKD + ACE Inhibitor + Potassium-rich foods ({', '.join(set(high_k_foods))}). Monitor potassium closely."
                )

        # ---------------------------------------------------------
        # PPIs
        # ---------------------------------------------------------
        elif 'prazole' in name or 'omeprazole' in name or 'pantoprazole' in name:
            advice.meal_association = "before_breakfast"
            advice.instruction = "Take 30-60 min before breakfast (empty stomach for efficacy)."
            advice.warnings.append("Long-term use may affect B12, Calcium, and Magnesium absorption.")

        # ---------------------------------------------------------
        # THIAZIDE DIURETICS
        # ---------------------------------------------------------
        elif 'thiazide' in name or 'hydrochlorothiazide' in name:
            advice.meal_association = "morning"
            advice.instruction = "Take in the morning to avoid nighttime urination (nocturia)."
            advice.warnings.append("May deplete potassium and magnesium. Ensure diet includes bananas, curd, or nuts if not restricted.")
            
        else:
            advice.meal_association = "as_directed"
            advice.instruction = "Take as directed by your physician."

        advice_list.append(advice)
        
    return advice_list
