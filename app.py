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

import logging
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from gtts import gTTS
from backend.config import Config
from models.speech_to_text import SpeechToTextEngine
from backend.llm_client import LLMClient

# Setup logging
os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'temp'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("app")

# Initialize Flask app pointing to our frontend structure
app = Flask(
    __name__,
    template_folder='frontend/templates',
    static_folder='frontend/static'
)
app.config.from_object(Config)

# Initialize engines
stt_engine = SpeechToTextEngine()
llm_client = LLMClient()

# Helper for login protection
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_role' in session:
        return redirect(url_for('dashboard_page'))
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        # Simple mockup session setup based on form input
        role = request.form.get('role', 'hero')
        username = request.form.get('username', 'Recovery Hero')
        session['user_role'] = role
        session['username'] = username
        logger.info(f"User '{username}' logged in as role: {role}")
        return redirect(url_for('dashboard_page'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('username')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html', role=session['user_role'], username=session['username'])

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html', role=session['user_role'], username=session['username'])

# API Endpoints
@app.route('/api/transcribe', methods=['POST'])
@login_required
def api_transcribe():
    """
    Accepts audio blob via form-data upload, transcribes it using speech_to_text.py
    and returns the transcribed text.
    """
    if 'audio' not in request.files:
        logger.error("No audio file found in the request")
        return jsonify({'error': 'No audio file part in request'}), 400
        
    audio_file = request.files['audio']
    if audio_file.filename == '':
        logger.error("Empty filename received")
        return jsonify({'error': 'Empty filename'}), 400

    # Save audio temporarily
    temp_filename = f"{uuid.uuid4()}.wav"
    temp_filepath = os.path.join(os.path.dirname(__file__), 'temp', temp_filename)
    
    try:
        audio_file.save(temp_filepath)
        logger.info(f"Saved temp audio file to: {temp_filepath}")

        # Transcribe audio using STT engine
        transcription = stt_engine.transcribe(temp_filepath)
        return jsonify({'text': transcription})
        
    except Exception as e:
        logger.exception("Error processing transcription request:")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
                logger.info(f"Cleaned up temp audio file: {temp_filepath}")
            except Exception as e:
                logger.error(f"Failed to remove temp file {temp_filepath}: {e}")

@app.route('/api/generate', methods=['POST'])
@login_required
def api_generate():
    """
    Generates response from LLM using severity-specific prompts.
    Expects JSON containing 'text' and 'severity'.
    """
    data = request.get_json() or {}
    user_text = data.get('text', '').strip()
    severity = data.get('severity', 'general_wellness').strip()
    
    if not user_text:
        return jsonify({'error': 'No text provided'}), 400
        
    try:
        response_text = llm_client.generate_response(user_text, severity)
        return jsonify({'response': response_text})
    except Exception as e:
        logger.exception("Error generating LLM response:")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts', methods=['GET'])
@login_required
def api_tts():
    """
    Generates Text-to-Speech audio from the provided query parameter 'text' and returns WAV/MP3 stream.
    """
    text = request.args.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    try:
        # Create TTS object using gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to temp file
        temp_filename = f"tts_{uuid.uuid4()}.mp3"
        temp_filepath = os.path.join(os.path.dirname(__file__), 'temp', temp_filename)
        tts.save(temp_filepath)
        
        # Return audio file and then clean it up later or serve directly
        @app.after_request
        def cleanup_tts(response):
            try:
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
            except Exception as e:
                logger.error(f"Error deleting temp tts file: {e}")
            return response
            
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'temp'), temp_filename, mimetype='audio/mpeg')
    except Exception as e:
        logger.exception("TTS generation failed:")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create required temp folders if they do not exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'temp'), exist_ok=True)
    logger.info(f"Starting Recovery & Prevention platform on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
