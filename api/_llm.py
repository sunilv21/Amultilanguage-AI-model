from openai import OpenAI
from ._config import settings
import time

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a fast multilingual voice assistant. Rules:
1. Reply in the SAME language as the user (Marathi/Hindi/English).
2. Keep replies to 1-2 SHORT sentences. Be concise like Alexa/Siri.
3. No long explanations. No bullet points. Just speak naturally.
4. If code-mixed, reply in same style."""


def generate_response(user_input: str, memory: list) -> str:
    t0 = time.time()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(memory)
    messages.append({"role": "user", "content": user_input})

    r = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
    )
    text = r.choices[0].message.content
    print(f"[LLM] {time.time()-t0:.2f}s | {text}")
    return text
