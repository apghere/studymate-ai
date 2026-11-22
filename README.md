# StudyMate AI

A prompt-engineering study assistant that turns a student's **own notes** into simple explanations, revision summaries, flashcards and practice quizzes.

SCSE4041 Prompt Engineering mini project, Bennett University.

**Prototype:** TODO add the Streamlit link
**Reel:** TODO add the Drive/YouTube link

## What it does

| Mode | Prompt | Output |
|---|---|---|
| Explain | `prompts/final/P1_explain.md` | explanation under 200 words, an analogy, 3-6 key terms |
| Summarize | `prompts/final/P2_summarize.md` | 3-6 revision points and a one-line takeaway |
| Flashcards | `prompts/final/P3_flashcards.md` | exactly N question/answer cards (Anki CSV export) |
| Quiz | `prompts/final/P4_quiz.md` | exactly N MCQs with answer key, scored in the app |

All four prompts use only the student's notes, answer in English (even for Hinglish notes), flag statements that look factually wrong in a `warnings` field, ignore instructions hidden inside the notes, and return `{"error": ...}` for input that is not study material.

The **Prompt Lab** tab runs prompt v1 and the final prompt on the same notes side by side.

## How to open / run

- **Online:** open the prototype link above. No login is needed.
- **Locally:**
  ```bash
  pip install -r requirements.txt
  cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # add your Gemini key
  streamlit run code/app.py
  ```
  You can get a free Gemini API key at https://aistudio.google.com/apikey

## Reproduce the experiments and the report

```bash
export GEMINI_API_KEY="..."      # never commit this
bash run_all.sh
```
This runs prompts v1, v2 and v3 on the same inputs, runs the 14-case test suite on the final prompts, saves every real output in `test-data/outputs/`, and builds `docs/M2_<TeamID>_StudyMateAI.pdf`, the technical report and `docs/form_answers.md`.

## Repository layout

```
README.md
CHANGELOG.md
prompts/
  v1/ v2/ v3/       older prompt versions (one file per prompt + settings.json)
  final/            final prompts P1-P4 (= v3)
code/
  app.py            Streamlit app
  studymate/        engine.py (prompt loading), llm.py (Gemini client), parse.py (JSON + schema checks)
  run_experiments.py  version experiment + test suite (real model calls)
  make_report.py    builds the Milestone 2 PDF, technical report, form answers
  make_test_data.py writes test-data/
  diagrams.py       draws the design diagrams (Graphviz)
test-data/
  notes/            input notes used in the tests
  tests.json        test cases, expected output and pass/fail rules
  outputs/          saved model outputs
docs/               diagrams, Milestone 2 PDF, technical report
results/            experiment and test summaries (JSON)
```

## Team

TODO: name – enrollment no. – role (one line per member)

## Model

Gemini Flash-Lite / Flash through the Gemini API (`google-genai`). The exact model used in each run is recorded in `results/*.json`. The API key is read from Streamlit secrets or the `GEMINI_API_KEY` environment variable and is never stored in this repository.
