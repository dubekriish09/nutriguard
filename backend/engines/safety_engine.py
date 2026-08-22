from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID

@dataclass
class SafetyResult:
    food_id: UUID
    is_safe_to_evaluate: bool
    is_safe_to_recommend: bool
    veto_reason: Optional[str]
    veto_priority: int
    warnings: List[str]
    requires_professional_review: bool
    rule_ids_fired: List[UUID]

class SafetyEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate(self, user_context: dict, food_id: UUID) -> SafetyResult:
        allergy_result = self._check_allergy(user_context, food_id)
        if allergy_result.get('is_blocked'):
            return SafetyResult(
                food_id=food_id,
                is_safe_to_evaluate=False,
                is_safe_to_recommend=False,
                veto_reason=allergy_result.get('reason'),
                veto_priority=1,
                warnings=[],
                requires_professional_review=False,
                rule_ids_fired=allergy_result.get('rule_ids', [])
            )

        critical_interactions = self._check_critical_interactions(user_context, food_id)
        if critical_interactions.get('has_critical'):
            return SafetyResult(
                food_id=food_id,
                is_safe_to_evaluate=False,
                is_safe_to_recommend=False,
                veto_reason=critical_interactions.get('reason'),
                veto_priority=2,
                warnings=critical_interactions.get('warnings', []),
                requires_professional_review=True,
                rule_ids_fired=critical_interactions.get('rule_ids', [])
            )
            
        return SafetyResult(
            food_id=food_id,
            is_safe_to_evaluate=True,
            is_safe_to_recommend=True,
            veto_reason=None,
            veto_priority=999,
            warnings=[],
            requires_professional_review=False,
            rule_ids_fired=[]
        )

    def _check_allergy(self, user_context: dict, food_id: UUID) -> Dict[str, Any]:
        if not self.db:
            return {'is_blocked': False}
            
        user_allergies = user_context.get('allergies', [])
        if not user_allergies:
            return {'is_blocked': False}
            
        from models.food import FoodAllergen, Allergen
        # Get all allergens for this food
        food_allergens = self.db.query(Allergen).join(FoodAllergen).filter(FoodAllergen.food_id == food_id).all()
        
        food_alg_names = [a.name.lower() for a in food_allergens]
        
        for u_alg in user_allergies:
            if u_alg.lower() in food_alg_names:
                return {'is_blocked': True, 'reason': f'Allergy match: {u_alg}', 'rule_ids': []}
                
        return {'is_blocked': False}

    def _check_critical_interactions(self, user_context: dict, food_id: UUID) -> Dict[str, Any]:
        from .interaction_engine import InteractionEngine
        if not self.db:
            return {'has_critical': False}
            
        ie = InteractionEngine(self.db)
        res = ie.evaluate(user_context, food_id)
        
        critical = [i for i in res.interactions if i.get('severity') == 'critical']
        if critical:
            return {
                'has_critical': True,
                'reason': critical[0]['mechanism'],
                'warnings': [c['recommendation'] for c in critical],
                'rule_ids': []
            }
        return {'has_critical': False}

    def validate_ai_output(self, ai_recommendation: dict, rule_engine_result: dict) -> dict:
        ai_class = ai_recommendation.get('classification')
        rule_class = rule_engine_result.get('classification')
        
        if rule_class in ('blocked_allergy', 'blocked_interaction', 'avoid'):
            if ai_class in ('recommended', 'recommended_in_moderation'):
                ai_recommendation['classification'] = rule_class
                ai_recommendation['explanation'] = 'Safety Engine Override: ' + ai_recommendation.get('explanation', '')
                
        return ai_recommendation
