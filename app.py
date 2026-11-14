"""OWNER: Member 2. Home: upload, schedule, goal, generate."""
from datetime import date, timedelta
import streamlit as st
from core.contracts import *
from core.ai_engine import extract_text, extract_topics, make_plan
from core.scheduler import schedule_sessions, build_calendar, all_deadlines, calendar_end
from core.schedule_input import (schedule_input_ui, deadlines_input_ui, goal_options, study_prefs_ui,
                                 schedule_kwargs, STUDY_PREFS_KEY)
from core.demo import load_demo_data, demo_picker, DATA_SOURCE_KEY, DEADLINES_KEY
from core.ai_engine import AIConfigError
from core.llm import api_key_configured

st.set_page_config(page_title="StudyPilot", layout="wide")
st.title("StudyPilot")
st.write("Upload your course material and schedule. Get a tailored study plan with guides and practice questions, placed in your week.")
st.caption("Demo data loads instantly (no API spend). Your own uploads are analyzed by Claude"
           + ("." if api_key_configured() else " — but AI is not configured on this server."))

demo_choice = demo_picker(st, st.sidebar, key="demo_pick_home")
if st.sidebar.button("Load demo data"):
    load_demo_data(st, demo_choice)
    st.switch_page("pages/1_Plan.py")

today = date.today()
next_monday = today + timedelta(days=(7 - today.weekday()) % 7)

# Step 1: documents
st.header("1. Your course material")
files = st.file_uploader("Course outline, slides, notes (PDF)", type=["pdf"], accept_multiple_files=True)
if files and st.button("Analyze my documents", type="primary"):
    st.session_state[DATA_SOURCE_KEY] = "user"  # the user's own material: always the real AI
    try:
        with st.spinner("Reading your documents..."):
            text = "\n\n".join(f"=== {f.name} ===\n" + extract_text(f.getvalue()) for f in files)
            topics_result = extract_topics(text)
        st.session_state[K_DOC_TEXT] = text
        st.session_state[K_TOPICS] = topics_result
    except AIConfigError as ex:
        st.error(str(ex))
    except Exception as ex:
        st.error(f"Couldn't analyze the documents: {ex}")

topics = st.session_state.get(K_TOPICS)
if topics:
    st.success(f"Found {len(topics['topics'])} topics in {topics['course']}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Topics**")
        for t in topics["topics"]:
            st.markdown(f"- {t['name']} ({round(t['weight'] * 100)}%)")
    with c2:
        st.markdown("**Deadlines**")
        for d in topics["deadlines"]:
            st.markdown(f"- {d['title']}: {d['date']}")

# Step 2: schedule
st.header("2. Your weekly schedule")
st.caption("Classes and commitments repeat every week. Study sessions will be placed around them.")
# Only saved to K_SCHEDULE when a plan is generated: the editor's example rows
# must not become the student's timetable (or a calendar) on their own.
schedule = schedule_input_ui(next_monday.isoformat())
course_deadlines = deadlines_input_ui()
study_prefs = study_prefs_ui()

# Step 3: goal + generate
st.header("3. Your goal")
if not topics:
    st.info("Analyze your documents first (step 1), or click 'Load demo data' in the sidebar.")
    st.stop()

deadlines = topics["deadlines"]
course = st.text_input("Course", topics["course"], key="goal_course")
goal_opts = goal_options(topics, st.session_state.get(DEADLINES_KEY, []))
labels = [o[0] for o in goal_opts]
choice = st.selectbox("What are you studying for?", labels, key="goal_choice")
_, chosen_title, chosen_day = goal_opts[labels.index(choice)]
other = st.text_input("Type what you are studying for", key="goal_other") if not chosen_title else ""
known = date.fromisoformat(chosen_day) if chosen_day else None
deadline = st.date_input(
    "Deadline" + ("" if known and known > today else " — pick the date yourself (not found in the documents)"),
    value=known if known and known > today else None, min_value=today + timedelta(days=1),
    key=f"goal_date_{labels.index(choice)}")  # new key per choice: shows that choice's date
hours = st.slider("Hours per week you can study", 2, 20, 6)
grade = "A"  # target grade is no longer asked; Goal.target_grade keeps a fixed default
go = st.button("Generate my plan", type="primary")

if go and deadline is None:
    st.error("Pick your deadline date first: it wasn't found in the documents.")
    go = False
if go:
    target = (other.strip() or "Exam") if not chosen_title else chosen_title
    goal: Goal = {"course": course, "target": target, "deadline": deadline.isoformat(),
                  "start_date": today.isoformat(), "hours_per_week": float(hours), "target_grade": grade}
    try:
        with st.spinner("Building your study plan..."):
            plan = make_plan(topics, goal)
        st.session_state[STUDY_PREFS_KEY] = study_prefs
        from core.board import task_events, TASKS_KEY  # the student's own blocking tasks
        busy = schedule + task_events(st.session_state.get(TASKS_KEY, []), blocking_only=True)
        study = schedule_sessions(plan, busy, **schedule_kwargs(study_prefs))
        st.session_state[K_SCHEDULE] = schedule
        st.session_state[K_GOAL] = goal
        st.session_state[K_PLAN] = plan
        marks = all_deadlines(deadlines, course_deadlines, goal)
        st.session_state[K_CALENDAR] = build_calendar(schedule, study, marks, goal["start_date"],
                                                      calendar_end(goal, marks))
        # New plan: session ids restart at s1, so drop guides/results of any old plan.
        st.session_state[K_CONTENT] = {}
        st.session_state[K_RESULTS] = {}
        st.session_state[K_CURRENT] = plan["sessions"][0]["id"]
        if len(study) < len(plan["sessions"]):
            st.warning(f"Only {len(study)} of {len(plan['sessions'])} sessions fit before the deadline.")
        st.switch_page("pages/1_Plan.py")
    except AIConfigError as ex:
        st.error(str(ex))
    except Exception as ex:
        st.error(f"Couldn't build the plan: {ex}")
