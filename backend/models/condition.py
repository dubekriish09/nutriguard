from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class Condition(Base):
    __tablename__ = 'conditions'
    
    condition_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    aliases = Column(JSON)
    icd10_code = Column(String)
    category = Column(String)
    description = Column(String)
    
    key_nutrients = Column(JSON, default=list)
    relevant_parameters = Column(JSON, default=list)
    
    evidence_level = Column(String)
    source_id = Column(UUID(as_uuid=True))
    last_review_date = Column(Date)
    reviewer = Column(String)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class ConditionNutritionRule(Base):
    __tablename__ = 'condition_nutrition_rules'
    
    cn_rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condition_id = Column(UUID(as_uuid=True), ForeignKey('conditions.condition_id'), nullable=False)
    nutrient_id = Column(UUID(as_uuid=True), ForeignKey('nutrients.nutrient_id'))
    food_category = Column(String)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'))
    
    action = Column(String, nullable=False)
    priority = Column(Integer, default=5, nullable=False)
    threshold_amount = Column(Numeric)
    threshold_unit = Column(String)
    
    is_conditional = Column(Boolean, default=False)
    condition_parameter = Column(String)
    condition_operator = Column(String)
    condition_value = Column(String)
    
    rationale = Column(String, nullable=False)
    evidence_id = Column(UUID(as_uuid=True))
    evidence_level = Column(String)
    source_id = Column(UUID(as_uuid=True))
    
    rule_version = Column(Integer, default=1, nullable=False)
    rule_status = Column(String)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
