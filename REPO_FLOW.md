# PromptWars Substance Use Disorders - Repository Flow

## 🎯 Project Overview
**Aegis** is a GenAI-powered Recovery & Prevention Platform designed to support individuals with substance use disorders and their caregivers. It uses voice-first interaction (speech-to-text → LLM → text-to-speech) to provide immediate, empathetic guidance.

### Tech Stack
- **Backend**: Flask (Python)
- **Frontend**: HTML/CSS/JavaScript (Jinja2 templates)
- **Database**: SQLite
- **Audio**: WebAudio API (browser) + speech_recognition library (Python)
- **LLM**: Google Gemini API (with mock fallback)
- **Authentication**: SQLite-based session management

---

## 🏗️ Architecture

### Directory Structure
```
.
├── app.py                          # Main Flask application
├── backend/
│   ├── auth_service.py             # User authentication & database
│   ├── config.py                   # Configuration management
│   └── llm_client.py               # LLM integration (Gemini API)
├── models/
│   └── speech_to_text.py           # Speech transcription engine
├── frontend/
│   ├── templates/
│   │   ├── login.html              # Login/registration page
│   │   ├── dashboard.html          # Main interaction interface
│   │   └── profile.html            # User profile & settings
│   └── static/
│       ├── css/styles.css          # Glassmorphism design system
│       └── js/app.js               # Client-side audio & API logic
├── data/
│   └── app.db                      # SQLite database
├── logs/
│   └── app.log                     # Application logs
└── temp/                           # Temporary audio files
```

---

## 🔄 Core User Flows

### 1. **Authentication Flow**
```
User visits / → Index route
  ↓
If authenticated → Redirect to dashboard
If not → Create anonymous user & redirect to dashboard
  ↓
User can login via /login (POST)
  - Create new account or authenticate existing
  - Two roles: "hero" (recovery) or "caretaker" (support)
  - Email + password required for persistent accounts
  - Anonymous users can upgrade account on profile page (/backup-account)
```

**Key Functions** (`backend/auth_service.py`):
- `init_db()` - Initialize SQLite schema
- `create_anonymous_user()` - Session-only user
- `create_user()` - Persistent email-based user
- `authenticate_user()` - Verify credentials
- `upgrade_anonymous_user()` - Convert anonymous to persistent
- `get_user_by_id()` - Retrieve user data
- `seed_demo_user()` - Pre-populate demo@aegis.local / Demo123!
- `seed_caretaker_user()` - Pre-populate caretaker@aegis.local / Caretaker123!

### 2. **Main Interaction Flow** (Dashboard)
```
User on /dashboard
  ↓
Selects severity level:
  - 🌱 Wellness Check-in (general_wellness)
  - ⚠️ Craving Support (moderate_support)
  - 🚨 Critical Emergency (critical_emergency)
  - [Caretaker only: caregiver_guidance]
  ↓
Clicks microphone button
  ↓
Browser captures audio (WebAudio API) → WavAudioRecorder class
  ↓
Sends WAV blob to /api/transcribe (POST)
  ↓
Backend transcribes via speech_to_text.py
  ↓
Transcribed text displayed in "What we heard" box
  ↓
Text sent to /api/generate (POST) with severity + user text
  ↓
Backend loads severity-specific prompt template
  ↓
LLM generates response (Gemini API or fallback)
  ↓
Response displayed in "Aegis Guidance" box
  ↓
Optional: User clicks speaker button for text-to-speech (/api/tts)
  ↓
Audio response played in browser
```

**Key API Endpoints**:
- `POST /api/transcribe` - Convert audio to text
- `POST /api/generate` - Generate LLM response
- `GET /api/tts` - Convert text to speech
- `POST /api/emergency` - Log emergency alert
- `GET /api/usage-log` - View activity (caretaker only)
- `POST /api/backup-account` - Upgrade anonymous account

### 3. **Caretaker Flow**
```
Caretaker logs in with role "caretaker"
  ↓
Dashboard shows "Care Buddy Control Room"
  ↓
Records observations/concerns via microphone
  ↓
Receives "Suggested Intervention Protocol"
  ↓
Right sidebar shows alerts from heroes' emergency presses
  ↓
Can access /api/usage-log to see activity history
```

---

## 🔐 Authentication Details

### Database Schema (SQLite)
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    provider TEXT NOT NULL,
    is_anonymous INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

### Session Management
- Flask session stores: `user_id`, `user_role`, `username`, `auth_provider`, `is_anonymous`, `email`
- Cookies: HttpOnly, SameSite=Lax, Secure (production)
- Protected routes via `@login_required` decorator

### Default Demo Users
1. **Hero**: demo@aegis.local / Demo123!
2. **Caretaker**: caretaker@aegis.local / Caretaker123!

---

## 🤖 LLM Integration

### LLM Client (`backend/llm_client.py`)
- **Provider**: Google Gemini API (configurable)
- **Model**: gemini-3.5-flash (configurable)
- **Temperature**: 0.3 (conservative, safe responses)
- **Max tokens**: 256

### Severity-Specific Prompts
Located in prompt templates directory (if exists), loaded dynamically:
- `general_wellness.txt` - General check-in guidance
- `moderate_support.txt` - Craving/stress management
- `critical_emergency.txt` - Immediate crisis intervention
- `caregiver_guidance.txt` - Support for caregivers

### Fallback Behavior
If LLM fails or no API key:
```python
_generate_fallback_response(user_input, severity)
```
Returns severity-appropriate calm, supportive guidance.

---

## 🎤 Speech Processing

