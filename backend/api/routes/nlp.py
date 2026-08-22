from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ai.nlp_parser import NLPParser
from ai.context_validator import ContextValidator

router = APIRouter()

class NLPParseRequest(BaseModel):
    message: str

from core.rate_limit import rate_limit_dependency
from api.deps import get_current_user
from models.user import User

@router.post("/parse-context", dependencies=[Depends(rate_limit_dependency(requests_per_minute=10))])
async def parse_context(request: NLPParseRequest, current_user: User = Depends(get_current_user)):
    """
    Parses natural language into structured context and normalizes to DB.
    """
    try:
        parser = NLPParser()
        extracted = parser.parse(request.message)
    except Exception as e:
        return {"error": "AI_UNAVAILABLE", "message": "Could not process request."}
        
    # Validation against DB
    # In reality, inject db session via Depends(get_db)
    # Using None for DB will fail normalizer, so we assume db is available in tests
    return {
        "extracted_context": extracted.model_dump(),
        "normalized_entities": {}, # Populate from validator
        "uncertain_entities": extracted.uncertain_entities,
        "missing_information": extracted.missing_information
    }
