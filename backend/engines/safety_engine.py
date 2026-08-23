from pydantic import BaseModel, Field
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID
from api.schemas.engine_schemas import UserProfileSchema, FoodSchema

class SafetyResult(BaseModel):
    food_id: str
    is_safe_to_evaluate: bool
    is_safe_to_recommend: bool
    veto_reason: Optional[str]
    veto_priority: int
    warnings: List[str]
    requires_professional_review: bool
    rule_ids_fired: List[str]

class SafetyEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate(self, user_context: UserProfileSchema, food: FoodSchema) -> SafetyResult:
        # Check allergy
        food_alg = [a.lower() for a in food.allergens]
        for u_alg in user_context.allergies:
            if u_alg.lower() in food_alg:
                return SafetyResult(
                    food_id=food.name,
                    is_safe_to_evaluate=False,
                    is_safe_to_recommend=False,
                    veto_reason=f'Allergy match: {u_alg}',
                    veto_priority=1,
                    warnings=[],
                    requires_professional_review=False,
                    rule_ids_fired=[]
                )

        # Check critical interactions
        from engines.interaction_engine import InteractionEngine
        ie = InteractionEngine(self.db)
        res = ie.evaluate(user_context, food)
        
        critical = [i for i in res['interactions'] if i.get('severity') in ('critical', 'high')]
        if critical:
            return SafetyResult(
                food_id=food.name,
                is_safe_to_evaluate=False,
                is_safe_to_recommend=False,
                veto_reason=critical[0]['mechanism'],
                veto_priority=2,
                warnings=[c['recommendation'] for c in critical],
                requires_professional_review=True,
                rule_ids_fired=[]
            )
            
        return SafetyResult(
            food_id=food.name,
            is_safe_to_evaluate=True,
            is_safe_to_recommend=True,
            veto_reason=None,
            veto_priority=999,
            warnings=[],
            requires_professional_review=False,
            rule_ids_fired=[]
        )

    def validate_ai_output(self, ai_recommendation: dict, rule_engine_result: dict) -> dict:
        ai_class = ai_recommendation.get('classification')
        rule_class = rule_engine_result.get('classification')
        
        if rule_class in ('blocked', 'blocked_allergy', 'blocked_interaction', 'avoid'):
            if ai_class in ('recommended', 'recommended_in_moderation'):
                ai_recommendation['classification'] = rule_class
                ai_recommendation['explanation'] = 'Safety Engine Override: ' + ai_recommendation.get('explanation', '')
                
        return ai_recommendation
