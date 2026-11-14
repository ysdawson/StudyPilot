"""OWNER: Member 2. Calendar page."""
import streamlit as st
from core.contracts import *
from core.demo import load_demo_data

if K_PLAN not in st.session_state:
    st.info("No study plan yet. Generate one on the Home page, or load the demo.")
    c1, c2 = st.columns(2)
    if c1.button("Go to Home"):
        st.switch_page("app.py")
    if c2.button("Load demo data"):
        load_demo_data(st)
        st.rerun()
    st.stop()

COLORS = {"class": "#9aa0a6", "busy": "#9aa0a6", "study": "#1a73e8", "deadline": "#d93025"}
events = [{"title": e["title"], "start": e["start"], "end": e["end"],
           "color": COLORS.get(e["kind"], "#1a73e8"), "id": e["id"]} for e in st.session_state.get(K_CALENDAR, [])]

st.title("Your week")
try:
    from streamlit_calendar import calendar
    calendar(events=events, options={
        "initialView": "timeGridWeek", "initialDate": st.session_state[K_PLAN]["goal"]["start_date"],
        "slotMinTime": "08:00:00", "slotMaxTime": "22:00:00", "allDaySlot": False, "height": 700,
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "timeGridWeek,dayGridMonth"},
    }, key="cal")
except ImportError:
    st.warning("Install streamlit-calendar for the calendar view. Showing a list instead.")
    st.dataframe(events, width="stretch")
st.caption("Grey: classes · Blue: study sessions · Red: deadlines")
