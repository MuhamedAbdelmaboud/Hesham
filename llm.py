import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("⚠️ حط GOOGLE_API_KEY في ملف .env")

client = genai.Client(api_key=api_key)
MODEL = "gemini-3.6-flash"


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def call_llm(prompt: str, json_mode: bool = False) -> str:
    config = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                time.sleep(15)  # الانتظار 15 ثانية لتصفية الكوتا
            elif attempt < 2:
                time.sleep(2)
            else:
                raise RuntimeError(f"خطأ في الاتصال بالـ LLM: {err_msg}")


def call_llm_json(prompt: str) -> dict:
    for attempt in range(2):
        try:
            raw_text = call_llm(prompt, json_mode=True)
            clean_text = _clean_json_text(raw_text)
            return json.loads(clean_text)
        except Exception as e:
            if attempt == 1:
                raise RuntimeError(f"فشل تحليل الـ JSON من الموديل: {str(e)}")


if __name__ == "__main__":
    res = call_llm_json("رد بـ JSON فيه مفتاح message وقيمته مرحبا")
    print("اختبار llm.py بنجاح:", res)