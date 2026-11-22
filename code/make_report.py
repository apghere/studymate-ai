"""Builds the Milestone 2 deliverables from team.json + results/*.json:

  docs/M2_<TeamID>_StudyMateAI.pdf        (7 sections, upload at Q21)
  docs/<TeamName>_BMC.pdf                 (supporting document: Business Model Canvas, upload at Q16)
  docs/form_answers.md                    (copy-paste answers for the form)

    python code/make_report.py
Screenshots are optional inputs: docs/screenshots/T01.png (any test id) and docs/screenshots/repo.png
"""
import argparse
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagrams  # noqa: E402
from studymate.engine import MODES, load_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS, SHOTS, RES = ROOT / "docs", ROOT / "docs" / "screenshots", ROOT / "results"

FD = "/usr/share/fonts/truetype/dejavu/"
try:
    pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")
    BODY, BOLD, MONO = "DV", "DVB", "DVM"
except Exception:  # fonts not present (e.g. Windows): fall back to built-ins
    BODY, BOLD, MONO = "Helvetica", "Helvetica-Bold", "Courier"

ss = getSampleStyleSheet()
S = {
    "body": ParagraphStyle("b", parent=ss["Normal"], fontName=BODY, fontSize=9.5, leading=13.5, spaceAfter=4),
    "small": ParagraphStyle("s", parent=ss["Normal"], fontName=BODY, fontSize=8, leading=10.5),
    "cell": ParagraphStyle("c", parent=ss["Normal"], fontName=BODY, fontSize=7.8, leading=10),
    "cellb": ParagraphStyle("cb", parent=ss["Normal"], fontName=BOLD, fontSize=7.8, leading=10, textColor=colors.white),
    "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName=BOLD, fontSize=15, leading=19, spaceBefore=4, spaceAfter=8, textColor=colors.HexColor("#1E1B4B")),
    "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=BOLD, fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#312E81")),
    "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName=BOLD, fontSize=9.8, leading=13, spaceBefore=6, spaceAfter=2),
    "mono": ParagraphStyle("m", parent=ss["Code"], fontName=MONO, fontSize=7, leading=9, backColor=colors.HexColor("#F8FAFC"),
                           borderColor=colors.HexColor("#CBD5E1"), borderWidth=0.5, borderPadding=4, spaceBefore=2, spaceAfter=6),
    "title": ParagraphStyle("t", parent=ss["Title"], fontName=BOLD, fontSize=24, leading=30, textColor=colors.HexColor("#1E1B4B")),
    "center": ParagraphStyle("ce", parent=ss["Normal"], fontName=BODY, fontSize=10.5, leading=15, alignment=TA_CENTER),
    "warnbox": ParagraphStyle("w", parent=ss["Normal"], fontName=BOLD, fontSize=9, leading=12, textColor=colors.HexColor("#B91C1C"),
                              backColor=colors.HexColor("#FEF2F2"), borderColor=colors.HexColor("#DC2626"), borderWidth=1, borderPadding=6, spaceBefore=4, spaceAfter=8),
}
WARNINGS = []


def P(text, style="body"):
    return Paragraph(text, S[style])


def mono(text):
    t = escape(text).replace("\n", "<br/>").replace("  ", "&nbsp;&nbsp;")
    return Paragraph(t, S["mono"])


def compact_json(obj):
    """One line per top-level key / list item, so sample outputs stay short in the PDF."""
    if not isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False)
    out = ["{"]
    keys = list(obj)
    for i, k in enumerate(keys):
        v, comma = obj[k], "," if i < len(keys) - 1 else ""
        if isinstance(v, list) and v:
            out.append(f'  "{k}": [')
            out += [f"    {json.dumps(x, ensure_ascii=False)}" + ("," if j < len(v) - 1 else "") for j, x in enumerate(v)]
            out.append("  ]" + comma)
        else:
            out.append(f'  "{k}": {json.dumps(v, ensure_ascii=False)}{comma}')
    return "\n".join(out + ["}"])


def short(s, n=70):
    return s if len(s) <= n else s[: n - 1] + "…"


def table(rows, widths, header=True, zebra=True):
    data = [[c if not isinstance(c, str) else Paragraph(escape(c) if not c.startswith("<") else c,
                                                         S["cellb"] if (header and i == 0) else S["cell"]) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3730A3")))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F7FF")))
    t.setStyle(TableStyle(st))
    return t


def img(path, max_w, max_h):
    from reportlab.lib.utils import ImageReader

    w, h = ImageReader(str(path)).getSize()
    s = min(max_w / w, max_h / h)
    return Image(str(path), width=w * s, height=h * s)


def missing(msg):
    WARNINGS.append(msg)
    return P("MISSING: " + escape(msg), "warnbox")


def todo(v):
    return isinstance(v, str) and "TODO" in v


