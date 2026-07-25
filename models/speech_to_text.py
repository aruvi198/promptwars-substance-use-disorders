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
import speech_recognition as sr
from backend.config import Config

logger = logging.getLogger(__name__)

class SpeechToTextEngine:
    def __init__(self):
        self.engine_type = Config.STT_ENGINE.lower()
        self.model_name = Config.STT_MODEL_NAME
        logger.info(f"Initialized STT Engine with type: {self.engine_type}")

    def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribes the given audio file using the configured STT engine.
        Supports:
        - 'google': SpeechRecognition package with Google Web Speech API (free)
        - 'mock': A fallback placeholder returning stub text
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        logger.info(f"Starting transcription for {audio_file_path} using {self.engine_type}")

        if self.engine_type == 'mock':
            logger.info("Using mock speech-to-text fallback")
            return "This is a mocked transcription. The user said: I am feeling overwhelmed and need help right now."

        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        try:
            with sr.AudioFile(audio_file_path) as source:
                # Adjust for ambient noise and record
                audio_data = recognizer.record(source)
                
            if self.engine_type == 'google':
                # Use Google Web Speech API (no credentials needed, fine for boilerplate/testing)
                text = recognizer.recognize_google(audio_data)
                logger.info(f"Transcription successful: {text}")
                return text
            else:
                # Placeholder for other custom STT models (e.g. offline whisper)
                logger.warning(f"Engine type '{self.engine_type}' not fully implemented. Falling back to google.")
                return recognizer.recognize_google(audio_data)

        except sr.UnknownValueError:
            logger.warning("Speech Recognition could not understand the audio.")
            return "[Unable to understand audio. Please speak clearly or try typing.]"
        except sr.RequestError as e:
            logger.error(f"Speech Recognition service error: {e}")
            return f"[Speech Recognition service error: {str(e)}]"
        except ConnectionError as e:
            logger.error(f"Speech recognition connection issue: {e}")
            return "[Speech recognition service is temporarily unavailable. Please try again or type your message.]"
        except Exception as e:
            logger.exception(f"Unexpected error during transcription: {e}")
            return f"[Transcription error: {str(e)}]"
