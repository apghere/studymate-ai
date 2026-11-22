"""StudyMate AI — Streamlit front end.

Run locally:   streamlit run code/app.py
API key:       GEMINI_API_KEY in .streamlit/secrets.toml, an environment variable,
               or typed into the sidebar (kept only in this browser session).
"""
import csv
import io
import json
import os
import sys
import uuid
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from studymate.engine import LEVELS, MAX_CHARS, MODES, run  # noqa: E402
from studymate.llm import GeminiClient, LLMError  # noqa: E402
from studymate.parse import word_count  # noqa: E402

st.set_page_config(page_title="StudyMate AI", page_icon="📘", layout="wide")

MODE_UI = {
    "explain": (":material/lightbulb:", "Explain", "explanation"),
    "summarize": (":material/notes:", "Summarize", "summary"),
    "flashcards": (":material/style:", "Flashcards", "flashcards"),
    "quiz": (":material/quiz:", "Quiz", "quiz"),
}


def esc(x):
    return escape(str(x or ""))


def html(s):
    st.html(s)


# ---------- styles ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #07070D;
  --surface: rgba(255,255,255,.035);
  --surface-2: rgba(255,255,255,.06);
  --line: rgba(255,255,255,.08);
  --line-2: rgba(255,255,255,.14);
  --text: #ECECF4;
  --muted: #9C9CB4;
  --faint: #6B6B85;
  --violet: #A78BFA;
  --cyan: #22D3EE;
  --pink: #F472B6;
  --green: #34D399;
  --red: #FB7185;
  --amber: #FBBF24;
  --grad: linear-gradient(120deg, #C4B5FD 0%, #A78BFA 35%, #22D3EE 100%);
  --serif: 'Instrument Serif', Georgia, serif;
  --sans: 'Inter', system-ui, -apple-system, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
}

/* ---- canvas ---- */
.stApp {
  font-family: var(--sans);
  background:
    radial-gradient(900px 520px at 12% -8%, rgba(167,139,250,.16), transparent 60%),
    radial-gradient(800px 480px at 95% 4%, rgba(34,211,238,.10), transparent 60%),
    radial-gradient(700px 600px at 50% 110%, rgba(244,114,182,.06), transparent 60%),
    var(--bg);
  background-attachment: fixed;
}
.stApp textarea, .stApp input, .stApp button, .stApp select { font-family: var(--sans); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1140px; padding-top: 2.2rem; padding-bottom: 5rem; }
::selection { background: rgba(167,139,250,.35); }

/* ---- sidebar ---- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(20,20,34,.92), rgba(10,10,18,.96));
  border-right: 1px solid var(--line);
  backdrop-filter: blur(12px);
}
[data-testid="stSidebar"] label p { font-size: .78rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); font-weight: 600; }

/* ---- tabs as pills ---- */
[role="tablist"] {
  gap: 4px; background: var(--surface); border: 1px solid var(--line); border-bottom: 1px solid var(--line) !important;
  padding: 5px; border-radius: 999px; width: fit-content; max-width: 100%; overflow-x: auto; box-shadow: none;
}
[role="tablist"] > :not([role="tab"]), .react-aria-SelectionIndicator { display: none !important; }
[data-testid="stTab"] {
  height: 38px; padding: 0 18px !important; border-radius: 999px; background: transparent; border: 0 !important;
  color: var(--muted); font-weight: 500; transition: all .2s ease; margin: 0 !important;
}
[data-testid="stTab"]:hover { color: var(--text); }
[data-testid="stTab"][aria-selected="true"] { background: var(--surface-2); color: var(--text); box-shadow: inset 0 0 0 1px var(--line-2); }
[data-testid="stTab"]::after, [data-testid="stTab"]::before { display: none !important; }
[role="tabpanel"] { padding-top: 1.6rem; }

/* ---- buttons ---- */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--grad); color: #0B0B14; border: 0; font-weight: 650; letter-spacing: .01em;
  min-height: 48px; border-radius: 14px;
  box-shadow: 0 10px 30px -10px rgba(167,139,250,.65), inset 0 1px 0 rgba(255,255,255,.35);
  transition: transform .15s ease, box-shadow .2s ease, filter .2s ease;
}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
  transform: translateY(-1px); filter: brightness(1.06); color: #0B0B14;
  box-shadow: 0 16px 40px -12px rgba(34,211,238,.55), inset 0 1px 0 rgba(255,255,255,.4);
}
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { font-weight: 650; }
[data-testid="stBaseButton-secondary"] {
  background: var(--surface); border: 1px solid var(--line-2); border-radius: 12px; color: var(--text);
  transition: all .2s ease;
}
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--violet); color: var(--text); background: rgba(167,139,250,.08); }