# ---------------------------------------------------------------- data
def load():
    team = json.loads((ROOT / "team.json").read_text())
    it = json.loads((RES / "iteration.json").read_text())
    ts = json.loads((RES / "tests.json").read_text())
    return team, it, ts


def model_name(it, ts):
    ms = sorted(set(ts["models"]) | {m for v in it["versions"].values() for m in v["metrics"]["models"]})
    return ", ".join(ms)


def metric_line(m):
    return (f"JSON readable in {m['json_ok']}/{m['n_normal']} runs ({m['json_clean']} with no cleanup); "
            f"schema valid {m['schema_ok']}/{m['n_normal']}; exact card/question count {m['count_ok']}/{m['n_counted']}; "
            f"invalid inputs refused {m['invalid_refused']}/{m['n_invalid']}; output length {m['words_min']}-{m['words_max']} words "
            f"(avg {m['words_avg']}); avg latency {m['latency_avg']} s")


CHANGES = {
    "v1": "First prompt: a one-line instruction per mode, e.g. \"Make flashcards from this: {notes}\". No system prompt, default settings.",
    "v2": "Added a role (StudyMate tutor), the student level, \"use only the notes\", length and count limits, and an explicit JSON output schema written in the prompt.",
    "v3": "Added one worked example per prompt (one-shot), a rule that returns {\"error\"} for non-study input, a guard against instructions hidden inside <notes>, a \"warnings\" field for false statements and an English-output rule. Settings: temperature 0.2 and JSON response mode.",
}


def why(v, it):
    if v == "v1":
        return "Starting point from the Milestone 1 idea."
    prev = it["versions"]["v1" if v == "v2" else "v2"]["metrics"]
    if v == "v2":
        return (f"v1 gave free text: only {prev['json_ok']}/{prev['n_normal']} outputs were machine-readable and length varied "
                f"from {prev['words_min']} to {prev['words_max']} words, so the app could not show cards or score a quiz.")
    return (f"v2 output still needed cleanup ({prev['n_normal'] - prev['json_clean']}/{prev['n_normal']} not clean JSON), "
            f"schema valid {prev['schema_ok']}/{prev['n_normal']}, and it refused only {prev['invalid_refused']}/{prev['n_invalid']} "
            f"invalid inputs. It had no protection against wrong facts or hidden instructions in notes.")


MODULES = [
    ("Input", "Paste notes, or upload .txt / .md / text-based .pdf (pypdf); blocks empty input; 20,000-character limit", []),
    ("Explain (P1)", "Simple explanation, analogy, key terms, warnings", ["T01", "T05", "T10"]),
    ("Summarize (P2)", "3-6 revision points and a one-line takeaway", ["T02", "T08", "T12"]),
    ("Flashcards (P3)", "Exactly N cards shown as flip cards; Anki CSV export", ["T03", "T07", "T09"]),
    ("Quiz (P4)", "Exactly N MCQs, student answers, instant score with explanations", ["T04", "T06", "T11"]),
    ("Input validation", "Returns a clear error for non-study input instead of making things up", ["T13", "T14"]),
    ("Export", "Download any result as Markdown or JSON", []),
    ("Prompt Lab", "Runs v1 and final prompt on the same notes side by side", []),
]


def module_status(ts):
    by = {t["id"]: t for t in ts["tests"]}
    rows = []
    for name, what, ids in MODULES:
        if not ids:
            rows.append((name, what, "Working", "Checked by hand in the deployed app (not in the automated test table)"))
            continue
        normal = [by[i] for i in ids if by[i]["type"] in ("Normal", "Invalid")]
        fails = [by[i] for i in ids if not by[i]["pass"]]
        ok_normal = sum(t["pass"] for t in normal)
        status = "Working" if ok_normal == len(normal) else ("Partly working" if ok_normal else "Not working")
        note = "Tests " + ", ".join(ids) + (": all passed" if not fails else
                                              "; failed: " + ", ".join(f"{t['id']} ({t['fail_reasons'][0]})" for t in fails))
        rows.append((name, what, status, note))
    return rows


# ---------------------------------------------------------------- sections
def cover(team, story):
    story += [Spacer(1, 1.2 * cm), P("SCSE4041 Prompt Engineering · Mini Project", "center"),
              P("Milestone 2: Prompt Design, Prototype, Testing and Demonstration", "center"), Spacer(1, 0.8 * cm),
              P(escape(team["project_title"]), "title"),
              P("A prompt-engineering study assistant that turns a student's own notes into explanations, summaries, flashcards and quizzes.", "center"),
              Spacer(1, 0.8 * cm)]
    info = [["Team ID", team["team_id"]], ["Team name", team["team_name"]], ["Project title", team["project_title"]],
            ["Batch", team["batch"]], ["Faculty", team["faculty"]]]
    story.append(table(info, [4 * cm, 12 * cm], header=False, zebra=False))
    story.append(Spacer(1, 0.4 * cm))
    mem = [["Member", "Enrollment no.", "Role"]] + [[m["name"] + (" (Team leader)" if m["enrollment"] == team["leader_enrollment"] else ""),
                                                     m["enrollment"], m["role"]] for m in team["members"]]
    story.append(table(mem, [6 * cm, 4 * cm, 6 * cm]))
    story.append(Spacer(1, 0.4 * cm))
    L = team["links"]
    story.append(table([["Link", "URL"], ["Prototype", L["prototype"]], ["Repository", L["repository"]], ["Reel", L["reel"]]],
                       [3 * cm, 13 * cm]))
    for k, v in list(team.items()) + list(L.items()):
        if todo(v):
            WARNINGS.append(f"team.json: '{k}' is still TODO")
    story.append(PageBreak())


