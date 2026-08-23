import re

MEAL_PLAN_INTENTS = [
    "meal plan", "diet plan", "what should i eat",
    "what to eat today", "plan my meals", "plan my diet",
    "what can i eat", "give me a plan", "suggest meals",
    "breakfast lunch dinner", "full day diet",
    "daily meal", "weekly plan",
]

MEAL_PLAN_REGEX = re.compile(
    r'\b(meal plan|diet plan|what (should|can) i eat|'
    r'plan my (meals|diet)|daily (meal|diet)|'
    r'breakfast.*lunch|what to eat)\b',
    re.IGNORECASE
)

def extract_intent(user_message: str) -> str:
    msg = user_message.lower().strip()
    if any(phrase in msg for phrase in MEAL_PLAN_INTENTS):
        return "meal_plan"
    return "food_evaluation"

def extract_intent_fallback(user_message: str) -> str:
    if MEAL_PLAN_REGEX.search(user_message):
        return "meal_plan"
    return "food_evaluation"
import os
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from google import genai

class FoodQueryIntent(BaseModel):
    intent: Literal["food_evaluation", "food_list", "food_alternatives", "food_restrictions", "food_information", "unknown"] = Field(
        description="The intention of the user's food query."
    )
    foods: List[str] = Field(
        default_factory=list, 
        description="Specific raw food names mentioned (e.g., 'spinach', 'peanut')."
    )
    requested_category: Optional[str] = Field(
        description="A broad category requested, e.g., 'vegetable', 'fruit', 'snack'."
    )
    requested_action: Optional[str] = Field(
        description="The action requested, e.g., 'eat', 'avoid'."
    )
    comparison_food: Optional[str] = Field(
        description="If asking for an alternative, the food they want an alternative to."
    )
    uncertain_entities: List[str] = Field(
        default_factory=list, 
        description="Any ambiguous references, like 'it', 'that', or unclear foods."
    )

class FoodParser:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.system_prompt = """
You are a specialized food intent parser for NutriGuard. 
Your job is to strictly extract the intent and entities from a user's food query.
Do NOT make medical decisions. Do NOT infer whether a food is safe.
If the user asks "Can I eat it?", extract 'it' as an uncertain entity.
"""

    def parse(self, text: str) -> FoodQueryIntent:
        interaction = self.client.interactions.create(
            model="gemini-3.7-flash",
            system_instruction=self.system_prompt,
            input=text,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": FoodQueryIntent.model_json_schema()
            }
        )
        return FoodQueryIntent.model_validate_json(interaction.output_text)
