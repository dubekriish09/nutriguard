
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from api.schemas.engine_schemas import UserProfileSchema, FoodSchema, Classification
from api.schemas.targets import NutrientTargetsSchema
from engines.rule_engine import RuleEngine

Food = FoodSchema

from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class BlockedFood:
    food: Food
    reasons: List[str]

@dataclass
class ScoredFood:
    food: Food
    classification: str
    fired_rules: List[FiredRule]
    nutrient_highlights: List[str]

@dataclass
class ApprovedFoodPool:
    recommended: List[ScoredFood] = field(default_factory=list)
    moderation: List[ScoredFood] = field(default_factory=list)
    blocked: List[BlockedFood] = field(default_factory=list)
    by_category: Dict[str, List[ScoredFood]] = field(default_factory=dict)
    by_nutrient_strength: Dict[str, List[ScoredFood]] = field(default_factory=dict)

def get_nutrient_highlights(food: Food) -> List[str]:
    highlights = []
    n = food.nutrients
    if n.get('protein_g', 0) >= 10:
        highlights.append("High protein")
    if n.get('fiber_g', 0) >= 4:
        highlights.append("High fiber")
    if n.get('iron_mg', 0) >= 2.5:
        highlights.append("Good iron source")
    if n.get('calcium_mg', 0) >= 150:
        highlights.append("Good calcium source")
    if n.get('vitamin_b12_mcg', 0) >= 0.4:
        highlights.append("Good B12 source")
    if n.get('vitamin_c_mg', 0) >= 30:
        highlights.append("High Vitamin C")
    if n.get('omega_3_mg', 0) >= 200:
        highlights.append("Omega-3 rich")
    if n.get('potassium_mg', 0) >= 400:
        highlights.append("High potassium")
    return highlights

def build_approved_pool(profile: UserProfileSchema, all_foods: List[Food]) -> ApprovedFoodPool:
    pool = ApprovedFoodPool()

    # Nutrients we want to index for gap filling
    key_nutrients = [
        'protein_g', 'fiber_g', 'iron_mg', 'calcium_mg', 
        'vitamin_b12_mcg', 'vitamin_c_mg', 'omega_3_mg', 'potassium_mg'
    ]
    
    # Initialize index dicts
    for n in key_nutrients:
        pool.by_nutrient_strength[n] = []

    for food in all_foods:
        # Pre-filter: Dietary Pattern strict constraints
        pattern = profile.dietary_pattern.value if hasattr(profile.dietary_pattern, 'value') else str(profile.dietary_pattern)
        pattern = pattern.lower()
        tags = [t.lower() for t in food.dietary_tags]
        
        is_violating = False
        if pattern == 'vegan':
            if 'non_veg' in tags or 'egg' in tags or 'dairy' in tags or food.category in ['dairy', 'egg', 'protein'] and not 'vegan' in tags:
                is_violating = True
        elif pattern == 'vegetarian':
            if 'non_veg' in tags or 'egg' in tags or food.category == 'egg':
                is_violating = True
        elif pattern == 'jain':
            if 'non_veg' in tags or 'egg' in tags:
                is_violating = True
            # For Jain, we also block typical root vegetables if identified (like potato, onion, garlic)
            if any(r in food.name.lower() for r in ['onion', 'garlic', 'potato', 'carrot', 'radish']):
                is_violating = True
        elif pattern == 'eggetarian':
            if 'non_veg' in tags:
                is_violating = True
                
        if is_violating:
            pool.blocked.append(BlockedFood(food=food, reasons=[f"Violates {pattern} dietary pattern."]))
            continue

        # GATEKEEPER: Run every food through deterministic evaluator
        result = RuleEngine(None).evaluate_food(profile, food)
        
        if result.classification in [Classification.BLOCKED, Classification.AVOID]:
            pool.blocked.append(BlockedFood(food=food, reasons=result.reasons))
            continue
            
        # Food passed. Score and highlight it.
        highlights = get_nutrient_highlights(food)
        scored = ScoredFood(
            food=food,
            classification=result.classification.value,
            fired_rules=result.fired_rules,
            nutrient_highlights=highlights
        )

        # Bucket into recommended or moderation
        if result.classification in [Classification.RECOMMENDED, Classification.NEUTRAL]:
            pool.recommended.append(scored)
        else: # Classification.LIMIT
            pool.moderation.append(scored)
            
        # Index by category
        if food.category not in pool.by_category:
            pool.by_category[food.category] = []
        pool.by_category[food.category].append(scored)

    # Now that all passed foods are bucketed, build the nutrient_strength indexes
    # We combine recommended and moderation for the pool, though composer may prefer recommended
    all_approved = pool.recommended + pool.moderation
    
    for nutrient in key_nutrients:
        # Filter foods that actually have a meaningful amount of the nutrient
        foods_with_nutrient = [sf for sf in all_approved if sf.food.nutrients.get(nutrient, 0) > 0]
        
        # Sort descending by the amount of the nutrient
        foods_with_nutrient.sort(key=lambda sf: sf.food.nutrients.get(nutrient, 0), reverse=True)
        
        pool.by_nutrient_strength[nutrient] = foods_with_nutrient

    return pool