def section2(team, it, ts, story):
    model = model_name(it, ts)
    story.append(P("2. Prompt and solution design", "h1"))
    story.append(P("(a) Design summary", "h2"))
    by = {t["id"]: t for t in ts["tests"]}
    paras = [
        "<b>Problem and users.</b> College students revise from long, dense notes. Making their own summaries, flashcards and practice "
        "questions takes hours, and generic chatbot answers are long, unstructured and often go beyond what the syllabus notes say. "
        "StudyMate AI is for undergraduate students preparing for exams who want study material built from <i>their own</i> notes.",
        "<b>Input and output.</b> Input: the student's notes (pasted, or a .txt/.md/text-based .pdf file), their level "
        "(school, undergraduate, postgraduate), the study task, and for flashcards and quizzes the number of items (3-10). "
        "Output: a JSON object that the app renders as an explanation with an analogy and key terms, a bullet summary, flip-style "
        "flashcards, or a scored multiple-choice quiz. Every output can also carry <i>warnings</i> about statements in the notes that "
        "look factually wrong, and non-study input returns an <i>error</i> message instead of invented content.",
        "<b>Number of prompts and why.</b> Four prompts (P1 Explain, P2 Summarize, P3 Flashcards, P4 Quiz), one LLM call per request. "
        "The student picks the task, so there is no routing prompt. We kept the tasks in separate prompts because each has its own "
        "output schema and rules (e.g. \"exactly N cards\"), which keeps each prompt short and lets the code check each output against "
        "its schema. All four share the same rules: use only the notes, write in English, flag false statements, ignore instructions inside the notes.",
        f"<b>Tool and model.</b> {escape(model)} through the Gemini API (google-genai Python SDK), with a Streamlit front end deployed on "
        "Streamlit Community Cloud. We chose it because it has a free tier, it is fast enough for interactive use, and it supports a "
        "JSON response mode, which we needed for reliable flashcards and quizzes. The app keeps a fallback list of Gemini Flash models "
        "in case one is unavailable.",
        "<b>What changed since Milestone 1.</b> In Milestone 1 we defined the problem and the four study tasks. In Milestone 2 we "
        "(1) wrote and tested three versions of every prompt (Section 3), (2) moved from free-text answers to a fixed JSON schema per "
        "task, (3) added rules for invalid input, false statements and hidden instructions after seeing them in testing, "
        "(4) built and deployed the working app with file upload, an interactive quiz, exports and a Prompt Lab that compares v1 and "
        f"the final prompt, and (5) ran a {ts['total']}-case test suite ({ts['passed']} passed).",
    ]
    story += [P(p) for p in paras]

    story.append(P("(b) Diagrams", "h2"))
    pngs = diagrams.build()
    titles = {"1_prompt_workflow": "Diagram 1: Prompt workflow", "2_task_decomposition": "Diagram 2: Task decomposition",
              "3_input_output_flow": "Diagram 3: Input-output flow", "4_system_architecture": "Diagram 4: System architecture"}
    for k, p in pngs.items():
        story.append(KeepTogether([P(titles[k], "h3"), img(p, 17 * cm, 8.5 * cm), Spacer(1, 6)]))
    story.append(P("No agents or retrieval are used, so there is no agent loop or RAG diagram.", "small"))

    story.append(PageBreak())
    story.append(P("(c) Prompt sheets", "h2"))
    sample = {"explain": "T01", "summarize": "T02", "flashcards": "T03", "quiz": "T04"}
    purpose = {"explain": "Explain the notes simply, with an analogy and key terms.",
               "summarize": "Condense the notes into 3-6 short revision points and a one-line takeaway.",
               "flashcards": "Turn the notes into exactly N question/answer flashcards for active recall.",
               "quiz": "Write exactly N multiple-choice questions with an answer key and explanations."}
    fmt = {"explain": '{"explanation", "analogy", "key_terms": [{"term", "meaning"}], "warnings": []} or {"error"}',
           "summarize": '{"title", "summary_points": [...], "one_line", "warnings": []} or {"error"}',
           "flashcards": '{"flashcards": [{"front", "back"}], "warnings": []} or {"error"}',
           "quiz": '{"questions": [{"question", "options": {A,B,C,D}, "answer", "explanation"}], "warnings": []} or {"error"}'}
    for mode, (pid, fname, label) in MODES.items():
        p = load_prompt("final", mode)
        st_ = p["settings"]
        vars_ = "{notes}: the student's notes (pasted or extracted from the file). {level}: school (class 11-12), undergraduate or postgraduate, chosen in the sidebar."
        if mode in ("flashcards", "quiz"):
            vars_ += " {count}: number of items, 3-10, chosen with the slider."
        rows = [["Field", "Value"], ["Prompt ID and name", f"{pid} - {label}"],
                ["Step in workflow", f"Step 3 of Diagram 1: called when the student chooses \"{label}\""],
                ["Purpose", purpose[mode]], ["Tool and model", f"Gemini API (google-genai SDK) - {model}"],
                ["Settings", f"temperature {st_['temperature']}; response_mime_type = application/json; other settings default"],
                ["Variables", vars_], ["Number of examples", "1 (one worked example inside the system prompt)"],
                ["Output format", fmt[mode]]]
        story.append(P(f"Prompt sheet {pid}: {label}", "h3"))
        story.append(table(rows, [3.6 * cm, 13.4 * cm]))
        story.append(P("<b>Full system prompt</b>", "small"))
        story.append(mono(p["system"]))
        story.append(P("<b>Full user prompt template</b>", "small"))
        story.append(mono(p["user"]))
        t = by[sample[mode]]
        story.append(P(f"<b>Sample run</b> (test {t['id']}, real input and actual output, model {escape(str(t['result']['model']))}, "
                       f"{t['result']['latency']} s)", "small"))
        notes = (ROOT / "test-data" / "notes" / f"{t['notes']}.txt").read_text().strip()
        story.append(mono(f"Input notes ({len(notes.split())} words), level = undergraduate" +
                          (f", count = {t['count']}" if mode in ("flashcards", "quiz") else "") + ":\n" + notes))
        out = t["result"]["parsed"]
        story.append(mono("Actual output:\n" + (compact_json(out) if out is not None else t["result"]["raw"])))
        story.append(PageBreak())


