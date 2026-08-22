from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from engines.safety_engine import SafetyEngine
from engines.rule_engine import RuleEngine
# In a real app we would depend on get_db
# from core.database import get_db

from api.deps import get_current_user
from models.user import User

router = APIRouter()

@router.post("/evaluate/{food_id}")
async def evaluate_food(food_id: UUID, user_context: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """
    Evaluates a specific food against the user's context.
    """
    # Initialize engines (in production these might be injected or initialized with a DB session)
    safety_engine = SafetyEngine(db_session=None)
    rule_engine = RuleEngine(db_session=None)
    
    # STEP 1: Safety pre-check (hard blocks applied immediately)
    safety_pre = safety_engine.evaluate(user_context.dict(), food_id)
    if not safety_pre.is_safe_to_evaluate:
        return {
            "food_id": food_id,
            "classification": "blocked_allergy" if safety_pre.veto_priority == 1 else "blocked_interaction",
            "reason": safety_pre.veto_reason,
            "requires_professional_review": safety_pre.requires_professional_review,
            "fired_rules": safety_pre.rule_ids_fired
        }
        
    # STEP 2: Rule engine
    rule_result = rule_engine.evaluate_food(user_context.dict(), food_id)
    
    # Steps 3 & 4 (Interaction & Scoring) would go here
    # ...
    
    # Step 5: Classify
    classification = rule_result.classification
    
    # Step 6 & 7 & 8 (Explainability & LLM & Safety post-validation)
    # Mocking explainability for MVP
    explanation = f"Evaluated safely. Based on your profile rules: {[r['rationale'] for r in rule_result.fired_rules]}"
    
    return {
        "food_id": food_id,
        "classification": classification,
        "explanation": explanation,
        "fired_rules": rule_result.fired_rules
    }