import random
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

@dataclass
class MealOption:
    food: Food
    portion_multiplier: float
    serving_description: str
    reason: str

@dataclass
class Meal:
    name: str
    options: List[MealOption] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # Totals
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0

    def calculate_totals(self):
        self.calories = sum(opt.food.nutrients.get('calories', 0) * opt.portion_multiplier for opt in self.options)
        self.protein_g = sum(opt.food.nutrients.get('protein_g', 0) * opt.portion_multiplier for opt in self.options)
        self.carbs_g = sum(opt.food.nutrients.get('carbs_g', 0) * opt.portion_multiplier for opt in self.options)
        self.fat_g = sum(opt.food.nutrients.get('fat_g', 0) * opt.portion_multiplier for opt in self.options)
        self.fiber_g = sum(opt.food.nutrients.get('fiber_g', 0) * opt.portion_multiplier for opt in self.options)
        self.sodium_mg = sum(opt.food.nutrients.get('sodium_mg', 0) * opt.portion_multiplier for opt in self.options)

@dataclass
class DailyMealPlan:
    meals: List[Meal]
    day_notes: List[str]
    
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_sodium: float = 0.0

    def calculate_totals(self):
        self.total_calories = sum(m.calories for m in self.meals)
        self.total_protein = sum(m.protein_g for m in self.meals)
        self.total_sodium = sum(m.sodium_mg for m in self.meals)


def get_serving_desc(food: Food) -> str:
    name = food.name.lower()
    if 'roti' in name or 'chapati' in name or 'bread' in name:
        return '1 medium (~30g)'
    elif 'idli' in name:
        return '1 piece (~40g)'
    elif 'dosa' in name or 'uttapam' in name:
        return '1 plain (~60g)'
    elif 'rice' in name or 'poha' in name or 'upma' in name or 'oats' in name or 'sabudana' in name:
        return '1 katori cooked (~150g)'
    elif food.category in ['pulse', 'vegetable']:
        return '1 katori (~150g)'
    elif food.category == 'dairy' and 'milk' in name:
        return '1 cup (~240ml)'
    elif food.category == 'dairy' and ('curd' in name or 'dahi' in name):
        return '1 katori (~150g)'
    elif food.category == 'fruit':
        return '1 serving'
    elif food.category == 'beverage':
        return '1 glass/cup'
    elif food.category == 'nuts' or food.category == 'seeds':
        return '1 handful / 1 tbsp'
    elif food.category == 'protein':
        if 'egg' in name:
            return '1 whole'
        return '100g cooked'
    return '1 serving'


def select_food(
    pool: ApprovedFoodPool, 
    category: str, 
    exclude: Set[str] = None, 
    prioritize_low_gi: bool = False,
    must_be_leafy: bool = False,
    require_dairy: bool = False
) -> Optional[ScoredFood]:
    
    options = pool.by_category.get(category, [])
    if not options:
        return None
        
    if exclude:
        options = [o for o in options if o.food.name not in exclude]

    if require_dairy:
        options = [o for o in options if 'dairy' in o.food.dietary_tags]
        
    if must_be_leafy:
        leafy_keywords = ['palak', 'methi', 'leaves', 'bathua', 'cabbage']
        options = [o for o in options if any(k in o.food.name.lower() for k in leafy_keywords)]

    if not options:
        # Fallback to any in category if filters are too strict (but maintain exclude list)
        options = pool.by_category.get(category, [])
        if exclude:
            options = [o for o in options if o.food.name not in exclude]
        if not options:
            return None

    if prioritize_low_gi:
        # Sort by GI (ascending). Use a large number if GI is None
        options.sort(key=lambda o: (o.food.glycemic_index if o.food.glycemic_index is not None else 999))
    else:
        # Sort by highest score (assuming classification RECOMMENDED > MODERATION)
        options.sort(key=lambda o: 0 if o.classification == 'recommended' else 1)

    return options[0]


