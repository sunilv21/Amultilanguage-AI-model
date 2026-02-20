import httpx
import base64
import time
from ._config import settings

_client = httpx.Client(timeout=20)

HEADERS = {"api-subscription-key": settings.SARVAM_API_KEY}


def sarvam_stt(audio_bytes: bytes, filename: str = "audio.wav"):
    t0 = time.time()
    url = f"{settings.SARVAM_BASE_URL}/speech-to-text"

    if filename.endswith(".webm"):
        ct = "audio/webm"
    elif filename.endswith(".mp4"):
        ct = "audio/mp4"
    elif filename.endswith(".ogg"):
        ct = "audio/ogg"
    else:
        ct = "audio/wav"

    files = {"file": (filename, audio_bytes, ct)}
    data = {"model": settings.SARVAM_STT_MODEL, "language_code": "unknown"}

    try:
        r = _client.post(url, headers=HEADERS, files=files, data=data)
        print(f"[STT] {r.status_code} in {time.time()-t0:.2f}s")
        if r.status_code != 200:
            return None, settings.SARVAM_DEFAULT_LANGUAGE, 0.0

        result = r.json()
        transcript = result.get("transcript", "").strip()
        lang = result.get("language_code", settings.SARVAM_DEFAULT_LANGUAGE)
        conf = result.get("language_probability", 0.0)
        if not transcript:
            return None, lang, 0.0
        return transcript, lang, conf if conf else 0.9
    except Exception as e:
        print(f"[STT] Error: {e}")
        return None, settings.SARVAM_DEFAULT_LANGUAGE, 0.0


def sarvam_tts(text: str, language: str) -> bytes:
    t0 = time.time()
    url = f"{settings.SARVAM_BASE_URL}/text-to-speech"

    if language and "-" not in language:
        language = f"{language}-IN"

    payload = {
        "text": text,
        "target_language_code": language or settings.SARVAM_DEFAULT_LANGUAGE,
        "model": settings.SARVAM_TTS_MODEL,
        "speaker": (settings.SARVAM_TTS_SPEAKER or "shubh").lower(),
        "output_audio_codec": "mp3",
    }

    try:
        r = _client.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=payload)
        print(f"[TTS] {r.status_code} in {time.time()-t0:.2f}s")
        if r.status_code != 200:
            return b""
        audios = r.json().get("audios", [])
        if not audios:
            return b""
        return base64.b64decode(audios[0])
    except Exception as e:
        print(f"[TTS] Error: {e}")
        return b""
