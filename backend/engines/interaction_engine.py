from api.schemas.engine_schemas import UserProfileSchema, FoodSchema
from typing import Dict, Any, List

class InteractionEngine:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate(self, user_context: UserProfileSchema, food: FoodSchema) -> Dict[str, Any]:
        interactions = []
        max_severity = 'none'

        severity_rank = {'none': 0, 'low': 1, 'moderate': 2, 'major': 3, 'critical': 4, 'high': 4}

        for med in user_context.medications:
            for interaction in med.food_interactions:
                if interaction.interacting_food_category in food.dietary_tags:
                    sev = interaction.severity.lower()
                    interactions.append({
                        'medication': med.name,
                        'mechanism': interaction.description,
                        'severity': sev,
                        'recommendation': interaction.description
                    })
                    if severity_rank.get(sev, 0) > severity_rank.get(max_severity, 0):
                        max_severity = sev

        return {
            'interactions': interactions,
            'max_severity': max_severity
        }
