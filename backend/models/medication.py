from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
import uuid

class Medication(Base):
    __tablename__ = 'medications'
    
    medication_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generic_name = Column(String, unique=True, nullable=False)
    brand_names = Column(JSON)
    drug_class = Column(String, nullable=False)
    drug_subclass = Column(String)
    indications = Column(JSON)
    dosage_forms = Column(JSON)
    route = Column(JSON)
    
    standard_timing = Column(String)
    timing_category = Column(String)
    half_life_hours = Column(Numeric)
    
    contraindications = Column(JSON)
    warnings = Column(JSON)
    black_box_warning = Column(String)
    
    source_id = Column(UUID(as_uuid=True))
    regulatory_label_date = Column(Date)
    evidence_level = Column(String)
    source_version = Column(String)
    last_review_date = Column(Date)
    reviewer = Column(String)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    depletions = relationship("DrugNutrientDepletion", back_populates="medication", lazy="joined")

class DrugFoodInteraction(Base):
    __tablename__ = 'drug_food_interactions'
    
    interaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey('medications.medication_id'), nullable=False)
    
    interaction_type = Column(String, nullable=False)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'))
    nutrient_id = Column(UUID(as_uuid=True), ForeignKey('nutrients.nutrient_id'))
    food_category = Column(String)
    food_component = Column(String)
    
    severity = Column(String, nullable=False)
    direction = Column(String)
    mechanism = Column(String, nullable=False)
    effect = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    timing_window = Column(String)
    quantity_threshold = Column(String)
    
    is_conditional = Column(Boolean, default=False)
    condition_id = Column(UUID(as_uuid=True))
    condition_parameter = Column(String)
    
    evidence_id = Column(UUID(as_uuid=True))
    evidence_level = Column(String)
    source_id = Column(UUID(as_uuid=True))
    last_review_date = Column(Date)
    reviewer = Column(String)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class DrugNutrientDepletion(Base):
    __tablename__ = 'drug_nutrient_depletions'
    
    depletion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medication_id = Column(UUID(as_uuid=True), ForeignKey('medications.medication_id'), nullable=False)
    nutrient_id = Column(UUID(as_uuid=True), ForeignKey('nutrients.nutrient_id'), nullable=False)
    severity = Column(String)
    mechanism = Column(String)
    clinical_significance = Column(String)
    recommendation = Column(String)
    
    evidence_id = Column(UUID(as_uuid=True))
    evidence_level = Column(String)
    source_id = Column(UUID(as_uuid=True))
    last_review_date = Column(Date)

    medication = relationship("Medication", back_populates="depletions")
    nutrient = relationship("Nutrient", lazy="joined")
