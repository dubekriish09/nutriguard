from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from uuid import UUID

from ai.food_parser import FoodParser
from ai.food_normalizer import FoodNormalizer
from ai.explanation_engine import ExplanationEngine
from services.recommendation_service import RecommendationService
from models.food import Food

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    user_context: Dict[str, Any] # Passed from frontend/validated previously

from core.rate_limit import rate_limit_dependency
from api.deps import get_current_user, get_db
from models.user import User
from sqlalchemy.orm import Session

@router.post("/food", dependencies=[Depends(rate_limit_dependency(requests_per_minute=10))])
async def chat_food(request: ChatRequest, db_session: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        try:
            parser = FoodParser()
            intent_res = parser.parse(request.message)
        except Exception as e:
            return {"clarification_required": True, "question": "I'm currently unable to process language (AI_UNAVAILABLE). Please try again later."}
        
        # 2. Check for clarification
        if intent_res.uncertain_entities:
            return {
                "clarification_required": True,
                "question": f"Which food are you referring to by '{intent_res.uncertain_entities[0]}'?"
            }
            
        normalizer = FoodNormalizer(db_session)
        service = RecommendationService(db_session)
        explainer = ExplanationEngine()
        
        # 3. Handle intents
        if intent_res.intent == "food_evaluation":
            if not intent_res.foods:
                return {"clarification_required": True, "question": "Which food do you want to evaluate?"}
                
            norm = normalizer.normalize(intent_res.foods[0])
            if norm.status != 'VALID':
                return {"clarification_required": True, "question": f"Could you clarify which food you mean by '{norm.original_raw}'?"}
                
            # Deterministic Evaluation
            det_result = await service.generate_recommendations(request.user_context, [UUID(norm.food_id)])
            res = det_result['foods'][0]
            res['food_name'] = norm.name
            
            try:
                explanation = explainer.generate_explanation(res)
            except Exception:
                explanation = "The recommendation is based on your medication and the applicable safety rules. (AI explanation unavailable)"
            
            return {
                "intent": "food_evaluation",
                "deterministic_result": res,
                "explanation": explanation,
                "clarification_required": False
            }
            
        elif intent_res.intent == "food_list":
            cat = intent_res.requested_category
            if not cat:
                return {"clarification_required": True, "question": "Which category of food are you looking for?"}
                
            # 1. Query the Food database
            foods = db_session.query(Food).filter(Food.category.ilike(f"%{cat}%")).all()
            if not foods:
                return {"intent": "food_list", "deterministic_result": {"category": cat, "foods": []}, "clarification_required": False}
                
            # 3. Evaluate each food through the deterministic engine
            food_ids = [f.food_id for f in foods]
            det_results = await service.generate_recommendations(request.user_context, food_ids)
            
            # 4. Remove VETO/BLOCKED foods. 5. Rank
            approved = []
            for r in det_results['foods']:
                if r['classification'] not in ('blocked_allergy', 'blocked_interaction', 'avoid', 'limit', 'use_cautiously'):
                    approved.append(r)
                    
            approved.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return {
                "intent": "food_list",
                "deterministic_result": {
                    "category": cat,
                    "foods": approved
                },
                "explanation": f"Here are the recommended {cat}s based on your profile.",
                "clarification_required": False
            }
            
        elif intent_res.intent == "food_restrictions":
            # "What foods should I limit?"
            # We would normally evaluate a large list of standard foods.
            # For MVP, evaluate all seeded foods and return LIMIT/CAUTION/AVOID
            all_foods = db_session.query(Food).all()
            food_ids = [f.food_id for f in all_foods]
            det_results = await service.generate_recommendations(request.user_context, food_ids)
            
            restricted = [r for r in det_results['foods'] if r['classification'] in ('blocked_allergy', 'blocked_interaction', 'avoid', 'limit', 'use_cautiously')]
            
            return {
                "intent": "food_restrictions",
                "deterministic_result": {"foods": restricted},
                "explanation": "These are the foods you should limit or avoid.",
                "clarification_required": False
            }
            
        elif intent_res.intent == "food_alternatives":
            if not intent_res.foods:
                return {"clarification_required": True, "question": "What food do you want alternatives for?"}
                
            norm = normalizer.normalize(intent_res.foods[0])
            if norm.status != 'VALID':
                return {"clarification_required": True, "question": f"Could you clarify the food '{norm.original_raw}'?"}
                
            # Identify alternatives by category
            target_food = db_session.query(Food).filter(Food.food_id == UUID(norm.food_id)).first()
            alts = db_session.query(Food).filter(Food.category == target_food.category, Food.food_id != target_food.food_id).all()
            
            alt_ids = [f.food_id for f in alts]
            if alt_ids:
                det_results = await service.generate_recommendations(request.user_context, alt_ids)
                approved = [r for r in det_results['foods'] if r['classification'] not in ('blocked_allergy', 'blocked_interaction', 'avoid')]
                approved.sort(key=lambda x: x.get('score', 0), reverse=True)
            else:
                approved = []
                
            return {
                "intent": "food_alternatives",
                "deterministic_result": {"alternatives": approved},
                "explanation": f"Here are safe alternatives to {norm.name}.",
                "clarification_required": False
            }
            
        return {"clarification_required": True, "question": "I'm not sure how to handle that request."}
    except Exception:
        return {"clarification_required": True, "question": "An unexpected error occurred. Please try again."}
