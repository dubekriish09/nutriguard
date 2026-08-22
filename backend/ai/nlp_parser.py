import os
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from google import genai

class ExtractedMedication(BaseModel):
    raw_name: str = Field(description="The exact name of the medication as stated by the user.")
    dose: Optional[str] = Field(description="The numeric dose amount if stated.")
    unit: Optional[str] = Field(description="The unit of the dose (e.g., mg, mcg) if stated.")
    frequency: Optional[str] = Field(description="How often the medication is taken.")
    timing: Optional[str] = Field(description="When the medication is taken (e.g., morning, with food).")
    confidence: float = Field(description="Confidence that this is a medication entity (0.0 to 1.0).")

class ExtractedCondition(BaseModel):
    raw_name: str = Field(description="The exact condition name stated by the user.")
    confidence: float = Field(description="Confidence that this is a condition entity (0.0 to 1.0).")

class ExtractedAllergy(BaseModel):
    raw_name: str = Field(description="The exact allergen name stated by the user.")
    confidence: float = Field(description="Confidence that this is an allergy entity (0.0 to 1.0).")

class ExtractedDemographics(BaseModel):
    age: Optional[int] = Field(description="Age of the user if stated.")
    sex: Optional[str] = Field(description="Sex of the user if stated.")
    lifestyle_notes: Optional[str] = Field(description="Relevant lifestyle information.")

class ExtractedContext(BaseModel):
    conditions: List[ExtractedCondition] = Field(default_factory=list)
    medications: List[ExtractedMedication] = Field(default_factory=list)
    allergies: List[ExtractedAllergy] = Field(default_factory=list)
    dietary_preferences: List[str] = Field(default_factory=list)
    food_preferences: List[str] = Field(default_factory=list)
    demographics: Optional[ExtractedDemographics] = None
    uncertain_entities: List[str] = Field(default_factory=list, description="Ambiguous medical terms like 'BP medicine'.")
    missing_information: List[str] = Field(default_factory=list, description="Missing details from stated entities.")

class NLPParser:
    def __init__(self, api_key: str = None):
        # Allow passing key or relying on GEMINI_API_KEY env var
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()
            
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, 'prompts', 'context_extraction.txt'), 'r') as f:
            self.system_prompt = f.read()

    def parse(self, text: str) -> ExtractedContext:
        """
        Parses unstructured text into structured ExtractedContext using Gemini.
        """
        interaction = self.client.interactions.create(
            model="gemini-3.7-flash",
            system_instruction=self.system_prompt,
            input=text,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ExtractedContext.model_json_schema()
            }
        )
        
        return ExtractedContext.model_validate_json(interaction.output_text)
