from http.server import BaseHTTPRequestHandler
import cgi
import json
import time
from ._sarvam import sarvam_stt

WAKE_WORDS = [
    'hello sarvam','hey sarvam','hi sarvam',
    'hello servam','hey servam','hi servam',
    'हेलो सरवम','हे सरवम',
    'hello sarvan','hey sarvan',
    'hello servant','hey servant',
]


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        t0 = time.time()
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" not in content_type:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Expected multipart/form-data"}).encode())
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
        )

        audio_item = form["audio"]
        audio_bytes = audio_item.file.read()
        filename = audio_item.filename or "audio.webm"

        transcript, language, confidence = sarvam_stt(audio_bytes, filename)

        if not transcript:
            self._respond({"wake": False, "text": ""})
            return

        text_lower = transcript.lower().strip()
        found = any(w in text_lower for w in WAKE_WORDS)
        print(f"[WAKE] \"{transcript}\" → {'✅' if found else '—'} ({time.time()-t0:.1f}s)")
        self._respond({"wake": found, "text": transcript})

    def _respond(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
