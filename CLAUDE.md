# StudyPilot - hackathon project (5-hour build, team of 4)

Streamlit app: student uploads course PDFs + weekly class schedule, picks a goal (exam/assignment, deadline, hours/week, target grade). The Claude API builds a tailored study plan (ordered sessions), a study guide + practice questions per session, and the sessions are placed in free slots of a weekly calendar. Quiz results feed back: weak topics (< 60%) get review sessions. The plan/guide/questions are the core; the calendar is supporting.

Full spec + per-member prompts: https://claude.ai/artifact/SGoHbBxyFJ9aTqBqrwzZ54 (Build kit tab)
Repo: https://github.com/ysdawson/StudyPilot

## Hard rules
- `core/contracts.py` is FROZEN. It defines every data shape (TypedDicts), every st.session_state key (K_* constants) and the mock helpers. Never change it; if something seems missing, tell the user so they can ask the team.
- Only edit the files owned by the member you're helping (table below). Never rewrite another member's file.
- Dates are strings in session_state: "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM". Ids: t1, s1, s1-q1, class-1, study-s1, deadline-1.
- Never hard-code the API key; read st.secrets["ANTHROPIC_API_KEY"]. `.streamlit/secrets.toml` is gitignored; never commit it.
- `MOCK_AI = "1"` in secrets -> ai_engine functions return the SELECTED demo dataset in mock_data/<dataset>/ (no API spend). It does NOT pre-fill session_state. Only member 1 uses "0" while building. Budget: $50 shared key.
- PRIVACY: private_data/ is gitignored and must never be committed (course outlines with teacher contact details, real names). Mock data and citations must not contain teacher names or contact details.
- Wrap every AI call in st.spinner + try/except with st.error so the demo never crashes.
- Prefer simple, working code. Feature freeze at 3:30 into the hackathon.

## Run (Windows)
    py -m pip install -r requirements.txt
    py -m streamlit run app.py
    py -m pytest -q tests

## Ownership
| Member | Files | Status |
|---|---|---|
| 1 - AI engine (Python) | core/llm.py, core/prompts.py, core/ai_engine.py, test_engine.py | llm.py stub; ai_engine mock mode works, real mode TODO |
| 2 - Yassine, app + integration (current user) | app.py, pages/1_Plan.py, pages/2_Calendar.py, core/scheduler.py, core/schedule_input.py, core/demo.py, core/board.py, tests/ | DONE and tested on mocks; now integration, deploy, polish |
| 3 - Session + quiz (non-technical, vibe codes) | pages/3_Session.py, core/quiz_logic.py, .streamlit/config.toml | placeholder page; grade() stub |
| 4 - Data + demo (non-technical) | mock_data/, sample_data/, check_mocks.py, slides | mocks done for "Circuit Analysis 1"; demo PDFs + slides TODO |

## Function interfaces (exact)
- core/llm.py: call_claude_json(system: str, content: str | list, max_tokens: int = 4000) -> dict | list  (cache in cache/, retry once on bad JSON)
- core/ai_engine.py: extract_text(pdf_bytes) -> str; extract_topics(doc_text) -> TopicsResult; make_plan(topics, goal) -> Plan; make_session(session, topics, doc_text) -> SessionContent; replan(plan, topics, results) -> Plan; parse_timetable_image(image_bytes, media_type, week_start) -> list[Event]
- core/scheduler.py: schedule_sessions(plan, busy, max_minutes_per_day=120, day_start="08:00", day_end="22:00") -> list[Event]; build_calendar(busy, study, deadlines, start_date, end_date) -> list[Event]
- core/schedule_input.py: schedule_input_ui(week_start) -> list[Event]
- core/quiz_logic.py: grade(questions, answers: dict[str, str], self_marked: dict[str, bool]) -> QuizResult

## Page flow
Home (app.py): upload -> extract_text -> K_DOC_TEXT -> extract_topics -> K_TOPICS; schedule_input_ui (editor only); goal form; Generate -> K_SCHEDULE + K_GOAL -> make_plan -> K_PLAN -> schedule_sessions + build_calendar -> K_CALENDAR (K_CONTENT/K_RESULTS reset) -> Plan page.
Plan: session cards; Open sets K_CURRENT -> pages/3_Session.py; "Update plan from my quiz results" -> replan -> reschedule.
Session (member 3): make_session if missing from K_CONTENT; guide + quiz; save -> grade -> K_RESULTS[sid].
Every page starts with (also in mock mode, no auto-loading):
    if K_PLAN not in st.session_state:
        st.info("No study plan yet. Generate one on the Home page, or load the demo.")
        c1, c2 = st.columns(2)
        if c1.button("Go to Home"): st.switch_page("app.py")
        choice = demo_picker(st, c2, key="demo_pick_<page>")
        if c2.button("Load demo data"): load_demo_data(st, choice); st.rerun()
        st.stop()
Demo data is loaded ONLY by a "Load demo data" button (Home sidebar + the pages above), via core/demo.py load_demo_data(st, dataset), which clears ALL app state first. Nothing writes K_PLAN, K_CALENDAR or K_SCHEDULE on startup. load_mock_state / load_mock in contracts.py are no longer used (they read the old flat mock_data/).

## Demo datasets (core/demo.py)
- Two datasets, each a full folder: mock_data/yassine/ (default: "1 — My real term (Network Applications I)", goal Class Test 4 on 2026-11-26, 10 classes, 10 course deadlines) and mock_data/calculus/ ("2 — Calculus I Test 1", 13 classes + 2 work shifts, no course deadlines). Files: topics.json, plan.json, session_*.json, schedule.json, calendar.json, deadlines.json.
- The selected dataset is st.session_state["demo_dataset"] (DATASET_KEY), set only when "Load demo data" is clicked. NEVER use a module-level global for it (Streamlit Cloud shares globals between visitors). The picker selectbox has its own widget key per page.
- Mock-mode AI functions read via demo.load_mock(st, filename) from the selected dataset.
- Course deadlines: st.session_state["course_deadlines"] (demo.DEADLINES_KEY, owned by Home / core/schedule_input.py), a list of {course, title, date, weight, source}. Upload on Home: "Upcoming deadlines (CSV)" with Course,Title,Date,Weight,Source. They go to build_calendar via scheduler.all_deadlines (titled "<Course>: <Title>", plus the goal unless already there); the calendar runs to calendar_end(goal, deadlines). Deadlines are markers only, never block study time, and their Source (e.g. "day estimated") is always shown with them.

## Timeline
0:20-2:30 build on mocks | 2:30 checkpoint + integrate | 3:30 FEATURE FREEZE | 3:30-4:15 test/fix | 4:15 record backup demo video | 4:30-5:00 rehearse.
Run the full demo once with the demo model before presenting so every AI result is cached (instant, free live demo). Don't delete cache/.
