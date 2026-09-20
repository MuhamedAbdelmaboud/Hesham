import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 4
RATE_LIMIT_WAIT_SECONDS = 15

_client = None


class LLMError(RuntimeError):
    pass


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMError("مفتاح GOOGLE_API_KEY مش موجود. حطه في ملف .env")
        _client = genai.Client(api_key=api_key)
    return _client


def _build_config(json_mode, thinking_level):
    settings = {
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
    }
    if json_mode:
        settings["response_mime_type"] = "application/json"
    if thinking_level:
        settings["thinking_config"] = types.ThinkingConfig(
            thinking_level=thinking_level.upper()
        )
    return types.GenerateContentConfig(**settings)


def _friendly_message(error):
    code = getattr(error, "code", None)
    text = str(error)
    if code == 429:
        return "وصلنا للحد المجاني للطلبات. استنى شوية وجرب تاني."
    if code == 404:
        return "اسم الموديل غلط. غيّر GEMINI_MODEL في ملف .env لاسم صحيح من AI Studio."
    if code in (401, 403) or "API key" in text:
        return "مفتاح الـ API غلط أو مش شغال. راجع GOOGLE_API_KEY في ملف .env"
    if code in (500, 503):
        return "خدمة Gemini مشغولة دلوقتي. جرب تاني بعد شوية."
    return f"حصلت مشكلة في الاتصال بالموديل: {text[:200]}"


def call_llm(prompt, json_mode=False, thinking_level=None):
    client = _get_client()
    config = _build_config(json_mode, thinking_level)

    response = None
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL, contents=prompt, config=config
            )
            break
        except errors.APIError as e:
            last_error = e
            code = getattr(e, "code", None)

            if code == 400 and thinking_level:
                thinking_level = None
                config = _build_config(json_mode, None)
                continue

            if code in (429, 500, 503) and attempt < MAX_RETRIES:
                wait = RATE_LIMIT_WAIT_SECONDS if code == 429 else RETRY_WAIT_SECONDS
                time.sleep(wait * (attempt + 1))
                continue
            break
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT_SECONDS)
                continue
            break

    if response is None:
        raise LLMError(_friendly_message(last_error))

    text = response.text
    if not text:
        raise LLMError("الموديل رجّع رد فاضي. جرب تاني.")
    return text


def _extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def call_llm_json(prompt, thinking_level=None):
    for _ in range(2):
        text = call_llm(prompt, json_mode=True, thinking_level=thinking_level)
        try:
            data = json.loads(_extract_json_object(text))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise LLMError("مقدرتش أفهم رد الموديل (مش JSON صالح). جرب تاني.")


if __name__ == "__main__":
    print("الموديل:", MODEL)
    print(call_llm_json('رد بـ JSON فيه مفتاح واحد اسمه message وقيمته "مرحبا"'))
