import os
import logging
import requests
import json
from backend.config import Config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.provider = Config.LLM_PROVIDER.lower()
        self.model_name = Config.LLM_MODEL_NAME
        self.api_key = Config.LLM_API_KEY
        self.api_endpoint = Config.LLM_API_ENDPOINT
        
        # Load prompt templates path
        self.prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        logger.info(f"Initialized LLM Client using provider: {self.provider}")

    def _load_prompt_template(self, severity: str) -> str:
        """Loads prompt template based on severity/category clicked."""
        filename = f"{severity}.txt"
        filepath = os.path.join(self.prompts_dir, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Prompt template {filename} not found, falling back to general_wellness")
            filepath = os.path.join(self.prompts_dir, 'general_wellness.txt')
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt template {filename}: {e}")
            return "Provide a warm response to the user's input: {user_input}"

    def generate_response(self, user_input: str, severity: str) -> str:
        """
        Wraps user_input in the severity-specific template and requests a response from the LLM.
        """
        template = self._load_prompt_template(severity)
        formatted_prompt = template.format(user_input=user_input)
        
        logger.info(f"Generating LLM response for severity: {severity}")

        if self.provider == 'mock' or not self.api_key:
            logger.info("Using mock GenAI response engine")
            return self._generate_mock_response(user_input, severity)

        if self.provider == 'gemini':
            return self._call_gemini_api(formatted_prompt)
        else:
            logger.warning(f"Provider '{self.provider}' not recognized. Falling back to mock response.")
            return self._generate_mock_response(user_input, severity)

    def _call_gemini_api(self, prompt: str) -> str:
        """Calls Google's Gemini API."""
        url = f"{self.api_endpoint}/{self.model_name}:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 256,
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Extract text content from Gemini's response structure
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', '').strip()
            return "I am here for you, but I couldn't receive a response from the GenAI model right now. Please try again."
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            return f"[API Error: Unable to contact LLM. Direct Assistance: Please reach out to your caregiver or contact emergency support lines.]"

    def _generate_mock_response(self, user_input: str, severity: str) -> str:
        """
        Returns realistic, comforting, and contextual mock responses for testing
        and offline demonstration of the platform.
        """
        user_input_lower = user_input.lower()
        
        if severity == 'critical_emergency':
            return (
                "I hear you, and please know that you are not alone. Let's focus on safety right now. "
                "Take a slow, deep breath: inhale for 4 seconds, hold, and exhale. "
                "We strongly encourage you to press the emergency call button or reach out to your caretaker immediately. "
                "Help is always available."
            )
        elif severity == 'moderate_support':
            return (
                "Cravings and distress can feel intense, but they are like waves that will peak and pass. "
                "Let's try a simple distraction: try drinking a glass of water or taking three deep breaths. "
                "I have also sent a notification option to your Caretaker if you'd like them to check in on you. You can do this."
            )
        elif severity == 'caregiver_guidance':
            return (
                "Thank you for being there. It is common to feel overwhelmed in this role. "
                "When responding, try to use calm, non-confrontational language, and validate their effort. "
                "Remember to check in on your own well-being today too. You are doing a wonderful job."
            )
        else:
            # general_wellness
            return (
                "Thank you for sharing that with me. Every step forward, no matter how small, is a victory. "
                "For today's reflection: try to focus on one thing you are grateful for or one small action that brings you peace. "
                "Keep going, you are making progress!"
            )
