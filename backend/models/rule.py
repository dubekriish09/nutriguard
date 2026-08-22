from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class Rule(Base):
    __tablename__ = 'rules'
    
    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code = Column(String, unique=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    parent_rule_id = Column(UUID(as_uuid=True), ForeignKey('rules.rule_id'))
    
    name = Column(String, nullable=False)
    description = Column(String)
    
    trigger_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    
    priority = Column(Integer, nullable=False)
    severity = Column(String)
    rationale = Column(String, nullable=False)
    
    evidence_id = Column(UUID(as_uuid=True))
    evidence_level = Column(String)
    source_id = Column(UUID(as_uuid=True))
    
    status = Column(String, default='DRAFT', nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    
    effective_from = Column(DateTime(timezone=True))
    effective_until = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    deprecated_at = Column(DateTime(timezone=True))
    deprecation_reason = Column(String)

class RuleTrigger(Base):
    __tablename__ = 'rule_triggers'
    
    trigger_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('rules.rule_id'), nullable=False)
    trigger_group = Column(Integer, default=1, nullable=False)
    trigger_seq = Column(Integer, default=1, nullable=False)
    
    trigger_on = Column(String, nullable=False)
    condition_id = Column(UUID(as_uuid=True), ForeignKey('conditions.condition_id'))
    medication_id = Column(UUID(as_uuid=True), ForeignKey('medications.medication_id'))
    drug_class = Column(String)
    allergen_id = Column(UUID(as_uuid=True), ForeignKey('allergies.allergen_id'))
    dietary_pattern = Column(String)
    parameter_name = Column(String)
    parameter_operator = Column(String)
    parameter_value = Column(String)
    is_negation = Column(Boolean, default=False)

class RuleTarget(Base):
    __tablename__ = 'rule_targets'
    
    target_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('rules.rule_id'), nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'))
    nutrient_id = Column(UUID(as_uuid=True), ForeignKey('nutrients.nutrient_id'))
    food_category = Column(String)
    food_component = Column(String)
    
    quantity_modifier = Column(String)
    threshold_amount = Column(Numeric)
    threshold_unit = Column(String)
    additional_context = Column(JSON, default=dict)

class RuleEvaluation(Base):
    __tablename__ = 'rule_evaluations'
    
    eval_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('rules.rule_id'), nullable=False)
    rule_version = Column(Integer, nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'))
    fired = Column(Boolean, nullable=False)
    action_taken = Column(String)
    context_snapshot = Column(JSON)
    evaluated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
