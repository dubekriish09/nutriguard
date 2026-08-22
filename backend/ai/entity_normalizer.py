from typing import Dict, Any, List, Optional
from models.condition import Condition
from models.medication import Medication
from models.food import Allergen
from .nlp_parser import ExtractedContext, ExtractedCondition, ExtractedMedication, ExtractedAllergy

class NormalizationResult:
    def __init__(self, entity_id: str, name: str, status: str, original_raw: str):
        self.entity_id = entity_id
        self.name = name
        self.status = status # 'VALID', 'UNKNOWN', 'AMBIGUOUS'
        self.original_raw = original_raw

class EntityNormalizer:
    def __init__(self, db_session):
        self.db = db_session

    def normalize_condition(self, ext_cond: ExtractedCondition) -> NormalizationResult:
        raw = ext_cond.raw_name.lower().strip()
        
        # Exact/ilike match on name
        cond = self.db.query(Condition).filter(Condition.name.ilike(f"%{raw}%")).first()
        if cond:
            return NormalizationResult(str(cond.condition_id), cond.name, 'VALID', ext_cond.raw_name)
            
        # Check aliases
        all_conds = self.db.query(Condition).all()
        for c in all_conds:
            aliases = [a.lower() for a in (c.aliases or [])]
            if raw in aliases:
                return NormalizationResult(str(c.condition_id), c.name, 'VALID', ext_cond.raw_name)
                
        # Heuristics for ambiguity (like "sugar" -> diabetes) should ideally be in DB aliases.
        # If the user says "BP", we map to Hypertension if "BP" is in aliases (it is, as 'High blood pressure', 'HTN')
        if "bp" in raw.split() or "blood pressure" in raw:
            c = self.db.query(Condition).filter(Condition.name.ilike("%Hypertension%")).first()
            if c:
                return NormalizationResult(str(c.condition_id), c.name, 'VALID', ext_cond.raw_name)
                
        if "sugar" in raw or "diabetes" in raw:
            c = self.db.query(Condition).filter(Condition.name.ilike("%Diabetes%")).first()
            if c:
                return NormalizationResult(str(c.condition_id), c.name, 'VALID', ext_cond.raw_name)
                
        return NormalizationResult(None, ext_cond.raw_name, 'AMBIGUOUS', ext_cond.raw_name)

    def normalize_medication(self, ext_med: ExtractedMedication) -> NormalizationResult:
        raw = ext_med.raw_name.lower().strip()
        
        # Ambiguous check first
        if "medicine" in raw or "pill" in raw or "tablet" in raw:
            return NormalizationResult(None, ext_med.raw_name, 'AMBIGUOUS', ext_med.raw_name)
            
        med = self.db.query(Medication).filter(Medication.generic_name.ilike(f"%{raw}%")).first()
        if med:
            return NormalizationResult(str(med.medication_id), med.generic_name, 'VALID', ext_med.raw_name)
            
        all_meds = self.db.query(Medication).all()
        for m in all_meds:
            brands = [b.lower() for b in (m.brand_names or [])]
            if raw in brands:
                return NormalizationResult(str(m.medication_id), m.generic_name, 'VALID', ext_med.raw_name)
                
        return NormalizationResult(None, ext_med.raw_name, 'UNKNOWN', ext_med.raw_name)

    def normalize_allergen(self, ext_alg: ExtractedAllergy) -> NormalizationResult:
        raw = ext_alg.raw_name.lower().strip()
        raw_singular = raw[:-1] if raw.endswith('s') else raw
        alg = self.db.query(Allergen).filter(Allergen.name.ilike(f"%{raw_singular}%")).first()
        if alg:
            return NormalizationResult(str(alg.allergen_id), alg.name, 'VALID', ext_alg.raw_name)
            
        all_algs = self.db.query(Allergen).all()
        for a in all_algs:
            aliases = [al.lower() for al in (a.aliases or [])]
            if raw in aliases:
                return NormalizationResult(str(a.allergen_id), a.name, 'VALID', ext_alg.raw_name)
                
        return NormalizationResult(None, ext_alg.raw_name, 'UNKNOWN', ext_alg.raw_name)
