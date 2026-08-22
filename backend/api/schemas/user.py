from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class UserProfileBase(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120)
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    dietary_pattern: Optional[str] = None
    nutritional_goals: List[str] = []
    cuisine_preferences: List[str] = []
    food_preferences: List[Dict[str, Any]] = []
    cooking_time_max_minutes: Optional[int] = None
    budget_level: Optional[str] = None
    lifestyle_notes: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    profile_id: UUID
    user_id: UUID
    version: int
    is_current: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserConditionBase(BaseModel):
    condition_id: UUID
    diagnosed: bool = True
    severity: Optional[str] = None
    disease_stage: Optional[str] = None
    lab_values: Dict[str, Any] = {}
    treatment_status: Optional[str] = None
    notes: Optional[str] = None

class UserConditionCreate(UserConditionBase):
    pass

class UserMedicationBase(BaseModel):
    medication_id: UUID
    dose_amount: Optional[float] = None
    dose_unit: Optional[str] = None
    frequency: Optional[str] = None
    timing_instructions: Optional[str] = None
    timing_relative_to_meal: Optional[str] = None
    notes: Optional[str] = None

class UserMedicationCreate(UserMedicationBase):
    pass

class UserContext(BaseModel):
    user_id: UUID
    profile: UserProfileBase
    conditions: List[UserConditionBase] = []
    medications: List[UserMedicationBase] = []
    allergies: List[str] = [] # list of allergen strings or IDs
