"""JSON schemas passed to Gemini's structured-output mode for the final prompts.

The model is forced to emit one of two shapes: the normal output for the mode,
or {"error": "..."} for input that is not study material. This stops the
model from producing structurally broken JSON (for example a stray
"warnings" key inside each quiz question, seen on long PDF notes).
"""

_S = {"type": "string"}
_WARN = {"type": "array", "items": _S}
_ERROR = {"type": "object", "properties": {"error": _S}, "required": ["error"]}


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or list(props)}


_MODE_SCHEMAS = {
    "explain": _obj({
        "explanation": _S,
        "analogy": _S,
        "key_terms": {"type": "array", "items": _obj({"term": _S, "meaning": _S})},
        "warnings": _WARN,
    }),
    "summarize": _obj({
        "title": _S,
        "summary_points": {"type": "array", "items": _S},
        "one_line": _S,
        "warnings": _WARN,
    }),
    "flashcards": _obj({
        "flashcards": {"type": "array", "items": _obj({"front": _S, "back": _S})},
        "warnings": _WARN,
    }),
    "quiz": _obj({
        "questions": {"type": "array", "items": _obj({
            "question": _S,
            "options": _obj({k: _S for k in "ABCD"}),
            "answer": {"type": "string", "enum": list("ABCD")},
            "explanation": _S,
        })},
        "warnings": _WARN,
    }),
}


_LIST_KEY = {"flashcards": "flashcards", "quiz": "questions"}


def response_schema(mode, count=None):
    import copy

    schema = copy.deepcopy(_MODE_SCHEMAS[mode])
    if count and mode in _LIST_KEY:
        arr = schema["properties"][_LIST_KEY[mode]]
        arr["minItems"] = arr["maxItems"] = int(count)
    return {"anyOf": [schema, _ERROR]}