def section3(it, ts, story):
    story.append(P("3. Implementation", "h1"))
    story.append(P("What is built", "h2"))
    story.append(P("A Streamlit web app (code/app.py) with three tabs. <b>Study</b>: the student pastes notes or uploads a file, picks a level, "
                   "a task and a count, and gets the result rendered as text, flip cards or an interactive quiz with a score, plus downloads. "
                   "<b>Prompt Lab</b>: runs the same notes through prompt v1 and the final prompt side by side, with word count, latency and "
                   "whether the output is valid JSON. <b>How it works</b>: a short description of the pipeline. "
                   "The core is a small Python package (code/studymate/): <i>engine.py</i> loads the prompt files from prompts/final/ and fills "
                   "the variables, <i>llm.py</i> calls Gemini with retry and model fallback, and <i>parse.py</i> extracts the JSON and checks it "
                   "against each task's schema. Prompts live in plain .md files, so changing a prompt does not need a code change. "
                   "<i>code/run_experiments.py</i> runs the prompt-version experiment and the test suite with real model calls and saves every "
                   "output in test-data/outputs/."))
    story.append(P("Module status", "h2"))
    rows = [["Module", "What it does", "Status", "Notes"]] + [list(r) for r in module_status(ts)]
    story.append(table(rows, [2.8 * cm, 5.6 * cm, 2.2 * cm, 6.4 * cm]))
    story.append(P("Prompt iteration log", "h2"))
    story.append(P(f"Each version was run on the same 3 notes (photosynthesis, TCP vs UDP, normalization) for all 4 tasks "
                   f"(12 runs, count = 5) plus 2 invalid inputs (random characters, a shopping list): 14 real calls per version, "
                   f"run on {it['run_at'][:10]}. The numbers are counted automatically by code/run_experiments.py; raw outputs are in "
                   f"test-data/outputs/iteration/.", "small"))
    rows = [["Version", "What changed", "Why it was changed", "Result after the change (measured)"]]
    for v in ("v1", "v2", "v3"):
        rows.append([v + (" (final)" if v == "v3" else ""), CHANGES[v], why(v, it), metric_line(it["versions"][v]["metrics"])])
    story.append(table(rows, [1.5 * cm, 5 * cm, 5 * cm, 5.5 * cm]))
    story.append(Spacer(1, 6))
    for v in ("v1", "v2", "v3"):
        story.append(P(f"Full text of {v}" + (" (final; identical to prompts/final/)" if v == "v3" else ""), "h3"))
        s = json.loads((ROOT / "prompts" / v / "settings.json").read_text())
        story.append(P(f"Settings: temperature {s['temperature'] if s['temperature'] is not None else 'default'}, "
                       f"JSON response mode {'on' if s['json_mode'] else 'off'}.", "small"))
        for mode, (pid, fname, label) in MODES.items():
            raw = (ROOT / "prompts" / v / f"{fname}.md").read_text().strip()
            story.append(mono(raw))
    story.append(PageBreak())


