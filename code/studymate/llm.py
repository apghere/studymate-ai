"""Thin wrapper around the Gemini API (google-genai SDK).

The API key is read from the GEMINI_API_KEY environment variable or passed in.
It is never written to disk or to any output file.
"""
import os
import re
import time

# Tried in order. If a model is not available to the key (404) or its free
# quota is used up (429 after retries), the next one is tried.
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]


class LLMError(Exception):
    pass


def _retry_delay(msg, attempt):
    m = re.search(r"retry(?:Delay)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", msg, re.I)
    if m:
        return min(float(m.group(1)) + 1, 65)
    return min(5 * (2 ** attempt), 60)


class GeminiClient:
    is_mock = False

    def __init__(self, api_key=None, model=None):
        try:
            from google import genai
        except ImportError as e:  # pragma: no cover
            raise LLMError("google-genai is not installed: pip install -r requirements.txt") from e
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise LLMError("No Gemini API key found. Set GEMINI_API_KEY.")
        self._client = genai.Client(api_key=key)
        env_models = [m.strip() for m in os.environ.get("GEMINI_MODEL", "").split(",") if m.strip()]
        self.models = [model] if model else (env_models or list(DEFAULT_MODELS))
        self.model = self.models[0]

    def generate(self, system, user, temperature=None, json_mode=False, max_retries=4, schema=None):
        from google.genai import types

        cfg = {}
        if system:
            cfg["system_instruction"] = system
        if temperature is not None:
            cfg["temperature"] = temperature
        if json_mode:
            cfg["response_mime_type"] = "application/json"
            if schema:
                cfg["response_json_schema"] = schema
        config = types.GenerateContentConfig(**cfg) if cfg else None

        start_idx = self.models.index(self.model) if self.model in self.models else 0
        last_err = ""
        for model in self.models[start_idx:]:
            for attempt in range(max_retries):
                t0 = time.time()
                try:
                    resp = self._client.models.generate_content(model=model, contents=user, config=config)
                    try:
                        text = resp.text or ""
                    except Exception:
                        text = ""
                    self.model = model
                    return {"text": text, "latency": round(time.time() - t0, 2), "model": model}
                except Exception as e:  # SDK raises several error types
                    msg = str(e)
                    last_err = msg
                    if "404" in msg or "NOT_FOUND" in msg or "not found" in msg.lower():
                        break  # model not available -> next model
                    if any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE", "INTERNAL", "DEADLINE")):
                        time.sleep(_retry_delay(msg, attempt))
                        continue
                    if "API key" in msg or "PERMISSION_DENIED" in msg or "401" in msg or "403" in msg:
                        raise LLMError("The Gemini API key was rejected. Check it in Google AI Studio.") from e
                    raise LLMError(msg[:300]) from e
        raise LLMError(f"All models failed. Last error: {last_err[:300]}")


class MockClient:
    """Offline stand-in used only to dry-run the pipeline without an API key.
    Every result it produces is flagged mock=True and the report generator
    refuses to build a submission PDF from mock results."""

    is_mock = True
    model = "MOCK (not a real model)"

    def generate(self, system, user, temperature=None, json_mode=False, max_retries=1, schema=None):
        import json

        u = user.lower()
        notes = user.split("<notes>")[-1] if "<notes>" in user else user
        bad = len(re.findall(r"[a-z]{3,}", notes.lower())) < 4 or "eggs" in u
        if not system:
            text = "Here is some help with your notes.\n\n" + "Lorem ipsum " * 40
        elif bad and json_mode:
            text = json.dumps({"error": "Please paste study notes, such as a paragraph from a textbook."})
        elif "flashcards" in u:
            n = int(re.search(r"number of flashcards: (\d+)", u).group(1))
            text = json.dumps({"flashcards": [{"front": f"Mock question {i+1}?", "back": f"Mock answer {i+1}."} for i in range(n)], "warnings": []})
        elif "number of questions" in u:
            n = int(re.search(r"number of questions: (\d+)", u).group(1))
            text = json.dumps({"questions": [{"question": f"Mock question {i+1}?", "options": {"A": "a", "B": "b", "C": "c", "D": "d"}, "answer": "ABCD"[i % 4], "explanation": "Mock."} for i in range(n)], "warnings": []})
        elif "summary" in (system or "").lower():
            text = json.dumps({"title": "Mock", "summary_points": ["Mock point one.", "Mock point two.", "Mock point three."], "one_line": "Mock takeaway.", "warnings": []})
        else:
            text = json.dumps({"explanation": "Mock explanation " * 10, "analogy": "Mock analogy.", "key_terms": [{"term": "a", "meaning": "b"}] * 3, "warnings": []})
        if not json_mode and system:
            text = "```json\n" + text + "\n```"
        return {"text": text, "latency": 0.01, "model": self.model}
