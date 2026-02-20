from http.server import BaseHTTPRequestHandler
import cgi
import json
import os
import time
import base64
import httpx
from openai import OpenAI

# ── Config from env ──
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL", "https://api.sarvam.ai")
SARVAM_STT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_TTS_MODEL = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3")
SARVAM_TTS_SPEAKER = os.environ.get("SARVAM_TTS_SPEAKER", "shubh")
SARVAM_DEFAULT_LANG = os.environ.get("SARVAM_DEFAULT_LANGUAGE", "mr-IN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMP = float(os.environ.get("LLM_TEMPERATURE", "0.5"))
LLM_MAX = int(os.environ.get("LLM_MAX_TOKENS", "150"))

SARVAM_HEADERS = {"api-subscription-key": SARVAM_API_KEY}
oai = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a fast multilingual voice assistant. Rules:
1. Reply in the SAME language as the user (Marathi/Hindi/English).
2. Keep replies to 1-2 SHORT sentences. Be concise like Alexa/Siri.
3. No long explanations. No bullet points. Just speak naturally.
4. If code-mixed, reply in same style."""


def do_stt(audio_bytes, filename):
    ct = "audio/webm" if filename.endswith(".webm") else "audio/mp4" if filename.endswith(".mp4") else "audio/wav"
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers=SARVAM_HEADERS,
            files={"file": (filename, audio_bytes, ct)},
            data={"model": SARVAM_STT_MODEL, "language_code": "unknown"},
        )
    print(f"[STT] {r.status_code}")
    if r.status_code != 200:
        return None, SARVAM_DEFAULT_LANG
    d = r.json()
    return d.get("transcript", "").strip() or None, d.get("language_code", SARVAM_DEFAULT_LANG)


def do_llm(user_input, memory):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + memory + [{"role": "user", "content": user_input}]
    r = oai.chat.completions.create(model=OPENAI_MODEL, messages=msgs, temperature=LLM_TEMP, max_tokens=LLM_MAX)
    return r.choices[0].message.content


def do_tts(text, lang):
    if lang and "-" not in lang:
        lang = f"{lang}-IN"
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SARVAM_BASE_URL}/text-to-speech",
            headers={**SARVAM_HEADERS, "Content-Type": "application/json"},
            json={"text": text, "target_language_code": lang or SARVAM_DEFAULT_LANG, "model": SARVAM_TTS_MODEL, "speaker": SARVAM_TTS_SPEAKER.lower(), "output_audio_codec": "mp3"},
        )
    print(f"[TTS] {r.status_code}")
    if r.status_code != 200:
        return b""
    audios = r.json().get("audios", [])
    return base64.b64decode(audios[0]) if audios else b""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        t0 = time.time()
        ct = self.headers.get("Content-Type", "")

        if "multipart/form-data" not in ct:
            self._json(400, {"error": "Need multipart/form-data"})
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ct})

        audio_item = form["audio"]
        audio_bytes = audio_item.file.read()
        filename = audio_item.filename or "audio.webm"

        memory = []
        if "history" in form:
            try:
                memory = json.loads(form["history"].value)
            except:
                pass

        # 1) STT
        transcript, lang = do_stt(audio_bytes, filename)
        if not transcript:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        print(f"[AGENT] '{transcript}' ({lang})")

        # 2) LLM
        memory.append({"role": "user", "content": transcript})
        response_text = do_llm(transcript, memory)
        print(f"[AGENT] → '{response_text}'")

        # 3) TTS
        audio_out = do_tts(response_text, lang)
        if not audio_out:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return

        print(f"[AGENT] ✅ {time.time()-t0:.1f}s")
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Expose-Headers", "X-Transcript, X-Response, X-Language")
        self.send_header("X-Transcript", transcript)
        self.send_header("X-Response", response_text)
        self.send_header("X-Language", lang)
        self.end_headers()
        self.wfile.write(audio_out)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}" if args else "")