/* ---- segmented control (mode picker) ---- */
.st-key-mode_pick, .st-key-lab_mode, [data-testid="stButtonGroup"], [data-testid="stButtonGroup"] > div { width: 100% !important; }
[data-testid="stButtonGroup"] > div { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
button[data-variant="segmented_control"] {
  width: 100%; border-radius: 12px !important; border: 1px solid var(--line) !important; background: var(--surface) !important;
  min-height: 48px; color: var(--muted) !important; transition: all .2s ease; margin: 0 !important; justify-content: center;
}
button[data-variant="segmented_control"]:hover { color: var(--text) !important; border-color: var(--line-2) !important; }
button[data-variant="segmented_control"][aria-checked="true"] {
  color: var(--text) !important; border-color: rgba(167,139,250,.65) !important;
  background: linear-gradient(135deg, rgba(167,139,250,.20), rgba(34,211,238,.10)) !important;
  box-shadow: 0 0 0 1px rgba(167,139,250,.25), 0 10px 26px -12px rgba(167,139,250,.7);
}
button[data-variant="segmented_control"][aria-checked="true"] * { color: var(--text) !important; }
.st-key-lab_mode [data-testid="stButtonGroup"] > div { grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 640px) { .st-key-lab_mode [data-testid="stButtonGroup"] > div { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

/* ---- inputs ---- */
.stTextArea textarea {
  background: rgba(0,0,0,.25) !important; border-radius: 14px; font-size: .95rem; line-height: 1.6;
  color: var(--text);
}
.stTextArea [data-baseweb="textarea"] { border-radius: 14px; border-color: var(--line) !important; background: transparent; }
.stTextArea [data-baseweb="textarea"]:focus-within { border-color: var(--violet) !important; box-shadow: 0 0 0 3px rgba(167,139,250,.18); }
[data-testid="stFileUploaderDropzone"] {
  background: rgba(167,139,250,.05); border: 1.5px dashed rgba(167,139,250,.35); border-radius: 14px;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--cyan); background: rgba(34,211,238,.05); }
[data-testid="stWidgetLabel"] p { color: var(--muted); font-weight: 500; }

/* ---- bordered containers as glass cards ---- */
.st-key-input_card, .st-key-lab_card {
  background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.02));
  border: 1px solid var(--line) !important; border-radius: 22px !important; padding: 22px !important;
  box-shadow: 0 30px 80px -40px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.05);
}

/* ---- expanders ---- */
[data-testid="stExpander"] details { border: 1px solid var(--line); border-radius: 14px; background: var(--surface); }

/* ---- quiz radios as option tiles ---- */
.st-key-quiz_area [data-testid="stElementContainer"], .st-key-quiz_area .stRadio, .st-key-quiz_area .stRadio > div { width: 100% !important; }
.st-key-quiz_area [role="radiogroup"] { gap: 8px; display: flex; flex-direction: column; width: 100%; align-items: stretch !important; }
.st-key-quiz_area [role="radiogroup"] > div { width: 100%; }
.st-key-quiz_area [role="radiogroup"] label {
  width: 100%; margin: 0; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--line);
  background: rgba(255,255,255,.025); transition: all .15s ease; cursor: pointer;
}
.st-key-quiz_area [role="radiogroup"] label:hover { border-color: var(--line-2); background: rgba(255,255,255,.05); }
.st-key-quiz_area [role="radiogroup"] label:has(input:checked) {
  border-color: rgba(167,139,250,.7); background: linear-gradient(135deg, rgba(167,139,250,.16), rgba(34,211,238,.06));
}
.st-key-quiz_area [data-testid="stForm"] { border: 0; padding: 0; }

/* ================= custom components ================= */
.sm-hero { padding: 6px 0 26px; animation: smUp .6s ease both; }
.sm-eyebrow {
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px 6px 8px; border-radius: 999px;
  border: 1px solid var(--line-2); background: var(--surface); color: var(--muted);
  font-size: .78rem; font-weight: 500; letter-spacing: .02em;
}
.sm-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 4px rgba(52,211,153,.15); }
.sm-title {
  font-family: var(--serif); font-weight: 400; font-size: clamp(2.6rem, 6vw, 4.6rem); line-height: 1.02;
  letter-spacing: -.02em; margin: 18px 0 14px; color: var(--text);
}
.sm-title em { font-style: italic; background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; padding-right: .06em; }
.sm-sub { color: var(--muted); font-size: 1.06rem; line-height: 1.65; max-width: 640px; margin: 0; }

