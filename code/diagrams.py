"""Draws the four Section 2(b) diagrams with Graphviz (dot). Output: docs/diagrams/*.dot and *.png"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs" / "diagrams"

STYLE = 'graph [fontname="Helvetica", fontsize=11, bgcolor="white", pad=0.3, nodesep=0.35, ranksep=0.4];\n' \
        'node [fontname="Helvetica", fontsize=10, shape=box, style="rounded,filled", fillcolor="#EEF2FF", color="#4F46E5"];\n' \
        'edge [fontname="Helvetica", fontsize=9, color="#475569"];\n'

DIAGRAMS = {
    "1_prompt_workflow": """digraph G { rankdir=LR; %s
  notes [label="Student notes\\n(paste / .txt / .pdf)", fillcolor="#F1F5F9", color="#64748B"];
  check [label="Input check\\n(empty? too long?)"];
  pick [label="Mode chosen\\nby student", shape=diamond, style=filled, fillcolor="#FEF3C7", color="#D97706"];
  p1 [label="P1 Explain"]; p2 [label="P2 Summarize"]; p3 [label="P3 Flashcards"]; p4 [label="P4 Quiz"];
  llm [label="Gemini\\ntemp 0.2, JSON mode", fillcolor="#DCFCE7", color="#16A34A"];
  val [label="Parse JSON +\\nschema check"];
  err [label="{error} -> show\\nwhat to paste", fillcolor="#FEE2E2", color="#DC2626"];
  ui [label="Study view +\\ndownloads", fillcolor="#F1F5F9", color="#64748B"];
  notes -> check -> pick; pick -> p1; pick -> p2; pick -> p3; pick -> p4;
  p1 -> llm; p2 -> llm; p3 -> llm; p4 -> llm; llm -> val; val -> ui [label="valid"]; val -> err [label="error / invalid"];
}""",
    "2_task_decomposition": """digraph G { rankdir=TB; %s
  root [label="Help a student revise from their own notes", fillcolor="#E0E7FF"];
  a [label="Understand\\n(P1 Explain)"]; b [label="Condense\\n(P2 Summarize)"]; c [label="Memorise\\n(P3 Flashcards)"]; d [label="Self-test\\n(P4 Quiz)"];
  root -> a; root -> b; root -> c; root -> d;
  node [fillcolor="#F8FAFC", color="#94A3B8", fontsize=9];
  a1 [label="simple explanation\\n<=200 words"]; a2 [label="analogy"]; a3 [label="3-6 key terms"];
  b1 [label="3-6 points\\n<=25 words each"]; b2 [label="one-line takeaway"];
  c1 [label="exactly N cards"]; c2 [label="one fact per card"];
  d1 [label="exactly N MCQs\\nA-D + answer key"]; d2 [label="explanation\\nper answer"];
  s [label="Shared rules: use only the notes, English output,\\nflag false statements, ignore hidden instructions,\\nreturn {error} for non-study input", fillcolor="#FEF3C7", color="#D97706"];
  a -> a1; a -> a2; a -> a3; b -> b1; b -> b2; c -> c1; c -> c2; d -> d1; d -> d2;
  {a1 b1 c1 d1} -> s [style=dashed, arrowhead=none];
}""",
    "3_input_output_flow": """digraph G { rankdir=LR; %s
  subgraph cluster_in { label="Input"; style=dashed; color="#94A3B8";
    i1 [label="{notes}\\nstudy text"]; i2 [label="{level}\\nschool / UG / PG"]; i3 [label="{count}\\n3-10 (P3, P4)"]; i4 [label="mode\\nP1-P4"]; }
  tmpl [label="Prompt template\\n(system + user)\\nvariables filled", fillcolor="#E0E7FF"];
  llm [label="Gemini API", fillcolor="#DCFCE7", color="#16A34A"];
  subgraph cluster_out { label="Output (JSON)"; style=dashed; color="#94A3B8";
    o1 [label="P1: explanation,\\nanalogy, key_terms"]; o2 [label="P2: title, summary_points,\\none_line"]; o3 [label="P3: flashcards[front, back]"]; o4 [label="P4: questions[question,\\noptions A-D, answer, explanation]"];
    o5 [label="all: warnings[]  |  or {error}", fillcolor="#FEF3C7", color="#D97706"]; }
  i1 -> tmpl; i2 -> tmpl; i3 -> tmpl; i4 -> tmpl; tmpl -> llm; llm -> o1; llm -> o2; llm -> o3; llm -> o4; llm -> o5;
}""",
    "4_system_architecture": """digraph G { rankdir=LR; %s
  user [label="Student\\n(browser)", shape=ellipse, fillcolor="#F1F5F9", color="#64748B"];
  subgraph cluster_app { label="Streamlit app (Streamlit Community Cloud)"; style=rounded; color="#4F46E5";
    ui [label="app.py\\nStudy tab | Prompt Lab | How it works"];
    up [label="pypdf\\ntext extraction"];
    eng [label="engine.py\\nload prompt file, fill variables"];
    pr [label="prompts/final/\\nP1-P4 .md + settings.json", shape=folder, fillcolor="#FFFFFF"];
    llmc [label="llm.py\\nGemini client, retry,\\nmodel fallback"];
    par [label="parse.py\\nJSON extract + schema check"];
    exp [label="exports\\nMarkdown / JSON / Anki CSV"]; }
  sec [label="Streamlit secrets\\nGEMINI_API_KEY", shape=cylinder, fillcolor="#FEE2E2", color="#DC2626"];
  api [label="Google Gemini API", fillcolor="#DCFCE7", color="#16A34A"];
  user -> ui; ui -> up; ui -> eng; pr -> eng; eng -> llmc; sec -> llmc [style=dashed]; llmc -> api; api -> llmc; llmc -> par; par -> ui; ui -> exp; exp -> user [style=dashed];
}""",
}


def build():
    D.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, src in DIAGRAMS.items():
        dot = src % STYLE
        (D / f"{name}.dot").write_text(dot)
        png = D / f"{name}.png"
        if shutil.which("dot") is None:  # Graphviz not installed: reuse the committed PNGs
            if not png.exists():
                raise SystemExit("Graphviz 'dot' not found and no PNG for " + name)
            out[name] = png
            continue
        subprocess.run(["dot", "-Tpng", "-Gdpi=170", "-o", str(png)], input=dot.encode(), check=True)
        out[name] = png
    return out


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)
