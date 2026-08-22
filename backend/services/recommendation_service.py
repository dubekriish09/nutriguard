from typing import List
from uuid import UUID
from datetime import datetime

from engines.safety_engine import SafetyEngine
from engines.rule_engine import RuleEngine
from engines.interaction_engine import InteractionEngine
from engines.scoring_engine import ScoringEngine

class RecommendationService:
    def __init__(self, db_session):
        self.db = db_session
        self.safety_engine = SafetyEngine(db_session)
        self.rule_engine = RuleEngine(db_session)
        self.interaction_engine = InteractionEngine(db_session)
        self.scoring_engine = ScoringEngine(db_session)

    async def generate_recommendations(self, user_context: dict, food_ids: List[UUID]) -> dict:
        """
        Full pipeline. LLM never bypasses engines.
        """
        results = []
        for food_id in food_ids:
            # STEP 1: Safety pre-check (hard blocks applied immediately)
            safety_pre = self.safety_engine.evaluate(user_context, food_id)
            if not safety_pre.is_safe_to_evaluate:
                results.append({
                    "food_id": food_id,
                    "classification": "blocked_allergy" if safety_pre.veto_priority == 1 else "blocked_interaction",
                    "reason": safety_pre.veto_reason,
                    "requires_professional_review": safety_pre.requires_professional_review,
                    "fired_rules": safety_pre.rule_ids_fired
                })
                continue

            # STEP 2: Rule engine
            rule_result = self.rule_engine.evaluate_food(user_context, food_id)

            # STEP 3: Interaction engine
            interaction_result = self.interaction_engine.evaluate(user_context, food_id)

            # STEP 4: Scoring
            score = self.scoring_engine.score_food(user_context, food_id, rule_result, interaction_result)

            # STEP 5: Classify (using the rule result logic for now)
            classification = rule_result.classification
            
            # Additional classification override logic based on interaction severity
            if interaction_result.max_severity in ('critical', 'major'):
                classification = 'avoid'
            elif interaction_result.max_severity == 'moderate' and classification not in ('avoid', 'limit'):
                classification = 'use_cautiously'

            # STEP 6: Rule-based explanation (NO LLM)
            rule_explanation = f"Evaluated safely. Based on your profile rules: {[r['rationale'] for r in rule_result.fired_rules]}"

            # STEP 7: LLM naturalizes (mocked for MVP engine logic)
            ai_explanation = rule_explanation # In reality, call the explanation_engine.naturalize()

            # STEP 8: Safety post-validation
            final = self.safety_engine.validate_ai_output(
                ai_recommendation={"classification": classification, "explanation": ai_explanation},
                rule_engine_result={"classification": classification} 
            )

            results.append({
                "food_id": food_id,
                "classification": final.get("classification"),
                "explanation": final.get("explanation"),
                "score": score,
                "fired_rules": rule_result.fired_rules,
                "interactions": interaction_result.interactions
            })

        return {
            "foods": results,
            "generated_at": datetime.now().isoformat()
        }
