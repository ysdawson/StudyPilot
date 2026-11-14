# StudyPilot

**Upload your course material and your timetable; get a study plan that fits your real week, with a study guide and a practice quiz for every session, which adapts to your quiz results.**

**Live app:** https://studypilot-hackathon.streamlit.app/

## Team

| Member | Role |
|---|---|
| Ylan Sabardeil | AI engine |
| Yassine Semraoui | App and integration |
| Ayyoub Oberoi | Study and quiz pages |
| Yaqoub Oberoi | Demo data, testing and pitch |

## The problem

Students get a course outline or a pile of lecture slides, a deadline, and a timetable that is already full of classes, labs and a part-time job. Turning that into "what do I study, when, and am I actually ready?" is slow and usually skipped. Generic planners don't know the course material, and generic AI chats don't know the student's week or remember what they got wrong.

## The solution

StudyPilot does the whole loop in one place:

1. **Understand the material.** It reads the uploaded PDFs and extracts the course, its main topics (with weights), the assessments, and any deadline that is actually written in the documents. It never invents a date.
2. **Plan.** For a goal (e.g. "Class Test 4" on a date the student picks) and the hours per week available, it builds an ordered list of study sessions: learn, then practice, then review, following the order the course teaches.
3. **Place it in the real week.** Sessions go into free time around classes, work shifts and the student's own tasks, with a 15-minute buffer, a daily cap, only on the days and hours the student says they can study, and spread out up to the deadline.
4. **Study and test.** Each session has a short study guide (key points, explanation, worked example, where to look in the material) and a multiple-choice quiz. Maths is rendered with LaTeX.
5. **Adapt.** Quiz results are graded per topic; any topic under 60% gets an extra review session, and the calendar is rescheduled.

Dates that come from estimates (e.g. "due day estimated" in a deadlines file) are always shown with that note, so an estimate is never presented as official.

## How to use it

**Fastest: demo data.** In the sidebar of the Home page, pick a dataset and click **Load demo data**:
- *1 — My real term (Network Applications I)*: a real college term with 10 classes, 10 course deadlines and a plan for Class Test 4.
- *2 — Calculus I Test 1*: 8 calculus lectures, a timetable with classes and work shifts, and a plan for Test 1.

Demo data loads instantly and makes no API calls. Then explore **Plan** (open a session), **Session** (study guide and quiz; save your results), back to **Plan** ("Update plan from my quiz results" adds review sessions), and **Calendar** (week board or time grid, "Up next", deadline countdowns, "Add my own task").

**Your own course.** On Home:
1. Upload your PDFs (outline, slides, notes) and click **Analyze my documents** (this uses the Claude API).
2. Enter your weekly timetable in the table, or upload it as a CSV (`Day,Date,Start,End,Activity,Type`, Type = Class or Work) or as a screenshot (read by Claude).
3. Optionally upload your upcoming deadlines for all courses (`Course,Title,Date,Weight,Source`).
4. Set when you can study (a Mon–Sun table of days and hours).
5. Choose what you are studying for, pick the deadline date and your hours per week, and click **Generate my plan**.

Sample files are in `sample_data/calculus/` and `sample_data/yassine/`.

## Run it locally (Windows)

    py -m pip install -r requirements.txt
    copy .streamlit\secrets.toml.example .streamlit\secrets.toml
    py -m streamlit run app.py

Edit `.streamlit/secrets.toml` and set `ANTHROPIC_API_KEY` to your key (`CLAUDE_MODEL` picks the model). Without a key the demo datasets still work fully; uploads of your own files then show "AI is not configured" instead of fake results. Never commit `secrets.toml`.

Tests (they never call the real API):

    py -m pytest -q tests

## Tech stack

- **Python 3.13** and **Streamlit 1.67** (multipage app, session state, `st.data_editor`, custom CSS for the week board)
- **Anthropic Claude API** (Claude Haiku during development; model set in secrets) for all AI steps
- **PyMuPDF** for PDF text extraction
- **streamlit-calendar** (FullCalendar) for the time-grid view
- **pytest** with Streamlit's `AppTest` for page-level tests