LIMITS = [
    ("Scanned PDFs are not supported: pypdf only reads PDFs that contain text, so photos of handwritten notes give no input.",
     "Add OCR for image PDFs (Gemini image input or Tesseract) in Milestone 3."),
    ("Output can only be as correct as the notes. The \"warnings\" rule depends on the model noticing an error; it is not a fact-checker. ",
     "Try a second verification prompt that checks each generated answer against the notes and flags unsupported claims."),
    ("The public demo uses a free-tier Gemini key, so many users at once can hit the rate limit (HTTP 429). The app retries and "
     "falls back to another model, and users can paste their own key.",
     "Cache results for repeated notes and add a per-session request limit."),
    ("No saved progress: flashcards and quiz scores disappear when the page is closed.",
     "Save decks and scores and add spaced-repetition review in Milestone 3."),
]


def section4(ts, story):
    story.append(P("4. Demonstration and testing", "h1"))
    types = {t: sum(1 for x in ts["tests"] if x["type"] == t) for t in ("Normal", "Edge", "Invalid")}
    story.append(P(f"{ts['total']} test inputs ({types['Normal']} normal, {types['Edge']} edge, {types['Invalid']} invalid), "
                   f"all run through the final prompts on {ts['run_at'][:10]} with {escape(', '.join(ts['models']))}. "
                   f"Pass/Fail is decided by automatic checks in code/run_experiments.py (schema, exact counts, topic words, "
                   f"language, warnings, forbidden words), not by hand. <b>Result: {ts['passed']}/{ts['total']} passed.</b> "
                   f"Inputs are in test-data/notes/ and every saved output is in test-data/outputs/T01.json to T{ts['total']:02d}.json.", "small"))
    rows = [["Test no.", "Input (short)", "Type", "Expected output", "Actual output (short)", "Pass / Fail"]]
    for t in ts["tests"]:
        act = t["actual"] + ("" if t["pass"] else " - " + "; ".join(t["fail_reasons"]))
        rows.append([t["id"], t["short"], t["type"], t["expected"], act, "Pass" if t["pass"] else "Fail"])
    tb = table(rows, [1.3 * cm, 3.8 * cm, 1.4 * cm, 3.8 * cm, 5.2 * cm, 1.5 * cm])
    st = []
    for i, t in enumerate(ts["tests"], 1):
        st.append(("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#15803D" if t["pass"] else "#B91C1C")))
    tb.setStyle(TableStyle(st))
    story.append(tb)

    story.append(P("Screenshots of real runs", "h2"))
    shots = sorted(p for p in SHOTS.glob("T*.png")) + sorted(p for p in SHOTS.glob("T*.jpg"))
    by = {t["id"]: t for t in ts["tests"]}
    if len(shots) < 2:
        story.append(missing("Add 2-3 screenshots of real app runs as docs/screenshots/T01.png, T04.png, T13.png "
                             "(name each file after the test number it shows), then re-run make_report.py."))
    for p in shots[:3]:
        tid = p.stem.split("_")[0].upper()
        cap = f"Screenshot: test {tid}" + (f" - {by[tid]['short']}" if tid in by else "")
        story.append(KeepTogether([img(p, 16 * cm, 10 * cm), P(escape(cap), "small"), Spacer(1, 8)]))

    story.append(P("Known limitations and what we will try next", "h2"))
    rows = [["Limitation", "What we will try next"]] + [list(x) for x in LIMITS]
    fails = [t for t in ts["tests"] if not t["pass"]]
    if fails:
        rows.append(["Failed tests in this run: " + "; ".join(f"{t['id']} ({short(t['fail_reasons'][0])})" for t in fails),
                     "Adjust the rule for that case in the prompt (v4) and re-run the same test."])
    story.append(table(rows, [9 * cm, 8 * cm]))
    story.append(PageBreak())


def section5(story):
    story.append(P("5. Repository", "h1"))
    shot = next((p for p in [SHOTS / "repo.png", SHOTS / "repo.jpg"] if p.exists()), None)
    if shot:
        story.append(img(shot, 16 * cm, 11 * cm))
    else:
        story.append(missing("Add a screenshot of the GitHub repository page as docs/screenshots/repo.png, then re-run make_report.py."))
    story.append(P("What changed since Milestone 1", "h2"))
    for line in [
        "Added prompts/v1, v2, v3 and final/ with one file per prompt (P1-P4) and a settings.json per version.",
        "Added the working Streamlit app (code/app.py) and the core package code/studymate/ (prompt loading, Gemini client, JSON/schema checks).",
        "Added test-data/ with 14 input notes, tests.json, and every real model output saved in test-data/outputs/.",
        "Added code/run_experiments.py (version experiment + test suite) and code/make_report.py (builds this PDF from the saved results).",
        "Added docs/ with the four diagrams and this PDF, and a dated CHANGELOG.md.",
    ]:
        story.append(P("• " + escape(line)))
    story.append(PageBreak())


