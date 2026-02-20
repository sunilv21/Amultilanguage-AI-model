from http.server import BaseHTTPRequestHandler
import cgi
import json
import os
import time
import httpx

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL", "https://api.sarvam.ai")
SARVAM_STT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_DEFAULT_LANG = os.environ.get("SARVAM_DEFAULT_LANGUAGE", "mr-IN")

SARVAM_HEADERS = {"api-subscription-key": SARVAM_API_KEY}

WAKE_WORDS = [
    'hello sarvam','hey sarvam','hi sarvam',
    'hello servam','hey servam','hi servam',
    'हेलो सरवम','हे सरवम',
    'hello sarvan','hey sarvan',
    'hello servant','hey servant',
]


def do_stt(audio_bytes, filename):
    ct = "audio/webm" if filename.endswith(".webm") else "audio/mp4" if filename.endswith(".mp4") else "audio/wav"
    with httpx.Client(timeout=20) as c:
        r = c.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers=SARVAM_HEADERS,
            files={"file": (filename, audio_bytes, ct)},
            data={"model": SARVAM_STT_MODEL, "language_code": "unknown"},
        )
    if r.status_code != 200:
        return None
    return r.json().get("transcript", "").strip() or None


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

        transcript = do_stt(audio_bytes, filename)

        if not transcript:
            self._json(200, {"wake": False, "text": ""})
            return

        text_lower = transcript.lower().strip()
        found = any(w in text_lower for w in WAKE_WORDS)
        print(f"[WAKE] '{transcript}' → {'✅' if found else '—'} ({time.time()-t0:.1f}s)")
        self._json(200, {"wake": found, "text": transcript})

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
