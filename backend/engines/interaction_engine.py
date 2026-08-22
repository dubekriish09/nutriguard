from dataclasses import dataclass
from typing import List, Dict, Any
from uuid import UUID

@dataclass
class InteractionResult:
    food_id: UUID
    has_interactions: bool
    interactions: List[Dict[str, Any]]
    
    @property
    def max_severity(self) -> str:
        if not self.interactions:
            return 'none'
        severities = [i.get('severity', 'minor') for i in self.interactions]
        for s in ['critical', 'major', 'moderate', 'minor', 'informational']:
            if s in severities:
                return s
        return 'none'

class InteractionEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate(self, user_context: dict, food_id: UUID) -> InteractionResult:
        if not self.db:
            return InteractionResult(food_id=food_id, has_interactions=False, interactions=[])
            
        user_meds = user_context.get('medications', [])
        interactions = []
        
        from models.medication import DrugFoodInteraction, Medication
        from models.food import Food, FoodNutrition, Nutrient
        
        food = self.db.query(Food).filter(Food.food_id == food_id).first()
        if not food:
            return InteractionResult(food_id=food_id, has_interactions=False, interactions=[])
            
        # Get nutrients for this food
        food_nutrients = self.db.query(Nutrient.name).join(FoodNutrition).filter(FoodNutrition.food_id == food_id).all()
        food_nutrient_names = [n[0].lower() for n in food_nutrients]
        
        for med_dict in user_meds:
            med_generic = med_dict.get('generic_name', '').lower()
            if not med_generic:
                continue
                
            med = self.db.query(Medication).filter(Medication.generic_name.ilike(f"%{med_generic}%")).first()
            if not med:
                continue
                
            db_interactions = self.db.query(DrugFoodInteraction).filter(DrugFoodInteraction.medication_id == med.medication_id).all()
            
            for inter in db_interactions:
                match = False
                if inter.interaction_type == 'food' and inter.food_category and inter.food_category.lower() in food.name.lower():
                    match = True
                elif inter.interaction_type == 'nutrient' and inter.food_component:
                    if inter.food_component.lower() in food_nutrient_names:
                        match = True
                elif inter.interaction_type == 'beverage' and inter.food_component:
                    # In MVP, treat alcohol check broadly or just check aliases
                    if inter.food_component.lower() in food.name.lower():
                        match = True
                        
                if match:
                    interactions.append({
                        "medication_id": str(med.medication_id),
                        "medication_name": med.generic_name,
                        "interaction_type": inter.interaction_type,
                        "severity": inter.severity,
                        "mechanism": inter.mechanism,
                        "recommendation": inter.recommendation,
                        "timing_window": inter.timing_window
                    })
                    
        return InteractionResult(
            food_id=food_id,
            has_interactions=len(interactions) > 0,
            interactions=interactions
        )