def tech_report(team, it, ts, story, standalone):
    model = model_name(it, ts)
    if standalone:
        story.append(P(f"{escape(team['project_title'])}: Technical Report", "h1"))
        story.append(P(f"Team {escape(team['team_id'])} · {escape(team['team_name'])} · {escape(team['course'])}", "small"))
    else:
        story.append(P("6. Supporting document", "h1"))
        story.append(P(f"Type: Technical report (also uploaded separately at Q16 as {escape(tech_name(team))}).", "small"))
    story.append(P("1. Architecture", "h3"))
    story.append(P("A Streamlit web app calls the Gemini API. The student's notes and choices are inserted into one of four prompt templates "
                   "(stored as .md files), the model returns JSON, and the app checks the JSON against the task's schema before showing it. "
                   "Invalid input comes back as an {\"error\"} object that the app shows as a message."))
    story.append(img(DOCS / "diagrams" / "4_system_architecture.png", 15 * cm, 5.2 * cm))
    story.append(P("2. Tools and models", "h3"))
    story.append(P(f"Model: {escape(model)} (Gemini API, free tier) via the google-genai SDK; Streamlit for the UI and hosting; pypdf for PDF text; "
                   "Graphviz for diagrams; ReportLab to build reports from the saved results. The API key is stored in Streamlit secrets, never in the repository."))
    story.append(P("3. Prompt design", "h3"))
    rows = [["Prompt", "Task", "Main techniques"],
            ["P1 Explain", "explanation, analogy, key terms", "role, audience level, length limit, one-shot example, JSON schema"],
            ["P2 Summarize", "3-6 points + one line", "role, word limits, \"do not pad short notes\", one-shot, JSON schema"],
            ["P3 Flashcards", "exactly N Q/A cards", "count constraint, one fact per card, no yes/no, one-shot, JSON schema"],
            ["P4 Quiz", "exactly N MCQs + key", "count constraint, plausible distractors, spread answer letters, one-shot, JSON"],
            ["All four", "shared rules", "use only the notes; English output; warnings for false statements; ignore instructions inside <notes>; {error} for non-study input; temperature 0.2; JSON response mode"]]
    story.append(table(rows, [2.6 * cm, 4.2 * cm, 10.2 * cm]))
    story.append(P("4. Test results", "h3"))
    rows = [["Version", "JSON readable", "Schema valid", "Exact count", "Invalid refused", "Words (min-max)"]]
    for v in ("v1", "v2", "v3"):
        m = it["versions"][v]["metrics"]
        rows.append([v, f"{m['json_ok']}/{m['n_normal']}", f"{m['schema_ok']}/{m['n_normal']}", f"{m['count_ok']}/{m['n_counted']}",
                     f"{m['invalid_refused']}/{m['n_invalid']}", f"{m['words_min']}-{m['words_max']}"])
    story.append(table(rows, [2 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm]))
    by_type = {}
    for t in ts["tests"]:
        a = by_type.setdefault(t["type"], [0, 0])
        a[0] += t["pass"]
        a[1] += 1
    story.append(P(f"Final-prompt test suite: <b>{ts['passed']}/{ts['total']} passed</b> (" +
                   ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in by_type.items()) + ")." +
                   ("" if ts["passed"] == ts["total"] else " Failed: " + "; ".join(
                       f"{t['id']} ({short(t['fail_reasons'][0], 60)})" for t in ts["tests"] if not t["pass"]) + ".")))
    story.append(P("5. Limitations", "h3"))
    for a, b in LIMITS:
        story.append(P("• " + escape(a.split(":")[0] if ":" in a[:60] else a.split(".")[0]) + ". Next: " + escape(b), "small"))
    if not standalone:
        story.append(PageBreak())


