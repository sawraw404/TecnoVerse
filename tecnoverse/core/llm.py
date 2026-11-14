"""One entry point for every agent: ask(system, user, Schema, agent=...) -> validated Schema instance.

Two providers, both with the Pydantic model as the JSON response schema:
  Gemini: free tier ~20 requests/day/model, handles long inputs. First choice for the Profiler,
          which sends whole web pages.
  Groq:   free tier ~1000 requests/day but only ~8000 tokens/minute. First choice for every other
          agent (monitors, matcher, guardrail, assistant), whose calls are short and frequent.
Each model gets one retry on invalid output. If a model is busy, rate-limited or times out, the
next model is tried, then the other provider. If all fail, raises LLMError rather than returning junk.

Scraped text must go in `user` (wrapped in <source_data> tags), never in `system`.
"""
import os
import re
import time
from typing import TypeVar

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# First choice can be overridden in .env; the rest are fallbacks for when it is overloaded.
GEMINI_MODELS = list(dict.fromkeys([
    os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]))
GROQ_MODELS = list(dict.fromkeys([os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), "openai/gpt-oss-20b"]))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_FIRST = {"profiler", "staff"}  # agents with long inputs or few calls; everyone else starts on Groq

_client = None


class LLMError(RuntimeError):
    pass


def _get_client():
    global _client
    if _client is None:
        from google import genai  # imported lazily so Groq-only use works without it configured
        from google.genai import types
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30_000))  # ms
    return _client


def _gemini(model: str, system: str, user: str, schema: type[BaseModel]) -> str:
    from google.genai import types
    resp = _get_client().models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    return resp.text or ""


def _seconds(s: str) -> float:
    """Groq reset values look like '2.07s', '1m3.5s' or '120ms'."""
    if s.endswith("ms"):
        return float(s[:-2]) / 1000
    m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)s", s)
    return int(m.group(1) or 0) * 60 + float(m.group(2)) if m else 999


def _groq(model: str, system: str, user: str, schema: type[BaseModel]) -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY is not set. Add it to .env.")
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}},
        "temperature": 0,
    }
    for attempt in (1, 2):
        r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
        if r.status_code == 429 and attempt == 1:
            # per-minute token limit: wait as long as Groq asks, if that is short
            wait = float(r.headers.get("retry-after") or 0) or _seconds(r.headers.get("x-ratelimit-reset-tokens", ""))
            if wait <= 30:
                time.sleep(wait + 0.5)
                continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""
    return ""


def _providers(agent: str):
    gemini = [(m, lambda s, u, sc, m=m: _gemini(m, s, u, sc)) for m in GEMINI_MODELS]
    groq = [(m, lambda s, u, sc, m=m: _groq(m, s, u, sc)) for m in GROQ_MODELS]
    return gemini + groq if agent in GEMINI_FIRST else groq + gemini


def ask(system: str, user: str, schema: type[T], agent: str = "default") -> T:
    failures = []
    for name, call in _providers(agent):
        for attempt in (1, 2):
            try:
                return schema.model_validate_json(call(system, user, schema))
            except ValidationError as e:
                failures.append(f"{name} attempt {attempt}: invalid output ({e.error_count()} errors)")
            except Exception as e:  # missing key, busy (503), rate limit (429), timeout, network: next model
                failures.append(f"{name}: {type(e).__name__}: {str(e)[:200]}")
                break
    raise LLMError("All LLM models failed:\n" + "\n".join(failures))


if __name__ == "__main__":  # self-check: cd tecnoverse && python -m core.llm   (makes real calls)
    assert _seconds("2.07s") == 2.07 and _seconds("1m3.5s") == 63.5 and _seconds("120ms") == 0.12
    assert _providers("profiler")[0][0].startswith("gemini") and _providers("monitor")[0][0] == GROQ_MODELS[0]

    class Capital(BaseModel):
        city: str

    for agent in ("monitor", "profiler"):
        out = ask("Answer in JSON.", "What is the capital of Sweden?", Capital, agent=agent)
        assert "stockholm" in out.city.lower(), out
    print("ok")
