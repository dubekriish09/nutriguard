from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import JSON
from sqlalchemy.sql import func
from .base import Base
import uuid

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String)
    role = Column(String, default='USER', nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    
    age = Column(Integer)
    sex = Column(String)
    height_cm = Column(Numeric(5, 1))
    weight_kg = Column(Numeric(5, 1))
    
    activity_level = Column(String)
    dietary_pattern = Column(String)
    
    nutritional_goals = Column(JSON, default=list)
    cuisine_preferences = Column(JSON, default=list)
    food_preferences = Column(JSON, default=list)
    
    cooking_time_max_minutes = Column(Integer)
    budget_level = Column(String)
    lifestyle_notes = Column(String)
    
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class UserCondition(Base):
    __tablename__ = 'user_conditions'
    
    user_condition_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    condition_id = Column(UUID(as_uuid=True), ForeignKey('conditions.condition_id'), nullable=False)
    diagnosed = Column(Boolean, default=True)
    severity = Column(String)
    disease_stage = Column(String)
    lab_values = Column(JSON, default=dict)
    treatment_status = Column(String)
    notes = Column(String)
    added_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class UserMedication(Base):
    __tablename__ = 'user_medications'
    
    user_medication_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    medication_id = Column(UUID(as_uuid=True), ForeignKey('medications.medication_id'), nullable=False)
    dose_amount = Column(Numeric)
    dose_unit = Column(String)
    frequency = Column(String)
    timing_instructions = Column(String)
    timing_relative_to_meal = Column(String)
    started_at = Column(DateTime(timezone=True))
    notes = Column(String)
    added_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

class UserAllergy(Base):
    __tablename__ = 'user_allergies'
    
    user_allergy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    allergen_id = Column(UUID(as_uuid=True), ForeignKey('allergies.allergen_id'))
    food_id = Column(UUID(as_uuid=True), ForeignKey('foods.food_id'))
    severity = Column(String)
    confirmed = Column(Boolean, default=False)
    notes = Column(String)
    added_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
