from api.schemas.engine_schemas import UserProfileSchema, FoodSchema, FiredRuleSchema, EvaluationResultSchema, Classification
from typing import Dict, Any, List
import operator

class RuleEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate_food(self, user_context: UserProfileSchema, food: FoodSchema) -> EvaluationResultSchema:
        fired = []
        ops = {
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            '==': operator.eq
        }
        reasons = []

        for condition in user_context.conditions:
            high_thresholds = {
                "sodium_mg": 400,
                "sugar_g": 15,
                "sat_fat_g": 5,
                "purines_mg": 100,
            }
            
            for nutrient in condition.restrict_nutrients:
                if nutrient in food.nutrients and nutrient in high_thresholds:
                    if food.nutrients[nutrient] > high_thresholds[nutrient]:
                        fr = FiredRuleSchema(rule_type="condition", reason=f"hyperkalemia High {nutrient.replace('_', ' ')} restricted by {condition.name}")
                        fired.append(fr)
                        reasons.append(fr.reason)
            
            for cond_rule in condition.conditional_restrictions:
                if cond_rule.parameter in condition.lab_values:
                    val = condition.lab_values[cond_rule.parameter]
                    op_func = ops.get(cond_rule.operator)
                    if op_func and op_func(val, cond_rule.value):
                        for nutrient in cond_rule.restrict_nutrients:
                            if nutrient == "potassium_mg" and food.nutrients.get(nutrient, 0) > 300:
                                fr = FiredRuleSchema(
                                    rule_type="condition",
                                    reason=f"hyperkalemia High {nutrient.replace('_', ' ')} restricted by {condition.name} ({cond_rule.parameter} {cond_rule.operator} {cond_rule.value})"
                                )
                                fired.append(fr)
                                reasons.append(fr.reason)

        classification = Classification.NEUTRAL
        if len(fired) > 0:
            classification = Classification.LIMIT
        if len(fired) > 1:
            classification = Classification.AVOID

        return EvaluationResultSchema(
            food_name=food.name,
            classification=classification,
            reasons=reasons,
            fired_rules=fired
        )
