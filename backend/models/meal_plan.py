import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    plan_date = Column(Date, nullable=False, default=date.today)
    plan_type = Column(String, default="single_day")
    is_ai_generated = Column(Boolean, default=False)
    safety_validated = Column(Boolean, default=False)
    targets_snapshot = Column(JSON)    # NutrientTargets at generation time
    gap_report = Column(JSON)          # NutrientGapReport
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship("MealPlanMeal", back_populates="plan", cascade="all, delete-orphan")
    user = relationship("User", back_populates="meal_plans")

class MealPlanMeal(Base):
    __tablename__ = "meal_plan_meals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    meal_type = Column(String, nullable=False)
    day_number = Column(Integer, default=1)
    foods = Column(JSON, nullable=False)
    total_nutrition = Column(JSON)
    rationale = Column(JSON)

    plan = relationship("MealPlan", back_populates="meals")
