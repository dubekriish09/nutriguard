from typing import Dict, Any, List, Optional
from models.food import Food

class FoodNormalizationResult:
    def __init__(self, food_id: str, name: str, status: str, original_raw: str):
        self.food_id = food_id
        self.name = name
        self.status = status # 'VALID', 'UNKNOWN', 'AMBIGUOUS'
        self.original_raw = original_raw

class FoodNormalizer:
    def __init__(self, db_session):
        self.db = db_session

    def normalize(self, raw_food: str) -> FoodNormalizationResult:
        raw = raw_food.lower().strip()
        raw_singular = raw[:-1] if raw.endswith('s') else raw
        
        # Exact/ilike match on name
        f1 = self.db.query(Food).filter(Food.name.ilike(f"%{raw_singular}%")).all()
        
        if len(f1) == 1:
            return FoodNormalizationResult(str(f1[0].food_id), f1[0].name, 'VALID', raw_food)
        elif len(f1) > 1:
            # Check if there's an exact match despite multiple fuzzy matches
            exacts = [f for f in f1 if f.name.lower() == raw_singular or f.name.lower() == raw]
            if len(exacts) == 1:
                return FoodNormalizationResult(str(exacts[0].food_id), exacts[0].name, 'VALID', raw_food)
            return FoodNormalizationResult(None, raw_food, 'AMBIGUOUS', raw_food)
            
        # Check aliases
        all_foods = self.db.query(Food).all()
        matched = []
        for fd in all_foods:
            aliases = [a.lower() for a in (fd.aliases or [])]
            if raw in aliases or raw_singular in aliases:
                matched.append(fd)
                
        if len(matched) == 1:
            return FoodNormalizationResult(str(matched[0].food_id), matched[0].name, 'VALID', raw_food)
        elif len(matched) > 1:
            return FoodNormalizationResult(None, raw_food, 'AMBIGUOUS', raw_food)
            
        return FoodNormalizationResult(None, raw_food, 'UNKNOWN', raw_food)