### Speech-to-Text (`models/speech_to_text.py`)
- **Engines**: Google Web Speech API (free) or mock
- **Fallback**: Returns placeholder text on error
- **Error Handling**: Graceful degradation with explanatory messages

### Text-to-Speech (`app.py` /api/tts endpoint)
- **Engine**: gTTS (Google Text-to-Speech)
- **Format**: MP3 streaming
- **Cleanup**: Temporary files removed after serving

### Audio Recording (`frontend/static/js/app.js`)
- **Class**: WavAudioRecorder
- **Encoding**: WAV (PCM, 16-bit)
- **Sample Rate**: Browser's native sample rate
- **Storage**: Temporary FormData upload

---

## 🎨 Frontend Design

### Design System (CSS)
- **Colors**:
  - Primary: #8b5cf6 (purple)
  - Secondary: #ec4899 (pink)
  - Severity Low: #10b981 (green)
  - Severity Medium: #f59e0b (amber)
  - Severity High: #ef4444 (red)
- **Style**: Glassmorphism (backdrop blur, semi-transparent backgrounds)
- **Fonts**: Plus Jakarta Sans, Outfit
- **Responsive**: Mobile-first grid layout

### Key Components
1. **Login Page** (`login.html`)
   - Role selection (hero vs caretaker)
   - Email/password/name inputs
   - Demo credentials displayed

2. **Dashboard** (`dashboard.html`)
   - Severity selector buttons
   - Microphone record button (main interaction)
   - Speech transcript display
   - LLM response display with speaker button
   - Right sidebar: Safety toolkit, alerts, resources
   - Modals: Grounding exercises, educational resources

3. **Profile Page** (`profile.html`)
   - Account upgrade option (anonymous → persistent)
   - Custom settings (caregiver contact, grounding phrase)

### JavaScript Features (`app.js`)
- Role selection on login
- Audio capture & WAV encoding
- API request handling
- Response streaming & display
- Text-to-speech playback
- Modal interactions
- Error messaging

---

## 🚀 API Endpoint Flow Summary

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---|
| `/` | GET | Index (auto-create anonymous user) | No |
| `/health` | GET | Health check | No |
| `/login` | GET/POST | Login/registration | No |
| `/logout` | GET | Logout | Yes |
| `/dashboard` | GET | Main app interface | Yes |
| `/profile` | GET | User profile | Yes |
| `/api/transcribe` | POST | Audio → text | Yes |
| `/api/generate` | POST | Text → LLM response | Yes |
| `/api/tts` | GET | Text → speech audio | Yes |
| `/api/emergency` | POST | Log emergency alert | Yes |
| `/api/usage-log` | GET | View activity (caretaker) | Yes (caretaker) |
| `/api/backup-account` | POST | Upgrade anonymous account | Yes |

---

## 🔧 Configuration

### Environment Variables
```
SECRET_KEY              - Flask session key (required in production)
FLASK_DEBUG             - Debug mode (default: False)
PORT                    - Server port (default: 5000)
HOST                    - Server host (default: 0.0.0.0)
LLM_API_KEY            - Google Gemini API key (optional)
LLM_PROVIDER           - LLM provider (default: gemini)
LLM_MODEL_NAME         - Model ID (default: gemini-3.5-flash)
STT_ENGINE             - Speech-to-text engine (default: mock)
RENDER                 - Platform detection (Render.com)
```

### Database Path
- Default: `./data/app.db`
- Override: `APP_DB_PATH` env var

---

## 📊 Usage Logging

Activity tracked in `logs/usage_log.json`:
```json
[
  {
    "event": "feature_used|critical_emergency",
    "detail": "severity=general_wellness",
    "user": "username",
    "role": "hero|caretaker"
  }
]
```

Caretakers can view last 20 entries via `/api/usage-log`.

---

## 🔐 Security Measures

✅ **Implemented**:
- SQLite database with parameterized queries
- Password hashing (SHA256)
- Session-based authentication
- HttpOnly cookies
- CSRF token ready (Flask built-in)
- Input validation & sanitization
- Role-based access control
- Max request size: 16MB
- Content-type validation

⚠️ **Production Checklist**:
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS (secure cookies)
- [ ] Use production WSGI server (gunicorn)
- [ ] Set LLM_API_KEY for live model
- [ ] Configure STT_ENGINE for production
- [ ] Monitor logs/usage_log.json

---

## 📝 Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment (optional)
export FLASK_DEBUG=true
export LLM_PROVIDER=mock  # or set LLM_API_KEY for live model

# Run app
python app.py

# Visit http://localhost:5000
```

---

## 🧪 Testing

Test files available in `tests/`:
- `test_app_security.py` - API security tests
- `test_auth_service.py` - Authentication tests
- `test_speech_to_text.py` - STT engine tests

```bash
pytest tests/
```

---

## 🚢 Deployment

### Platforms Supported
- **Render.com** (via render.yaml, Procfile)
- **Heroku** (via Procfile)
- **Railway** (via Procfile)
- **Vercel** (with WSGI adapter in wsgi.py)

### Production Entry Point
```python
# wsgi.py
from app import app
```

Run with gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

---

## 🎓 Key Design Principles

1. **Zero-Typing UX**: Voice-first interaction to remove friction
2. **Severity-Aware Responses**: LLM adjusts guidance based on crisis level
3. **Graceful Fallbacks**: No external API needed; offline capability with mock responses
4. **Dual Role Support**: Different UX/APIs for "hero" (in recovery) vs "caretaker" (supporter)
5. **Accessibility**: ARIA labels, screen-reader friendly, keyboard navigable
6. **Privacy**: Anonymous sessions, optional account upgrade, minimal data collection

---

**Last Updated**: 2024-07-25 | **Branch**: main
