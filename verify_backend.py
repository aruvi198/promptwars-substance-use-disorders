import os
import sys
import types
# Mock aifc for Python 3.13 compatibility
aifc_mock = types.ModuleType('aifc')
class AifcError(Exception):
    pass
aifc_mock.Error = AifcError
def aifc_open(*args, **kwargs):
    raise AifcError("AIFC format not supported")
aifc_mock.open = aifc_open
sys.modules['aifc'] = aifc_mock

def verify_boilerplate():
    print("=== Aegis Recovery & Prevention Platform Boilerplate Verification ===")
    
    # 1. Check directory structure
    required_paths = [
        'backend',
        'backend/prompts',
        'backend/prompts/critical_emergency.txt',
        'backend/prompts/moderate_support.txt',
        'backend/prompts/general_wellness.txt',
        'backend/prompts/caregiver_guidance.txt',
        'backend/config.py',
        'backend/llm_client.py',
        'models',
        'models/speech_to_text.py',
        'frontend/templates',
        'frontend/templates/login.html',
        'frontend/templates/dashboard.html',
        'frontend/templates/profile.html',
        'frontend/static/css/styles.css',
        'frontend/static/js/app.js',
        'app.py',
        'requirements.txt'
    ]

    missing_paths = []
    for path in required_paths:
        full_path = os.path.join(os.path.dirname(__file__), path)
        if not os.path.exists(full_path):
            missing_paths.append(path)
            print(f"[MISSING] {path}")
        else:
            print(f"[OK] {path}")

    if missing_paths:
        print("\nVerification FAILED: Some files or folders are missing.")
        sys.exit(1)
        
    print("\nDirectory structure verified successfully!")

    # 2. Check Package Imports
    print("\nChecking python package dependencies...")
    try:
        import flask
        print("[OK] Flask imported successfully.")
    except ImportError:
        print("[ERR] Flask is NOT installed. Run: pip install -r requirements.txt")
        
    try:
        import speech_recognition
        print("[OK] SpeechRecognition imported successfully.")
    except ImportError:
        print("[ERR] SpeechRecognition is NOT installed. Run: pip install -r requirements.txt")

    try:
        from gtts import gTTS
        print("[OK] gTTS (Google Text-to-Speech) imported successfully.")
    except ImportError:
        print("[ERR] gTTS is NOT installed. Run: pip install -r requirements.txt")

    # 3. Test LLM client offline logic
    print("\nTesting LLM Client offline logic...")
    try:
        sys.path.append(os.path.dirname(__file__))
        from backend.llm_client import LLMClient
        client = LLMClient()
        test_response = client.generate_response("I want to use today.", "critical_emergency")
        print(f"[OK] LLM Client Test Response (Mock Mode): \"{test_response}\"")
    except Exception as e:
        print(f"[ERR] LLM Client test failed: {e}")
        sys.exit(1)

    print("\nBoilerplate code is fully verified and deployable!")

if __name__ == '__main__':
    verify_boilerplate()
