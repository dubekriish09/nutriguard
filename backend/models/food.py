from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base
import uuid

class Allergen(Base):
    __tablename__ = 'allergies'
    
    allergen_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    aliases = Column(JSON)
    allergen_family = Column(String)
    cross_reactive_with = Column(JSON)
    description = Column(String)
    evidence_id = Column(UUID(as_uuid=True)) # references evidence

class Food(Base):
    __tablename__ = 'foods'
    
    food_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    aliases = Column(JSON)
    category = Column(String, nullable=False)
    subcategory = Column(String)
    cuisine_origin = Column(JSON)
    description = Column(String)
    preparation_notes = Column(String)
    is_raw = Column(Boolean, default=True)
    cooking_methods = Column(JSON)
    
    is_vegetarian = Column(Boolean, default=True)
    is_vegan = Column(Boolean, default=False)
    is_jain = Column(Boolean, default=False)
    is_gluten_free = Column(Boolean)
    is_lactose_free = Column(Boolean)
    
    glycemic_index = Column(Integer, nullable=True)
    purine_level = Column(String, nullable=True)
    vitamin_k_mcg = Column(Numeric, nullable=True)
    nutrient_source = Column(String, nullable=True)
    
    source_id = Column(UUID(as_uuid=True)) # references data_sources
    source_food_id = Column(String)
    evidence_level = Column(String)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class FoodAllergen(Base):
    __tablename__ = 'food_allergens'
    
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'), primary_key=True)
    allergen_id = Column(UUID(as_uuid=True), ForeignKey('allergies.allergen_id'), primary_key=True)
    is_primary = Column(Boolean, default=True)
    is_trace = Column(Boolean, default=False)

class Nutrient(Base):
    __tablename__ = 'nutrients'
    
    nutrient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    unit = Column(String, nullable=False)
    category = Column(String)
    aliases = Column(JSON)
    description = Column(String)

class FoodNutrition(Base):
    __tablename__ = 'food_nutrition'
    
    food_nutrition_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'), nullable=False)
    nutrient_id = Column(UUID(as_uuid=True), ForeignKey('nutrients.nutrient_id'), nullable=False)
    amount = Column(Numeric, nullable=False)
    unit = Column(String, nullable=False)
    per_quantity = Column(Numeric, default=100)
    per_unit = Column(String, default='g')
    preparation_state = Column(String, default='raw')
    confidence = Column(String)
    source_id = Column(UUID(as_uuid=True))

class FoodServingSize(Base):
    __tablename__ = 'food_serving_sizes'
    
    serving_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'), nullable=False)
    description = Column(String, nullable=False)
    amount_g = Column(Numeric, nullable=False)
    is_default = Column(Boolean, default=False)
