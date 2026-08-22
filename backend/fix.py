import sys
filepath = 'tests/ai/test_nlp_layer.py'
with open(filepath, 'r') as f:
    content = f.read()
content = content.replace("patch('google.genai.Client', return_value=mock_genai_response(mock_data))", "patch.object(parser, 'client', mock_genai_response(mock_data))")
with open(filepath, 'w') as f:
    f.write(content)
