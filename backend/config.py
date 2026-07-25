import os
from dotenv import load_dotenv

# Load environment variables from a .env file only for local development.
if os.environ.get('RENDER', '').lower() not in {'1', 'true', 'yes'}:
    load_dotenv()
else:
    os.environ.setdefault('STT_ENGINE', 'mock')
    os.environ.setdefault('LLM_PROVIDER', 'mock')

class Config:
    # Flask Settings
    SECRET_KEY = (
        os.environ.get('SECRET_KEY')
        or os.environ.get('FLASK_SECRET_KEY')
        or os.environ.get('SESSION_SECRET')
        or ''
    )
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', 5000))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # LLM Model Config
    # Supports Gemini API or mock endpoints for testing/offline scenarios
    LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
    LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'gemini')  # 'gemini', 'openai', or 'mock'
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gemini-3.5-flash')
    LLM_API_ENDPOINT = os.environ.get('LLM_API_ENDPOINT', 'https://generativelanguage.googleapis.com/v1beta/models')
    
    # Audio Speech-to-Text Model Config
    # Supports offline local models, standard APIs, or lightweight local python speech processors
    STT_ENGINE = os.environ.get('STT_ENGINE', 'mock').lower()  # 'google' (free web api), 'whisper_local', or 'mock'
    STT_MODEL_NAME = os.environ.get('STT_MODEL_NAME', 'openai/whisper-tiny') # used if local model is loaded
    
    # Log configuration
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'app.log')
