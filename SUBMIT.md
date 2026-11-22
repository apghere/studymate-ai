# Tonight's submission steps (deadline 22 Nov, 11:59 PM)

Total: about 2–2.5 hours. Do the steps in order.

## 1. Fill in team.json (5 min)
Replace every `TODO`: team ID, team name (exactly as in M1), batch (e.g. B13-24), faculty, members (name, enrollment, role, tasks, evidence, %), leader enrollment, project type (look at the form's Q8 options and pick at most 2). Percentages must add up to 100. **Every member must own one real task they can explain in a viva.**

## 2. Get a Gemini API key (3 min)
https://aistudio.google.com/apikey → Create API key. **Never paste it into any file in the repo.**

## 3. Run the real experiments + build the PDFs (10–15 min, mostly waiting)
```bash
cd studymate-ai
export GEMINI_API_KEY="your-key"
bash run_all.sh
```
This makes about 56 API calls with a 4-second gap (free-tier friendly). It prints PASS/FAIL per test. **Failures are fine. Do not edit the results.** The guidelines say honest failures score better than a table where everything passes.
If you hit `429` errors, wait a minute and run `python3 code/run_experiments.py --only tests` (or `--only iterate`), then `python3 code/make_report.py`.

## 4. Push to GitHub (10 min)
Create a **public** repo `studymate-ai` on github.com (no README), then:
```bash
git init && git add . && git commit -m "Milestone 2: prompts v1-v3, Streamlit app, tests, report"
git branch -M main
git remote add origin https://github.com/<you>/studymate-ai.git
git push -u origin main
```
Check that `.streamlit/secrets.toml` is NOT in the repo (it's git-ignored). A visible key = 0 for the repository part.
Better still: have each member push their own part (prompts / app / tests / docs) from their own account, so the commits back up the contribution table.

## 5. Deploy the prototype (10 min)
share.streamlit.io → sign in with GitHub → **Create app** → repo `studymate-ai`, branch `main`, main file `code/app.py` → **Advanced settings → Secrets**:
```
GEMINI_API_KEY = "your-key"
```
Deploy. Then open the link **in an incognito window** and try every module: Explain, Summarize, Flashcards (open a card, download CSV), Quiz (answer, submit, see score), upload a text PDF, paste random characters (should show an error), Prompt Lab. If any module fails, mark it honestly in the module table (edit `MODULES` notes) and in Q19/Q20.

## 6. Screenshots (10 min)
From the deployed app, run the same inputs as tests T01, T04 and T13 (inputs are in `test-data/notes/photosynthesis.txt`, `newton.txt`, `gibberish.txt`, with count 5) and save the screenshots as:
- `docs/screenshots/T01.png`, `docs/screenshots/T04.png`, `docs/screenshots/T13.png`
- `docs/screenshots/repo.png`: your GitHub repo page

Put the 3 links + reel length into `team.json`, then run `python3 code/make_report.py` again, commit and push.

## 7. Record the reel: 90–150 s (30–40 min)
Screen recording (OBS / Kazam / phone) with voice-over or captions. Real run only.

| Time | Show | Say (roughly) |
|---|---|---|
| 0–12 s | App home | "Students revise from long notes. StudyMate AI turns your own notes into explanations, summaries, flashcards and quizzes, using only what's in the notes." |
| 12–50 s | **Prompt Lab** tab: paste `normalization.txt`, choose Flashcards, Run both versions | "Our first prompt was one line: 'make flashcards from this'. Look at the left: free text, N words, the app can't use it. The final prompt adds a tutor role, a JSON schema, an exact count, one worked example, temperature 0.2. Right side: exactly 5 cards, valid JSON." (read the real numbers from your iteration table) |
| 50–110 s | **Study** tab: upload/paste `newton.txt` → Quiz (5) → answer → Submit → score. Then paste `factual_error.txt` → Explain → show the warning. Then paste gibberish → error. | "Here it's running live on Gemini… it caught the false claim in the notes… and refuses non-study input instead of making things up." |
| 110–135 s | Test table / repo | "We tested 14 inputs, X passed; failures are listed with fixes. Milestone 3: OCR for scanned notes, saved decks and spaced repetition." |

Upload to Drive (Anyone with the link → Viewer) or YouTube (Unlisted). Note the **exact length in seconds**.

## 8. Final check, then submit the form (15 min)
- Run `python3 code/make_report.py` one last time. It must print **no "!" warnings**.
- Open `docs/M2_<TeamID>_StudyMateAI.pdf`: 7 sections, real model name, no "MISSING" boxes.
- Open all 3 links in incognito.
- Fill the form from `docs/form_answers.md`. Upload `docs/M2_....pdf` (Q21) and `docs/<TeamName>_TechnicalReport.pdf` (Q16).
- Team leader submits **once**.
