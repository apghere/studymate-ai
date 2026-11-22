"""Runs the prompt-version experiment (v1, v2, v3) and the test suite, with real model calls.

    export GEMINI_API_KEY=...        (never commit this)
    python code/run_experiments.py              # both
    python code/run_experiments.py --only tests
    python code/run_experiments.py --mock       # offline dry run, NOT for submission

Writes results/iteration.json, results/tests.json and test-data/outputs/*.json
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studymate.engine import ROOT, run  # noqa: E402
from studymate.llm import GeminiClient, MockClient  # noqa: E402
from studymate.parse import output_text, word_count  # noqa: E402

TD = ROOT / "test-data"
OUT = TD / "outputs"
RES = ROOT / "results"
HINGLISH = {"hai", "hota", "hoti", "hote", "mein", "jisme", "isliye", "lekin", "sakte", "padta",
            "wapas", "nahi", "paas", "aur", "ek", "karna", "jaata", "kisi", "dono", "shuru"}


def notes(name):
    return (TD / "notes" / f"{name}.txt").read_text(encoding="utf-8").strip()


def short_actual(r):
    o = r["parsed"]
    if r.get("error_msg"):
        return f'Error: "{r["error_msg"][:70]}"'
    if o is None:
        return f"No parseable JSON ({r.get('output_words', 0)} words of free text)"
    m = r["mode"]
    w = len(o.get("warnings") or [])
    ws = f", {w} warning(s)" if w else ""
    if m == "explain":
        return f"{word_count(o.get('explanation', ''))}-word explanation, {len(o.get('key_terms') or [])} key terms{ws}"
    if m == "summarize":
        pts = o.get("summary_points") or []
        longest = max((word_count(p) for p in pts if isinstance(p, str)), default=0)
        return f"{len(pts)} points (longest {longest} words){ws}"
    if m == "flashcards":
        return f"{len(o.get('flashcards') or [])} cards{ws}"
    if m == "quiz":
        qs = o.get("questions") or []
        keys = "".join(str(q.get("answer", "?")) for q in qs if isinstance(q, dict))
        return f"{len(qs)} MCQs, answer key {keys}{ws}"
    return "?"


def apply_checks(test, r):
    c, o = test["checks"], r["parsed"]
    reasons = []
    if c["expect"] == "error":
        if not r.get("error_msg"):
            reasons.append("expected an error message but got study material")
        return reasons
    if r.get("error_msg"):
        return ["returned an error for valid notes"]
    if o is None:
        return ["no parseable JSON"]
    reasons += r["issues"]
    text = output_text(r["mode"], o).lower()
    if c.get("keywords_any") and not any(k in text for k in c["keywords_any"]):
        reasons.append("none of the expected topic words: " + ", ".join(c["keywords_any"]))
    for k in c.get("keywords_all", []):
        if k not in text:
            reasons.append(f"missing '{k}'")
    pts = o.get("summary_points") or []
    if "min_points" in c and len(pts) < c["min_points"]:
        reasons.append(f"only {len(pts)} points (min {c['min_points']})")
    if "max_points" in c and len(pts) > c["max_points"]:
        reasons.append(f"{len(pts)} points for a one-sentence input (max {c['max_points']})")
    if c.get("english"):
        words = re.findall(r"[a-z]+", text)
        hits = [w for w in words if w in HINGLISH]
        if re.search(r"[ऀ-ॿ]", text) or (words and len(hits) / len(words) > 0.03):
            reasons.append(f"output not in English ({len(hits)} Hinglish words)")
    if c.get("warnings_nonempty") and not (o.get("warnings")):
        reasons.append("false claim not flagged in warnings")
    for f in c.get("forbid", []):
        if re.search(rf"\b{re.escape(f)}s?\b", text):
            reasons.append(f"followed injected instruction ('{f}' in output)")
    return reasons


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def iterate(client, sleep):
    cfg = json.loads((TD / "iteration_set.json").read_text())
    report = {"run_at": dt.datetime.now().isoformat(timespec="seconds"), "mock": client.is_mock, "versions": {}}
    for v in ("v1", "v2", "v3"):
        runs = []
        for n in cfg["notes"]:
            for m in cfg["modes"]:
                print(f"[iterate] {v} {m:<10} {n}", flush=True)
                r = run(client, m, notes(n), "undergraduate", cfg["count"], v)
                r.update(note=n, kind="normal")
                runs.append(r)
                save(OUT / "iteration" / f"{v}_{m}_{n}.json", r)
                time.sleep(sleep)
        for p in cfg["invalid_probes"]:
            print(f"[iterate] {v} {p['mode']:<10} {p['notes']} (invalid probe)", flush=True)
            r = run(client, p["mode"], notes(p["notes"]), "undergraduate", cfg["count"], v)
            r.update(note=p["notes"], kind="invalid")
            runs.append(r)
            save(OUT / "iteration" / f"{v}_{p['mode']}_{p['notes']}.json", r)
            time.sleep(sleep)
        normal = [r for r in runs if r["kind"] == "normal"]
        counted = [r for r in normal if r["mode"] in ("flashcards", "quiz")]
        words = [r.get("output_words", 0) for r in normal]
        metrics = {
            "n_normal": len(normal),
            "json_ok": sum(r["parsed"] is not None for r in normal),
            "json_clean": sum(r.get("json_how") == "clean" for r in normal),
            "schema_ok": sum(not r["issues"] for r in normal),
            "n_counted": len(counted),
            "count_ok": sum(not any("instead of" in i for i in r["issues"]) and r["parsed"] is not None for r in counted),
            "n_invalid": len(runs) - len(normal),
            "invalid_refused": sum(bool(r.get("error_msg")) for r in runs if r["kind"] == "invalid"),
            "words_min": min(words), "words_max": max(words), "words_avg": round(sum(words) / len(words)),
            "latency_avg": round(sum(r["latency"] for r in runs) / len(runs), 2),
            "models": sorted({r["model"] for r in runs if r["model"]}),
        }
        report["versions"][v] = {"metrics": metrics, "runs": runs}
        print(f"[iterate] {v} metrics: {json.dumps(metrics)}", flush=True)
    save(RES / "iteration.json", report)
    return report


def tests(client, sleep):
    suite = json.loads((TD / "tests.json").read_text())
    rows = []
    for t in suite:
        print(f"[tests] {t['id']} {t['short']}", flush=True)
        r = run(client, t["mode"], notes(t["notes"]), "undergraduate", t["count"], "final")
        reasons = apply_checks(t, r)
        row = {**t, "result": r, "actual": short_actual(r), "pass": not reasons, "fail_reasons": reasons}
        rows.append(row)
        save(OUT / f"{t['id']}.json", row)
        print(f"        -> {'PASS' if row['pass'] else 'FAIL'}: {row['actual']} {reasons if reasons else ''}", flush=True)
        time.sleep(sleep)
    report = {"run_at": dt.datetime.now().isoformat(timespec="seconds"), "mock": client.is_mock,
              "passed": sum(r["pass"] for r in rows), "total": len(rows),
              "models": sorted({r["result"]["model"] for r in rows if r["result"]["model"]}), "tests": rows}
    save(RES / "tests.json", report)
    print(f"[tests] {report['passed']}/{report['total']} passed", flush=True)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["iterate", "tests"], default=None)
    ap.add_argument("--mock", action="store_true", help="offline dry run (results flagged as mock)")
    ap.add_argument("--sleep", type=float, default=4.0, help="seconds between calls (free-tier rate limit)")
    a = ap.parse_args()
    client = MockClient() if a.mock else GeminiClient()
    if a.mock:
        a.sleep = 0
        print("*** MOCK MODE: results are fake and must not be submitted ***")
    if a.only in (None, "iterate"):
        iterate(client, a.sleep)
    if a.only in (None, "tests"):
        tests(client, a.sleep)


if __name__ == "__main__":
    main()
