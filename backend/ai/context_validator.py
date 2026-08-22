from typing import Dict, Any, List
from .nlp_parser import ExtractedContext
from .entity_normalizer import EntityNormalizer

class ContextValidator:
    def __init__(self, db_session):
        self.db = db_session
        self.normalizer = EntityNormalizer(db_session)

    def validate(self, extracted: ExtractedContext) -> Dict[str, Any]:
        """
        Validates the extracted context against the database and builds the UserContext.
        Returns the UserContext and any clarifications needed.
        """
        user_context = {
            "conditions": [],
            "medications": [],
            "allergies": [],
            "dietary_preferences": extracted.dietary_preferences,
            "food_preferences": extracted.food_preferences
        }
        
        clarifications = []
        normalized_entities = {
            "conditions": [],
            "medications": [],
            "allergies": []
        }
        
        # Conditions
        for cond in extracted.conditions:
            res = self.normalizer.normalize_condition(cond)
            if res.status == 'VALID':
                user_context["conditions"].append({
                    "condition_id": res.entity_id,
                    "name": res.name,
                    "parameters": {}
                })
                normalized_entities["conditions"].append(res.__dict__)
            else:
                clarifications.append(f"Could you clarify what condition you mean by '{res.original_raw}'?")
                
        # Medications
        for med in extracted.medications:
            res = self.normalizer.normalize_medication(med)
            if res.status == 'VALID':
                user_context["medications"].append({
                    "medication_id": res.entity_id,
                    "generic_name": res.name,
                    "dose": med.dose,
                    "unit": med.unit,
                    "frequency": med.frequency
                })
                normalized_entities["medications"].append(res.__dict__)
            else:
                clarifications.append(f"Could you clarify the medication name for '{res.original_raw}'?")
                
        # Allergies
        for alg in extracted.allergies:
            res = self.normalizer.normalize_allergen(alg)
            if res.status == 'VALID':
                # Map to standard string name for the current mock MVP engines
                user_context["allergies"].append(res.name)
                normalized_entities["allergies"].append(res.__dict__)
            else:
                clarifications.append(f"We don't recognize the allergen '{res.original_raw}'. Could you provide another name?")
                
        # Check uncertain entities and missing info from LLM
        for unc in extracted.uncertain_entities:
            clarifications.append(f"Could you provide more details about '{unc}'?")
            
        return {
            "status": "needs_clarification" if clarifications else "validated",
            "user_context": user_context,
            "normalized_entities": normalized_entities,
            "questions": clarifications
        }
