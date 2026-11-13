"""One entry point for every agent: ask(system, user, Schema) -> validated Schema instance.

Calls Gemini with the Pydantic model as the JSON response schema. Each model gets
one retry on invalid output. If a model is busy, rate-limited or times out, the
next model in MODELS is tried. If all fail, raises LLMError rather than returning junk.

Scraped text must go in `user` (wrapped in <source_data> tags), never in `system`.
"""
import os
from typing import TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)

# First choice can be overridden in .env; the rest are fallbacks for when it is overloaded.
MODELS = list(dict.fromkeys([
    os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]))

_client = None


class LLMError(RuntimeError):
    pass


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30_000))  # ms
    return _client


def _gemini(model: str, system: str, user: str, schema: type[BaseModel]) -> str:
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


def ask(system: str, user: str, schema: type[T]) -> T:
    failures = []
    for model in MODELS:
        for attempt in (1, 2):
            try:
                return schema.model_validate_json(_gemini(model, system, user, schema))
            except ValidationError as e:
                failures.append(f"{model} attempt {attempt}: invalid output ({e.error_count()} errors)")
            except LLMError:
                raise
            except Exception as e:  # busy (503), rate limit (429), timeout (504), network: next model
                failures.append(f"{model}: {type(e).__name__}: {str(e)[:200]}")
                break
    raise LLMError("All Gemini models failed:\n" + "\n".join(failures))


if __name__ == "__main__":  # self-check: python tecnoverse/core/llm.py
    class Capital(BaseModel):
        city: str

    out = ask("Answer in JSON.", "What is the capital of Sweden?", Capital)
    assert "stockholm" in out.city.lower(), out
    print("ok:", out)
