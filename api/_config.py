import os

class Settings:
    SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
    SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL", "https://api.sarvam.ai")
    SARVAM_STT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
    SARVAM_TTS_MODEL = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3")
    SARVAM_TTS_SPEAKER = os.environ.get("SARVAM_TTS_SPEAKER", "shubh")
    SARVAM_DEFAULT_LANGUAGE = os.environ.get("SARVAM_DEFAULT_LANGUAGE", "mr-IN")

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.5"))
    LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "150"))

settings = Settings()
