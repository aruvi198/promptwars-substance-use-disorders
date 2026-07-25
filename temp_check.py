from backend.llm_client import LLMClient

client = LLMClient()
for severity in ['general_wellness', 'moderate_support', 'critical_emergency', 'caregiver_guidance']:
    print(severity, '=>', client._generate_fallback_response('I am having a hard time', severity))