def compose_daily_plan(profile: UserProfileSchema, targets: NutrientTargetsSchema, pool: ApprovedFoodPool) -> DailyMealPlan:
    meals = []
    used_foods: Set[str] = set()
    day_notes = []
    
    # ---------------------------------------------------------
    # BREAKFAST (25% kcal target)
    # ---------------------------------------------------------
    bk_options = []
    bk_notes = []
    
    # 1. Grain
    base = select_food(pool, 'grain', exclude=used_foods, prioritize_low_gi=targets.prioritize_low_gi)
    if base:
        used_foods.add(base.food.name)
        reason = "Low-GI priority for diabetes/PCOS." if targets.prioritize_low_gi else "Standard breakfast base."
        bk_options.append(MealOption(base.food, 1.0, get_serving_desc(base.food), reason))
        
    # 2. Protein
    prot = select_food(pool, 'dairy', exclude=used_foods)
    if not prot:
        prot = select_food(pool, 'egg', exclude=used_foods)
    if not prot:
        prot = select_food(pool, 'pulse', exclude=used_foods)
        
    if prot:
        used_foods.add(prot.food.name)
        bk_options.append(MealOption(prot.food, 1.0, get_serving_desc(prot.food), "Protein source for breakfast."))
        
    # 3. Veg side
    veg = select_food(pool, 'vegetable', exclude=used_foods)
    if veg:
        bk_options.append(MealOption(veg.food, 0.5, "1/2 katori", "Added fiber and micronutrients."))
        
    # 4. Beverage
    bev = select_food(pool, 'beverage', exclude=used_foods)
    if bev:
        bk_options.append(MealOption(bev.food, 1.0, "1 cup", "Morning hydration."))
        
    # 5. Levothyroxine Flag
    if any(m.name.lower() == 'levothyroxine' for m in profile.medications):
        bk_notes.append("⚕ Take levothyroxine 30 min BEFORE this meal on an empty stomach.")

    bk_meal = Meal("Breakfast", bk_options, bk_notes)
    bk_meal.calculate_totals()
    meals.append(bk_meal)

    # ---------------------------------------------------------
    # MID-MORNING (10% kcal target)
    # ---------------------------------------------------------
    mm_options = []
    mm_notes = []
    
    # B12 Depletion logic
    b12_flagged = any(f.nutrient == 'vitamin_b12' for f in targets.depletion_flags)
    
    if b12_flagged:
        snack = select_food(pool, 'dairy', exclude=used_foods)
        reason = "Dairy selected to address B12 depletion from medication."
    else:
        snack = select_food(pool, 'fruit', exclude=used_foods, prioritize_low_gi=targets.prioritize_low_gi)
        reason = "Low-GI fruit priority." if targets.prioritize_low_gi else "Fresh fruit snack."
        
    if not snack:
        snack = select_food(pool, 'nuts', exclude=used_foods)
        reason = "Healthy fats and protein."
        
    if snack:
        used_foods.add(snack.food.name)
        mm_options.append(MealOption(snack.food, 1.0, get_serving_desc(snack.food), reason))
        
    mm_meal = Meal("Mid-Morning", mm_options, mm_notes)
    mm_meal.calculate_totals()
    meals.append(mm_meal)

    # ---------------------------------------------------------
    # LUNCH (35% kcal target)
    # ---------------------------------------------------------
    lun_options = []
    lun_notes = []
    
    # 1. Base
    lun_base = select_food(pool, 'grain', exclude=used_foods, prioritize_low_gi=targets.prioritize_low_gi)
    if lun_base:
        used_foods.add(lun_base.food.name)
        portion = 2.0 if 'roti' in lun_base.food.name.lower() else 1.0
        lun_options.append(MealOption(lun_base.food, portion, f"{portion} portion(s) ({get_serving_desc(lun_base.food)})", "Lunch complex carbohydrate."))
        
    # 2. Dal/Pulse
    lun_dal = select_food(pool, 'pulse', exclude=used_foods)
    if lun_dal:
        used_foods.add(lun_dal.food.name)
        lun_options.append(MealOption(lun_dal.food, 1.0, get_serving_desc(lun_dal.food), "Primary protein source."))
        
    # 3. Vegetables (1 leafy if iron flagged, else 2 normal)
    iron_flagged = any('iron' in f.nutrient for f in targets.depletion_flags) or targets.iron_mg > 20
    lun_veg1 = select_food(pool, 'vegetable', exclude=used_foods, must_be_leafy=iron_flagged)
    if lun_veg1:
        used_foods.add(lun_veg1.food.name)
        lun_options.append(MealOption(lun_veg1.food, 1.0, get_serving_desc(lun_veg1.food), "Leafy green for iron/folate." if iron_flagged else "Vegetable fiber."))
        
    lun_veg2 = select_food(pool, 'vegetable', exclude=used_foods)
    if lun_veg2:
        used_foods.add(lun_veg2.food.name)
        lun_options.append(MealOption(lun_veg2.food, 0.5, "1/2 katori", "Additional micronutrients."))
        
    # 4. Curd
    lun_curd = select_food(pool, 'dairy', require_dairy=True) # It's fine to repeat curd if it passes evaluate_food
    if lun_curd:
        lun_options.append(MealOption(lun_curd.food, 1.0, get_serving_desc(lun_curd.food), "Probiotics and calcium."))

    lun_meal = Meal("Lunch", lun_options, lun_notes)
    lun_meal.calculate_totals()
    
    if lun_meal.sodium_mg > (targets.sodium_mg * 0.4):
        lun_notes.append("⚠ Sodium check: Avoid adding extra table salt to this meal.")
        
    meals.append(lun_meal)

    # ---------------------------------------------------------
    # EVENING SNACK (10% kcal target)
    # ---------------------------------------------------------
    es_options = []
    es_notes = []
    
    es_snack = select_food(pool, 'nuts', exclude=used_foods)
    if not es_snack:
        es_snack = select_food(pool, 'seeds', exclude=used_foods)
    if es_snack:
        used_foods.add(es_snack.food.name)
        es_options.append(MealOption(es_snack.food, 1.0, get_serving_desc(es_snack.food), "Healthy fat and satiety."))
        
    es_meal = Meal("Evening Snack", es_options, es_notes)
    es_meal.calculate_totals()
    meals.append(es_meal)

    # ---------------------------------------------------------
    # DINNER (20% kcal target)
    # ---------------------------------------------------------
    din_options = []
    din_notes = []
    
    # GERD Warning
    if targets.avoid_late_dinner:
        din_notes.append("⚠ Ensure dinner is consumed 2-3 hours before your typical sleep time (GERD).")
        
    din_base = select_food(pool, 'grain', exclude=used_foods, prioritize_low_gi=targets.prioritize_low_gi)
    if din_base:
        portion = 1.0 # Dinner lighter than lunch
        din_options.append(MealOption(din_base.food, portion, get_serving_desc(din_base.food), "Light evening carb base."))
        
    din_veg = select_food(pool, 'vegetable', exclude=used_foods)
    if din_veg:
        din_options.append(MealOption(din_veg.food, 1.0, get_serving_desc(din_veg.food), "Evening fiber."))
        
    din_protein = select_food(pool, 'pulse', exclude=used_foods)
    if not din_protein:
        din_protein = select_food(pool, 'dairy', exclude=used_foods)
    if din_protein:
        din_options.append(MealOption(din_protein.food, 1.0, get_serving_desc(din_protein.food), "Light evening protein."))

    din_meal = Meal("Dinner", din_options, din_notes)
    din_meal.calculate_totals()
    meals.append(din_meal)
    
    # ---------------------------------------------------------
    # FINAL ASSEMBLY
    # ---------------------------------------------------------
    plan = DailyMealPlan(meals=meals, day_notes=day_notes)
    plan.calculate_totals()
    
    if plan.total_sodium > targets.sodium_mg:
        day_notes.append(f"⚠ Warning: Projected sodium ({plan.total_sodium}mg) exceeds target ({targets.sodium_mg}mg). Ensure no added salt.")
        
    return plan
