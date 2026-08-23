from api.schemas.engine_schemas import UserProfileSchema
from api.schemas.targets import NutrientTargetsSchema, DepletionFlagSchema


DEPLETION_MAP = {
    'metformin': ['vitamin_b12'],
    'atorvastatin': ['coq10'],
    'rosuvastatin': ['coq10'],
    'pantoprazole': ['vitamin_b12', 'calcium', 'magnesium'],
    'omeprazole': ['vitamin_b12', 'calcium', 'magnesium'],
    'hydrochlorothiazide': ['potassium', 'magnesium', 'zinc'],
    'enalapril': ['zinc'],
    'ramipril': ['zinc'],
    'statin': ['coq10'],
}

def calculate_daily_targets(profile: UserProfileSchema) -> NutrientTargetsSchema:
    # 1. Base ICMR RDA estimation (2020)
    # Simple logic to mirror the local engine
    t = NutrientTargetsSchema()
    
    if profile.sex.lower() == 'male':
        t.calories_kcal = 2100 if profile.activity_level == 'sedentary' else 2700 if profile.activity_level == 'moderately_active' else 3400
        t.protein_g = 54.0
        t.iron_mg = 19.0
    else:
        t.calories_kcal = 1660 if profile.activity_level == 'sedentary' else 2130 if profile.activity_level == 'moderately_active' else 2720
        t.protein_g = 46.0
        t.iron_mg = 29.0
        
    t.carbs_g = (t.calories_kcal * 0.55) / 4
    t.fat_g = (t.calories_kcal * 0.25) / 9
    t.fiber_g = 30.0 if profile.sex.lower() == 'male' else 25.0
    
    condition_names = [
        c.name.lower().replace(' ', '_').replace('-', '_')
        for c in profile.conditions
    ]
    med_names = [
        m.name.lower().replace(' ', '_').replace('-', '_')
        for m in profile.medications
    ]
    
    # 2. Condition-specific Modifiers
    if 'hypertension' in condition_names:
        t.sodium_mg = 1500.0
        t.calculation_notes.append("Hypertension: Sodium restricted to <1500mg/day.")
        
    if 'type_2_diabetes' in condition_names or 'type_1_diabetes' in condition_names:
        t.added_sugar_g = 0.0
        t.prioritize_low_gi = True
        t.calculation_notes.append("Diabetes: Added sugar restricted to 0g. Prioritizing low-GI foods.")
        
    if 'ckd' in condition_names:
        ckd = next(c for c in profile.conditions if c.name.lower() == 'ckd')
        egfr = ckd.lab_values.get('egfr', 90)
        
        if egfr < 60:
            t.restrict_protein = True
            t.protein_g = 0.6 * profile.weight_kg
            t.protein_limit_g = 0.6 * profile.weight_kg
            t.calculation_notes.append(f"CKD (eGFR {egfr}): Protein restricted to {round(t.protein_limit_g, 1)}g.")
            
        if egfr < 30:
            t.restrict_potassium = True
            t.potassium_limit_mg = 2000.0
            t.restrict_phosphorus = True
            t.phosphorus_limit_mg = 800.0
            t.calculation_notes.append(f"CKD Stage 4/5 (eGFR {egfr}): Potassium restricted to <2000mg. Phosphorus restricted to <800mg.")

    if 'iron_def_anemia' in condition_names:
        t.iron_mg *= 1.5
        t.calculation_notes.append("Anemia: Daily iron target increased by 50% for therapeutic repletion.")
        
    if 'gerd' in condition_names:
        t.avoid_late_dinner = True
        t.calculation_notes.append("GERD: Late dinner avoidance flagged.")
        
    if 'hyperlipidemia' in condition_names:
        t.sat_fat_g = (t.calories_kcal * 0.06) / 9
        t.calculation_notes.append("Hyperlipidemia: Saturated fat restricted to <6% of daily calories.")


    if 'hypothyroidism' in condition_names:
        t.avoid_raw_cruciferous = True
        t.calculation_notes.append(
            "Large amounts of raw cruciferous vegetables (cabbage, "
            "cauliflower, broccoli) flagged for moderation. Cooking "
            "significantly reduces goitrogenic effect. Small cooked "
            "portions are acceptable. (Hypothyroidism)"
        )

    if 'gout' in condition_names:
        t.restrict_purines = True
        t.calculation_notes.append(
            "High-purine animal foods restricted (mutton, organ meats, "
            "prawns). Plant-source purines (rajma, chana) limited to "
            "moderate portions - plant purines have significantly lower "
            "urate-raising effect than animal purines per EULAR guidelines. "
            "(Gout)"
        )

    if 'pcos' in condition_names:
        t.prioritize_low_gi = True
        t.fiber_g = max(t.fiber_g, 25)
        t.calculation_notes.append(
            "Low-GI foods prioritized to support insulin sensitivity. "
            "Fiber target set to minimum 25g. (PCOS)"
        )

    if 'gerd' in condition_names:
        t.fat_g = min(t.fat_g, (t.calories_kcal * 0.25) / 9)
        t.small_frequent_meals = True
        t.avoid_late_dinner = True
        t.calculation_notes.append(
            "Fat target reduced to max 25% of calories. Small frequent "
            "meals recommended. Late dinner flagged. Spicy, acidic, and "
            "fried foods will be excluded from meal plan. (GERD)"
        )

    if 'osteoporosis' in condition_names:
        t.calcium_mg = 1200
        t.vitamin_d_iu = max(t.vitamin_d_iu, 800)
        t.calculation_notes.append(
            "Calcium target raised to 1200mg. Vitamin D raised to 800 IU. "
            "(Osteoporosis)"
        )

    if 'iron_def_anemia' in condition_names:
        t.iron_mg = 32 if profile.sex.lower() == 'female' else 20
        t.vitamin_c_mg = max(t.vitamin_c_mg, 80)
        t.calculation_notes.append(
            f"Iron target increased to {t.iron_mg}mg (therapeutic). "
            "Vitamin C raised to 80mg minimum to enhance non-heme "
            "iron absorption. (Iron Deficiency Anemia)"
        )

    if 'hyperlipidemia' in condition_names:
        t.sat_fat_g = (t.calories_kcal * 0.07) / 9
        t.fiber_g = max(t.fiber_g, 30)
        t.calculation_notes.append(
            "Saturated fat capped at 7% of calories. Fiber target "
            "raised to minimum 30g to support LDL reduction. "
            "(Hyperlipidemia)"
        )

    # 3. Medication Depletion Flags
    for med in profile.medications:
        for depletion in med.depletes_nutrients:
            # depletes_nutrients is now List[DepletionSchema] — access .nutrient attribute
            nutrient = depletion.nutrient.lower() if hasattr(depletion, 'nutrient') else str(depletion).lower()
            if nutrient == 'vitamin_b12':
                t.vitamin_b12_mcg *= 1.2
                t.depletion_flags.append(DepletionFlagSchema(
                    medication_name=med.name,
                    nutrient="vitamin_b12",
                    note=f"{med.name} can reduce Vitamin B12 absorption over time."
                ))
            if nutrient == 'coq10':
                t.depletion_flags.append(DepletionFlagSchema(
                    medication_name=med.name,
                    nutrient="coq10",
                    note=f"{med.name} can reduce CoQ10 levels over time."
                ))
            
    return t
