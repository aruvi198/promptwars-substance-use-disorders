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
import json
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from gtts import gTTS
from backend.config import Config
from models.speech_to_text import SpeechToTextEngine
from backend.llm_client import LLMClient
from backend.auth_service import authenticate_user, create_anonymous_user, create_user, get_user_by_id, init_db, upgrade_anonymous_user

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
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=not Config.DEBUG,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)

if not Config.DEBUG and not Config.SECRET_KEY:
    raise RuntimeError('SECRET_KEY must be set in production mode.')

# Initialize engines
stt_engine = SpeechToTextEngine()
llm_client = LLMClient()
init_db()

LOG_FILE_PATH = Path(__file__).resolve().parent / 'logs' / 'usage_log.json'
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
ALLOWED_ROLES = {'hero', 'caretaker'}
ALLOWED_SEVERITIES = {'general_wellness', 'moderate_support', 'critical_emergency', 'caregiver_guidance'}
MAX_USERNAME_LENGTH = 80
MAX_TEXT_LENGTH = 2000


def _load_usage_log():
    if not LOG_FILE_PATH.exists():
        return []
    try:
        with LOG_FILE_PATH.open('r', encoding='utf-8') as handle:
            data = json.load(handle)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_usage_log(entries):
    with LOG_FILE_PATH.open('w', encoding='utf-8') as handle:
        json.dump(entries, handle, indent=2)


def _record_usage(event_name: str, detail: str = ''):
    entries = _load_usage_log()
    entries.append({
        'event': event_name,
        'detail': detail,
        'user': session.get('username', 'Unknown'),
        'role': session.get('user_role', 'unknown'),
    })
    _save_usage_log(entries)


def _get_caretaker_alerts():
    entries = _load_usage_log()
    return [entry for entry in entries if entry.get('event') in {'critical_emergency', 'feature_used'}]


def _sanitize_username(username: str) -> str:
    cleaned = (username or '').strip()
    if not cleaned or len(cleaned) > MAX_USERNAME_LENGTH:
        raise ValueError('Please enter a valid name.')
    return cleaned


def _sanitize_role(role: str) -> str:
    cleaned = (role or '').strip().lower()
    if cleaned not in ALLOWED_ROLES:
        raise ValueError(f'Invalid role selected. Expected one of: {", ".join(sorted(ALLOWED_ROLES))}.')
    return cleaned


def _sanitize_severity(severity: str) -> str:
    cleaned = (severity or '').strip().lower()
    if cleaned not in ALLOWED_SEVERITIES:
        raise ValueError('Unsupported severity selected.')
    return cleaned


def _set_authenticated_session(user_payload: dict):
    session.clear()
    session['user_id'] = user_payload['id']
    session['user_role'] = user_payload['role']
    session['username'] = user_payload['username']
    session['auth_provider'] = user_payload['provider']
    session['is_anonymous'] = user_payload['is_anonymous']
    session['email'] = user_payload.get('email') or ''


def _load_authenticated_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_user_by_id(user_id)


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

    anonymous_user = create_anonymous_user(username='Guest User', role='hero')
    _set_authenticated_session(anonymous_user)
    return redirect(url_for('dashboard_page'))


@app.route('/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'service': 'promptwars-substance-use-disorders',
        'debug': Config.DEBUG,
    })

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        password = (request.form.get('password') or '').strip()
        role = request.form.get('role', 'hero')
        username = (request.form.get('username') or '').strip()

        try:
            role = _sanitize_role(role)
            if email and password:
                user_payload = authenticate_user(email, password)
                if not user_payload:
                    return render_template('login.html', error='Invalid email or password.'), 401
            else:
                if not username:
                    return render_template('login.html', error='Please enter your name.'), 400
                user_payload = create_user(email=email or f'{username.lower()}@local', password=password or 'changeme123', username=username, role=role)
        except ValueError as exc:
            return render_template('login.html', error=str(exc)), 400

        _set_authenticated_session(user_payload)
        logger.info(f"User '{user_payload['username']}' logged in as role: {user_payload['role']}")
        return redirect(url_for('dashboard_page'))
    return render_template('login.html', error='')

