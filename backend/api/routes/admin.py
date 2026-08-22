from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.deps import get_db, get_current_clinical_reviewer, get_current_admin
from models.user import User
from services.recommendation_service import RecommendationService
from models.rule import Rule
from models.evidence import Evidence, DataSource
from models.condition import Condition
from models.food import Food

router = APIRouter()

class SimulationRequest(BaseModel):
    user_context: Dict[str, Any]
    food_id: str

@router.post("/rules/simulate")
async def simulate_rules(
    request: SimulationRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_clinical_reviewer)
):
    try:
        food_uuid = UUID(request.food_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid food_id UUID format")
        
    service = RecommendationService(db)
    det_results = await service.generate_recommendations(request.user_context, [food_uuid])
    
    if not det_results or not det_results.get('foods'):
        raise HTTPException(status_code=404, detail="Food not found or evaluation failed")
        
    res = det_results['foods'][0]
    
    trace = {
        "food": res.get("food_name", request.food_id),
        "safety": {"status": "FAIL" if res.get("classification") in ["blocked_allergy", "blocked_interaction", "avoid"] else "PASS"},
        "allergy": {"status": "FAIL" if res.get("classification") == "blocked_allergy" else "PASS"},
        "interactions": [r for r in res.get("fired_rules", []) if "interaction" in str(r).lower()],
        "rules_evaluated": ["(All active rules)"],
        "rules_triggered": res.get("fired_rules", []),
        "scores": {"final_score": res.get("score", 0)},
        "final_classification": res.get("classification"),
        "rule_versions": ["v1"],
        "evidence": ["EVIDENCE_PLACEHOLDER"]
    }
    
    return trace

@router.get("/rules")
def list_rules(db: Session = Depends(get_db), current_user: User = Depends(get_current_clinical_reviewer)):
    rules = db.query(Rule).all()
    return rules

@router.post("/rules/{rule_id}/approve")
def approve_rule(rule_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_clinical_reviewer)):
    rule = db.query(Rule).filter(Rule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.status = "APPROVED"
    rule.approved_by_user_id = current_user.user_id
    
    from models.audit import AuditLog
    import uuid
    log = AuditLog(
        actor_user_id=current_user.user_id,
        action="RULE_APPROVED",
        entity_type="Rule",
        entity_id=str(rule.rule_id),
        entity_version=rule.version,
        request_id=str(uuid.uuid4())
    )
    db.add(log)
    db.commit()
    return {"status": "success", "rule_id": rule_id}
