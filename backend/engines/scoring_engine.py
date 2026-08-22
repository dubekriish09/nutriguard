from typing import Dict, Any
from uuid import UUID
from .rule_engine import RuleResult
from .interaction_engine import InteractionResult

class ScoringEngine:
    def __init__(self, db_session):
        self.db = db_session

    def score_food(self, user_context: dict, food_id: UUID, rule_result: RuleResult, interaction_result: InteractionResult) -> Dict[str, Any]:
        """
        Multi-factor weighted scoring algorithm for food suitability.
        """
        # Base Sub-scores
        nutrition_score = 70.0
        condition_compatibility = 50.0
        medication_safety = 100.0
        nutrient_relevance = 50.0
        preference_score = 50.0
        goal_alignment = 50.0
        
        # Apply interaction penalties
        if interaction_result.max_severity == 'moderate':
            medication_safety -= 30.0
        elif interaction_result.max_severity in ('major', 'critical'):
            medication_safety = 0.0
            
        # Apply rule penalties/boosts
        for rule in rule_result.fired_rules:
            action = rule.get('action')
            if action == 'encourage':
                condition_compatibility += 20.0
            elif action == 'limit':
                condition_compatibility -= 30.0
                
        # Final calculation
        final_score = (
            (nutrition_score * 0.3) +
            (condition_compatibility * 0.3) +
            (medication_safety * 0.2) +
            (preference_score * 0.1) +
            (goal_alignment * 0.1)
        )
        
        return {
            'food_id': food_id,
            'nutrition_score': max(0.0, min(100.0, nutrition_score)),
            'condition_compatibility': max(0.0, min(100.0, condition_compatibility)),
            'medication_safety': max(0.0, min(100.0, medication_safety)),
            'final_score': max(0.0, min(100.0, final_score))
        }