# ---------------------------------------------------------------- supporting document: Business Model Canvas
BMC = {
    "Key Partners": [
        "Google (Gemini API, free tier)",
        "Streamlit Community Cloud (hosting)",
        "Universities and faculty (pilot courses, feedback)",
        "Student clubs and study groups (early users)",
    ],
    "Key Activities": [
        "Prompt design and versioning (P1-P4)",
        "Testing outputs against a fixed test suite",
        "App development and schema checks on model output",
        "Collecting student feedback and improving prompts",
    ],
    "Key Resources": [
        "Four tested prompts with JSON schemas",
        "Streamlit app and Gemini client code",
        "Test suite (14 cases) and iteration log",
        "Team skills in prompt engineering and Python",
    ],
    "Value Propositions": [
        "Turns a student's own notes into explanations, summaries, flashcards and scored quizzes in seconds",
        "Grounded only in the notes: no invented facts, and false statements are flagged as warnings",
        "Works with Hinglish notes and text PDFs; Anki CSV export",
        "Free, no login, no setup",
    ],
    "Customer Relationships": [
        "Self-service web app",
        "In-app feedback and error messages that explain what to paste",
        "Course-level onboarding through faculty",
    ],
    "Channels": [
        "Web link shared in class groups and LMS pages",
        "Short demo reels on social media",
        "Faculty and student-club recommendations",
    ],
    "Customer Segments": [
        "Undergraduate students revising for exams",
        "Class 11-12 students preparing for boards and entrance tests",
        "Postgraduate students with dense reading",
        "Teachers making quick practice quizzes",
    ],
    "Cost Structure": [
        "Gemini API usage beyond the free tier (cost grows with number of requests)",
        "Hosting once usage outgrows the free tier",
        "Development and prompt maintenance time",
        "Outreach to colleges",
    ],
    "Revenue Streams": [
        "Freemium: free daily limit; paid plan for unlimited use, scanned-PDF OCR, saved decks and spaced repetition",
        "Institution licence for colleges and coaching centres (per-student yearly fee)",
        "Currently free (student project, no revenue yet)",
    ],
}


