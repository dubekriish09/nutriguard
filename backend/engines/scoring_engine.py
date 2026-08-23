from api.schemas.engine_schemas import UserProfileSchema, FoodSchema

class ScoringEngine:
    def __init__(self, db_session):
        self.db = db_session

    def score_food(self, user_context: UserProfileSchema, food: FoodSchema, rule_result, interaction_result) -> int:
        score = 50 # baseline
        
        # Deduct for condition rules
        score -= len(rule_result.fired_rules) * 10
        
        # Deduct for interactions
        sev_penalties = {'low': 5, 'moderate': 15, 'major': 30, 'critical': 50, 'high': 50}
        for inter in interaction_result.get('interactions', []):
            score -= sev_penalties.get(inter.get('severity', 'none'), 0)
            
        # Add for benefits
        beneficial = False
        for med in user_context.medications:
            for nutrient in med.depletes_nutrients:
                if food.nutrients.get(nutrient, 0) > 0:
                    score += 15
                    beneficial = True
        
        for cond in user_context.conditions:
            for nutrient in cond.encourage_nutrients:
                if food.nutrients.get(nutrient, 0) > 0:
                    score += 15
                    beneficial = True
                    
        # Preference
        if food.name.lower() in [d.lower() for d in user_context.food_dislikes]:
            score -= 40
            
        return max(0, min(100, score))
