"""One entry point for every agent: ask(system, user, Schema) -> validated Schema instance.

Tries Gemini, then local Ollama. Each provider gets one retry on invalid output.
Raises LLMError rather than returning junk.

Scraped text must go in `user` (wrapped in <source_data> tags), never in `system`.
"""
import os
import sys
import time
from typing import TypeVar

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# Tried in order. gemini-3.8-flash was overloaded (503) on the free tier on 13 Nov, so it is the backup.
GEMINI_MODELS = os.getenv("GEMINI_MODEL", "gemini-3.5-flash,gemini-3.8-flash").split(",")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-vl:4b-instruct")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class LLMError(RuntimeError):
    pass


def _gemini(system: str, user: str, schema: type[BaseModel], model: str) -> str:
    from google import genai  # imported here so offline mode works without the package
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return resp.text or ""


def _ollama(system: str, user: str, schema: type[BaseModel]) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema.model_json_schema(),
            "stream": False,
            "options": {"num_ctx": 16384, "temperature": 0},  # default 4k context truncates 8 pages
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _providers():
    offline = os.getenv("TECNOVERSE_OFFLINE") == "1"
    if not offline and os.getenv("GEMINI_API_KEY"):
        for model in GEMINI_MODELS:
            yield model, lambda s, u, sc, m=model: _gemini(s, u, sc, m)
    if os.getenv("TECNOVERSE_CLOUD_ONLY") != "1":  # batch runs set this: the local model is too slow for 100 sites
        yield "ollama", _ollama


def ask(system: str, user: str, schema: type[T]) -> T:
    errors = []
    for name, call in _providers():
        for attempt in (1, 2):
            try:
                return schema.model_validate_json(call(system, user, schema))
            except Exception as e:
                # overloaded or rate limited: wait once, then retry the same provider
                if attempt == 1 and any(code in str(e) for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                    time.sleep(20)
                    continue
                if not isinstance(e, ValidationError):
                    errors.append(f"{name}: {type(e).__name__}: {e}")
                    print(f"[llm] {name} failed, trying next provider: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
                    break
                errors.append(f"{name} attempt {attempt}: invalid output ({e.error_count()} errors)")
    raise LLMError("All LLM providers failed:\n" + ("\n".join(errors) or "none configured (no GEMINI_API_KEY, and TECNOVERSE_CLOUD_ONLY=1)"))


if __name__ == "__main__":  # self-check: cd tecnoverse && python -m core.llm
    class Capital(BaseModel):
        city: str

    out = ask("Answer in JSON.", "What is the capital of Sweden?", Capital)
    assert "stockholm" in out.city.lower(), out
    print("ok:", out)
