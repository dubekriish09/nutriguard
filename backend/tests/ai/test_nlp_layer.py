import pytest
from unittest.mock import patch, MagicMock
from ai.nlp_parser import NLPParser, ExtractedContext, ExtractedCondition, ExtractedMedication, ExtractedAllergy
from ai.context_validator import ContextValidator
from services.recommendation_service import RecommendationService
from models.food import Food

# ---------------------------------------------------------
# MOCKING GEMINI OUTPUT TO AVOID REAL API CALLS IN TESTS
# ---------------------------------------------------------

def mock_genai_response(extracted_context: dict):
    class MockInteraction:
        def __init__(self, text):
            self.output_text = text
            
    class MockInteractions:
        def create(self, **kwargs):
            import json
            return MockInteraction(json.dumps(extracted_context))
            
    class MockClient:
        def __init__(self):
            self.interactions = MockInteractions()
            
    return MockClient()

@pytest.fixture
def parser():
    return NLPParser(api_key="mock")

def test_test1_diabetes(db_session, parser):
    # TEST 1: "I have diabetes." -> type_2_diabetes
    mock_data = {
        "conditions": [{"raw_name": "diabetes", "confidence": 0.95}],
        "medications": [], "allergies": [], "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I have diabetes.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated', f"Failed with questions: {result['questions']}"
        assert len(result['user_context']['conditions']) == 1
        assert result['user_context']['conditions'][0]['name'] == 'Type 2 Diabetes'

def test_test2_medication_details(db_session, parser):
    # TEST 2: "I take metformin 500 mg twice a day."
    mock_data = {
        "conditions": [],
        "medications": [{
            "raw_name": "metformin", "dose": "500", "unit": "mg", 
            "frequency": "twice a day", "timing": None, "confidence": 0.99
        }], 
        "allergies": [], "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I take metformin 500 mg twice a day.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated'
        med = result['user_context']['medications'][0]
        assert med['generic_name'] == 'Metformin'
        assert med['dose'] == '500'
        assert med['frequency'] == 'twice a day'

def test_test3_allergy(db_session, parser):
    # TEST 3: "I'm allergic to peanuts."
    mock_data = {
        "conditions": [], "medications": [],
        "allergies": [{"raw_name": "peanuts", "confidence": 0.99}], 
        "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I'm allergic to peanuts.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated'
        assert 'peanut' in result['user_context']['allergies']

def test_test4_dietary_preference(db_session, parser):
    # TEST 4: "I'm vegetarian."
    mock_data = {
        "conditions": [], "medications": [], "allergies": [], 
        "dietary_preferences": ["vegetarian"], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I'm vegetarian.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated'
        assert 'vegetarian' in result['user_context']['dietary_preferences']

def test_test5_multiple_conditions(db_session, parser):
    # TEST 5: "I have diabetes and hypertension."
    mock_data = {
        "conditions": [
            {"raw_name": "diabetes", "confidence": 0.9},
            {"raw_name": "hypertension", "confidence": 0.9}
        ], 
        "medications": [], "allergies": [], "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I have diabetes and hypertension.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated'
        assert len(result['user_context']['conditions']) == 2

def test_test6_ambiguous_medication(db_session, parser):
    # TEST 6: "I take thyroid medicine."
    mock_data = {
        "conditions": [], 
        "medications": [{"raw_name": "thyroid medicine", "dose": None, "unit": None, "frequency": None, "timing": None, "confidence": 0.8}], 
        "allergies": [], "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": ["thyroid medicine"], "missing_information": []
    }
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I take thyroid medicine.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'needs_clarification'
        assert any('thyroid medicine' in q for q in result['questions'])

def test_test7_medication_and_condition(db_session, parser):
    # TEST 7: "I take metformin and have diabetes."
    mock_data = {
        "conditions": [{"raw_name": "diabetes", "confidence": 0.95}],
        "medications": [{"raw_name": "metformin", "dose": None, "unit": None, "frequency": None, "timing": None, "confidence": 0.99}], 
        "allergies": [], "dietary_preferences": [], "food_preferences": [],
        "uncertain_entities": [], "missing_information": []
    }
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I take metformin and have diabetes.")
        validator = ContextValidator(db_session)
        result = validator.validate(extracted)
        
        assert result['status'] == 'validated'
        assert len(result['user_context']['conditions']) == 1
        assert len(result['user_context']['medications']) == 1

@pytest.mark.asyncio
async def test_test8_recommend_peanut_allergy(db_session, parser):
    # TEST 8: "Recommend peanuts." with user allergy.
    # The NLP layer extracts nothing medical from the query itself, 
    # but the recommendation engine must still block it.
    
    # NLP Context extracted
    mock_data = {
        "conditions": [], "medications": [], "allergies": [{"raw_name": "peanuts", "confidence": 0.99}], 
        "dietary_preferences": [], "food_preferences": ["peanuts"],
        "uncertain_entities": [], "missing_information": []
    }
    
    with patch.object(parser, 'client', mock_genai_response(mock_data)):
        extracted = parser.parse("I'm allergic to peanuts. Recommend peanuts.")
        validator = ContextValidator(db_session)
        val_res = validator.validate(extracted)
        
        assert val_res['status'] == 'validated'
        user_context = val_res['user_context']
        
        food = db_session.query(Food).filter_by(name="Peanuts").first()
        service = RecommendationService(db_session)
        result = await service.generate_recommendations(user_context, [food.food_id])
        
        res = result['foods'][0]
        # Must NOT override safety result
        assert res['classification'] == 'blocked_allergy'

def test_guardrails_malformed_output(parser):
    # AI GUARDRAIL TEST: "Simulate malicious/incorrect model output"
    class MaliciousResponse:
        output_text = '{"recommendation": "eat peanuts", "medication": "stop warfarin"}'
        
    class MaliciousClient:
        class interactions:
            @staticmethod
            def create(**kwargs):
                return MaliciousResponse()
                
    with patch('google.genai.Client', return_value=MaliciousClient()):
        with pytest.raises(Exception): # Pydantic ValidationError
            parser.parse("I want peanuts.")
