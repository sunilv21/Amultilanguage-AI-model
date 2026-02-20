from http.server import BaseHTTPRequestHandler
import cgi
import json
import time
from ._sarvam import sarvam_stt, sarvam_tts
from ._llm import generate_response

# Serverless = no persistent memory across invocations
# We pass conversation history from the frontend instead


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        t0 = time.time()

        # Parse multipart form data
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
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

        # Parse conversation history if provided
        memory = []
        if "history" in form:
            try:
                memory = json.loads(form["history"].value)
            except:
                pass

        print(f"[AGENT] Received {filename} ({len(audio_bytes)} bytes)")

        # 1) STT
        transcript, language, confidence = sarvam_stt(audio_bytes, filename)

        if not transcript:
            self.send_response(204)
            self.end_headers()
            return

        print(f"[AGENT] \"{transcript}\" ({language})")

        # 2) LLM
        memory.append({"role": "user", "content": transcript})
        response_text = generate_response(transcript, memory)

        # 3) TTS
        audio_output = sarvam_tts(response_text, language)

        if not audio_output:
            self.send_response(204)
            self.end_headers()
            return

        print(f"[AGENT] ✅ {time.time()-t0:.1f}s total")

        # Return audio + transcript info in headers for the frontend
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Expose-Headers", "X-Transcript, X-Response, X-Language")
        self.send_header("X-Transcript", transcript)
        self.send_header("X-Response", response_text)
        self.send_header("X-Language", language)
        self.end_headers()
        self.wfile.write(audio_output)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
