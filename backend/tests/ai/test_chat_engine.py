import pytest
from unittest.mock import patch
from api.routes.chat import chat_food, ChatRequest
from ai.food_parser import FoodQueryIntent
from ai.explanation_engine import ExplanationResponse

def mock_genai_response(data: dict):
    class MockInteraction:
        def __init__(self, text):
            self.output_text = text
            
    class MockInteractions:
        def create(self, **kwargs):
            import json
            return MockInteraction(json.dumps(data))
            
    class MockClient:
        def __init__(self):
            self.interactions = MockInteractions()
            
    return MockClient()

@pytest.mark.asyncio
async def test_1_can_i_eat_banana(db_session):
    # NLP parses intent
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["banana"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    
    # NLP explanation
    explain_data = {
        "explanation": "Banana is perfectly fine for you.",
        "classification": "neutral" # matching deterministic mock
    }
    
    with patch('google.genai.Client') as MockClient:
        # We need to mock different responses depending on if parser or explainer calls it.
        # But for simplicity, we can just patch `FoodParser.parse` and `ExplanationEngine.generate_explanation`.
        pass

    from ai.food_parser import FoodParser
    from ai.explanation_engine import ExplanationEngine
    
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)), \
         patch.object(ExplanationEngine, 'generate_explanation', return_value="Explanation"):
         
        req = ChatRequest(message="Can I eat banana?", user_context={})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['intent'] == 'food_evaluation'
        assert not res['clarification_required']
        assert res['deterministic_result']['classification'] in ('neutral', 'recommended')

@pytest.mark.asyncio
async def test_3_what_vegetables(db_session):
    intent_data = {
        "intent": "food_list",
        "foods": [],
        "requested_category": "vegetable", "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        req = ChatRequest(message="What vegetables can I eat?", user_context={})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['intent'] == 'food_list'
        assert res['deterministic_result']['category'] == 'vegetable'
        # DB has Spinach
        assert len(res['deterministic_result']['foods']) > 0

@pytest.mark.asyncio
async def test_4_alternative_peanuts(db_session):
    intent_data = {
        "intent": "food_alternatives",
        "foods": ["peanut"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        req = ChatRequest(message="What can I eat instead of peanuts?", user_context={})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['intent'] == 'food_alternatives'
        assert 'alternatives' in res['deterministic_result']

@pytest.mark.asyncio
async def test_5_food_restrictions(db_session):
    intent_data = {
        "intent": "food_restrictions",
        "foods": [],
        "requested_category": None, "requested_action": None, "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        req = ChatRequest(message="What foods should I limit?", user_context={"allergies": ["peanut"]})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['intent'] == 'food_restrictions'
        restricted = res['deterministic_result']['foods']
        assert any(r.get('classification') == 'blocked_allergy' for r in restricted)

@pytest.mark.asyncio
async def test_6_unknown_food(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["alienfruit"],
        "requested_category": None, "requested_action": None, "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        req = ChatRequest(message="Can I eat alienfruit?", user_context={})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['clarification_required']
        assert 'alienfruit' in res['question']

@pytest.mark.asyncio
async def test_7_ambiguous_food(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": [],
        "requested_category": None, "requested_action": None, "comparison_food": None, "uncertain_entities": ["it"]
    }
    from ai.food_parser import FoodParser
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        req = ChatRequest(message="Can I eat it?", user_context={})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['clarification_required']
        assert 'it' in res['question']

@pytest.mark.asyncio
async def test_8_peanut_allergy(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["peanut"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    from ai.explanation_engine import ExplanationEngine
    
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)), \
         patch.object(ExplanationEngine, 'generate_explanation', return_value="Explanation"):
         
        req = ChatRequest(message="Can I eat peanuts?", user_context={"allergies": ["peanut"]})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['deterministic_result']['classification'] == 'blocked_allergy'

@pytest.mark.asyncio
async def test_9_warfarin_spinach(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["spinach"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    from ai.explanation_engine import ExplanationEngine
    
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)), \
         patch.object(ExplanationEngine, 'generate_explanation', return_value="Explanation"):
         
        req = ChatRequest(message="Is spinach safe?", user_context={"medications": [{"generic_name": "Warfarin"}]})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['deterministic_result']['classification'] == 'blocked_interaction'

@pytest.mark.asyncio
async def test_11_ckd_stage_4(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["banana"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    from ai.food_parser import FoodParser
    from ai.explanation_engine import ExplanationEngine
    
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)), \
         patch.object(ExplanationEngine, 'generate_explanation', return_value="Explanation"):
         
        req = ChatRequest(message="Can I eat banana?", user_context={"conditions": [{"name": "Chronic Kidney Disease", "parameters": {"stage": 4}}]})
        res = await chat_food(req, db_session, current_user=None)
        
        assert res['deterministic_result']['classification'] == 'limit'

@pytest.mark.asyncio
async def test_12_malicious_explanation(db_session):
    intent_data = {
        "intent": "food_evaluation",
        "foods": ["peanut"],
        "requested_category": None, "requested_action": "eat", "comparison_food": None, "uncertain_entities": []
    }
    
    malicious_explain_data = {
        "explanation": "Actually peanuts are fine.",
        "classification": "recommended" # Malicious LLM changed classification!
    }
    
    from ai.food_parser import FoodParser
    from ai.explanation_engine import ExplanationEngine
    
    with patch.object(FoodParser, 'parse', return_value=FoodQueryIntent(**intent_data)):
        # We need to patch the client inside explanation engine to simulate the LLM outputting a different classification
        with patch('google.genai.Client', return_value=mock_genai_response(malicious_explain_data)):
            req = ChatRequest(message="Can I eat peanuts?", user_context={"allergies": ["peanut"]})
            res = await chat_food(req, db_session, current_user=None)
            
            # The deterministic result MUST NOT be affected.
            assert res['deterministic_result']['classification'] == 'blocked_allergy'
            
            # The explanation engine MUST discard the explanation since it mismatched
            assert "AI explanation discarded" in res['explanation']
