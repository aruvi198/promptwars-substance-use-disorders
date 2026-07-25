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
        Falls back to a calm, category-aware message if the model request fails.
        """
        template = self._load_prompt_template(severity)
        formatted_prompt = template.format(user_input=user_input)

        logger.info(f"Generating LLM response for severity: {severity}")

        if self.provider == 'mock' or not self.api_key:
            logger.info("Using local fallback response because no live model key is configured")
            return self._generate_fallback_response(user_input, severity)

        if self.provider == 'gemini':
            try:
                return self._call_gemini_api(formatted_prompt)
            except Exception as exc:
                logger.exception("Gemini request failed; using fallback response")
                return self._generate_fallback_response(user_input, severity, error=str(exc))
        else:
            logger.warning(f"Provider '{self.provider}' not recognized. Falling back to safe response.")
            return self._generate_fallback_response(user_input, severity)

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

    def _generate_fallback_response(self, user_input: str, severity: str, error: str = '') -> str:
        """
        Returns calm, category-aware support text when the live model fails.
        This keeps the experience helpful even if the model or transcription layer is unavailable.
        """
        user_input = (user_input or '').strip()

        if severity == 'critical_emergency':
            return (
                "I’m here with you, and I want to help you focus on immediate safety. "
                "Please move to a safe place, call emergency services or a trusted person if you feel in danger, "
                "and take one slow breath in and out. If you’re in immediate danger, seek urgent help now."
            )
        elif severity == 'moderate_support':
            return (
                "Cravings and stress can feel overwhelming, but they often pass with time and a small next step. "
                "Try drinking a glass of water, taking three slow breaths, or stepping away for a few minutes. "
                "If you want extra support, reach out to a trusted person or caregiver."
            )
        elif severity == 'caregiver_guidance':
            return (
                "Thank you for being there for someone who needs support. Keep your tone calm and nonjudgmental, "
                "validate their effort, and encourage one small next step. You are doing meaningful work."
            )
        else:
            # wellness check-in
            return (
                "Thank you for checking in. You do not need to have everything figured out right now. "
                f"Take a moment to notice one small thing that feels grounding today. {user_input[:120] if user_input else ''}".strip()
            )
