from typing import List, Dict, Any
from uuid import UUID
from dataclasses import dataclass

@dataclass
class RuleResult:
    food_id: UUID
    fired_rules: List[Dict[str, Any]]
    
    @property
    def classification(self) -> str:
        if not self.fired_rules:
            return 'neutral'
            
        classifications = [r.get('action') for r in self.fired_rules]
        if 'blocked_allergy' in classifications or 'blocked_interaction' in classifications or 'avoid' in classifications:
            return 'avoid'
        elif 'limit' in classifications:
            return 'limit'
        elif 'use_cautiously' in classifications:
            return 'use_cautiously'
        elif 'encourage' in classifications or 'recommend' in classifications:
            return 'recommended'
        return 'neutral'

class RuleEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate_food(self, user_context: dict, food_id: UUID) -> RuleResult:
        applicable_rules = self._get_applicable_rules(user_context)
        fired_rules = []
        
        for rule in sorted(applicable_rules, key=lambda r: r.priority):
            if self._rule_targets_food(rule, food_id):
                if self._evaluate_triggers(rule, user_context):
                    fired_rules.append({
                        "rule_id": str(rule.cn_rule_id),
                        "action": rule.action,
                        "priority": rule.priority,
                        "rationale": rule.rationale
                    })
                    
        return RuleResult(food_id=food_id, fired_rules=fired_rules)

    def _get_applicable_rules(self, user_context: dict) -> List[Any]:
        if not self.db:
            return []
            
        user_conditions = user_context.get('conditions', [])
        cond_names = [c.get('name').lower() for c in user_conditions if c.get('name')]
        
        from models.condition import Condition, ConditionNutritionRule
        
        rules = []
        for c_name in cond_names:
            cond = self.db.query(Condition).filter(Condition.name.ilike(f"%{c_name}%")).first()
            if cond:
                cond_rules = self.db.query(ConditionNutritionRule).filter(
                    ConditionNutritionRule.condition_id == cond.condition_id,
                    ConditionNutritionRule.rule_status == 'ACTIVE'
                ).all()
                rules.extend(cond_rules)
                
        return rules

    def _rule_targets_food(self, rule: Any, food_id: UUID) -> bool:
        if not self.db:
            return False
            
        from models.food import Food, FoodNutrition, Nutrient
        food = self.db.query(Food).filter(Food.food_id == food_id).first()
        if not food:
            return False
            
        if rule.food_category and rule.food_category.lower() in food.name.lower():
            return True
            
        if rule.nutrient_id:
            fn = self.db.query(FoodNutrition).filter(
                FoodNutrition.food_id == food_id, 
                FoodNutrition.nutrient_id == rule.nutrient_id
            ).first()
            if fn:
                return True
                
        return False

    def _evaluate_triggers(self, rule: Any, user_context: dict) -> bool:
        if not rule.is_conditional:
            return True
            
        # e.g., condition_parameter = 'stage', condition_operator = '>=', condition_value = '4'
        user_conditions = user_context.get('conditions', [])
        
        # Find the specific condition the user has
        from models.condition import Condition
        cond = self.db.query(Condition).filter(Condition.condition_id == rule.condition_id).first()
        if not cond:
            return False
            
        for u_cond in user_conditions:
            if u_cond.get('name', '').lower() == cond.name.lower():
                # Evaluate parameter
                param = rule.condition_parameter
                val = u_cond.get('parameters', {}).get(param)
                if val is None:
                    return False
                    
                op = rule.condition_operator
                target_val = rule.condition_value
                
                try:
                    v1 = float(val)
                    v2 = float(target_val)
                except ValueError:
                    v1, v2 = str(val), str(target_val)
                    
                if op == '=' or op == '==': return v1 == v2
                if op == '>': return v1 > v2
                if op == '>=': return v1 >= v2
                if op == '<': return v1 < v2
                if op == '<=': return v1 <= v2
                
        return False
