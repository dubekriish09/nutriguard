from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.food import Food, FoodAllergen

class AllergyResult(BaseModel):
    is_blocked: bool
    reason: Optional[str] = None
    matched_allergens: List[str] = []
    cross_reactive: List[str] = []
    is_trace: bool = False

class AllergyEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def check_allergies(self, user_allergies: List[str], food_id: UUID) -> AllergyResult:
        """
        Hard block if any user allergen matches any allergen
        associated with this food.
        Returns immediately on first match.
        """
        if not user_allergies:
            return AllergyResult(is_blocked=False, reason=None)

        # Get all allergens associated with this food
        food_allergen_rows = self.db.query(FoodAllergen).filter(
            FoodAllergen.food_id == food_id
        ).all()

        if not food_allergen_rows:
            return AllergyResult(is_blocked=False, reason=None)

        # Normalize food allergen names
        food_allergen_names = set()
        for row in food_allergen_rows:
            if row.allergen:
                food_allergen_names.add(
                    row.allergen.name.lower().replace(' ', '_')
                )

        # Normalize user allergy names
        user_allergen_names = set(
            a.lower().replace(' ', '_') for a in user_allergies
        )

        # Check for intersection
        matched = food_allergen_names.intersection(user_allergen_names)
        if matched:
            return AllergyResult(
                is_blocked=True,
                reason=f"Allergen match: {', '.join(matched)}",
                matched_allergens=list(matched)
            )

        return AllergyResult(is_blocked=False, reason=None)