@app.route('/logout')
def logout():
    username = session.get('username')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return redirect(url_for('login_page'))

@app.route('/dashboard')
@login_required
def dashboard_page():
    alerts = _get_caretaker_alerts() if session.get('user_role') == 'caretaker' else []
    return render_template('dashboard.html', role=session['user_role'], username=session['username'], alerts=alerts)

@app.route('/profile')
@login_required
def profile_page():
    user_payload = _load_authenticated_user() or {
        'id': session.get('user_id'),
        'username': session.get('username', 'Guest'),
        'role': session.get('user_role', 'hero'),
        'provider': session.get('auth_provider', 'anonymous'),
        'is_anonymous': session.get('is_anonymous', False),
    }
    return render_template(
        'profile.html',
        role=user_payload['role'],
        username=user_payload['username'],
        is_anonymous=user_payload['is_anonymous'],
        auth_provider=user_payload['provider'],
    )


@app.route('/api/backup-account', methods=['POST'])
@login_required
def backup_account():
    email = (request.form.get('email') or '').strip()
    password = (request.form.get('password') or '').strip()

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    if session.get('is_anonymous', False):
        user_id = session.get('user_id')
        if not user_id:
            anonymous_user = create_anonymous_user(username=session.get('username', 'Guest User'), role=session.get('user_role', 'hero'))
            user_id = anonymous_user['id']
            session['user_id'] = user_id

        upgraded_user = upgrade_anonymous_user(
            user_id,
            email,
            password,
            session.get('username', 'Guest User'),
            session.get('user_role', 'hero'),
        )
        _set_authenticated_session(upgraded_user)
        session['backup_email'] = email
        logger.info(f"Anonymous session upgraded using email: {email}")
        return jsonify({'message': 'Account backup completed.', 'provider': 'email'})

    return jsonify({'message': 'Account already upgraded.'}), 200


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({'error': 'Request body is too large.'}), 413

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

    temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb', suffix='.wav', dir=temp_dir, delete=False) as handle:
        temp_filepath = handle.name

    try:
        audio_file.save(temp_filepath)
        logger.info(f"Saved temp audio file to: {temp_filepath}")

        transcription = stt_engine.transcribe(temp_filepath)
        return jsonify({'text': transcription})
    except Exception as e:
        logger.exception("Error processing transcription request:")
        return jsonify({'error': str(e)}), 500
    finally:
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
    user_text = (data.get('text', '') or '').strip()
    severity = (data.get('severity', 'general_wellness') or '').strip()

    if not user_text:
        return jsonify({'error': 'No text provided'}), 400

    if len(user_text) > MAX_TEXT_LENGTH:
        return jsonify({'error': 'Text is too long.'}), 413

    try:
        severity_key = _sanitize_severity(severity)
        response_text = llm_client.generate_response(user_text, severity_key)
        _record_usage('feature_used', f"severity={severity_key}")
        return jsonify({'response': response_text})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as e:
        logger.exception("Error generating LLM response:")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emergency', methods=['POST'])
@login_required
def api_emergency():
    _record_usage('critical_emergency', 'Emergency button pressed')
    return jsonify({'status': 'alerted', 'message': 'Caretaker alert recorded.'})


@app.route('/api/usage-log', methods=['GET'])
@login_required
def api_usage_log():
    if session.get('user_role') != 'caretaker':
        return jsonify({'error': 'Only caretakers can view this'}), 403
    return jsonify({'entries': _load_usage_log()[-20:]})


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
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile('wb', suffix='.mp3', dir=temp_dir, delete=False) as handle:
            temp_filepath = handle.name

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_filepath)

        response = send_from_directory(temp_dir, os.path.basename(temp_filepath), mimetype='audio/mpeg')
        return response
    except Exception as e:
        logger.exception("TTS generation failed:")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create required temp folders if they do not exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'temp'), exist_ok=True)
    logger.info(f"Starting Recovery & Prevention platform on http://{Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