.sm-label {
  font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 600; color: var(--faint);
  margin: 0 0 10px; display: flex; align-items: center; gap: 8px;
}
.sm-label .sm-n { font-family: var(--mono); color: var(--violet); letter-spacing: 0; }

.sm-brand { display: flex; align-items: center; gap: 12px; margin: 4px 0 6px; }
.sm-logo {
  width: 40px; height: 40px; border-radius: 12px; background: var(--grad);
  display: grid; place-items: center; color: #0B0B14; font-family: var(--serif); font-size: 1.5rem; font-style: italic;
  box-shadow: 0 10px 30px -10px rgba(167,139,250,.8);
}
.sm-brand-name { font-weight: 650; font-size: 1.08rem; color: var(--text); letter-spacing: -.01em; }
.sm-brand-tag { font-size: .78rem; color: var(--muted); }
.sm-side-foot { font-size: .75rem; color: var(--faint); line-height: 1.5; margin-top: 8px; }

.sm-wc { font-family: var(--mono); font-size: .75rem; color: var(--faint); margin-top: -6px; }

/* result header */
.sm-res-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 34px 0 18px; animation: smUp .5s ease both; }
.sm-res-title { font-family: var(--serif); font-size: 2.2rem; line-height: 1; margin: 0; color: var(--text); }
.sm-res-title em { font-style: italic; background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.sm-meta { display: flex; gap: 6px; flex-wrap: wrap; }
.sm-pill {
  font-family: var(--mono); font-size: .72rem; color: var(--muted); padding: 5px 10px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--surface);
}
.sm-pill b { color: var(--text); font-weight: 500; }

/* cards */
.sm-card {
  position: relative; background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.018));
  border: 1px solid var(--line); border-radius: 20px; padding: 24px 26px; margin-bottom: 14px;
  animation: smUp .5s ease both;
}
.sm-lead { font-size: 1.08rem; line-height: 1.8; color: #DCDCEA; margin: 0; }
.sm-analogy { overflow: hidden; }
.sm-analogy::before {
  content: ""; position: absolute; inset: 0; border-radius: 20px; padding: 1px; background: var(--grad);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude;
  opacity: .55; pointer-events: none;
}
.sm-analogy p { font-family: var(--serif); font-style: italic; font-size: 1.45rem; line-height: 1.4; margin: 0; color: var(--text); }
.sm-terms { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
.sm-term { border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; background: rgba(0,0,0,.18); transition: border-color .2s ease, transform .2s ease; }
.sm-term:hover { border-color: rgba(167,139,250,.45); transform: translateY(-2px); }
.sm-term b { display: block; color: var(--violet); font-weight: 600; margin-bottom: 4px; }
.sm-term span { color: var(--muted); font-size: .92rem; line-height: 1.55; }

/* summary */
.sm-points { list-style: none; padding: 0 !important; margin: 0 !important; counter-reset: pt; }
.sm-points li { margin: 0 !important; }
.sm-points li {
  counter-increment: pt; display: grid; grid-template-columns: 44px 1fr; gap: 14px; align-items: start;
  padding: 14px 0; border-bottom: 1px solid var(--line); color: #DCDCEA; line-height: 1.6; font-size: 1.02rem;
}
.sm-points li:last-child { border-bottom: 0; }
.sm-points li::before {
  content: counter(pt, decimal-leading-zero); font-family: var(--mono); font-size: .8rem; color: var(--violet);
  border: 1px solid rgba(167,139,250,.35); border-radius: 10px; height: 32px; display: grid; place-items: center;
  background: rgba(167,139,250,.08);
}
.sm-take {
  background: linear-gradient(135deg, rgba(167,139,250,.16), rgba(34,211,238,.10)); border-color: rgba(167,139,250,.35);
}
.sm-take p { font-family: var(--serif); font-size: 1.6rem; line-height: 1.3; margin: 0; color: var(--text); }

/* warnings */
.sm-warn {
  display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: 14px; margin-bottom: 10px;
  border: 1px solid rgba(251,191,36,.28); background: rgba(251,191,36,.07); color: #F5E6C4; font-size: .93rem; line-height: 1.55;
}
.sm-warn i { font-style: normal; color: var(--amber); font-weight: 700; }
.sm-note { font-family: var(--mono); font-size: .75rem; color: var(--faint); margin: 0 0 12px; }

/* flashcards */
.sm-flip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.sm-flip { display: block; perspective: 1400px; cursor: pointer; height: 220px; animation: smUp .5s ease both; animation-delay: calc(var(--i) * 50ms); }
.sm-flip input { position: absolute; opacity: 0; pointer-events: none; }
.sm-flip-inner { position: relative; height: 100%; transition: transform .7s cubic-bezier(.2,.8,.2,1); transform-style: preserve-3d; }
.sm-flip input:checked + .sm-flip-inner { transform: rotateY(180deg); }
.sm-flip:hover .sm-face { border-color: var(--line-2); }
.sm-face {
  position: absolute; inset: 0; backface-visibility: hidden; -webkit-backface-visibility: hidden;
  border-radius: 20px; border: 1px solid var(--line); padding: 20px; display: flex; flex-direction: column; overflow: auto;
}
.sm-front { background: linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.015)); }
.sm-back { transform: rotateY(180deg); background: linear-gradient(160deg, rgba(167,139,250,.20), rgba(34,211,238,.10)); border-color: rgba(167,139,250,.4); }
.sm-face-n { font-family: var(--mono); font-size: .72rem; color: var(--violet); letter-spacing: .08em; }
.sm-face p { margin: auto 0; font-size: 1.05rem; line-height: 1.5; color: var(--text); }
.sm-front p { font-weight: 550; }
.sm-face-hint { font-size: .72rem; color: var(--faint); display: flex; align-items: center; gap: 6px; }

