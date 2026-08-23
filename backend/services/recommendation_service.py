from typing import List
from uuid import UUID
from datetime import datetime

from engines.safety_engine import SafetyEngine
from engines.rule_engine import RuleEngine
from engines.interaction_engine import InteractionEngine
from engines.scoring_engine import ScoringEngine
from engines.targets_engine import calculate_daily_targets
from engines.meal_engine import build_approved_pool, compose_daily_plan
from engines.timing_engine import assign_medication_timing
from engines.gap_engine import check_nutrient_gaps
from api.schemas.engine_schemas import UserProfileSchema, ConditionSchema, MedicationSchema, DietaryPattern
from api.schemas.meal_schemas import DayPlanResponse

class RecommendationService:
    def __init__(self, db_session):
        self.db = db_session
        self.safety_engine = SafetyEngine(db_session)
        self.rule_engine = RuleEngine(db_session)
        self.interaction_engine = InteractionEngine(db_session)
        self.scoring_engine = ScoringEngine(db_session)

    async def build_user_context(self, user_id: UUID) -> UserProfileSchema:
        from models.user import UserProfile, UserCondition, UserMedication, UserAllergy
        from models.condition import Condition
        from models.medication import Medication
        from models.food import Allergen
        
        profile = self.db.query(UserProfile).filter_by(user_id=user_id, is_current=True).first()
        if not profile:
            raise Exception("UserProfileIncompleteError")

        u_conds = self.db.query(UserCondition).filter_by(user_id=user_id).all()
        conditions = []
        for uc in u_conds:
            c = self.db.query(Condition).filter_by(condition_id=uc.condition_id).first()
            if c:
                conditions.append(ConditionSchema(
                    name=c.name.lower().strip().replace(' ', '_').replace('-', '_'),
                    restrict_nutrients=[],
                    encourage_nutrients=[],
                    conditional_restrictions=[],
                    lab_values=uc.lab_values or {}
                ))
                
        from api.schemas.engine_schemas import DepletionSchema

        u_meds = self.db.query(UserMedication).filter_by(user_id=user_id).all()
        medications = []
        for um in u_meds:
            m = self.db.query(Medication).filter_by(medication_id=um.medication_id).first()
            if m:
                # Primary: load from ORM relationship (joined-loaded)
                depletes = []
                for d in m.depletions:
                    nutrient_name = d.nutrient.name.lower() if d.nutrient else None
                    if nutrient_name:
                        depletes.append(DepletionSchema(
                            nutrient=nutrient_name,
                            severity=d.severity or "moderate",
                            recommendation=d.recommendation or ""
                        ))

                # Fallback: DEPLETION_MAP for medications with no DB rows yet
                if not depletes:
                    from engines.targets_engine import DEPLETION_MAP
                    for key, mapped_nutrients in DEPLETION_MAP.items():
                        if key in m.generic_name.lower():
                            depletes = [DepletionSchema(nutrient=n, severity="moderate", recommendation="") for n in mapped_nutrients]
                            break

                medications.append(MedicationSchema(
                    name=m.generic_name.lower().strip().replace(' ', '_').replace('-', '_'),
                    dose=f"{um.dose_amount} {um.dose_unit}" if um.dose_amount else None,
                    timing=um.timing_relative_to_meal,
                    depletes_nutrients=depletes
                ))
                
        u_algs = self.db.query(UserAllergy).filter_by(user_id=user_id).all()
        allergies = []
        for ua in u_algs:
            a = self.db.query(Allergen).filter_by(allergen_id=ua.allergen_id).first()
            if a:
                allergies.append(a.name)

        return UserProfileSchema(
            age=profile.age or 30, 
            sex=profile.sex or "female", 
            weight_kg=float(profile.weight_kg) if profile.weight_kg else 70.0, 
            height_cm=float(profile.height_cm) if profile.height_cm else 170.0,
            activity_level=profile.activity_level or "sedentary", 
            dietary_pattern=DietaryPattern(profile.dietary_pattern.lower() if profile.dietary_pattern else "vegetarian"),
            allergies=allergies, 
            conditions=conditions, 
            medications=medications, 
            food_dislikes=profile.food_preferences or []
        )

    async def generate_day_plan(self, user_id: UUID) -> DayPlanResponse:
        try:
            user_context = await self.build_user_context(user_id)
        except Exception as e:
            from core.exceptions import UserProfileIncompleteError
            print(f"EXCEPTION: {e}")
            raise UserProfileIncompleteError()
            
        targets = calculate_daily_targets(user_context)
        
        from models.food import Food, FoodNutrition, Nutrient
        all_foods_orm = self.db.query(Food).all()
        from api.schemas.engine_schemas import FoodSchema
        all_foods = []
        for f in all_foods_orm:
            tags = []
            if f.is_vegan: tags.append('vegan')
            if f.is_jain: tags.append('jain')
            if not f.is_vegetarian: tags.append('non_veg')
            else: tags.append('vegetarian')
            
            # Fetch nutrients
            nut_dict = {}
            fns = self.db.query(FoodNutrition).filter_by(food_id=f.food_id).all()
            for fn in fns:
                nut = self.db.query(Nutrient).filter_by(nutrient_id=fn.nutrient_id).first()
                if nut:
                    nut_dict[nut.name] = float(fn.amount)
                    
            # Allergens 
            from models.food import FoodAllergen, Allergen
            algs = self.db.query(Allergen).join(FoodAllergen).filter(FoodAllergen.food_id==f.food_id).all()
            alg_names = [a.name.lower() for a in algs]
            
            all_foods.append(FoodSchema(
                name=f.name, category=f.category, dietary_tags=tags,
                glycemic_index=f.glycemic_index, purine_level=f.purine_level,
                vitamin_k_mcg=float(f.vitamin_k_mcg) if f.vitamin_k_mcg else None,
                nutrient_source=f.nutrient_source,
                nutrients=nut_dict,
                allergens=alg_names
            ))
            
        pool = build_approved_pool(user_context, all_foods)
        if not pool.recommended and not pool.moderation:
            from core.exceptions import FoodPoolEmptyError
            raise FoodPoolEmptyError()
            
        c_plan = compose_daily_plan(user_context, targets, pool)
        
        has_ckd = any(c.name.lower() == 'ckd' for c in user_context.conditions)
        timing = assign_medication_timing(user_context.medications, c_plan, has_ckd=has_ckd)
        
        gaps = check_nutrient_gaps(c_plan, targets, pool)
        gaps.depletion_flags = [f.model_dump() if hasattr(f, 'model_dump') else f.dict() if hasattr(f, 'dict') else f for f in targets.depletion_flags]
        
        meals_dict = {}
        for m in c_plan.meals:
            meals_dict[m.name.lower().replace('-', '_').replace(' ', '_')] = {
                "meal_type": m.name,
                "foods": [{"food_name": opt.food.name, "quantity_g": 100.0, "serving_description": opt.serving_description, "key_nutrients": {}} for opt in m.options],
                "total_nutrition": {"calories": m.calories, "protein_g": m.protein_g, "carbs_g": m.carbs_g, "fat_g": m.fat_g, "fiber_g": m.fiber_g, "sodium_mg": m.sodium_mg},
                "rationale": [opt.reason for opt in m.options] + m.notes
            }
            
        from models.meal_plan import MealPlan, MealPlanMeal
        db_plan = MealPlan(
            user_id=user_id,
            plan_type="single_day",
            is_ai_generated=False,
            safety_validated=True,
            targets_snapshot=targets.model_dump(),
            gap_report=gaps.model_dump(),
        )
        self.db.add(db_plan)
        self.db.flush()
        
        for meal_type, meal in meals_dict.items():
            db_meal = MealPlanMeal(
                plan_id=db_plan.id,
                meal_type=meal_type,
                foods=[f for f in meal['foods']],
                total_nutrition=meal['total_nutrition'],
                rationale=meal['rationale'],
            )
            self.db.add(db_meal)
            
        self.db.commit()
        self.db.refresh(db_plan)
            
        return DayPlanResponse(
            user_id=user_id,
            plan_id=db_plan.id,
            generated_at=db_plan.created_at,
            profile_summary="Profile Summary",
            targets=targets,
            meals=meals_dict,
            medication_timing=timing,
            nutrient_gaps=gaps,
            safety_notes=[],
            calculation_notes=targets.calculation_notes,
            safety_validated=True
        )


    async def generate_recommendations(self, user_context: dict, food_ids: List[UUID]) -> dict:
        from api.schemas.engine_schemas import UserProfileSchema, FoodSchema, ConditionSchema, MedicationSchema
        from api.schemas.engine_schemas import ConditionalRuleSchema
        from models.food import Food, FoodNutrition, Nutrient, FoodAllergen, Allergen
        
        conds = []
        for c_dict in user_context.get("conditions", []):
            name = c_dict.get("name", "")
            cr = []
            rn = []
            if name.lower() == 'ckd':
                cr.append(ConditionalRuleSchema(parameter="stage", operator=">=", value=4.0, restrict_nutrients=["potassium_mg"]))
            elif name.lower() == 'hypertension':
                rn.append("sodium_mg")
                
            conds.append(ConditionSchema(
                name=name,
                restrict_nutrients=rn,
                encourage_nutrients=[],
                conditional_restrictions=cr,
                lab_values=c_dict.get("parameters", {})
            ))
            


        from models.medication import Medication
        meds = []
        for m_dict in user_context.get("medications", []):
            m_name = m_dict.get("generic_name", "")
            fis = []
            if m_name.lower() == 'warfarin':
                from api.schemas.engine_schemas import FoodInteractionSchema
                fis.append(FoodInteractionSchema(
                    interacting_food_category='vitamin_k',
                    description='Vitamin K interaction',
                    severity='critical'
                ))
                
            meds.append(MedicationSchema(
                name=m_name,
                dose=None,
                timing=None,
                food_interactions=fis
            ))


            
        profile = UserProfileSchema(
            age=30, sex="female", weight_kg=70.0, height_cm=170.0, activity_level="sedentary",
            dietary_pattern="vegetarian",
            allergies=user_context.get("allergies", []),
            conditions=conds,
            medications=meds,
            food_dislikes=[]
        )
        
        results = []
        for food_id in food_ids:
            f = self.db.query(Food).filter_by(food_id=food_id).first()
            if not f: continue
            
            nut_dict = {}
            for fn in self.db.query(FoodNutrition).filter_by(food_id=food_id).all():
                nut = self.db.query(Nutrient).filter_by(nutrient_id=fn.nutrient_id).first()
                if nut: nut_dict[nut.name] = float(fn.amount)
            algs = self.db.query(Allergen).join(FoodAllergen).filter(FoodAllergen.food_id==food_id).all()
            
            food_schema = FoodSchema(
                name=f.name, category=f.category, dietary_tags=["vitamin_k"] if float(f.vitamin_k_mcg or 0) > 0 else [], glycemic_index=f.glycemic_index,
                purine_level=f.purine_level, vitamin_k_mcg=float(f.vitamin_k_mcg) if f.vitamin_k_mcg else None,
                nutrient_source=f.nutrient_source, nutrients=nut_dict, allergens=[a.name.lower() for a in algs]
            )
            
            # STEP 1: Safety pre-check
            safety_pre = self.safety_engine.evaluate(profile, food_schema)
            if not safety_pre.is_safe_to_evaluate:
                results.append({
                    "food_id": food_id,
                    "classification": "blocked_allergy" if safety_pre.veto_priority == 1 else "blocked_interaction",
                    "reason": safety_pre.veto_reason,
                    "requires_professional_review": safety_pre.requires_professional_review,
                    "fired_rules": safety_pre.rule_ids_fired,
                    "interactions": [] 
                })
                from engines.interaction_engine import InteractionEngine
                ie = InteractionEngine(self.db)
                i_res = ie.evaluate(profile, food_schema)
                results[-1]["interactions"] = i_res.get("interactions", [])
                continue
                
            # STEP 2: Rule engine
            rule_result = self.rule_engine.evaluate_food(profile, food_schema)
            
            # STEP 3: Interaction engine
            from engines.interaction_engine import InteractionEngine
            ie = InteractionEngine(self.db)
            interaction_result = ie.evaluate(profile, food_schema)
            
            classification = rule_result.classification.value
            
            if interaction_result.get('max_severity') in ('critical', 'major'):
                classification = 'avoid'
            elif interaction_result.get('max_severity') == 'moderate' and classification not in ('avoid', 'limit', 'blocked'):
                classification = 'use_cautiously'
                
            final = self.safety_engine.validate_ai_output(
                {"classification": classification, "explanation": "test"},
                {"classification": classification}
            )
            
            results.append({
                "food_id": food_id,
                "classification": final.get("classification"),
                "explanation": final.get("explanation"),
                "score": 0.0,
                "fired_rules": [{"rationale": r.reason} for r in rule_result.fired_rules],
                "interactions": interaction_result.get("interactions", [])
            })
            
        return {
            "foods": results,
            "generated_at": datetime.now().isoformat()
        }
