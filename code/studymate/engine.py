"""Loads prompt files, fills the variables, calls the model, parses the result."""
import json
from pathlib import Path

from .parse import extract_json, validate, word_count
from .schemas import response_schema

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "prompts"

MODES = {
    "explain": ("P1", "P1_explain", "Explain"),
    "summarize": ("P2", "P2_summarize", "Summarize"),
    "flashcards": ("P3", "P3_flashcards", "Flashcards"),
    "quiz": ("P4", "P4_quiz", "Quiz"),
}
LEVELS = ["school (class 11-12)", "undergraduate", "postgraduate"]
MAX_CHARS = 20000


def load_prompt(version, mode):
    folder = PROMPTS / version
    raw = (folder / f"{MODES[mode][1]}.md").read_text(encoding="utf-8")
    body = raw.split("## SYSTEM", 1)[1]
    system, user = body.split("## USER", 1)
    system = system.strip()
    if system.lower() == "none":
        system = ""
    settings = json.loads((folder / "settings.json").read_text())
    return {"system": system, "user": user.strip(), "settings": settings, "raw": raw}


def render(template, notes, level, count):
    # plain replace (not str.format) so the JSON braces in the prompts are safe
    return template.replace("{notes}", notes).replace("{level}", level).replace("{count}", str(count))


def run(client, mode, notes, level="undergraduate", count=5, version="final"):
    notes = (notes or "").strip()
    result = {"mode": mode, "version": version, "level": level, "count": count,
              "input_words": word_count(notes), "mock": getattr(client, "is_mock", False)}
    if not notes:
        result.update(raw="", parsed=None, json_how=None, issues=["empty input (blocked before API call)"],
                      error_msg="Paste some notes or upload a file first.", latency=0.0, model=None)
        return result
    truncated = len(notes) > MAX_CHARS
    notes = notes[:MAX_CHARS]
    p = load_prompt(version, mode)
    system = render(p["system"], notes, level, count)
    user = render(p["user"], notes, level, count)
    json_mode = p["settings"].get("json_mode", False)
    # Structured output only for the final prompts, so the Prompt Lab still shows
    # how the older versions behave on their own.
    schema = response_schema(mode, count) if json_mode and version == "final" else None
    out = client.generate(system, user, temperature=p["settings"].get("temperature"),
                          json_mode=json_mode, schema=schema)
    parsed, how = extract_json(out["text"])
    issues = validate(mode, parsed, count if mode in ("flashcards", "quiz") else None) if parsed is not None else ["no parseable JSON"]
    error_msg = parsed.get("error") if isinstance(parsed, dict) and "error" in parsed else None
    result.update(raw=out["text"], parsed=parsed, json_how=how, issues=issues, error_msg=error_msg,
                  latency=out["latency"], model=out["model"], truncated=truncated,
                  output_words=word_count(out["text"]))
    return result