/* quiz */
.sm-q { display: flex; gap: 14px; align-items: flex-start; margin: 22px 0 10px; }
.sm-qn {
  font-family: var(--mono); font-size: .75rem; color: var(--violet); border: 1px solid rgba(167,139,250,.35);
  background: rgba(167,139,250,.08); padding: 4px 8px; border-radius: 8px; flex-shrink: 0; margin-top: 2px;
}
.sm-q p { margin: 0; font-size: 1.08rem; font-weight: 550; line-height: 1.5; color: var(--text); }

.sm-score { display: flex; align-items: center; gap: 26px; flex-wrap: wrap; }
.sm-ring {
  --p: 0; width: 132px; height: 132px; border-radius: 50%; flex-shrink: 0;
  background: conic-gradient(from -90deg, var(--violet), var(--cyan) calc(var(--p) * 1%), rgba(255,255,255,.07) 0);
  display: grid; place-items: center; box-shadow: 0 20px 60px -20px rgba(167,139,250,.6);
}
.sm-ring > div { width: 108px; height: 108px; border-radius: 50%; background: #0D0D17; display: grid; place-items: center; text-align: center; }
.sm-ring b { font-family: var(--serif); font-size: 2.4rem; font-weight: 400; line-height: 1; color: var(--text); }
.sm-ring span { display: block; font-family: var(--mono); font-size: .72rem; color: var(--muted); }
.sm-score h3 { font-family: var(--serif); font-weight: 400; font-size: 2rem; margin: 0 0 6px; color: var(--text); }
.sm-score p { color: var(--muted); margin: 0; }

.sm-rev { padding: 20px 22px; }
.sm-rev-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.sm-tag { font-size: .72rem; font-weight: 600; padding: 3px 9px; border-radius: 999px; letter-spacing: .03em; }
.sm-tag.ok { color: var(--green); background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.3); }
.sm-tag.bad { color: var(--red); background: rgba(251,113,133,.12); border: 1px solid rgba(251,113,133,.3); }
.sm-tag.skip { color: var(--muted); background: var(--surface); border: 1px solid var(--line); }
.sm-rev-q { font-weight: 550; font-size: 1.04rem; margin: 0 0 12px; color: var(--text); line-height: 1.5; }
.sm-opt { display: flex; gap: 12px; align-items: flex-start; padding: 10px 12px; border-radius: 12px; border: 1px solid transparent; color: var(--muted); font-size: .95rem; margin-bottom: 4px; }
.sm-opt b { font-family: var(--mono); font-weight: 500; font-size: .8rem; width: 22px; height: 22px; border-radius: 6px; display: grid; place-items: center; background: var(--surface-2); flex-shrink: 0; }
.sm-opt.correct { color: var(--text); border-color: rgba(52,211,153,.4); background: rgba(52,211,153,.08); }
.sm-opt.correct b { background: var(--green); color: #052E1F; }
.sm-opt.wrong { color: var(--text); border-color: rgba(251,113,133,.4); background: rgba(251,113,133,.08); }
.sm-opt.wrong b { background: var(--red); color: #3B0710; }
.sm-expl { margin: 10px 0 0; color: var(--muted); font-size: .9rem; line-height: 1.55; padding-left: 12px; border-left: 2px solid rgba(167,139,250,.4); }

/* lab + about */
.sm-lab-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.sm-lab-head h4 { margin: 0; font-family: var(--serif); font-weight: 400; font-size: 1.5rem; color: var(--text); }
.sm-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.sm-step { padding: 10px 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); font-size: .9rem; color: var(--text); }
.sm-step.hl { border-color: rgba(167,139,250,.5); background: linear-gradient(135deg, rgba(167,139,250,.16), rgba(34,211,238,.08)); }
.sm-arrow { color: var(--faint); font-family: var(--mono); }
.sm-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.sm-chip { padding: 7px 12px; border-radius: 999px; border: 1px solid var(--line); background: var(--surface); font-size: .85rem; color: #D6D6E4; }
.sm-prose { color: #D0D0DE; line-height: 1.75; font-size: 1rem; margin: 0; }

.sm-empty { text-align: center; padding: 34px 20px; color: var(--faint); font-size: .92rem; }
.sm-empty b { display: block; font-family: var(--serif); font-weight: 400; font-size: 1.5rem; color: var(--muted); margin-bottom: 4px; }

@keyframes smUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
@media (max-width: 640px) {
  .sm-card { padding: 18px; }
  .sm-res-title { font-size: 1.8rem; }
  .st-key-input_card, .st-key-lab_card { padding: 16px !important; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- helpers ----------
def get_key():
    k = st.session_state.get("user_key", "").strip()
    if k:
        return k
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


@st.cache_resource(show_spinner=False)
def make_client(key):
    return GeminiClient(api_key=key)


def read_upload(f):
    name = f.name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(f)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if not text.strip():
            st.warning("No text found in this PDF. It may be a scanned image; scanned PDFs are not supported yet.")
        return text
    return f.read().decode("utf-8", errors="ignore")


def to_markdown(mode, obj):
    if mode == "explain":
        s = f"## Explanation\n\n{obj['explanation']}\n\n**Analogy:** {obj['analogy']}\n\n### Key terms\n"
        s += "\n".join(f"- **{k['term']}**: {k['meaning']}" for k in obj["key_terms"])
    elif mode == "summarize":
        s = f"## {obj.get('title', 'Summary')}\n\n" + "\n".join(f"- {p}" for p in obj["summary_points"])
        s += f"\n\n**In one line:** {obj['one_line']}"
    elif mode == "flashcards":
        s = "## Flashcards\n\n" + "\n\n".join(f"**Q{i}.** {c['front']}\n\n{c['back']}" for i, c in enumerate(obj["flashcards"], 1))
    else:
        s = "## Quiz\n\n"
        for i, q in enumerate(obj["questions"], 1):
            s += f"**Q{i}.** {q['question']}\n\n" + "\n".join(f"- {k}) {v}" for k, v in q["options"].items())
            s += f"\n\n*Answer: {q['answer']}*. {q.get('explanation', '')}\n\n"
    if obj.get("warnings"):
        s += "\n\n### Possible errors in your notes\n" + "\n".join(f"- {w}" for w in obj["warnings"])
    return s


def show_warnings(obj):
    for w in obj.get("warnings") or []:
        html(f"<div class='sm-warn'><i>!</i><div><b>Check your notes.</b> {esc(w)}</div></div>")


# ---------- result views ----------
def render_explain(obj):
    html(
        "<div class='sm-card'><div class='sm-label'>Explanation</div>"
        f"<p class='sm-lead'>{esc(obj.get('explanation'))}</p></div>"
        "<div class='sm-card sm-analogy' style='animation-delay:.08s'><div class='sm-label'>Think of it like this</div>"
        f"<p>{esc(obj.get('analogy'))}</p></div>"
    )
    terms = "".join(
        f"<div class='sm-term'><b>{esc(k.get('term'))}</b><span>{esc(k.get('meaning'))}</span></div>"
        for k in obj.get("key_terms", []) if isinstance(k, dict)
    )
    html(f"<div class='sm-card' style='animation-delay:.16s'><div class='sm-label'>Key terms</div><div class='sm-terms'>{terms}</div></div>")


def render_summary(obj):
    pts = "".join(f"<li>{esc(p)}</li>" for p in obj.get("summary_points", []))
    html(
        f"<div class='sm-card'><div class='sm-label'>{esc(obj.get('title') or 'Summary')}</div><ol class='sm-points'>{pts}</ol></div>"
        "<div class='sm-card sm-take' style='animation-delay:.08s'><div class='sm-label'>In one line</div>"
        f"<p>{esc(obj.get('one_line'))}</p></div>"
    )


def render_flashcards(obj):
    cards = [c for c in obj.get("flashcards", []) if isinstance(c, dict)]
    items = "".join(
        f"<label class='sm-flip' style='--i:{i}'><input type='checkbox'><div class='sm-flip-inner'>"
        f"<div class='sm-face sm-front'><span class='sm-face-n'>CARD {i + 1:02d}</span><p>{esc(c.get('front'))}</p>"
        "<span class='sm-face-hint'>↻ Tap to flip</span></div>"
        f"<div class='sm-face sm-back'><span class='sm-face-n'>ANSWER</span><p>{esc(c.get('back'))}</p>"
        "<span class='sm-face-hint'>↻ Tap to flip back</span></div>"
        "</div></label>"
        for i, c in enumerate(cards)
    )
    html(f"<p class='sm-note'>{len(cards)} cards · answer in your head, then tap a card to check</p><div class='sm-flip-grid'>{items}</div>")


def render_quiz(obj, rid):
    qs = [q for q in obj.get("questions", []) if isinstance(q, dict)]
    done_key, ans_key = f"quiz_done_{rid}", f"quiz_ans_{rid}"

    def submit():
        st.session_state[ans_key] = {i: st.session_state.get(f"q_{rid}_{i}") for i in range(len(qs))}
        st.session_state[done_key] = True

    def retake():
        st.session_state[done_key] = False
        st.session_state.pop(ans_key, None)
        for i in range(len(qs)):
            st.session_state.pop(f"q_{rid}_{i}", None)

    with st.container(key="quiz_area"):
        if not st.session_state.get(done_key):
            with st.form(f"quiz_{rid}", border=False):
                for i, q in enumerate(qs):
                    opts = q.get("options") or {}
                    html(f"<div class='sm-q'><span class='sm-qn'>Q{i + 1:02d}</span><p>{esc(q.get('question'))}</p></div>")
                    st.radio(
                        f"Question {i + 1}", list(opts.keys()), index=None, key=f"q_{rid}_{i}",
                        format_func=lambda k, o=opts: f"{k}.  {o.get(k, '')}", label_visibility="collapsed",
                    )
                st.write("")
                st.form_submit_button("Submit answers", type="primary", width="stretch", on_click=submit)
            return

    answers = st.session_state.get(ans_key, {})
    score = sum(1 for i, q in enumerate(qs) if answers.get(i) == q.get("answer"))
    n = max(len(qs), 1)
    pct = round(100 * score / n)
    verdict = ("Flawless." if pct == 100 else "Great work." if pct >= 80 else
               "Solid start." if pct >= 50 else "Worth another pass.")
    html(
        "<div class='sm-card'><div class='sm-score'>"
        f"<div class='sm-ring' style='--p:{pct}'><div><div><b>{score}</b><span>of {len(qs)}</span></div></div></div>"
        f"<div><h3>{verdict}</h3><p>You scored {pct}%. Review each answer below, then retake the quiz.</p></div>"
        "</div></div>"
    )
    for i, q in enumerate(qs):
        chosen, right = answers.get(i), q.get("answer")
        tag = ("<span class='sm-tag skip'>Skipped</span>" if chosen is None else
               "<span class='sm-tag ok'>Correct</span>" if chosen == right else
               "<span class='sm-tag bad'>Incorrect</span>")
        rows = ""
        for k, v in (q.get("options") or {}).items():
            cls = "correct" if k == right else "wrong" if k == chosen else ""
            rows += f"<div class='sm-opt {cls}'><b>{esc(k)}</b><span>{esc(v)}</span></div>"
        html(
            f"<div class='sm-card sm-rev' style='animation-delay:{i * 0.05:.2f}s'>"
            f"<div class='sm-rev-head'><span class='sm-qn'>Q{i + 1:02d}</span>{tag}</div>"
            f"<p class='sm-rev-q'>{esc(q.get('question'))}</p>{rows}"
            f"<p class='sm-expl'>{esc(q.get('explanation'))}</p></div>"
        )
    st.button("Retake quiz", icon=":material/refresh:", on_click=retake, key=f"retake_{rid}")


def render_result(res):
    mode, obj = res["mode"], res["parsed"]
    title = MODE_UI[mode][2]
    html(
        "<div class='sm-res-head'>"
        f"<h2 class='sm-res-title'>Your <em>{esc(title)}</em></h2>"
        "<div class='sm-meta'>"
        f"<span class='sm-pill'>prompt <b>{MODES[mode][0]}</b></span>"
        f"<span class='sm-pill'><b>{esc(res['model'] or '-')}</b></span>"
        f"<span class='sm-pill'><b>{res['latency']}</b> s</span>"
        f"<span class='sm-pill'><b>{res.get('input_words', 0)}</b> words in</span>"
        "</div></div>"
    )
    if res.get("error_msg"):
        st.error(f"StudyMate couldn't use this input: {res['error_msg']}", icon=":material/block:")
        return
    if obj is None:
        st.error("The model did not return a readable result. Please try again.", icon=":material/error:")
        with st.expander("Raw model output"):
            st.code(res["raw"] or "(empty)")
        return
    if res["issues"]:
        html(f"<p class='sm-note'>note: {esc('; '.join(res['issues']))}</p>")

    show_warnings(obj)
    if mode == "explain":
        render_explain(obj)
    elif mode == "summarize":
        render_summary(obj)
    elif mode == "flashcards":
        render_flashcards(obj)
    elif mode == "quiz":
        render_quiz(obj, res.get("rid", "x"))

    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Markdown", to_markdown(mode, obj), file_name=f"studymate_{mode}.md",
                       icon=":material/description:", width="stretch")
    c2.download_button("JSON", json.dumps(obj, indent=2, ensure_ascii=False), file_name=f"studymate_{mode}.json",
                       icon=":material/data_object:", width="stretch")
    if mode == "flashcards":
        buf = io.StringIO()
        w = csv.writer(buf)
        for c in obj.get("flashcards", []):
            w.writerow([c.get("front"), c.get("back")])
        c3.download_button("Anki CSV", buf.getvalue(), file_name="studymate_flashcards.csv",
                           icon=":material/style:", width="stretch")


# ---------- sidebar ----------
with st.sidebar:
    html(
        "<div class='sm-brand'><div class='sm-logo'>S</div><div>"
        "<div class='sm-brand-name'>StudyMate AI</div><div class='sm-brand-tag'>Your notes, made studyable</div>"
        "</div></div>"
    )
    st.write("")
    level = st.selectbox("Your level", LEVELS, index=1)
    count = st.slider("Cards / questions", 3, 10, 5)
    st.divider()
    with st.expander("Use your own Gemini key", icon=":material/key:"):
        st.text_input("API key", type="password", key="user_key",
                      help="Only used in this browser session. Get one free at aistudio.google.com.")
    html("<div class='sm-side-foot'>SCSE4041 Prompt Engineering<br>Mini project · Bennett University</div>")

# ---------- hero ----------
html(
    "<div class='sm-hero'>"
    "<span class='sm-eyebrow'><span class='sm-dot'></span>Grounded only in your notes · powered by Gemini</span>"
    "<h1 class='sm-title'>Study <em>smarter</em>,<br>straight from your notes.</h1>"
    "<p class='sm-sub'>Paste a page or drop a PDF. Get a clear explanation, a revision summary, "
    "flip-cards or a scored quiz, built only from what you wrote.</p>"
    "</div>"
)

key = get_key()
if not key:
    st.warning("No Gemini API key configured. Add one in the sidebar to start.", icon=":material/key:")
    st.stop()
try:
    client = make_client(key)
except LLMError as e:
    st.error(str(e))
    st.stop()

tab_main, tab_lab, tab_about = st.tabs([":material/auto_stories: Study", ":material/science: Prompt Lab", ":material/info: How it works"])

# ---------- Study tab ----------
with tab_main:
    with st.container(border=True, key="input_card"):
        left, right = st.columns([1.55, 1], gap="large")
        with right:
            html("<div class='sm-label'><span class='sm-n'>02</span> Or upload a file</div>")
            up = st.file_uploader("Upload a .txt, .md or text-based .pdf", type=["txt", "md", "pdf"],
                                  label_visibility="collapsed")
            html("<div class='sm-label' style='margin-top:14px'><span class='sm-n'>03</span> Choose a mode</div>")
            picked = st.segmented_control(
                "Mode", list(MODES), default="explain", key="mode_pick", label_visibility="collapsed",
                format_func=lambda m: f"{MODE_UI[m][0]} {MODE_UI[m][1]}",
            )
            mode = picked or "explain"
            st.write("")
            go = st.button(f"Generate {MODE_UI[mode][1].lower()}", type="primary", width="stretch",
                           icon=":material/auto_awesome:")
        with left:
            html("<div class='sm-label'><span class='sm-n'>01</span> Your notes</div>")
            default = read_upload(up) if up else ""
            notes = st.text_area("Notes", value=default, height=300, max_chars=MAX_CHARS, label_visibility="collapsed",
                                 placeholder="Paste a paragraph or a page from your notes or textbook…")
            html(f"<div class='sm-wc'>{word_count(notes)} words · {len(notes):,} / {MAX_CHARS:,} chars</div>")

    if go:
        with st.spinner("StudyMate is reading your notes…"):
            try:
                res = run(client, mode, notes, level, count, "final")
                res["rid"] = uuid.uuid4().hex[:8]
                st.session_state["result"] = res
            except LLMError as e:
                st.session_state.pop("result", None)
                st.error(f"Model call failed: {e}", icon=":material/error:")
    res = st.session_state.get("result")
    if res:
        render_result(res)
    elif not go:
        html("<div class='sm-empty'><b>Nothing here yet.</b>Add your notes, pick a mode, and hit generate.</div>")

# ---------- Prompt Lab tab ----------
with tab_lab:
    html(
        "<div class='sm-label'>Prompt Lab</div>"
        "<p class='sm-prose' style='margin-bottom:18px'>Run the same notes through the <b>first</b> prompt version (v1) "
        "and the <b>final</b> version, side by side, to see what the prompt engineering changed.</p>"
    )
    with st.container(border=True, key="lab_card"):
        lab_notes = st.text_area("Notes for the comparison", height=150, key="lab_notes",
                                 placeholder="Paste the notes to compare on…")
        lab_mode = st.segmented_control(
            "Prompt", list(MODES), default="explain", key="lab_mode",
            format_func=lambda m: f"{MODE_UI[m][0]} {MODE_UI[m][1]}",
        ) or "explain"
        lab_go = st.button("Run both versions", type="primary", key="lab_run", width="stretch",
                           icon=":material/compare_arrows:")
    if lab_go:
        with st.spinner("Running v1 and final…"):
            try:
                st.session_state["lab"] = [run(client, lab_mode, lab_notes, level, count, v) for v in ("v1", "final")]
            except LLMError as e:
                st.error(f"Model call failed: {e}")
    if st.session_state.get("lab"):
        st.write("")
        cols = st.columns(2, gap="medium")
        for col, r in zip(cols, st.session_state["lab"]):
            with col:
                ok_json = r["parsed"] is not None
                badge = ("<span class='sm-tag ok'>schema OK</span>" if ok_json and not r["issues"] else
                         f"<span class='sm-tag bad'>{esc('; '.join(r['issues']) or 'not machine-readable')}</span>")
                html(
                    "<div class='sm-lab-head'>"
                    f"<h4>{'v1 · first prompt' if r['version'] == 'v1' else 'final · v3'}</h4>{badge}</div>"
                    "<div class='sm-meta' style='margin-bottom:10px'>"
                    f"<span class='sm-pill'><b>{r.get('output_words', 0)}</b> words</span>"
                    f"<span class='sm-pill'><b>{r['latency']}</b> s</span>"
                    f"<span class='sm-pill'>{'valid JSON' if ok_json else 'free text'}</span></div>"
                )
                st.code(r["raw"][:6000] or "(empty)", language="json" if ok_json else None)

# ---------- About tab ----------
with tab_about:
    html(
        "<div class='sm-card'><div class='sm-label'>Pipeline</div><div class='sm-flow'>"
        "<span class='sm-step'>Your notes</span><span class='sm-arrow'>→</span>"
        "<span class='sm-step'>Input check</span><span class='sm-arrow'>→</span>"
        "<span class='sm-step hl'>P1–P4 prompt</span><span class='sm-arrow'>→</span>"
        "<span class='sm-step hl'>Gemini · JSON schema</span><span class='sm-arrow'>→</span>"
        "<span class='sm-step'>Parse + validate</span><span class='sm-arrow'>→</span>"
        "<span class='sm-step'>Study view + exports</span></div></div>"
        "<div class='sm-card' style='animation-delay:.06s'><div class='sm-label'>Prompt techniques in the final prompts</div>"
        "<div class='sm-chips'>"
        + "".join(f"<span class='sm-chip'>{t}</span>" for t in [
            "Role prompting", "Audience level", "Explicit JSON schema", "Length + count constraints",
            "One-shot example", "Invalid-input rule", "Prompt-injection guard", "Fact-check warnings",
            "Temperature 0.2", "JSON response mode", "Structured output"])
        + "</div></div>"
        "<div class='sm-card' style='animation-delay:.12s'><div class='sm-label'>Good to know</div>"
        "<p class='sm-prose'>The model is told to use <b>only</b> the facts in your notes, so the output is only as good "
        "as the notes. Statements that look factually wrong are flagged as warnings instead of being repeated.</p></div>"
    )