## Third-party tools vs. what we built

**Third-party:** Streamlit, streamlit-calendar (FullCalendar), PyMuPDF, the Anthropic Python SDK and the Claude API, pandas (via Streamlit), pytest.

**Built by us during the hackathon:**
- **Data contracts** (`core/contracts.py`): every data shape and session-state key the team shared.
- **AI engine**: prompts for topics, plans, study sessions, replanning and timetable images; validation that turns model output into the contract shapes (drops malformed questions, never keeps invented dates, keeps the student's own goal); response caching and JSON retry.
- **Scheduler**: places sessions in free time with buffers, daily caps, per-day availability, spreading to the deadline, one-off tasks and weekly classes; builds the calendar with deadlines.
- **Pages**: Home, Plan, Session and Calendar, including the week board, "Up next", countdowns and own tasks.
- **Demo datasets** generated with the app's own code and hand-checked.
- **Tests**: 60 automated tests covering the scheduler, grading, imports, both demo datasets and full click-throughs of the pages.

## AI use

- **Claude (Anthropic API)** is the AI inside the product: it extracts topics and assessments from documents, writes the study plan, generates study guides and quizzes, adds review sessions from quiz results, and reads timetable screenshots. All model output is validated in code before it is used. The demo datasets were generated by the app itself in real mode, and every quiz answer in them was checked during the build (with Claude Code); the few uncertain items were noted.
- **Claude Code** was used as a coding assistant to build and integrate the app: writing and refactoring code, writing tests, running the test suite and click-throughs, and preparing commits. The team decided the features, priorities and timeboxes, and reviewed the results.
- **Gemini** was used by a team member to draft a visual redesign of the Session page; its visual elements were merged into `pages/3_Session.py`, while the app's own logic and grading were kept.

Privacy: a real course outline used to build the first dataset contains teacher contact details. It stays in `private_data/`, which is git-ignored, and no names or contact details appear in the committed data.

## Code tour

**Entry and pages**
- `app.py`: Home page: upload and analyze documents, timetable editor, deadlines CSV, study availability, goal and **Generate my plan**; the sidebar demo picker.
- `pages/1_Plan.py`: the plan as session cards with progress; Open a session; **Update plan from my quiz results** (replan and reschedule).
- `pages/2_Calendar.py`: week board (cards per day, course colours, Up next, countdowns, week progress, Add my own task) and the FullCalendar time grid.
- `pages/3_Session.py`: one session: study guide tab and multiple-choice quiz with answer review, per-topic scores and adaptive-review hint.

**core/**
- `core/contracts.py`: the shared data shapes (TypedDicts) and session-state keys; frozen during the hackathon.
- `core/llm.py`: Claude API access: lazy client, JSON parsing with one retry, caching of responses in `cache/`.
- `core/prompts.py`: the system prompts for topics, plan, session, replan and timetable images.
- `core/ai_engine.py`: the AI functions the pages call; validates and normalizes model output; uses demo data only for loaded demos and the real API for the user's own files.
- `core/scheduler.py`: places study sessions in free time (buffers, daily cap, availability, spreading) and builds the calendar with classes, tasks and deadlines.
- `core/schedule_input.py`: Home's timetable editor, CSV and image import, deadlines CSV, goal choices and the study-availability table.
- `core/board.py`: pure helpers for the Calendar week board: course colours, events per day, Up next, countdowns, own tasks.
- `core/demo.py`: the two demo datasets in `mock_data/<dataset>/` and the **Load demo data** logic (clears all state, then loads one dataset).
- `core/quiz_logic.py`: grades a quiz into per-question results, a score and per-topic scores.

**Other:** `tests/` (pytest + AppTest; `conftest.py` blocks real API calls), `mock_data/` (the two demo datasets), `sample_data/` (demo PDFs, timetables and deadlines), `test_engine.py` (manual end-to-end check of the AI engine).
