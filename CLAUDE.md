# StudyPilot - hackathon project (5-hour build, team of 4)

Streamlit app: student uploads course PDFs + weekly class schedule, picks a goal (exam/assignment, deadline, hours/week, target grade). The Claude API builds a tailored study plan (ordered sessions), a study guide + practice questions per session, and the sessions are placed in free slots of a weekly calendar. Quiz results feed back: weak topics (< 60%) get review sessions. The plan/guide/questions are the core; the calendar is supporting.

Full spec + per-member prompts: https://claude.ai/artifact/SGoHbBxyFJ9aTqBqrwzZ54 (Build kit tab)
Repo: https://github.com/ysdawson/StudyPilot

## Hard rules
- `core/contracts.py` is FROZEN. It defines every data shape (TypedDicts), every st.session_state key (K_* constants) and the mock helpers. Never change it; if something seems missing, tell the user so they can ask the team.
- Only edit the files owned by the member you're helping (table below). Never rewrite another member's file.
- Dates are strings in session_state: "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM". Ids: t1, s1, s1-q1, class-1, study-s1, deadline-1.
- Never hard-code the API key; read st.secrets["ANTHROPIC_API_KEY"]. `.streamlit/secrets.toml` is gitignored; never commit it.
- `MOCK_AI = "1"` in secrets -> ai_engine returns mock_data/ (no API spend). Only member 1 uses "0" while building. Budget: $50 shared key.
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
| 2 - Yassine, app + integration (current user) | app.py, pages/1_Plan.py, pages/2_Calendar.py, core/scheduler.py, core/schedule_input.py, tests/ | DONE and tested on mocks; now integration, deploy, polish |
| 3 - Session + quiz (non-technical, vibe codes) | pages/3_Session.py, core/quiz_logic.py, .streamlit/config.toml | placeholder page; grade() stub |
| 4 - Data + demo (non-technical) | mock_data/, sample_data/, check_mocks.py, slides | mocks done for "Circuit Analysis 1"; demo PDFs + slides TODO |

## Function interfaces (exact)
- core/llm.py: call_claude_json(system: str, content: str | list, max_tokens: int = 4000) -> dict | list  (cache in cache/, retry once on bad JSON)
- core/ai_engine.py: extract_text(pdf_bytes) -> str; extract_topics(doc_text) -> TopicsResult; make_plan(topics, goal) -> Plan; make_session(session, topics, doc_text) -> SessionContent; replan(plan, topics, results) -> Plan; parse_timetable_image(image_bytes, media_type, week_start) -> list[Event]
- core/scheduler.py: schedule_sessions(plan, busy, max_minutes_per_day=120, day_start="08:00", day_end="22:00") -> list[Event]; build_calendar(busy, study, deadlines, start_date, end_date) -> list[Event]
- core/schedule_input.py: schedule_input_ui(week_start) -> list[Event]
- core/quiz_logic.py: grade(questions, answers: dict[str, str], self_marked: dict[str, bool]) -> QuizResult

## Page flow
Home (app.py): upload -> extract_text -> K_DOC_TEXT -> extract_topics -> K_TOPICS; schedule_input_ui -> K_SCHEDULE; goal form -> K_GOAL; Generate -> make_plan -> K_PLAN -> schedule_sessions + build_calendar -> K_CALENDAR -> Plan page.
Plan: session cards; Open sets K_CURRENT -> pages/3_Session.py; "Update plan from my quiz results" -> replan -> reschedule.
Session (member 3): make_session if missing from K_CONTENT; guide + quiz; save -> grade -> K_RESULTS[sid].
Every page starts with: if K_PLAN not in st.session_state: load_mock_state(st) in mock mode, else st.info + st.stop().

## Timeline
0:20-2:30 build on mocks | 2:30 checkpoint + integrate | 3:30 FEATURE FREEZE | 3:30-4:15 test/fix | 4:15 record backup demo video | 4:30-5:00 rehearse.
Run the full demo once with the demo model before presenting so every AI result is cached (instant, free live demo). Don't delete cache/.
