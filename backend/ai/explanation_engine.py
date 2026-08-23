import json
from google import genai
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class ExplanationResponse(BaseModel):
    explanation: str = Field(description="Natural language explanation of the deterministic result.")
    classification: str = Field(description="The classification that is being explained (must match the deterministic input exactly).")

class ExplanationEngine:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.system_prompt = """
You are the NutriGuard Explanation Engine. 
You will be given a strictly evaluated deterministic medical result for a food.
Your ONLY job is to explain this result in natural language to the user.

CRITICAL RULES:
1. You MUST NOT change the classification.
2. You MUST NOT add new warnings, interactions, or rules that are not present in the input.
3. You MUST NOT recommend medication changes.
4. You MUST NOT contradict the safety decisions.
5. If the food is blocked or limit, gently explain the reasons provided in the deterministic result.
"""

    def generate_explanation(self, deterministic_result: Dict[str, Any]) -> str:
        # Simple extraction of what needs to be explained
        food_name = deterministic_result.get("food_name", "the food")
        classification = deterministic_result.get("classification")
        
        prompt = f"""
Please explain the following deterministic result for {food_name}:
{json.dumps(deterministic_result, indent=2, default=str)}
"""
        try:
            interaction = self.client.interactions.create(
                model="gemini-3.7-flash",
                system_instruction=self.system_prompt,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ExplanationResponse.model_json_schema()
                }
            )
            resp = ExplanationResponse.model_validate_json(interaction.output_text)
            
            # Post-generation validation
            if resp.classification != classification:
                # Validation failed: discard LLM explanation
                return f"Deterministic classification: {classification}. (AI explanation discarded due to mismatch)."
            
            return resp.explanation
        except Exception:
            return f"Deterministic classification: {classification}. (Explanation generation failed)."

import json
from api.schemas.meal_schemas import DayPlanResponse

async def explain_meal_plan(plan: DayPlanResponse) -> str:
    llm_context = {
        "profile_summary": plan.profile_summary,
        "meals": {
            meal_type: {
                "foods": [
                    f"{f.serving_description} {f.food_name}"
                    for f in meal.foods
                ],
                "rationale": meal.rationale
            }
            for meal_type, meal in plan.meals.items()
        },
        "medication_timing": [
            {
                "medication": t.medication_name,
                "instruction": t.instruction,
                "warnings": t.warnings
            }
            for t in plan.medication_timing
        ],
        "gaps": {
            "deficient": plan.nutrient_gaps.deficient,
            "suggestions": [
                s.note for s in plan.nutrient_gaps.suggestions
            ],
            "depletion_notes": plan.nutrient_gaps.medication_depletion_notes
        },
        "calculation_notes": plan.calculation_notes,
        "safety_notes": plan.safety_notes,
    }

    try:
        # mocked response
        return "\n".join(plan.calculation_notes)
    except Exception as e:
        return "\n".join(plan.calculation_notes)