def bmc_table(width, fs=7.2):
    head = ParagraphStyle("bh", parent=ss["Normal"], fontName=BOLD, fontSize=fs + 1.2, leading=fs + 4,
                          textColor=colors.HexColor("#312E81"), spaceAfter=3)
    item = ParagraphStyle("bi", parent=ss["Normal"], fontName=BODY, fontSize=fs, leading=fs * 1.35,
                          leftIndent=7, firstLineIndent=-7, spaceAfter=2)

    def cell(name):
        return [Paragraph(escape(name), head)] + [Paragraph("• " + escape(x), item) for x in BMC[name]]

    c = width / 5
    data = [
        [cell("Key Partners"), cell("Key Activities"), cell("Value Propositions"), cell("Customer Relationships"), cell("Customer Segments")],
        ["", cell("Key Resources"), "", cell("Channels"), ""],
        [cell("Cost Structure"), "", "", cell("Revenue Streams"), ""],
    ]
    t = Table(data, colWidths=[c] * 5)
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 1)), ("SPAN", (2, 0), (2, 1)), ("SPAN", (4, 0), (4, 1)),
        ("SPAN", (0, 2), (2, 2)), ("SPAN", (3, 2), (4, 2)),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#6366F1")),
        ("BACKGROUND", (2, 0), (2, 1), colors.HexColor("#EEF2FF")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def bmc(team, story, standalone):
    if standalone:
        story.append(P(f"Business Model Canvas: {escape(team['project_title'])}", "h1"))
        story.append(P(f"Team {escape(team['team_name'])} ({escape(team['team_id'])}) · {escape(team['course'])} · "
                       f"Faculty: {escape(team['faculty'])}", "small"))
        story.append(Spacer(1, 8))
        story.append(bmc_table(landscape(A4)[0] - 3.6 * cm, fs=9.4))
    else:
        story.append(P("6. Supporting document", "h1"))
        story.append(P(f"Type: Business Model Canvas (also uploaded separately at Q16 as {escape(bmc_name(team))}).", "small"))
        story.append(Spacer(1, 6))
        story.append(bmc_table(A4[0] - 3.6 * cm, fs=6.9))
    story.append(PageBreak())


def section7(team, story):
    story.append(P("7. Team contribution", "h1"))
    rows = [["Member name", "Enrollment no.", "Role", "Tasks done in Milestone 2", "Evidence", "Contribution (%)"]]
    for m in team["members"]:
        rows.append([m["name"], m["enrollment"], m["role"], m["tasks"], m["evidence"], str(m["percent"])])
    total = sum(m["percent"] for m in team["members"])
    rows.append(["Total", "", "", "", "", str(total)])
    story.append(table(rows, [3 * cm, 2.6 * cm, 2.4 * cm, 4.2 * cm, 3.4 * cm, 1.6 * cm]))
    if total != 100:
        story.append(missing(f"Contribution percentages add up to {total}, not 100."))
    story.append(Spacer(1, 6))
    story.append(P("All members have read and agreed to this table.", "small"))


# ---------------------------------------------------------------- outputs
def clean(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s) or "Team"


def m2_name(team):
    return f"M2_{clean(team['team_id'])}_{clean(team['project_title'])}.pdf"


def tech_name(team):
    return f"{clean(team['team_name'])}_TechnicalReport.pdf"


def bmc_name(team):
    return f"{clean(team['team_name'])}_BMC.pdf"


def footer(canvas, doc, label):
    canvas.saveState()
    canvas.setFont(BODY, 7.5)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(1.6 * cm, 1 * cm, label)
    canvas.drawRightString(doc.pagesize[0] - 1.6 * cm, 1 * cm, f"Page {doc.page}")
    if doc._mock:
        canvas.setFont(BOLD, 40)
        canvas.setFillColor(colors.Color(0.86, 0.15, 0.15, alpha=0.25))
        canvas.translate(doc.pagesize[0] / 2, doc.pagesize[1] / 2)
        canvas.rotate(40)
        canvas.drawCentredString(0, 0, "DRY RUN - FAKE RESULTS")
    canvas.restoreState()


def build_pdf(path, story, label, mock, pagesize=A4):
    doc = SimpleDocTemplate(str(path), pagesize=pagesize, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title=label, author="StudyMate AI team")
    doc._mock = mock
    doc.build(story, onFirstPage=lambda c, d: footer(c, d, label), onLaterPages=lambda c, d: footer(c, d, label))


def form_answers(team, it, ts):
    mods = [r[0] for r in module_status(ts) if r[2] == "Working"]
    all_ok = len(mods) == len(MODULES)
    model = model_name(it, ts)
    L = team["links"]
    lines = [f"# Milestone 2 form answers (generated {ts['run_at'][:10]})", "",
             "Copy these into the Microsoft Form. Every number below matches the PDF.", "",
             f"**Q1 Team ID:** {team['team_id']}", f"**Q2 Team name:** {team['team_name']}",
             f"**Q3 Project title:** {team['project_title']}"]
    leader = next((m for m in team["members"] if m["enrollment"] == team["leader_enrollment"]), team["members"][0])
    lines += [f"**Q4 Team leader name:** {leader['name']}", f"**Q5 Team leader enrollment no.:** {leader['enrollment']}",
              f"**Q6 Group (batch):** {team['batch']}", "**Q7 Enrollment numbers (one per line):**", "```",
              *[m["enrollment"] for m in team["members"]], "```",
              f"**Q8 Project type (max 2):** {team['project_type']}",
              f"**Q9 Main AI tool and model:** {model} via the Gemini API (google-genai SDK) in a Streamlit app",
              "**Q10 Number of prompts:** 4", f"**Q11 Prototype link:** {L['prototype']}", f"**Q12 Repository link:** {L['repository']}",
              f"**Q13 Reel link:** {L['reel']}", f"**Q14 Reel length (seconds):** {team['reel_seconds'] or 'TODO (90-150)'}",
              "**Q15 Supporting document type:** Business Model Canvas BMC", f"**Q16 Upload:** docs/{bmc_name(team)}",
              f"**Q17 Number of test inputs:** {ts['total']}", "**Q18 Number of prompt versions:** 3",
              f"**Q19 Prototype status:** {'All modules working' if all_ok else 'Some modules working'}",
              "**Q20 Working modules (one per line):**", "```", *mods, "```", f"**Q21 Upload:** docs/{m2_name(team)}",
              "**Q22 Main task of each member:**", "```",
              *[f"{m['enrollment']} – {m['name']} – {m['tasks']}" for m in team["members"]], "```",
              "**Q23 Anything the evaluator should know:** No login needed. Open the prototype link, paste notes (or upload a text "
              "PDF), pick Explain / Summarize / Flashcards / Quiz and press Generate. The Prompt Lab tab shows prompt v1 vs the "
              "final prompt on the same notes. If the shared free-tier key hits its rate limit, a Gemini key can be pasted in the "
              "sidebar (optional). Test inputs are in test-data/notes/ in the repository.",
              "**Q24:** Tick only after every member has agreed to the contribution table (Section 7).", ""]
    if WARNINGS:
        lines += ["---", "## Still to fix before submitting", *[f"- {w}" for w in sorted(set(WARNINGS))]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-mock", action="store_true", help="build from mock results (watermarked, not for submission)")
    a = ap.parse_args()
    team, it, ts = load()
    mock = it.get("mock") or ts.get("mock")
    if mock and not a.allow_mock:
        sys.exit("results/ contains MOCK results. Run code/run_experiments.py with a real GEMINI_API_KEY first.")
    if mock:
        WARNINGS.append("Built from MOCK results: re-run with a real API key before submitting.")

    story = []
    cover(team, story)
    section2(team, it, ts, story)
    section3(it, ts, story)
    section4(ts, story)
    section5(story)
    bmc(team, story, standalone=False)
    section7(team, story)
    m2 = DOCS / m2_name(team)
    build_pdf(m2, story, f"{team['team_id']} · {team['project_title']} · Milestone 2", mock)

    story2 = []
    bmc(team, story2, standalone=True)
    if story2 and isinstance(story2[-1], PageBreak):
        story2.pop()
    tr = DOCS / bmc_name(team)
    build_pdf(tr, story2, f"{team['team_name']} · Business Model Canvas", mock, pagesize=landscape(A4))

    (DOCS / "form_answers.md").write_text(form_answers(team, it, ts), encoding="utf-8")
    print(f"wrote {m2}\nwrote {tr}\nwrote {DOCS / 'form_answers.md'}")
    for w in sorted(set(WARNINGS)):
        print("  ! " + w)


if __name__ == "__main__":
    main()
