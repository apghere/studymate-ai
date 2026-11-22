"""JSON extraction and schema checks for the four StudyMate outputs."""
import json
import re


def word_count(text):
    return len(re.findall(r"\S+", text or ""))


def _repair(s):
    """Fix a known model slip: a stray "warnings" key closing each list item,
    e.g.  ...}, "warnings": []}, {"question": ...  ->  ...}, {"question": ..."""
    return re.sub(r'\}\s*,\s*"warnings"\s*:\s*\[[^\]]*\]\s*\}', "}", s)


def extract_json(text):
    """Return (obj, how). how is 'clean', 'fenced', 'embedded', 'repaired' or None if no JSON found."""
    if not text:
        return None, None
    s = text.strip()
    try:
        return json.loads(s), "clean"
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip()), "fenced"
        except Exception:
            pass
    a, b = s.find("{"), s.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(s[a : b + 1]), "embedded"
        except Exception:
            pass
        try:
            return json.loads(_repair(s[a : b + 1])), "repaired"
        except Exception:
            pass
    return None, None


def _is_str(x):
    return isinstance(x, str) and x.strip() != ""


def validate(mode, obj, count=None):
    """Return a list of schema problems. Empty list = valid.
    An {"error": ...} object is reported as the single issue 'error_returned'."""
    if not isinstance(obj, dict):
        return ["not a JSON object"]
    if "error" in obj:
        return ["error_returned"]
    issues = []
    if mode == "explain":
        if not _is_str(obj.get("explanation")):
            issues.append("missing explanation")
        elif word_count(obj["explanation"]) > 200:
            issues.append(f"explanation is {word_count(obj['explanation'])} words (>200)")
        if not _is_str(obj.get("analogy")):
            issues.append("missing analogy")
        kt = obj.get("key_terms")
        if not isinstance(kt, list) or not (3 <= len(kt) <= 6):
            issues.append("key_terms not a list of 3-6")
        elif not all(isinstance(k, dict) and _is_str(k.get("term")) and _is_str(k.get("meaning")) for k in kt):
            issues.append("key_terms items malformed")
    elif mode == "summarize":
        pts = obj.get("summary_points")
        if not isinstance(pts, list) or not (1 <= len(pts) <= 6):
            issues.append("summary_points not a list of 1-6")
        else:
            long_pts = [p for p in pts if not _is_str(p) or word_count(p) > 25]
            if long_pts:
                issues.append(f"{len(long_pts)} summary point(s) over 25 words")
        if not _is_str(obj.get("one_line")):
            issues.append("missing one_line")
        elif word_count(obj["one_line"]) > 20:
            issues.append("one_line over 20 words")
    elif mode == "flashcards":
        cards = obj.get("flashcards")
        if not isinstance(cards, list):
            issues.append("flashcards missing")
        else:
            if count is not None and len(cards) != count:
                issues.append(f"{len(cards)} cards instead of {count}")
            if not all(isinstance(c, dict) and _is_str(c.get("front")) and _is_str(c.get("back")) for c in cards):
                issues.append("card(s) missing front/back")
            else:
                fronts = [c["front"].strip().lower() for c in cards]
                if len(set(fronts)) != len(fronts):
                    issues.append("duplicate card fronts")
    elif mode == "quiz":
        qs = obj.get("questions")
        if not isinstance(qs, list):
            issues.append("questions missing")
        else:
            if count is not None and len(qs) != count:
                issues.append(f"{len(qs)} questions instead of {count}")
            for i, q in enumerate(qs, 1):
                if not isinstance(q, dict) or not _is_str(q.get("question")):
                    issues.append(f"Q{i} malformed")
                    continue
                opts = q.get("options")
                if not isinstance(opts, dict) or sorted(opts.keys()) != ["A", "B", "C", "D"]:
                    issues.append(f"Q{i} options are not A-D")
                if q.get("answer") not in ("A", "B", "C", "D"):
                    issues.append(f"Q{i} answer not A-D")
            texts = [q.get("question", "").strip().lower() for q in qs if isinstance(q, dict)]
            if len(set(texts)) != len(texts):
                issues.append("duplicate questions")
    return issues


def output_text(mode, obj):
    """All human-readable text in an output, for keyword/language checks."""
    if not isinstance(obj, dict):
        return ""
    parts = []

    def walk(x):
        if isinstance(x, str):
            parts.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                if k != "warnings":
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return " ".join(parts)
