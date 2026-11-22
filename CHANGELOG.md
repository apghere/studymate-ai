# Changelog

All dates are in 2026. Add earlier entries above if your team worked on the project before 22 November.

## 2026-11-22 — Milestone 2
- Added prompt versions v1, v2, v3 for all four tasks (P1 Explain, P2 Summarize, P3 Flashcards, P4 Quiz); final = v3.
- v2: role, student level, "use only the notes", length/count limits, JSON schema.
- v3: one worked example per prompt, `{"error"}` rule for invalid input, guard against instructions inside notes, `warnings` field for false statements, English-output rule, temperature 0.2 and JSON response mode.
- Built the Streamlit app: paste or upload notes (.txt/.md/.pdf), four modes, interactive scored quiz, Markdown/JSON/Anki CSV export, Prompt Lab (v1 vs final).
- Added the Gemini client with retry and model fallback, and JSON/schema validation.
- Added 14 test cases (7 normal, 5 edge, 2 invalid) with automatic pass/fail checks, and the v1-v3 experiment runner.
- Added design diagrams and the report generator for the Milestone 2 PDF and technical report.
- Fixed Quiz on long notes (e.g. a 22-page PDF): the model sometimes returned broken JSON (a stray `warnings` key inside each question). The final prompts now run with Gemini structured output (`code/studymate/schemas.py`), which enforces each mode's JSON shape and the exact number of cards/questions; the parser also repairs that specific slip. Older versions (v1/v2) run without the schema so the Prompt Lab comparison is unchanged.
- Redesigned the app UI: dark theme, new typography, mode picker, flip-card flashcards, quiz with score ring and per-answer review, restyled Prompt Lab and How it works tabs.

## Milestone 1
- Problem identified and submitted: StudyMate AI, self-defined problem based on students' difficulty with long notes during exam preparation.
